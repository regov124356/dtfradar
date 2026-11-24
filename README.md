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

## Kontakt

E-mail: ADRES_EMAIL_WLASCICIELA
