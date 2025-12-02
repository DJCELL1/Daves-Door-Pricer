from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, Image
)
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from io import BytesIO
import os


def generate_production_pdf(data, jamb_summary, stop_summary):
    """
    Fully styled HDL PDF — works on Streamlit Cloud.
    """

    # ---------------------------------------------------
    # PDF BUFFER
    # ---------------------------------------------------
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()

    h1 = ParagraphStyle(
        name="Heading1",
        parent=styles["Heading1"],
        fontSize=16,
        textColor="#57585A",
        spaceAfter=10,
        leading=18
    )

    h2 = ParagraphStyle(
        name="Heading2",
        parent=styles["Heading2"],
        fontSize=13,
        textColor="#57585A",
        spaceAfter=6,
        leading=15
    )

    normal = ParagraphStyle(
        name="NormalHDL",
        parent=styles["Normal"],
        fontSize=9,
        textColor="#333333"
    )

    story = []

    # ---------------------------------------------------
    # HEADER WITH LOGO
    # ---------------------------------------------------
    logo_path = os.path.join("pdf", "assets", "hdl_logo.png")
    if os.path.exists(logo_path):
        img = Image(logo_path, width=60*mm, height=20*mm)
        story.append(img)
        story.append(Spacer(1, 12))
    else:
        story.append(Paragraph("<b>Hardware Direct</b>", h1))
        story.append(Spacer(1, 12))

    # ---------------------------------------------------
    # TITLE
    # ---------------------------------------------------
    story.append(Paragraph("<b>Production Report</b>", h1))
    story.append(Spacer(1, 12))

    # ---------------------------------------------------
    # SECTION: PRODUCTION DATA
    # ---------------------------------------------------
    story.append(Paragraph("<b>Production Data</b>", h2))
    story.append(Spacer(1, 6))

    prod_table_data = [list(data.columns)] + data.values.tolist()

    prod_table = Table(prod_table_data, repeatRows=1)
    prod_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#57585A")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(prod_table)
    story.append(Spacer(1, 18))

    # ---------------------------------------------------
    # SECTION: JAMB SUMMARY
    # ---------------------------------------------------
    story.append(Paragraph("<b>Jamb Summary</b>", h2))
    story.append(Spacer(1, 6))

    if not jamb_summary.empty:
        js_data = [list(jamb_summary.columns)] + jamb_summary.values.tolist()
        js_table = Table(js_data, repeatRows=1)
        js_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#57585A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ]))
        story.append(js_table)
        story.append(Spacer(1, 18))
    else:
        story.append(Paragraph("No jamb summary available.", normal))
        story.append(Spacer(1, 12))

    # ---------------------------------------------------
    # SECTION: STOP SUMMARY
    # ---------------------------------------------------
    story.append(Paragraph("<b>Stop Summary</b>", h2))
    story.append(Spacer(1, 6))

    if not stop_summary.empty:
        st_data = [list(stop_summary.columns)] + stop_summary.values.tolist()
        st_table = Table(st_data, repeatRows=1)
        st_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#57585A")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
            ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ]))
        story.append(st_table)
    else:
        story.append(Paragraph("No stop summary available.", normal))

    # ---------------------------------------------------
    # BUILD PDF
    # ---------------------------------------------------
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
