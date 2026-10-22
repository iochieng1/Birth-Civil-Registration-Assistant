"""Static reference data: counties and the document catalogue."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources


def _load(name: str):
    with resources.files("crs_assistant.data").joinpath(name).open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache
def counties() -> list[dict]:
    return _load("counties.json")


@lru_cache
def county_by_code(code: str) -> dict | None:
    code = code.zfill(3)
    return next((c for c in counties() if c["code"] == code), None)


@lru_cache
def documents() -> dict[str, dict]:
    return {k: v for k, v in _load("documents.json").items() if not k.startswith("_")}


def document_name(doc_id: str, lang: str = "en") -> str:
    entry = documents()[doc_id]
    return entry.get(lang) or entry["en"]
