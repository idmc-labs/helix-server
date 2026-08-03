"""Shared helpers for the bulk-import framework."""

# A cell is considered "empty" when it is missing or blank.
EMPTY_VALUES = (None, "")

# Display-only separator for human-facing value lists (never used to parse input).
DISPLAY_SEP = " · "


def is_empty(value) -> bool:
    return value in EMPTY_VALUES or (isinstance(value, str) and value.strip() == "")
