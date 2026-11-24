"""Raport HTML (jeden plik, dziala offline, wykresy jako SVG)."""

import math
from html import escape

CSS = """
:root{color-scheme:light;--bg:#fcfcfb;--card:#ffffff;--text:#0b0b0b;--muted:#52514e;
--faint:#8a8984;--grid:#e6e5e1;--s1:#2a78d6;--neg:#e34948;--ok:#008300;--warn:#b87d00;--bad:#c83232}
@media (prefers-color-scheme:dark){:root{color-scheme:dark;--bg:#1a1a19;--card:#232322;
--text:#f0efec;--muted:#c3c2b7;--faint:#8f8e88;--grid:#3a3a38;--s1:#3987e5;--neg:#e66767;
--ok:#0ca30c;--warn:#c98500;--bad:#e66767}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 20px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:36px 0 12px}
.sub{color:var(--muted);margin:0 0 24px}
.banner{padding:10px 14px;border-radius:8px;margin-bottom:20px;font-weight:600;
background:color-mix(in srgb,var(--warn) 18%,transparent);border:1px solid var(--warn)}
.verdict{background:var(--card);border:1px solid var(--grid);border-radius:12px;padding:20px 24px}
.verdict .label{font-size:28px;font-weight:700;text-transform:uppercase;letter-spacing:.02em}
.verdict ul{margin:12px 0 0;padding-left:0;list-style:none}.verdict li{margin:4px 0}
.v-warto{color:var(--ok)}.v-ryzykowne{color:var(--warn)}.v-nie{color:var(--bad)}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-top:16px}
.tile{background:var(--card);border:1px solid var(--grid);border-radius:10px;padding:14px 16px}
.tile .k{color:var(--muted);font-size:13px}.tile .v{font-size:24px;font-weight:650;font-variant-numeric:tabular-nums}
.card{background:var(--card);border:1px solid var(--grid);border-radius:12px;padding:16px 20px}
.note{color:var(--muted);font-size:13px;margin-top:8px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums;font-size:14px}
th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid)}
th{color:var(--muted);font-weight:600}td.n,th.n{text-align:right}
.neg{color:var(--bad)}a{color:var(--s1)}
svg text{fill:var(--muted);font-size:12px}svg .val{fill:var(--text)}
svg .bar{fill:var(--s1)}svg .bar.neg{fill:var(--neg)}svg .bar:hover{opacity:.8}
svg .grid{stroke:var(--grid)}svg .ref{stroke:var(--text);stroke-dasharray:4 3}
svg .line{fill:none;stroke:var(--s1);stroke-width:2}svg .dot{fill:var(--s1);stroke:var(--card);stroke-width:2}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media(max-width:760px){.two{grid-template-columns:1fr}}
"""


def zl(v, sign=False):
    if v is None:
        return "–"
    s = f"{v:+,.2f}" if sign else f"{v:,.2f}"
    return s.replace(",", " ").replace("-", "−") + " zł"


def num(v, digits=0):
    if v is None:
        return "–"
    return f"{v:,.{digits}f}".replace(",", " ")


def _bar_path(x, y, w, h, r=4, side="top"):
    """Prostokat z zaokraglonym koncem danych (gora albo prawa strona)."""
    r = max(0, min(r, w / 2, h / 2))
    if side == "top":
        return (f"M{x},{y+h}V{y+r}Q{x},{y} {x+r},{y}H{x+w-r}Q{x+w},{y} {x+w},{y+r}V{y+h}Z")
    if side == "left":
        return (f"M{x+w},{y}H{x+r}Q{x},{y} {x},{y+r}V{y+h-r}Q{x},{y+h} {x+r},{y+h}H{x+w}Z")
    return (f"M{x},{y}H{x+w-r}Q{x+w},{y} {x+w},{y+r}V{y+h-r}Q{x+w},{y+h} {x+w-r},{y+h}H{x}Z")


