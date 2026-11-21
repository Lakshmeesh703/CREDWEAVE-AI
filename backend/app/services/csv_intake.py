"""Shared CSV decoding and structural checks."""

import csv
import io

from fastapi import HTTPException


def _validate_headers(headers: list[str], required: set[str], allowed: set[str]) -> None:
    actual = {header.strip() for header in headers if header.strip()}
    if len(actual) != len(headers):
        raise HTTPException(422, "CSV headers must be non-empty and unique.")
    missing = sorted(required - actual)
    unknown = sorted(actual - allowed)
    if missing or unknown:
        problems = []
        if missing:
            problems.append(f"missing columns: {', '.join(missing)}")
        if unknown:
            problems.append("unexpected columns are present")
        raise HTTPException(422, "Invalid CSV columns; " + "; ".join(problems) + ".")


def read_rows(content: bytes, required: set[str], allowed: set[str], *, allow_blank: set[str] = frozenset()) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(422, "CSV must be UTF-8 encoded.") from exc
    if any(ord(char) < 32 and char not in "\t\r\n" for char in text):
        raise HTTPException(422, "CSV contains unsupported control characters.")
    try:
        return _read_csv(text, required, allowed, allow_blank)
    except csv.Error as exc:
        raise HTTPException(422, "Malformed CSV quoting or field size.") from exc


def _read_csv(text: str, required: set[str], allowed: set[str], allow_blank: set[str]) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
    if not reader.fieldnames:
        raise HTTPException(422, "CSV must include a header row.")
    _validate_headers(reader.fieldnames, required, allowed)
    rows = []
    for row_number, raw in enumerate(reader, start=2):
        if None in raw or any(value is None for value in raw.values()):
            raise HTTPException(422, f"Row {row_number}: column count does not match the header.")
        row = {key.strip(): (value or "").strip() for key, value in raw.items() if key}
        if not any(row.values()):
            raise HTTPException(422, f"Row {row_number}: blank rows are not allowed.")
        if any(not row[key] for key in required - allow_blank):
            raise HTTPException(422, f"Row {row_number}: required values cannot be blank.")
        rows.append(row)
    if not rows:
        raise HTTPException(422, "CSV must contain at least one data row.")
    return rows
