"""Country names/codes -> ISO 3166-1 alpha-2 (the common cases in German exports)."""
from __future__ import annotations

_NAMES = {
    "deutschland": "DE", "germany": "DE", "bundesrepublik deutschland": "DE", "brd": "DE", "d": "DE", "deu": "DE",
    "österreich": "AT", "oesterreich": "AT", "austria": "AT", "a": "AT", "aut": "AT",
    "schweiz": "CH", "switzerland": "CH", "ch": "CH", "che": "CH",
    "frankreich": "FR", "france": "FR", "fra": "FR",
    "niederlande": "NL", "netherlands": "NL", "holland": "NL", "nld": "NL",
    "belgien": "BE", "belgium": "BE", "bel": "BE",
    "luxemburg": "LU", "luxembourg": "LU", "lux": "LU",
    "italien": "IT", "italy": "IT", "ita": "IT",
    "spanien": "ES", "spain": "ES", "esp": "ES",
    "polen": "PL", "poland": "PL", "pol": "PL",
    "tschechien": "CZ", "czechia": "CZ", "czech republic": "CZ", "cze": "CZ",
    "dänemark": "DK", "daenemark": "DK", "denmark": "DK", "dnk": "DK",
    "schweden": "SE", "sweden": "SE", "swe": "SE",
    "vereinigtes königreich": "GB", "großbritannien": "GB", "united kingdom": "GB", "uk": "GB", "gbr": "GB",
    "irland": "IE", "ireland": "IE", "portugal": "PT", "finnland": "FI", "finland": "FI",
    "norwegen": "NO", "norway": "NO", "ungarn": "HU", "hungary": "HU", "liechtenstein": "LI",
    "usa": "US", "vereinigte staaten": "US", "united states": "US",
}

# ISO alpha-2 codes we accept as-is (EU/EEA + neighbours + common trading partners).
_CODES = {
    "DE", "AT", "CH", "FR", "NL", "BE", "LU", "IT", "ES", "PL", "CZ", "DK", "SE", "GB", "IE", "PT", "FI", "NO", "HU",
    "LI", "US", "SK", "SI", "HR", "RO", "BG", "GR", "EE", "LV", "LT", "MT", "CY", "IS", "TR", "CN", "JP", "CA", "AU",
}


def country_code(value: str) -> str | None:
    v = value.strip()
    if not v:
        return None
    if len(v) == 2 and v.upper() in _CODES:
        return v.upper()
    return _NAMES.get(v.lower())