def histogram(prices, median, break_even):
    if not prices:
        return "<p class='note'>Brak cen.</p>"
    lo = math.floor(min(prices) / 10) * 10
    cap = math.ceil(sorted(prices)[int(len(prices) * 0.95) - 1 if len(prices) > 1 else 0] / 10) * 10
    cap = max(cap, lo + 10)
    edges = list(range(lo, cap + 1, 10))
    counts = [0] * len(edges)  # ostatni kubelek = >= cap
    for p in prices:
        i = min(int((p - lo) // 10), len(edges) - 1)
        counts[i] += 1
    W, H, L, B, T = 960, 280, 44, 34, 28
    pw, ph = W - L - 12, H - B - T
    bw = pw / len(counts)
    ymax = max(counts) or 1
    step = max(1, 10 ** int(math.log10(ymax)) if ymax >= 10 else 1)
    while ymax / step > 5:
        step *= 2
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Rozkład cen ofert">']
    y = 0
    while y <= ymax:
        yy = T + ph - y / ymax * ph
        out.append(f'<line class="grid" x1="{L}" x2="{W-12}" y1="{yy:.1f}" y2="{yy:.1f}"/>'
                   f'<text x="{L-6}" y="{yy+4:.1f}" text-anchor="end">{y}</text>')
        y += step
    for i, c in enumerate(counts):
        x = L + i * bw + 1
        h = c / ymax * ph
        label = f"{edges[i]}–{edges[i]+10} zł" if i < len(counts) - 1 else f"≥ {edges[i]} zł"
        if c:
            out.append(f'<path class="bar" d="{_bar_path(x, T+ph-h, bw-2, h)}"><title>{label}: {c} ofert</title></path>')
        if len(counts) <= 16 or i % 2 == 0:
            out.append(f'<text x="{x+bw/2-1:.1f}" y="{H-B+16}" text-anchor="middle">'
                       f'{edges[i] if i < len(counts)-1 else "≥"+str(edges[i])}</text>')

    def ref(value, text, dy):
        if value is None or value < lo or value > cap + 10:
            return ""
        x = L + (value - lo) / 10 * bw
        return (f'<line class="ref" x1="{x:.1f}" x2="{x:.1f}" y1="{T-4}" y2="{T+ph}"/>'
                f'<text class="val" x="{x+4:.1f}" y="{T+dy}">{text}</text>')
    out.append(ref(median, f"mediana {zl(median)}", 6))
    out.append(ref(break_even, f"Twój próg {zl(break_even)}", 22))
    out.append(f'<text x="{L}" y="{H-2}">cena (zł, bez dostawy)</text></svg>')
    return "".join(out)


def hbars(rows, value_key, label_key, fmt, signed=False):
    """Poziome slupki. rows: lista dictow. Ujemne wartosci rysowane na czerwono w lewo od zera."""
    if not rows:
        return "<p class='note'>Brak danych.</p>"
    W, rowh, L, R = 960, 30, 190, 110
    H = rowh * len(rows) + 10
    vals = [r[value_key] for r in rows]
    vmin = min(0, min(vals)) if signed else 0
    vmax = max(0, max(vals)) or 1
    span = (vmax - vmin) or 1
    pw = W - L - R
    x0 = L + (-vmin) / span * pw
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img">']
    if signed and vmin < 0:
        out.append(f'<line class="grid" x1="{x0:.1f}" x2="{x0:.1f}" y1="0" y2="{H}"/>')
    for i, r in enumerate(rows):
        v = r[value_key]
        y = 5 + i * rowh
        w = abs(v) / span * pw
        neg = v < 0
        x = x0 - w if neg else x0
        cls = "bar neg" if neg else "bar"
        name = escape(str(r[label_key]))[:28]
        out.append(f'<text x="{L-8}" y="{y+rowh/2+4:.1f}" text-anchor="end">{name}</text>')
        if w > 0:
            out.append(f'<path class="{cls}" d="{_bar_path(x, y+4, w, rowh-10, side="left" if neg else "right")}">'
                       f'<title>{name}: {escape(fmt(v))}</title></path>')
        tx = x - 6 if neg else x + w + 6
        out.append(f'<text class="val" x="{tx:.1f}" y="{y+rowh/2+4:.1f}" '
                   f'text-anchor="{"end" if neg else "start"}">{escape(fmt(v))}</text>')
    out.append("</svg>")
    return "".join(out)


def line_chart(points, title, fmt):
    """points: lista (etykieta_x, wartosc). Jedna seria, bez legendy - tytul ja nazywa."""
    W, H, L, B, T = 470, 200, 56, 30, 16
    pw, ph = W - L - 16, H - B - T
    vals = [v for _, v in points]
    lo, hi = min(vals), max(vals)
    if hi == lo:
        lo, hi = lo * 0.9, hi * 1.1 or 1
    pad = (hi - lo) * 0.1
    lo, hi = lo - pad, hi + pad
    def X(i):
        return L + (i / (len(points) - 1) * pw if len(points) > 1 else pw / 2)
    def Y(v):
        return T + ph - (v - lo) / (hi - lo) * ph
    out = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{escape(title)}">']
    for k in range(3):
        v = lo + (hi - lo) * k / 2
        out.append(f'<line class="grid" x1="{L}" x2="{W-16}" y1="{Y(v):.1f}" y2="{Y(v):.1f}"/>'
                   f'<text x="{L-6}" y="{Y(v)+4:.1f}" text-anchor="end">{escape(fmt(v))}</text>')
    d = " ".join(f"{'M' if i == 0 else 'L'}{X(i):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(points))
    out.append(f'<path class="line" d="{d}"/>')
    for i, (lab, v) in enumerate(points):
        out.append(f'<circle class="dot" cx="{X(i):.1f}" cy="{Y(v):.1f}" r="5">'
                   f'<title>{escape(lab)}: {escape(fmt(v))}</title></circle>')
    out.append(f'<text x="{L}" y="{H-6}">{escape(points[0][0])}</text>'
               f'<text x="{W-16}" y="{H-6}" text-anchor="end">{escape(points[-1][0])}</text></svg>')
    return "".join(out)


def tile(k, v):
    return f'<div class="tile"><div class="k">{escape(k)}</div><div class="v">{escape(v)}</div></div>'


def render(run, a, pr, verdict, cfg, history, offer_url):
    label, score, reasons = verdict
    vcls = {"warto": "v-warto", "ryzykowne": "v-ryzykowne"}.get(label, "v-nie")
    parts = [f"<!doctype html><html lang='pl'><head><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>DtfRadar – raport</title><style>{CSS}</style></head><body><main>"]
    parts.append("<h1>DtfRadar: rynek koszulek DTF na Allegro</h1>")
    parts.append(f"<p class='sub'>Migawka #{run['id']} z {escape(run['started_at'].replace('T', ' '))} · "
                 f"źródło: {escape(run['env'])} · frazy: {escape(', '.join(cfg['phrases']))}</p>")
    if run["env"] == "demo":
        parts.append("<div class='banner'>DANE DEMO – wygenerowane losowo do testu programu. "
                     "Nie opieraj na nich decyzji.</div>")
    elif run["env"] == "sandbox":
        parts.append("<div class='banner'>DANE Z SANDBOXA – testowe oferty Allegro, nie prawdziwy rynek.</div>")

    parts.append(f"<div class='verdict'><div class='k'>Werdykt (punkty: {score})</div>"
                 f"<div class='label {vcls}'>{escape(label)}</div><ul>"
                 + "".join(f"<li>{escape(r)}</li>" for r in reasons) + "</ul>"
                 "<p class='note'>Werdykt to prosta heurystyka z danych o ofertach i Twoich kosztów. "
                 "Nie uwzględnia jakości projektów, marketingu ani sezonowości.</p></div>")

    parts.append("<div class='tiles'>"
                 + tile("Oferty w próbce", num(a["offers"]))
                 + tile("Sprzedawcy", num(a["sellers"]))
                 + tile("Ofert w Allegro (max fraza)", num(a["market_size_est"]))
                 + tile("Mediana ceny", zl(a["price"][50]))
                 + tile("Mediana z dostawą", zl(a["price_total"][50]))
                 + tile("Top 5 sprzedawców", f"{a['top5_share']:.0f}% ofert")
                 + tile("Darmowa dostawa", f"{a['free_delivery_share']:.0f}% ofert")
                 + tile("Super Sprzedawcy", f"{a['super_share']:.0f}% ofert")
                 + "</div>")

    parts.append("<h2>Rozkład cen</h2><div class='card'>"
                 + histogram(a["prices"], a["price"][50], pr["break_even"])
                 + f"<p class='note'>Kubełki co 10 zł. 25–75% ofert mieści się w {zl(a['price'][25])} – "
                 f"{zl(a['price'][75])}. Najtańsza {zl(a['price'][0])}, najdroższa {zl(a['price'][100])}.</p></div>")

    parts.append("<h2>Twój zysk na sztuce przy cenach rynkowych</h2><div class='card'>"
                 + hbars(pr["rows"], "margin", "label", lambda v: zl(v, sign=True), signed=True)
                 + "<table><tr><th>Poziom</th><th class='n'>Cena</th><th class='n'>Prowizja</th>"
                 "<th class='n'>Koszt</th><th class='n'>Zysk</th><th class='n'>Sztuk / mies. do celu</th></tr>"
                 + "".join(
                     f"<tr><td>{escape(r['label'])}</td><td class='n'>{zl(r['price'])}</td>"
                     f"<td class='n'>{zl(r['commission'])}</td><td class='n'>{zl(r['cost'])}</td>"
                     f"<td class='n{' neg' if r['margin'] < 0 else ''}'>{zl(r['margin'], sign=True)}</td>"
                     f"<td class='n'>{num(r['units_for_target']) if r['units_for_target'] else 'nieosiągalne'}</td></tr>"
                     for r in pr["rows"])
                 + "</table>"
                 + f"<p class='note'>Koszt sztuki: {zl(pr['unit_cost'])} "
                 f"({', '.join(f'{k} {v}' for k, v in cfg['costs'].items() if not k.startswith('_'))}). "
                 f"Prowizja Allegro {cfg['commission_pct']}% (sprawdź aktualny cennik). "
                 f"{'VAT ' + str(cfg.get('vat_pct', 23)) + '% odliczony. ' if cfg.get('vat_payer') else 'Bez VAT. '}"
                 f"Próg opłacalności: {zl(pr['break_even'])}. Cel: {zl(cfg['target_monthly_profit'])} / mies. "
                 f"Dostawę płaci kupujący.</p></div>")

    parts.append("<h2>Największi sprzedawcy (liczba ofert)</h2><div class='card'>"
                 + hbars(a["top_sellers"][:10], "offers", "seller", lambda v: f"{v} ofert")
                 + "<table><tr><th>Sprzedawca</th><th class='n'>Oferty</th><th class='n'>Udział</th>"
                 "<th class='n'>Mediana ceny</th>"
                 + ("<th class='n'>Popularność</th>" if a["has_popularity"] else "")
                 + "<th>Super Sprzedawca</th></tr>"
                 + "".join(
                     f"<tr><td>{escape(s['seller'])}</td><td class='n'>{s['offers']}</td>"
                     f"<td class='n'>{s['share']:.1f}%</td><td class='n'>{zl(s['median_price'])}</td>"
                     + (f"<td class='n'>{num(s['popularity'])}</td>" if a["has_popularity"] else "")
                     + f"<td>{'tak' if s['super'] else 'nie'}</td></tr>"
                     for s in a["top_sellers"])
                 + f"</table><p class='note'>Wskaźnik koncentracji HHI: {a['hhi']:.0f} "
                 f"(poniżej 1500 = rynek rozproszony, powyżej 2500 = skoncentrowany). "
                 f"Top 10 ma {a['top10_share']:.0f}% ofert.</p></div>")

    if a["has_popularity"] and a["best_offers"]:
        parts.append("<h2>Najpopularniejsze oferty</h2><div class='card'><table><tr><th>Oferta</th>"
                     "<th>Sprzedawca</th><th class='n'>Cena</th><th class='n'>Popularność</th></tr>"
                     + "".join(
                         f"<tr><td><a href='{escape(offer_url(o['offer_id']))}'>{escape(o['name'][:80])}</a></td>"
                         f"<td>{escape(o['seller_login'] or o['seller_id'])}</td><td class='n'>{zl(o['price'])}</td>"
                         f"<td class='n'>{num(o['popularity'])}</td></tr>" for o in a["best_offers"])
                     + f"</table><p class='note'>{a['with_sales_share']:.0f}% ofert ma sprzedaż. "
                     f"Top 5 sprzedawców ma {a['top5_sales_share'] or 0:.0f}% sumy popularności. "
                     "Popularność to pole sellingMode.popularity z API.</p></div>")
    else:
        parts.append("<h2>Popularność z API</h2><div class='card'><p class='note'>API nie zwróciło pola "
                     "sellingMode.popularity dla tych ofert. Sprzedaż szacujemy ze stanów magazynowych niżej.</p></div>")

    ss = a.get("stock_sales")
    parts.append("<h2>Sprzedane sztuki (szacunek ze stanów magazynowych)</h2><div class='card'>")
    if ss:
        parts.append("<div class='tiles' style='margin-top:0'>"
                     + tile("Sprzedane w próbce / 30 dni", f"~{num(ss['sold_30d'])} szt.")
                     + tile("Średnio na ofertę / 30 dni", f"{ss['per_offer_30d']:.1f} szt.")
                     + tile("Oferty ze sprzedażą", f"{ss['with_sales']} z {ss['tracked']}")
                     + tile("Top 5 sprzedawców", f"{ss['top5_share']:.0f}% sztuk")
                     + "</div>")
        parts.append(hbars(ss["top_sellers"], "sold_30d", "seller", lambda v: f"~{v:.0f} szt. / 30 dni"))
        parts.append("<table><tr><th>Oferta</th><th>Sprzedawca</th><th class='n'>Cena</th>"
                     f"<th class='n'>Sprzedane w {ss['days']:.1f} dni</th></tr>"
                     + "".join(
                         f"<tr><td><a href='{escape(offer_url(o['offer_id']))}'>{escape(o['name'][:80])}</a></td>"
                         f"<td>{escape(o['seller_login'] or o['seller_id'])}</td><td class='n'>{zl(o['price'])}</td>"
                         f"<td class='n'>{o['sold']}</td></tr>" for o in ss["top_offers"])
                     + "</table>")
        parts.append(f"<p class='note'>Porównanie stanów {ss['tracked']} ofert obecnych w obu migawkach, "
                     f"odstęp {ss['days']:.1f} dni, przeliczone na 30 dni. Dostawy towaru i oferty "
                     "zakończone są pomijane, więc to raczej dolne oszacowanie. Sprzedawcy z dużym "
                     "stanem „na zapas” lub dodruk na zamówienie mogą nie zmieniać stanu – wtedy ich sprzedaż nie widać.</p>")
    else:
        parts.append("<p class='note'>Potrzebne są dwie migawki z tego samego źródła w odstępie kilku dni. "
                     "Program porówna stany magazynowe ofert i policzy, ile sztuk zeszło.</p>")
    parts.append("</div>")

    if len(history) >= 2:
        pts_med = [(h["date"], h["median"]) for h in history if h["median"] is not None]
        pts_sel = [(h["date"], h["sellers"]) for h in history]
        parts.append("<h2>Trend między migawkami</h2><div class='two'>"
                     f"<div class='card'><div class='k'>Mediana ceny</div>{line_chart(pts_med, 'Mediana ceny', zl)}</div>"
                     f"<div class='card'><div class='k'>Liczba sprzedawców</div>"
                     f"{line_chart(pts_sel, 'Liczba sprzedawców', lambda v: num(v))}</div></div>")
    else:
        parts.append("<p class='note'>Trend pojawi się po co najmniej dwóch migawkach z tego samego źródła "
                     "(uruchamiaj <code>fetch</code> np. co tydzień).</p>")

    parts.append(f"<p class='note'>Ofert pobranych: {a['offers_raw']}, unikalnych: {a['offers_unique']}, "
                 f"odrzuconych filtrem słów: {a['excluded']}. Nazwy zawierające „DTF”: "
                 f"{a['dtf_mention_share']:.0f}%. Allegro zwraca maks. 600 ofert na zapytanie, "
                 "dlatego program pyta kilkoma sortowaniami.</p>")
    parts.append("</main></body></html>")
    return "".join(parts)
