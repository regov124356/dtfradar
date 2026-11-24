"""DtfRadar - analiza rynku koszulek z nadrukiem DTF na Allegro.

Komendy:
    python dtfradar.py fetch              pobierz migawke ofert (produkcja)
    python dtfradar.py fetch --sandbox    pobierz z sandboxa Allegro (dane testowe)
    python dtfradar.py fetch --demo       wygeneruj dane DEMO (bez API)
    python dtfradar.py report             raport HTML z ostatniej migawki
    python dtfradar.py runs               lista migawek

Sprzedane sztuki liczone sa z roznicy stanow miedzy migawkami,
wiec uruchamiaj fetch regularnie (np. co 3-7 dni).
"""

import argparse
import os
import sys
import webbrowser
from datetime import datetime, timedelta

from radar import analysis, config, demo, report
from radar.allegro import AllegroClient, AllegroError, normalize_offer
from radar.storage import Storage

OFFER_URLS = {
    "prod": "https://allegro.pl/oferta/{}",
    "sandbox": "https://allegro.pl.allegrosandbox.pl/oferta/{}",
    "demo": "https://allegro.pl/oferta/{}",
}


def cmd_fetch(args, cfg, db):
    if args.demo:
        return fetch_demo(args, cfg, db)

    client_id, secret = config.credentials(args.sandbox)
    if not client_id or not secret:
        name = "ALLEGRO_SANDBOX_CLIENT_ID / ALLEGRO_SANDBOX_CLIENT_SECRET" if args.sandbox \
            else "ALLEGRO_CLIENT_ID / ALLEGRO_CLIENT_SECRET"
        sys.exit(f"Brak kluczy w .env: {name}")

    env = "sandbox" if args.sandbox else "prod"
    client = AllegroClient(client_id, secret, config.user_agent(), sandbox=args.sandbox)
    try:
        client.token()
    except AllegroError as e:
        sys.exit(f"Nie udalo sie pobrac tokenu ({e.status}). Sprawdz klucze w .env.\n{e.body}")

    run_id = db.new_run(env)
    max_pages = args.max_pages or cfg.get("max_pages", 10)
    total = 0
    for phrase in cfg["phrases"]:
        meta_saved = False
        for sort in cfg.get("sorts", ["relevance"]):
            got = 0
            try:
                for page, total_count in client.search(phrase, cfg.get("category_id"), sort, max_pages):
                    offers = [normalize_offer(o, promoted) for o, promoted in page]
                    db.add_offers(run_id, phrase, sort, offers)
                    got += len(offers)
                    if not meta_saved:
                        db.add_meta(run_id, phrase, total_count)
                        meta_saved = True
            except AllegroError as e:
                if e.status == 403:
                    db.delete_run(run_id)
                    sys.exit("HTTP 403: aplikacja nie ma dostepu do /offers/listing "
                             "(wymagana weryfikacja przez Allegro). Migawka niezapisana.")
                if e.status in (400, 422):
                    print(f"  [pomijam] sort={sort}: Allegro odrzucilo parametr ({e.status})")
                    continue
                raise
            print(f"  {phrase!r:32} sort={sort:12} ofert: {got}")
            total += got
    db.finish_run(run_id)
    print(f"Migawka #{run_id} ({env}) zapisana: {total} ofert (z duplikatami).")


def fetch_demo(args, cfg, db):
    prev_runs = db.runs("demo")
    if prev_runs and not args.fresh:
        prev = prev_runs[-1]
        prev_time = datetime.fromisoformat(prev["started_at"])
        started = prev_time + timedelta(days=args.days)
        offers = db.offers(prev["id"])
        run_id = db.new_run("demo", started)
        by_phrase = {}
        for o in demo.next_snapshot(offers, args.days, seed=args.seed):
            by_phrase.setdefault((o["phrase"], o["sort"]), []).append(o)
        for (phrase, sort), items in by_phrase.items():
            db.add_offers(run_id, phrase, sort, items)
        for m in db.meta(prev["id"]):
            db.add_meta(run_id, m["phrase"], m["total_count"])
        print(f"Migawka DEMO #{run_id}: kolejna po #{prev['id']}, +{args.days} dni.")
    else:
        run_id = db.new_run("demo", datetime.now() - timedelta(days=args.days) if args.fresh else None)
        for phrase, (offers, total_count) in demo.generate(cfg["phrases"], seed=args.seed).items():
            db.add_offers(run_id, phrase, "relevance", offers)
            db.add_meta(run_id, phrase, total_count)
        print(f"Migawka DEMO #{run_id}: nowe dane losowe.")
    db.finish_run(run_id)


