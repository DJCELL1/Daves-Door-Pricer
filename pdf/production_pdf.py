import pdfkit
from jinja2 import Template
import os

# ============================================================
#  PRODUCTION PDF GENERATOR (FULL CLEAN VERSION)
# ============================================================

def generate_production_pdf(data, jamb_summary, stop_summary):
    """
    Generate the Production PDF using wkhtmltopdf + Jinja2 template.
    Returns raw PDF bytes.
    """

    # ------------------------------------------------------------
    # 1. Load the HTML template
    # ------------------------------------------------------------
    template_path = os.path.join("pdf", "templates", "production.html")

    if not os.path.exists(template_path):
        raise FileNotFoundError(
            f"Production template not found at: {template_path}"
        )

    with open(template_path, "r", encoding="utf-8") as f:
        template = Template(f.read())

    # ------------------------------------------------------------
    # 2. Render the HTML string
    # ------------------------------------------------------------
    html = template.render(
        data=data,
        jamb_summary=jamb_summary,
        stop_summary=stop_summary
    )

    # ------------------------------------------------------------
    # 3. PDFKIT CONFIG – point directly to wkhtmltopdf.exe
    # ------------------------------------------------------------
    wkhtml_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"

    if not os.path.exists(wkhtml_path):
        raise FileNotFoundError(
            f"wkhtmltopdf not found at: {wkhtml_path}\n"
            f"Install it here: https://wkhtmltopdf.org/downloads.html"
        )

    config = pdfkit.configuration(wkhtmltopdf=wkhtml_path)

    # ------------------------------------------------------------
    # 4. Generate the PDF
    # ------------------------------------------------------------
    pdf = pdfkit.from_string(
        html,
        False,              # Return bytes instead of writing to file
        configuration=config,
        options={
            "margin-top": "10mm",
            "margin-bottom": "10mm",
            "margin-left": "10mm",
            "margin-right": "10mm",
            "encoding": "UTF-8",
            "enable-local-file-access": None
        }
    )

    return pdf
