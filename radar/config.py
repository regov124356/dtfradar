"""Konfiguracja: klucze z .env, ustawienia analizy z config.json."""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_USER_AGENT = "DtfRadar/0.1.0 (+https://github.com/regov124356/dtfradar)"
DEFAULT_DB = os.path.join(ROOT, "data", "dtfradar.db")


def load_dotenv(path=os.path.join(ROOT, ".env")):
    """Wczytuje KLUCZ=wartosc z pliku .env. Zmienne ustawione w systemie maja pierwszenstwo."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            if value:
                os.environ.setdefault(key.strip(), value)


def load_config(path=os.path.join(ROOT, "config.json")):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def credentials(sandbox):
    """Zwraca (client_id, client_secret) dla produkcji albo sandboxa."""
    prefix = "ALLEGRO_SANDBOX_" if sandbox else "ALLEGRO_"
    return os.environ.get(prefix + "CLIENT_ID"), os.environ.get(prefix + "CLIENT_SECRET")


def user_agent():
    return os.environ.get("ALLEGRO_USER_AGENT", DEFAULT_USER_AGENT)
