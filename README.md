# DtfRadar

Aplikacja do analizy rynku koszulek z nadrukiem DTF na Allegro, na własny użytek jej właściciela.

## Opis

DtfRadar to skrypt w Pythonie uruchamiany lokalnie z wiersza poleceń. Wyszukuje publiczne oferty
dla kilku fraz (np. „koszulka dtf”, „koszulka z nadrukiem dtf”) i zapisuje je w lokalnej bazie
SQLite. Z zebranych danych tworzy raport: liczba ofert i sprzedawców, rozkład cen, koncentracja
rynku oraz porównanie cen rynkowych z kosztami właściciela.

Aplikacja:
- działa wyłącznie na potrzeby właściciela, nie jest udostępniana innym sprzedawcom;
- tylko odczytuje dane, nie tworzy ani nie zmienia ofert, nie składa zamówień;
- nie przetwarza danych osobowych kupujących;
- nie publikuje zebranych danych.

## Autoryzacja (OAuth)

Aplikacja nie działa w imieniu użytkownika Allegro. Używa przepływu **client_credentials**:
token pobierany z `https://allegro.pl/auth/oauth/token` przy użyciu Client ID i Client Secret.

## Używane zasoby REST API

| Zasób | Metoda | Cel | Scope |
|---|---|---|---|
| `/offers/listing` | GET | wyszukiwanie publicznych ofert po frazie | brak (zasób publiczny) |

## Częstotliwość

Uruchamiana ręcznie lub według harmonogramu, kilka razy w miesiącu. Jedno uruchomienie to
od kilkudziesięciu do kilkuset zapytań, wysyłanych sekwencyjnie.

## User-Agent

`DtfRadar/0.1.0 (+https://github.com/regov124356/dtfradar)`

## Uruchomienie

Wymaga Pythona 3.10+, bez dodatkowych bibliotek.

1. Skopiuj `.env.example` jako `.env` i wpisz klucze aplikacji.
2. Uzupełnij koszty i frazy w `config.json`.
3. Pobierz migawkę ofert i zrób raport:

```
python dtfradar.py fetch            # produkcja (wymaga weryfikacji /offers/listing)
python dtfradar.py fetch --sandbox  # środowisko testowe Allegro
python dtfradar.py fetch --demo     # dane DEMO bez API
python dtfradar.py report --open    # raport HTML z ostatniej migawki
python dtfradar.py runs             # lista migawek
```

Liczba sprzedanych sztuk jest szacowana z różnicy stanów magazynowych ofert między
migawkami, dlatego `fetch` warto uruchamiać regularnie, np. co 3–7 dni.

## Kontakt

E-mail: mrwidmopl213@gmail.com
