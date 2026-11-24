"""Analiza rynku z jednej migawki ofert + werdykt."""

from collections import Counter, defaultdict

from . import profit


def percentile(values, p):
    """Percentyl z interpolacja liniowa, p w zakresie 0-100."""
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def _seller_key(o):
    return o.get("seller_login") or o.get("seller_id") or "?"


def analyze(offers, meta, cfg):
    # Jedna oferta moze wystapic w kilku frazach i sortowaniach - liczymy ja raz.
    unique = {}
    for o in offers:
        if o["offer_id"] and o["offer_id"] not in unique:
            unique[o["offer_id"]] = o
    all_unique = list(unique.values())

    excluded_kw = [k.lower() for k in cfg.get("exclude_keywords", [])]
    required_kw = [k.lower() for k in cfg.get("require_keywords", [])]

    def keep(o):
        name = (o.get("name") or "").lower()
        if any(k in name for k in excluded_kw):
            return False
        if required_kw and not any(k in name for k in required_kw):
            return False
        return o.get("price") is not None

    items = [o for o in all_unique if keep(o)]
    n = len(items)
    prices = [o["price"] for o in items]
    totals = [o["price"] + (o["delivery_price"] or 0) for o in items]

    seller_offers = Counter(_seller_key(o) for o in items)
    seller_prices = defaultdict(list)
    seller_pop = defaultdict(int)
    seller_super = {}
    for o in items:
        key = _seller_key(o)
        seller_prices[key].append(o["price"])
        seller_pop[key] += o["popularity"] or 0
        seller_super[key] = bool(o.get("super_seller"))

    top = []
    for key, count in seller_offers.most_common(15):
        top.append({
            "seller": key,
            "offers": count,
            "share": count / n * 100 if n else 0,
            "median_price": percentile(seller_prices[key], 50),
            "popularity": seller_pop[key],
            "super": seller_super[key],
        })

    shares = [c / n * 100 for c in seller_offers.values()] if n else []
    pop_known = [o for o in items if o.get("popularity") is not None]
    has_pop = len(pop_known) >= max(1, n // 2)
    pop_total = sum(o["popularity"] for o in pop_known)
    by_sales = Counter({k: v for k, v in seller_pop.items()})
    top5_sales = sum(v for _, v in by_sales.most_common(5))

    totals_by_phrase = {}
    for m in meta:
        if m["total_count"] is not None:
            totals_by_phrase[m["phrase"]] = max(totals_by_phrase.get(m["phrase"], 0), m["total_count"])

    return {
        "offers_raw": len(offers),
        "offers_unique": len(all_unique),
        "offers": n,
        "excluded": len(all_unique) - n,
        "sellers": len(seller_offers),
        "totals_by_phrase": totals_by_phrase,
        "market_size_est": max(totals_by_phrase.values()) if totals_by_phrase else None,
        "price": {p: percentile(prices, p) for p in (0, 10, 25, 50, 75, 90, 100)},
        "price_total": {p: percentile(totals, p) for p in (10, 25, 50, 75, 90)},
        "prices": prices,
        "free_delivery_share": (sum(1 for o in items if o["delivery_price"] == 0) / n * 100) if n else 0,
        "top_sellers": top,
        "top5_share": sum(sorted(shares, reverse=True)[:5]),
        "top10_share": sum(sorted(shares, reverse=True)[:10]),
        "hhi": sum(s * s for s in shares),
        "super_share": (sum(1 for o in items if o.get("super_seller")) / n * 100) if n else 0,
        "dtf_mention_share": (sum(1 for o in items if "dtf" in (o.get("name") or "").lower()) / n * 100) if n else 0,
        "has_popularity": has_pop,
        "popularity_total": pop_total if has_pop else None,
        "with_sales_share": (sum(1 for o in pop_known if o["popularity"] > 0) / len(pop_known) * 100) if has_pop else None,
        "top5_sales_share": (top5_sales / pop_total * 100) if has_pop and pop_total else None,
        "best_offers": sorted(pop_known, key=lambda o: o["popularity"], reverse=True)[:10] if has_pop else [],
    }


def stock_sales(prev_offers, cur_offers, days):
    """Szacunek sprzedanych sztuk ze spadku stanu magazynowego miedzy dwiema migawkami.

    Wzrost stanu (dostawa towaru) liczymy jako 0 - szacunek jest raczej zanizony.
    Oferty, ktore zniknely, pomijamy (nie wiadomo, czy sie wyprzedaly, czy zostaly zakonczone).
    """
    prev = {}
    for o in prev_offers:
        if o.get("stock") is not None:
            prev.setdefault(o["offer_id"], o)
    cur = {}
    for o in cur_offers:
        if o.get("stock") is not None:
            cur.setdefault(o["offer_id"], o)
    common = [oid for oid in cur if oid in prev]
    if not common or days <= 0:
        return None

    by_seller = defaultdict(int)
    by_offer = []
    sold_total = 0
    for oid in common:
        sold = max(0, prev[oid]["stock"] - cur[oid]["stock"])
        if sold:
            o = cur[oid]
            sold_total += sold
            by_seller[_seller_key(o)] += sold
            by_offer.append({**o, "sold": sold})
    scale = 30 / days
    top_sellers = sorted(by_seller.items(), key=lambda kv: kv[1], reverse=True)[:10]
    return {
        "days": days,
        "tracked": len(common),
        "with_sales": len(by_offer),
        "sold": sold_total,
        "sold_30d": sold_total * scale,
        "per_offer_30d": sold_total * scale / len(common),
        "top_sellers": [{"seller": s, "sold": n, "sold_30d": n * scale} for s, n in top_sellers],
        "top_offers": sorted(by_offer, key=lambda o: o["sold"], reverse=True)[:10],
        "top5_share": (sum(n for _, n in top_sellers[:5]) / sold_total * 100) if sold_total else 0,
    }


def profitability(a, cfg):
    rows = []
    for label, p in (("Najtańsze 10%", 10), ("Dolny kwartyl", 25), ("Mediana rynku", 50),
                     ("Górny kwartyl", 75), ("Najdroższe 10%", 90)):
        price = a["price"].get(p)
        if price is None:
            continue
        row = profit.margin_at(price, cfg)
        row["label"] = label
        row["units_for_target"] = profit.units_for_target(row["margin"], cfg["target_monthly_profit"])
        rows.append(row)
    return {
        "unit_cost": profit.unit_cost(cfg),
        "break_even": profit.break_even_price(cfg),
        "rows": rows,
    }


def verdict(a, pr, cfg):
    """Prosta punktacja. Zwraca (etykieta, punkty, powody). To heurystyka, nie wyrocznia."""
    score = 0
    reasons = []
    if a["offers"] == 0:
        return "brak danych", 0, ["Brak ofert do analizy."]

    median = next((r for r in pr["rows"] if r["label"] == "Mediana rynku"), None)
    if median:
        m, pct = median["margin"], median["margin_pct"]
        if pct >= 30:
            score += 2
            reasons.append(f"+ Przy medianie rynku ({median['price']:.2f} zł) zostaje {m:.2f} zł na sztuce ({pct:.0f}%).")
        elif pct >= 15:
            score += 1
            reasons.append(f"+ Marża przy medianie {m:.2f} zł ({pct:.0f}%) – przyzwoita, ale bez zapasu na reklamę.")
        elif m > 0:
            reasons.append(f"– Marża przy medianie tylko {m:.2f} zł ({pct:.0f}%).")
        else:
            score -= 2
            reasons.append(f"– Przy medianie rynku ({median['price']:.2f} zł) sprzedajesz ze stratą {m:.2f} zł.")

    be = pr["break_even"]
    q1 = a["price"].get(25)
    if be and q1 is not None and q1 < be:
        score -= 1
        reasons.append(f"– Co najmniej 25% ofert kosztuje mniej ({q1:.2f} zł) niż Twój próg opłacalności ({be:.2f} zł).")

    if a["top5_share"] > 50:
        score -= 1
        reasons.append(f"– Rynek zdominowany: 5 sprzedawców ma {a['top5_share']:.0f}% ofert.")
    else:
        reasons.append(f"+ Rynek rozproszony: top 5 sprzedawców ma {a['top5_share']:.0f}% ofert (HHI {a['hhi']:.0f}).")

    size = a["market_size_est"]
    if size and size > cfg.get("saturation_offers", 20000):
        score -= 1
        reasons.append(f"– Dużo konkurencji: ok. {size:,} ofert dla najszerszej frazy.".replace(",", " "))

    if a["has_popularity"]:
        ws = a["with_sales_share"]
        if ws >= 30:
            score += 1
            reasons.append(f"+ Popyt: {ws:.0f}% ofert ma sprzedaż.")
        elif ws < 10:
            score -= 1
            reasons.append(f"– Słaby popyt: tylko {ws:.0f}% ofert ma sprzedaż.")
        else:
            reasons.append(f"· Popyt umiarkowany: {ws:.0f}% ofert ma sprzedaż.")
        if a["top5_sales_share"] and a["top5_sales_share"] > 60:
            score -= 1
            reasons.append(f"– Sprzedaż skupiona: 5 sprzedawców ma {a['top5_sales_share']:.0f}% sprzedaży.")
    elif a.get("stock_sales"):
        ss = a["stock_sales"]
        share = ss["with_sales"] / ss["tracked"] * 100
        if share >= 30:
            score += 1
            reasons.append(f"+ Popyt (ze stanów): {share:.0f}% ofert coś sprzedało, ok. {ss['sold_30d']:.0f} szt. / 30 dni w próbce.")
        elif share < 10:
            score -= 1
            reasons.append(f"– Słaby popyt (ze stanów): tylko {share:.0f}% ofert coś sprzedało.")
        else:
            reasons.append(f"· Popyt umiarkowany (ze stanów): {share:.0f}% ofert coś sprzedało.")
        if ss["top5_share"] > 60:
            score -= 1
            reasons.append(f"– Sprzedaż skupiona: 5 sprzedawców ma {ss['top5_share']:.0f}% sprzedanych sztuk.")
    else:
        reasons.append("· Brak danych o sprzedaży – popyt nieoceniony. Zrób drugą migawkę za kilka dni.")

    if score >= 2:
        label = "warto"
    elif score >= 0:
        label = "ryzykowne"
    else:
        label = "nie warto"
    return label, score, reasons
