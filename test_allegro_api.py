"""Test dostepu do Allegro REST API: czy GET /offers/listing dziala dla tej aplikacji.

Uzycie (PowerShell):
    $env:ALLEGRO_CLIENT_ID = "..."
    $env:ALLEGRO_CLIENT_SECRET = "..."
    python test_allegro_api.py                  # produkcja
    python test_allegro_api.py --sandbox        # srodowisko testowe
    python test_allegro_api.py --phrase "koszulka z nadrukiem dtf"

Tylko biblioteka standardowa, bez pip install.
"""

import argparse
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

ENVS = {
    "prod": {
        "auth": "https://allegro.pl/auth/oauth/token",
        "api": "https://api.allegro.pl",
    },
    "sandbox": {
        "auth": "https://allegro.pl.allegrosandbox.pl/auth/oauth/token",
        "api": "https://api.allegro.pl.allegrosandbox.pl",
    },
}

# Musi zgadzac sie z User-Agentem wygenerowanym na apps.developer.allegro.pl/user-agent
USER_AGENT = os.environ.get(
    "ALLEGRO_USER_AGENT", "DtfRadar/0.1.0 (+https://github.com/regov124356/dtfradar)"
)
ACCEPT = "application/vnd.allegro.public.v1+json"


def http(req):
    """Zwraca (status, body_text). Nie rzuca wyjatku przy bledach HTTP."""
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")


def get_token(env, client_id, client_secret):
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    req = urllib.request.Request(
        env["auth"] + "?grant_type=client_credentials",
        method="POST",
        headers={"Authorization": f"Basic {creds}", "User-Agent": USER_AGENT},
    )
    status, body = http(req)
    if status != 200:
        print(f"[BLAD] Token: HTTP {status}\n{body}")
        print("Sprawdz Client ID/Secret i czy pasuja do srodowiska (prod vs sandbox).")
        sys.exit(1)
    print("[OK] Token pobrany.")
    return json.loads(body)["access_token"]


def search(env, token, phrase):
    query = urllib.parse.urlencode({"phrase": phrase, "limit": 20})
    req = urllib.request.Request(
        f"{env['api']}/offers/listing?{query}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": ACCEPT,
            "User-Agent": USER_AGENT,
        },
    )
    return http(req)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument("--phrase", default="koszulka dtf")
    args = parser.parse_args()

    client_id = os.environ.get("ALLEGRO_CLIENT_ID")
    client_secret = os.environ.get("ALLEGRO_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Ustaw zmienne ALLEGRO_CLIENT_ID i ALLEGRO_CLIENT_SECRET.")
        sys.exit(1)

    env = ENVS["sandbox" if args.sandbox else "prod"]
    print(f"Srodowisko: {'sandbox' if args.sandbox else 'produkcja'}")

    token = get_token(env, client_id, client_secret)
    status, body = search(env, token, args.phrase)

    if status == 200:
        data = json.loads(body)
        items = data.get("items", {})
        offers = items.get("promoted", []) + items.get("regular", [])
        total = data.get("searchMeta", {}).get("totalCount")
        print(f"[OK] /offers/listing DZIALA. Wynikow dla '{args.phrase}': {total}")
        for o in offers[:10]:
            price = o.get("sellingMode", {}).get("price", {})
            seller = o.get("seller", {})
            print(f"  {price.get('amount', '?'):>8} {price.get('currency', '')}  "
                  f"sprzedawca={seller.get('login') or seller.get('id')}  "
                  f"{o.get('name', '')[:70]}")
        # Pelna pierwsza oferta - zeby zobaczyc, jakie pola API zwraca
        if offers:
            print("\nPrzykladowa oferta (wszystkie pola):")
            print(json.dumps(offers[0], ensure_ascii=False, indent=2))
    elif status == 403:
        print(f"[NIE] HTTP 403 - aplikacja nie ma dostepu do /offers/listing.")
        print("Potrzebna weryfikacja aplikacji przez Allegro.")
        print(body)
    else:
        print(f"[BLAD] /offers/listing: HTTP {status}\n{body}")


if __name__ == "__main__":
    main()
