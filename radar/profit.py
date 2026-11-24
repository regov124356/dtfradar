"""Kalkulator oplacalnosci jednej koszulki."""

import math


def unit_cost(cfg):
    return sum(float(v) for k, v in cfg["costs"].items() if not k.startswith("_"))


def _net_factor(cfg):
    vat = float(cfg.get("vat_pct", 23)) if cfg.get("vat_payer") else 0.0
    return 1 / (1 + vat / 100)


def margin_at(price, cfg):
    """Zysk na sztuce przy cenie brutto `price` (dostawe placi kupujacy)."""
    net = price * _net_factor(cfg)
    commission = price * float(cfg["commission_pct"]) / 100
    cost = unit_cost(cfg)
    margin = net - commission - cost
    return {
        "price": price,
        "net": net,
        "commission": commission,
        "cost": cost,
        "margin": margin,
        "margin_pct": margin / price * 100 if price else 0.0,
    }


def break_even_price(cfg):
    """Najnizsza cena, przy ktorej sprzedaz wychodzi na zero."""
    k = _net_factor(cfg) - float(cfg["commission_pct"]) / 100
    return unit_cost(cfg) / k if k > 0 else None


def units_for_target(margin, target):
    if margin <= 0:
        return None
    return math.ceil(target / margin)
