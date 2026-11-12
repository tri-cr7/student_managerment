"""System rule repository."""
from flask import g

from studentapp.extensions import db
from studentapp.models.system_rule import SystemRule


def _cache():
    if not hasattr(g, "_rules_cache"):
        g._rules_cache = {}
    return g._rules_cache


def get_rule(key: str) -> SystemRule | None:
    cache = _cache()
    if key in cache:
        return cache[key]
    r = SystemRule.query.filter_by(rule_key=key).first()
    cache[key] = r
    return r


def get_int(key: str, default: int) -> int:
    r = get_rule(key)
    if r is None:
        return default
    try:
        tv = r.typed_value()
        return tv if isinstance(tv, int) else int(float(r.rule_value))
    except (ValueError, TypeError):
        return default


def get_float(key: str, default: float) -> float:
    r = get_rule(key)
    if r is None:
        return default
    try:
        return float(r.rule_value)
    except (ValueError, TypeError):
        return default


def list_all():
    return SystemRule.query.order_by(SystemRule.rule_key).all()


def upsert(key: str, value: str, updated_by=None) -> SystemRule:
    r = SystemRule.query.filter_by(rule_key=key).first()
    if r is None:
        r = SystemRule(rule_key=key, rule_value=str(value))
        db.session.add(r)
    else:
        r.rule_value = str(value)
    if updated_by is not None:
        r.updated_by = updated_by
    return r
