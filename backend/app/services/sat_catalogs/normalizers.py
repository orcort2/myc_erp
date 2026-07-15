import re
import unicodedata
from datetime import date


def normalize_header(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


def normalize_text(value: object) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def normalize_search(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def normalize_row(row: dict[str, object]) -> dict[str, str | None]:
    return {normalize_header(key): normalize_text(value) for key, value in row.items()}


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    for separator in ("-", "/"):
        parts = value.split(separator)
        if len(parts) == 3:
            try:
                if len(parts[0]) == 4:
                    return date(int(parts[0]), int(parts[1]), int(parts[2]))
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
            except ValueError:
                return None
    return None
