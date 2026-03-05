from fpdf import FPDF
from datetime import datetime


def generate_panel_pdf(panel, panel_index):
    """Generate a PDF report for a single panel. Returns PDF bytes."""
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # ── Header ──
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "APMS - Panel Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Generated on {datetime.now().strftime('%d %b %Y, %H:%M')}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    # ── Panel Info ──
    _section_heading(pdf, f"Panel {panel_index} Details")
    info_rows = [
        ("Panel Type", panel.get("panel_type", "N/A")),
        ("File Number", panel.get("file_no", "N/A")),
        ("Post / Exam", panel.get("post_name", "N/A")),
        ("Total Advisors", str(len(panel.get("selected_advisors", [])))),
        ("Number of Boards", str(panel.get("num_boards", 1))),
    ]
    for label, value in info_rows:
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(50, 7, label, border=1)
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(100, 7, str(value), border=1, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # ── Board Details ──
    boards = panel.get("boards", [])
    if boards:
        _section_heading(pdf, "Board Configuration")
        headers = ["Board", "President", "Advisors Needed", "Interview Date"]
        col_widths = [20, 90, 40, 40]
        _table_header(pdf, headers, col_widths)
        for idx, b in enumerate(boards):
            pdf.set_font("Helvetica", "", 9)
            pdf.cell(col_widths[0], 7, str(idx + 1), border=1, align="C")
            pdf.cell(col_widths[1], 7, _safe(b.get("president", "")), border=1)
            pdf.cell(col_widths[2], 7, str(b.get("num_advisors", "")), border=1, align="C")
            pdf.cell(col_widths[3], 7, _safe(b.get("date", "")), border=1, align="C",
                     new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ── Selected Advisors ──
    advisors = panel.get("selected_advisors", [])
    if advisors:
        _section_heading(pdf, "Selected Advisors")
        adv_headers = ["#", "ID", "Profession", "Designation", "Zone", "Gender", "Employment", "AI Score"]
        adv_widths = [10, 25, 55, 55, 35, 20, 30, 25]
        _table_header(pdf, adv_headers, adv_widths)
        for idx, adv in enumerate(advisors):
            pdf.set_font("Helvetica", "", 8)
            pdf.cell(adv_widths[0], 6, str(idx + 1), border=1, align="C")
            pdf.cell(adv_widths[1], 6, _safe(adv.get("INDEX_NO", "")), border=1)
            pdf.cell(adv_widths[2], 6, _safe(adv.get("PROFESSION_NAME", ""))[:35], border=1)
            pdf.cell(adv_widths[3], 6, _safe(adv.get("DESIGNATION_DESC", ""))[:35], border=1)
            pdf.cell(adv_widths[4], 6, _safe(adv.get("ZONE_NAME", "")), border=1)
            pdf.cell(adv_widths[5], 6, _safe(adv.get("GENDER", "")), border=1, align="C")
            pdf.cell(adv_widths[6], 6, _safe(adv.get("EMPLOYMENT_STATUS", "")), border=1, align="C")
            score = adv.get("composite_score", "")
            score_str = f"{score:.1f}" if isinstance(score, (int, float)) else str(score)
            pdf.cell(adv_widths[7], 6, score_str, border=1, align="C",
                     new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ── Health Card ──
    health = panel.get("health", {})
    if health:
        _section_heading(pdf, "AI Panel Health Card")

        # Overall score
        overall = health.get("overall", 0)
        if overall >= 70:
            label = "Good"
        elif overall >= 40:
            label = "Fair"
        else:
            label = "Needs Improvement"
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Overall Score: {overall:.0f} / 100  ({label})",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

        # Dimension scores
        dim_labels = {
            "gender": "Gender Balance",
            "zone": "Zone Diversity",
            "experience": "Experience Mix",
            "expertise": "Expertise Coverage",
        }
        scores = health.get("scores", {})
        dim_headers = ["Dimension", "Score"]
        dim_widths = [80, 30]
        _table_header(pdf, dim_headers, dim_widths)
        for key, label in dim_labels.items():
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(dim_widths[0], 7, label, border=1)
            pdf.cell(dim_widths[1], 7, f"{scores.get(key, 0):.0f} / 100", border=1, align="C",
                     new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Suggestions
        suggestions = health.get("suggestions", [])
        if suggestions:
            _section_heading(pdf, "AI Suggestions")
            pdf.set_font("Helvetica", "", 9)
            for s in suggestions:
                pdf.cell(5, 6, "")
                pdf.cell(0, 6, f"- {_safe(s)}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        # Conflicts
        conflicts = health.get("conflicts", [])
        if conflicts:
            _section_heading(pdf, "Conflicts Detected")
            pdf.set_font("Helvetica", "", 9)
            for c in conflicts:
                pdf.cell(5, 6, "")
                pdf.cell(0, 6, f"- {_safe(c)}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

    # ── Footer ──
    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "APMS - Advisor Panel Management System | UPSC | AI-Powered POC",
             new_x="LMARGIN", new_y="NEXT", align="C")

    return bytes(pdf.output())


def _section_heading(pdf, text):
    """Render a section heading."""
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_fill_color(230, 236, 245)
    pdf.cell(0, 8, f"  {text}", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(2)


def _table_header(pdf, headers, widths):
    """Render a table header row."""
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(41, 65, 122)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(0, 0, 0)


def _safe(value):
    """Convert value to string safely for PDF output."""
    if value is None:
        return ""
    return str(value)
