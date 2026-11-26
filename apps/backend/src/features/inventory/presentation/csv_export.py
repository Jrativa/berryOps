# src/features/inventory/presentation/csv_export.py
import csv
import io
import re
from datetime import date
from typing import Iterable, Optional, Sequence

from fastapi import Response

# Excel interpreta como fórmula lo que empieza por estos caracteres
_FORMULA_START = re.compile(r"^[=+\-@\t\r]")


def safe_cell(value) -> str:
    """Texto seguro para una celda: neutraliza fórmulas (CSV injection) en campos de texto libre."""
    if value is None:
        return ""
    text = str(value)
    return "'" + text if _FORMULA_START.match(text) else text


def csv_response(filename: str, header: Sequence[str], rows: Iterable[Sequence]) -> Response:
    """CSV UTF-8 con BOM para que Excel respete tildes y eñes."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows(rows)
    return Response(
        content="\ufeff" + buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def export_filename(kind: str, date_from: Optional[date], date_to: Optional[date]) -> str:
    stamp = f"{date_from or 'inicio'}_{date_to or date.today()}"
    return f"{kind}_{stamp}.csv"
