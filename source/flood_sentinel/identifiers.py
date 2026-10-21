"""Strict identifiers shared by source adapters and the causal loader."""
from __future__ import annotations

import re
from collections.abc import Mapping


_USGS_SITE = re.compile(r"^(?:USGS-)?([0-9]{8})$")
_SAMPLE = re.compile(r"^(.+)_([0-9]{8}T[0-9]{6}Z)$")


class SourceIdentityError(ValueError):
    """An identifier or source binding is empty, inconsistent, or unresolved."""


def require_identifier(value: object, *, field: str) -> str:
    if (not isinstance(value, str) or not value or value.strip() != value
            or any(character.isspace() for character in value)):
        raise SourceIdentityError(f"{field} must be a nonempty string without whitespace")
    return value


def canonical_site(value: object, *, field: str = "site") -> str:
    site = require_identifier(value, field=field)
    match = _USGS_SITE.fullmatch(site)
    return f"USGS-{match.group(1)}" if match else site


def parse_sample_identity(sample_id: object) -> tuple[str, str]:
    value = require_identifier(sample_id, field="sample_id")
    match = _SAMPLE.fullmatch(value)
    if not match:
        raise SourceIdentityError("sample_id must end in _YYYYMMDDTHHMMSSZ and contain a canonical site")
    return canonical_site(match.group(1), field="sample site"), match.group(2)


def split_source_ids(value: object, *, field: str = "source_ids") -> tuple[str, ...]:
    raw = require_identifier(value, field=field)
    ids = tuple(require_identifier(part, field=f"{field} entry") for part in raw.split("|"))
    if len(ids) != len(set(ids)):
        raise SourceIdentityError(f"{field} contains duplicate IDs")
    return ids


def validate_record_lookup(lookup: Mapping[object, Mapping[str, object]]) -> None:
    if not isinstance(lookup, Mapping):
        raise SourceIdentityError("A record-ID keyed mapping is required")
    for key, record in lookup.items():
        key_id = require_identifier(key, field="source lookup key")
        if not isinstance(record, Mapping):
            raise SourceIdentityError(f"Source lookup value for {key_id!r} is not a record mapping")
        record_id = require_identifier(record.get("record_id"), field="record_id")
        if key_id != record_id:
            raise SourceIdentityError(f"Source lookup key {key_id!r} differs from record_id {record_id!r}")
