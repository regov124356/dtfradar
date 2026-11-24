"""Klient Allegro REST API: token client_credentials i GET /offers/listing."""

import base64
import json
import time
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
ACCEPT = "application/vnd.allegro.public.v1+json"
MAX_OFFSET = 600  # limit Allegro dla /offers/listing
PAGE_SIZE = 60


class AllegroError(Exception):
    def __init__(self, status, body):
        super().__init__(f"HTTP {status}: {body[:500]}")
        self.status = status
        self.body = body


class AllegroClient:
    def __init__(self, client_id, client_secret, user_agent, sandbox=False, delay=0.3):
        self.env = ENVS["sandbox" if sandbox else "prod"]
        self.client_id = client_id
        self.client_secret = client_secret
        self.user_agent = user_agent
        self.delay = delay  # przerwa miedzy zapytaniami (s), zeby nie obciazac API
        self._token = None
        self._token_expires = 0.0

    def _send(self, req):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return resp.status, resp.read().decode("utf-8"), resp.headers
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace"), e.headers

    def token(self):
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        creds = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        req = urllib.request.Request(
            self.env["auth"] + "?grant_type=client_credentials",
            method="POST",
            headers={"Authorization": f"Basic {creds}", "User-Agent": self.user_agent},
        )
        status, body, _ = self._send(req)
        if status != 200:
            raise AllegroError(status, body)
        data = json.loads(body)
        self._token = data["access_token"]
        self._token_expires = time.time() + int(data.get("expires_in", 3600))
        return self._token

    def listing(self, phrase, category_id=None, sort=None, offset=0, limit=PAGE_SIZE):
        params = {"phrase": phrase, "offset": offset, "limit": limit}
        if category_id:
            params["category.id"] = category_id
        if sort:
            params["sort"] = sort
        url = f"{self.env['api']}/offers/listing?{urllib.parse.urlencode(params)}"
        for attempt in range(4):
            req = urllib.request.Request(url, headers={
                "Authorization": f"Bearer {self.token()}",
                "Accept": ACCEPT,
                "User-Agent": self.user_agent,
            })
            status, body, headers = self._send(req)
            time.sleep(self.delay)
            if status == 200:
                return json.loads(body)
            if status == 429 and attempt < 3:
                wait = int(headers.get("Retry-After", 0) or 0) or 5 * (attempt + 1)
                time.sleep(wait)
                continue
            raise AllegroError(status, body)

    def search(self, phrase, category_id=None, sort=None, max_pages=10):
        """Generator stron wynikow: (lista_ofert, total_count). Oferta = (dict, promoted)."""
        offset = 0
        pages = 0
        while offset < MAX_OFFSET and pages < max_pages:
            data = self.listing(phrase, category_id, sort, offset)
            items = data.get("items", {})
            promoted = items.get("promoted", [])
            regular = items.get("regular", [])
            total = (data.get("searchMeta") or {}).get("totalCount")
            yield [(o, True) for o in promoted] + [(o, False) for o in regular], total
            pages += 1
            if len(regular) < PAGE_SIZE:
                break
            offset += PAGE_SIZE


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_offer(o, promoted=False):
    """Splaszcza oferte z API do pol uzywanych w analizie. Surowy JSON zostaje w 'raw'."""
    selling = o.get("sellingMode") or {}
    delivery = o.get("delivery") or {}
    seller = o.get("seller") or {}
    delivery_price = _num((delivery.get("lowestPrice") or {}).get("amount"))
    if delivery.get("availableForFree"):
        delivery_price = 0.0
    return {
        "offer_id": str(o.get("id", "")),
        "name": o.get("name", "") or "",
        "price": _num((selling.get("price") or {}).get("amount")),
        "delivery_price": delivery_price,
        "seller_id": str(seller.get("id", "") or ""),
        "seller_login": seller.get("login") or "",
        "super_seller": 1 if seller.get("superSeller") else 0,
        "company": 1 if seller.get("company") else 0,
        "popularity": _int(selling.get("popularity")),
        "category_id": str((o.get("category") or {}).get("id", "") or ""),
        "stock": _int((o.get("stock") or {}).get("available")),
        "promoted": 1 if promoted else 0,
        "raw": json.dumps(o, ensure_ascii=False),
    }
