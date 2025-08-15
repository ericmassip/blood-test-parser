from __future__ import annotations

import os
import tempfile
from pathlib import Path
import sys
import logging
from typing import Any, Dict, List, Tuple
from dotenv import load_dotenv

from flask import Flask, render_template, request

# Local imports from project root
# Ensure project root is on sys.path so we can import local modules when running from /web
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from parser import BloodTestParser
from google_sheets_service import GoogleSheetsService

from babel.numbers import format_decimal


app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)

# Load environment variables from .env during local development
load_dotenv()

# Limit uploads to 5 MB for Vercel compatibility
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

# Basic logging setup for clearer diagnostics in development
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s'
)
app.logger.setLevel(logging.INFO)


def _format_number_spanish(value: Any) -> str:
    """Format numbers using Spanish locale with Babel."""
    if isinstance(value, bool):
        return "1" if value else "0"

    if isinstance(value, (int,)):
        return str(value)

    if isinstance(value, float):
        return format_decimal(value, locale="es_ES")

    return str(value)


def _build_headers_and_values(extracted: Dict[str, Any]) -> Tuple[List[str], List[str], str]:
    """Create ordered headers, display values, and TSV string.

    The order is dictated by the Google Sheets mapping to ensure copy-paste alignment.
    """
    mapping = GoogleSheetsService.COLUMN_MAPPING
    headers: List[str] = []
    display_values: List[str] = []

    for json_key, spreadsheet_header in mapping.items():
        headers.append(spreadsheet_header)
        raw_value = extracted.get(json_key)

        if raw_value is None:
            display_values.append("")
        else:
            value_to_render = raw_value

            # Apply domain-specific transformation for eosinophils, mirroring the Sheets logic
            if json_key == "EOSINOFILOS_TOTALES" and isinstance(raw_value, (int, float)):
                value_to_render = raw_value * 1000

            if isinstance(value_to_render, (int, float)):
                display_values.append(_format_number_spanish(value_to_render))
            else:
                display_values.append(str(value_to_render))

        # 'Hepatitis B codigo' is not extracted from the PDF but sits between VIH and VHC
        # and must be present (empty) to preserve copy-paste alignment.
        if json_key == "VIH":
            headers.append("Hepatitis B codigo")
            display_values.append("")

        # 'Urianálisis' and 'Parasitos en orina' sit between SARAMPIÓN and SEROL SCHISTOSOMA
        # and must be present (empty) to preserve copy-paste alignment.
        if json_key == "SARAMPION":
            headers.append("Urianálisis")
            display_values.append("")
            headers.append("Parasitos en orina")
            display_values.append("")

    # TSV must preserve empty fields for correct spreadsheet pasting.
    # Add a trailing newline to ensure the last column is recognised by Google Sheets on paste.
    tsv = "\t".join(display_values) + "\n"
    return headers, display_values, tsv


@app.get("/")
def index():
    """Render the main page with the upload form."""
    return render_template("index.html")


@app.post("/extract")
def extract():
    """Handle PDF upload, run extraction, and return an HTMX partial with the result."""
    uploaded = request.files.get("file")
    if not uploaded or uploaded.filename == "":
        app.logger.warning("Upload error: no file provided")
        return render_template(
            "partials/result_row.html",
            error_message="Por favor, seleccione un archivo PDF.",
        ), 200

    filename_lower = uploaded.filename.lower()
    if not (filename_lower.endswith(".pdf") or uploaded.mimetype == "application/pdf"):
        app.logger.warning(
            "Upload error: wrong type -> name=%s mimetype=%s",
            uploaded.filename,
            uploaded.mimetype,
        )
        return render_template(
            "partials/result_row.html",
            error_message="El archivo debe ser un PDF.",
        ), 200

    # Ensure the API key is available early to provide a clearer error to the user
    if not (os.getenv("GOOGLE_API_KEY")):
        app.logger.error("Configuration error: GOOGLE_API_KEY not set")
        return render_template(
            "partials/result_row.html",
            error_message=(
                "Falta la variable de entorno GOOGLE_API_KEY. "
                "Configúrela antes de intentar la extracción."
            ),
        ), 200

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir) / "input.pdf"
            uploaded.save(str(temp_path))
            app.logger.info("Saved upload to %s (%d bytes)", temp_path, temp_path.stat().st_size)

            parser = BloodTestParser()
            app.logger.info("Starting extraction with BloodTestParser")
            extracted = parser.extract_data_from_document(temp_path)
            app.logger.info("Extraction completed successfully")

        if not isinstance(extracted, dict) or ("error" in extracted):
            message = extracted.get("error") if isinstance(extracted, dict) else "Error desconocido"
            app.logger.error("Extraction returned error: %s", message)
            return render_template(
                "partials/result_row.html",
                error_message=f"No se pudo extraer la información: {message}",
            ), 200

        headers, values, tsv = _build_headers_and_values(extracted)
        app.logger.info("Built TSV with %d columns", len(values))
        return render_template(
            "partials/result_row.html",
            headers=headers,
            values=values,
            tsv=tsv,
        )

    except Exception as exc:  # Broad catch to provide a friendly error partial
        app.logger.exception("Unhandled error during extraction")
        return render_template(
            "partials/result_row.html",
            error_message=f"Se produjo un error durante la extracción: {exc}",
        ), 200


if __name__ == "__main__":
    # For local development convenience
    app.run(host="127.0.0.1", port=5000, debug=True)


