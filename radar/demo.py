"""Generator danych DEMO - sztuczne oferty do testowania programu bez dostepu do API.

Liczby sa wymyslone. Nie wolno na nich opierac decyzji biznesowych.
"""

import json
import random

ADJECTIVES = ["Śmieszna", "Personalizowana", "Męska", "Damska", "Oversize", "Bawełniana",
              "Na prezent", "Retro", "Z własnym nadrukiem", "Premium"]
THEMES = ["gaming", "wędkarz", "kot", "pies", "motocykl", "urodziny", "wieczór kawalerski",
          "anime", "rower", "kawa", "tata", "mama", "piwo", "góry", "IT programista"]


def generate(phrases, seed=None, n_sellers=150):
    """Zwraca {fraza: (lista_ofert_znormalizowanych, total_count)}."""
    rnd = random.Random(seed)
    sellers = []
    for i in range(n_sellers):
        size = max(1, int(rnd.paretovariate(1.3)))  # kilku duzych, wielu malych
        sellers.append({
            "id": str(10_000_000 + i),
            "login": f"demo_sklep_{i:03d}",
            "size": size,
            "super": rnd.random() < 0.25 + min(size, 20) / 60,
            "base_price": rnd.lognormvariate(4.05, 0.28),  # mediana ~57 zl
        })

    result = {}
    oid = 1_000_000_000
    for phrase in phrases:
        offers = []
        for s in sellers:
            if rnd.random() < 0.35:
                continue
            for _ in range(min(s["size"] * rnd.randint(1, 3), 40)):
                oid += 1
                price = round(max(19.99, s["base_price"] * rnd.uniform(0.85, 1.2)), 2)
                pop = 0 if rnd.random() < 0.55 else int(rnd.paretovariate(1.1) * min(s["size"], 15))
                name = (f"{rnd.choice(ADJECTIVES)} koszulka {rnd.choice(THEMES)}"
                        f"{' nadruk DTF' if rnd.random() < 0.6 else ' z nadrukiem'}")
                offers.append({
                    "offer_id": str(oid),
                    "name": name,
                    "price": price,
                    "delivery_price": 0.0 if rnd.random() < 0.3 else rnd.choice([8.99, 9.99, 11.99, 13.99]),
                    "seller_id": s["id"],
                    "seller_login": s["login"],
                    "super_seller": 1 if s["super"] else 0,
                    "company": 1,
                    "popularity": pop,
                    "category_id": "demo",
                    "stock": rnd.randint(5, 500),
                    "promoted": 1 if rnd.random() < 0.08 else 0,
                    "raw": json.dumps({"demo": True}),
                })
        offers.sort(key=lambda o: int(o["offer_id"]))
        total = int(len(offers) * rnd.uniform(4, 9))  # API widzi wiecej niz 600 na fraze
        result[phrase] = (offers[:600], total)
    return result


def next_snapshot(prev_offers, days, seed=None):
    """Kolejna migawka DEMO: te same oferty, stany spadaja wg popularnosci, czesc ofert znika."""
    rnd = random.Random(seed)
    out = []
    for o in prev_offers:
        if rnd.random() < 0.05:
            continue  # oferta zakonczona
        o = dict(o)
        rate = (o["popularity"] or 0) / 30 * rnd.uniform(0.5, 1.5)
        sold = int(rate * days + rnd.random())
        if o["stock"] is not None:
            o["stock"] = max(0, o["stock"] - sold)
            if o["stock"] < 3 and rnd.random() < 0.5:
                o["stock"] += rnd.randint(50, 200)  # dostawa
        out.append(o)
    return out
