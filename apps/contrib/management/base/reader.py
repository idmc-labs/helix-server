"""Reading and validating rows from an import .xlsx sheet."""

import typing

from django.core.management.base import CommandError

from .utils import DISPLAY_SEP, is_empty


def read_rows(
    file_path: str,
    *,
    data_sheet: str,
    allowed_columns: typing.Iterable[str],
) -> typing.List[typing.Dict]:
    """
    Read the data sheet into a list of {header: value} dicts.

    The header row must contain only columns in `allowed_columns` (any other column is an error).
    Fully blank rows are skipped.
    """
    from openpyxl import load_workbook

    workbook = load_workbook(file_path, read_only=True, data_only=True)
    worksheet = workbook[data_sheet] if data_sheet in workbook.sheetnames else workbook.active

    rows_iter = worksheet.iter_rows(values_only=True)
    try:
        header_row = next(rows_iter)
    except StopIteration:
        raise CommandError("The sheet is empty.")

    headers = [str(cell).strip() for cell in header_row if cell is not None]
    allowed = set(allowed_columns)
    unknown = [header for header in headers if header not in allowed]
    if unknown:
        raise CommandError(f"Unknown column(s): {DISPLAY_SEP.join(unknown)}. Allowed columns: {', '.join(sorted(allowed))}")

    rows = []
    for values in rows_iter:
        if all(is_empty(value) for value in values):
            continue  # skip fully blank rows
        rows.append({header: value for header, value in zip(headers, values)})
    return rows