def cmd_report(args, cfg, db):
    if args.run:
        run = db.run(args.run)
    else:
        runs = db.runs()
        run = runs[-1] if runs else None
    if not run:
        sys.exit("Brak migawek. Najpierw: python dtfradar.py fetch")

    same_env = db.runs(run["env"])
    offers = db.offers(run["id"])
    a = analysis.analyze(offers, db.meta(run["id"]), cfg)

    earlier = [r for r in same_env if r["id"] < run["id"]]
    a["stock_sales"] = None
    if earlier:
        prev = earlier[-1]
        days = (datetime.fromisoformat(run["started_at"])
                - datetime.fromisoformat(prev["started_at"])).total_seconds() / 86400
        if days >= 0.5:
            a["stock_sales"] = analysis.stock_sales(db.offers(prev["id"]), offers, days)

    pr = analysis.profitability(a, cfg)
    verdict = analysis.verdict(a, pr, cfg)

    history = []
    for r in same_env:
        if r["id"] > run["id"]:
            break
        ha = a if r["id"] == run["id"] else analysis.analyze(db.offers(r["id"]), db.meta(r["id"]), cfg)
        history.append({"date": r["started_at"][:10], "median": ha["price"][50], "sellers": ha["sellers"]})

    url_tpl = OFFER_URLS.get(run["env"], OFFER_URLS["prod"])
    html = report.render(run, a, pr, verdict, cfg, history, url_tpl.format)
    out = os.path.abspath(args.out)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)

    label, score, reasons = verdict
    print(f"Migawka #{run['id']} ({run['env']}): {a['offers']} ofert, {a['sellers']} sprzedawcow, "
          f"mediana {a['price'][50]:.2f} zl" if a["offers"] else "Brak ofert.")
    print(f"Werdykt: {label.upper()} (punkty {score})")
    for r in reasons:
        print("  " + r)
    print(f"Raport: {out}")
    if args.open:
        webbrowser.open("file://" + out)


def cmd_runs(args, cfg, db):
    runs = db.runs()
    if not runs:
        print("Brak migawek.")
    for r in runs:
        print(f"#{r['id']:<4} {r['started_at']}  {r['env']:8} ofert: {db.count_offers(r['id'])}")


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except AttributeError:
        pass
    config.load_dotenv()

    p = argparse.ArgumentParser(description="DtfRadar - analiza rynku koszulek DTF na Allegro")
    p.add_argument("--config", default=os.path.join(config.ROOT, "config.json"))
    p.add_argument("--db", default=config.DEFAULT_DB)
    sub = p.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch", help="pobierz migawke ofert")
    f.add_argument("--sandbox", action="store_true", help="srodowisko testowe Allegro")
    f.add_argument("--demo", action="store_true", help="dane DEMO bez API")
    f.add_argument("--max-pages", type=int, help="limit stron na fraze i sortowanie (test)")
    f.add_argument("--days", type=float, default=7, help="DEMO: odstep od poprzedniej migawki")
    f.add_argument("--fresh", action="store_true", help="DEMO: nowe dane zamiast kolejnej migawki")
    f.add_argument("--seed", type=int, help="DEMO: ziarno losowania")

    r = sub.add_parser("report", help="raport HTML")
    r.add_argument("--run", type=int, help="numer migawki (domyslnie ostatnia)")
    r.add_argument("--out", default=os.path.join(config.ROOT, "raport.html"))
    r.add_argument("--open", action="store_true", help="otworz raport w przegladarce")

    sub.add_parser("runs", help="lista migawek")

    args = p.parse_args()
    cfg = config.load_config(args.config)
    db = Storage(args.db)
    {"fetch": cmd_fetch, "report": cmd_report, "runs": cmd_runs}[args.cmd](args, cfg, db)


if __name__ == "__main__":
    main()
