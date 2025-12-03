from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, PageBreak, Image
)
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from io import BytesIO
import os

CHECKED = "☑"
UNCHECKED = "☐"

HDL_GREY = colors.HexColor("#57585A")
LOGO_PATH = "assets/hdl_logo.png"


def add_logo_and_title(story, title, h1):
    if os.path.exists(LOGO_PATH):
        img = Image(LOGO_PATH, width=45*mm, height=15*mm)
        story.append(img)
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>{title}</b>", h1))
    story.append(Spacer(1, 10))


def generate_production_pdf(
    data,
    jamb_summary,
    stop_summary,
    blanks_df=None,
    hinge_qty=None,
    screw_qty=None,
    cutlists=None,
    job_name="Job Name",
    customer="Customer",
    qnum="Q-XXXX"
):

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=20,
        leftMargin=20,
        topMargin=20,
        bottomMargin=20
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=20,
        textColor=HDL_GREY,
        spaceAfter=6,
    )

    h2 = ParagraphStyle(
        "Heading2",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=HDL_GREY,
        spaceAfter=6
    )

    normal = ParagraphStyle(
        "Normal",
        parent=styles["Normal"],
        fontSize=9,
        textColor="#333333",
        leading=12
    )

    story = []

    # ============================================================
    # PAGE 1 — DOOR LIST
    # ============================================================

    add_logo_and_title(story, f"{job_name} — Door List", title_style)

    story.append(Paragraph(f"Customer: <b>{customer}</b>", normal))
    story.append(Paragraph(f"Quote #: <b>{qnum}</b>", normal))
    story.append(Spacer(1, 12))

    door_table_data = [["Door #", "Form", "Jamb Type", "Leg (mm)", "Head (mm)", "Measured"]]

    for _, r in data.iterrows():
        measured = CHECKED if r.get("Measured", False) else UNCHECKED
        door_table_data.append([
            r.get("Door #", ""),
            r.get("Form", ""),
            r.get("JambType", ""),
            r.get("Leg (mm)", ""),
            r.get("Head (mm)", ""),
            measured
        ])

    door_table = Table(door_table_data, repeatRows=1)
    door_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HDL_GREY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))

    story.append(door_table)
    story.append(PageBreak())

    # ============================================================
    # PAGE 2 — SUMMARY OF PARTS
    # ============================================================

    add_logo_and_title(story, f"{job_name} — Summary of Parts", title_style)

    story.append(Paragraph("<b>Door Blanks</b>", h2))

    if blanks_df is not None and not blanks_df.empty:
        bd = [list(blanks_df.columns)] + blanks_df.values.tolist()
        t = Table(bd)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HDL_GREY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No door blanks found.", normal))

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Jambs (Stock Summary)</b>", h2))

    if jamb_summary is not None and not jamb_summary.empty:
        js = [list(jamb_summary.columns)] + jamb_summary.values.tolist()
        jtab = Table(js)
        jtab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HDL_GREY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ]))
        story.append(jtab)

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Stops</b>", h2))

    if stop_summary is not None and not stop_summary.empty:
        ss = [list(stop_summary.columns)] + stop_summary.values.tolist()
        stab = Table(ss)
        stab.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HDL_GREY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ]))
        story.append(stab)

    story.append(Spacer(1, 12))

    story.append(Paragraph("<b>Hardware</b>", h2))

    hw_data = [["Item", "Qty"], ["Hinges", hinge_qty or 0], ["Screws", screw_qty or 0]]

    hw_table = Table(hw_data)
    hw_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), HDL_GREY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
    ]))

    story.append(hw_table)
    story.append(PageBreak())

    # ============================================================
    # PAGE 3 — CUT LISTS
    # ============================================================

    add_logo_and_title(story, f"{job_name} — Cut Lists", title_style)

    if cutlists:
        for label, df in cutlists.items():
            story.append(Paragraph(f"<b>{label}</b>", h2))
            if df is not None and not df.empty:
                ct = [list(df.columns)] + df.values.tolist()
                tbl = Table(ct)
                tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), HDL_GREY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ]))
                story.append(tbl)
                story.append(Spacer(1, 14))
            else:
                story.append(Paragraph("No cuts found for this profile.", normal))
                story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ============================================================
    # PAGE 4+ — ASSEMBLY PLANS
    # ============================================================

    add_logo_and_title(story, f"{job_name} — Assembly Plans", title_style)

    for _, row in data.iterrows():
        door_num = row.get("Door #")
        form = row.get("Form")
        leaf_type = row.get("LeafType")
        leaf_height = row.get("LeafHeight")
        leaf_thickness = row.get("LeafThickness")

        # Full width
        leaf_width = int(row.get("Width", 0))
        leaves = 2 if form == "Double" else 1

        jamb_type = row.get("JambType")
        leg = row.get("Leg (mm)")
        head = row.get("Head (mm)")

        hinges = row.get("Hinges", 0)
        screws = hinges * 6
        measured = CHECKED if row.get("Measured", False) else UNCHECKED

        story.append(Paragraph(f"<b>Door {door_num} – Assembly Plan</b>", h2))

        story.append(Paragraph(
            f"""
            <b>Leaf Makeup</b><br/>
            • Type: {leaf_type}<br/>
            • Leaf Height: {leaf_height} mm<br/>
            • Leaf Width: {leaf_width} mm<br/>
            • Thickness: {leaf_thickness} mm<br/>
            • Leaves: {leaves}<br/><br/>

            <b>Frame</b><br/>
            • Jamb Type: {jamb_type}<br/>
            • Leg Lengths: {leg} mm ×2<br/>
            • Head Length: {head} mm<br/><br/>

            <b>Stops</b><br/>
            • Stop Lengths: {leg} mm ×2<br/>
            • Head Stop Length: {head} mm<br/><br/>

            <b>Hardware</b><br/>
            • Hinges: {hinges}<br/>
            • Screws: {screws}<br/><br/>

            <b>Measured:</b> {measured}
            """,
            normal
        ))

        story.append(Spacer(1, 6))
        story.append(Paragraph("<hr/>", normal))
        story.append(Spacer(1, 8))

    # ============================================================
    # FINISH
    # ============================================================

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
