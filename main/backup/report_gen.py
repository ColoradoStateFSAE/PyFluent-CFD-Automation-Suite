# report_gen.py
# Generates PDF analysis reports for Ram Racing FSAE Aero Automation Suite

import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors


def generate_report(results: dict, outdir: str) -> str:
    """
    Generates a PDF CFD report for a simulation.

    Parameters
    ----------
    results : dict
        {
            "component": "Undertray",
            "geom": "/path/to/file.stp",
            "mesh_file": "/path/to/mesh.msh.h5",
            "coeffs": {"Cd": ..., "Cl": ..., "SCx": ..., "SCz": ...},
            "dimensions": {"L":..., "W":..., "H":...},
            "contours": {
                "pressure": ".../pressure.png",
                "velocity": ".../velocity.png",
                "residuals": ".../residuals.png"
            }
        }
    outdir : str
        Directory to save the final PDF

    Returns
    -------
    str : full path to generated PDF
    """

    pdf_path = os.path.join(outdir, "report.pdf")

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    styles = getSampleStyleSheet()
    flow = []

    # ------------------------------------------------------------
    # Title
    # ------------------------------------------------------------
    title = Paragraph(
        "<para align='center'><b><font size=20>Ram Racing FSAE Aero Automation Suite</font></b></para>",
        styles["Title"]
    )
    flow.append(title)
    flow.append(Spacer(1, 24))

    subtitle = Paragraph(
        f"<para align='center'><font size=14>CFD Report — {results.get('component','Component')}</font></para>",
        styles["Title"]
    )
    flow.append(subtitle)
    flow.append(Spacer(1, 36))

    # ------------------------------------------------------------
    # Simulation Information Table
    # ------------------------------------------------------------
    info_data = [
        ["Geometry File:", results.get("geom", "N/A")],
        ["Mesh File:", results.get("mesh_file", "N/A")],
        ["Vehicle Dimensions (L/W/H):",
         f"{results['dimensions']['L']}  /  {results['dimensions']['W']}  /  {results['dimensions']['H']} m"],
    ]

    info_table = Table(info_data, colWidths=[160, 360])
    info_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.black),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
    ]))
    flow.append(info_table)
    flow.append(Spacer(1, 24))

    # ------------------------------------------------------------
    # Aerodynamic Coefficients Section
    # ------------------------------------------------------------
    coeffs = results.get("coeffs", {})
    coeff_table_data = [
        ["Coefficient", "Value"],
        ["Cd", f"{coeffs.get('Cd','N/A'):.5f}"],
        ["Cl", f"{coeffs.get('Cl','N/A'):.5f}"],
        ["SCx", f"{coeffs.get('SCx','N/A'):.5f}"],
        ["SCz", f"{coeffs.get('SCz','N/A'):.5f}"],
    ]

    coeff_table = Table(coeff_table_data, colWidths=[200, 150])
    coeff_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
    ]))

    header = Paragraph("<b><font size=14>Aerodynamic Coefficients</font></b>", styles["Heading2"])
    flow.append(header)
    flow.append(Spacer(1, 12))
    flow.append(coeff_table)
    flow.append(Spacer(1, 24))

    # ------------------------------------------------------------
    # Contour Images (Pressure / Velocity)
    # ------------------------------------------------------------
    contours = results.get("contours", {})

    if os.path.exists(contours.get("pressure", "")):
        flow.append(Paragraph("<b>Pressure Contour</b>", styles["Heading3"]))
        flow.append(Image(contours["pressure"], width=420, height=280))
        flow.append(Spacer(1, 18))

    if os.path.exists(contours.get("velocity", "")):
        flow.append(Paragraph("<b>Velocity Contour</b>", styles["Heading3"]))
        flow.append(Image(contours["velocity"], width=420, height=280))
        flow.append(Spacer(1, 18))

    if os.path.exists(contours.get("residuals", "")):
        flow.append(Paragraph("<b>Residual Plot</b>", styles["Heading3"]))
        flow.append(Image(contours["residuals"], width=420, height=280))
        flow.append(Spacer(1, 18))

    # ------------------------------------------------------------
    # Notes Section
    # ------------------------------------------------------------
    notes = Paragraph(
        "<b>Notes:</b><br/>"
        "This report was automatically generated by the "
        "<i>Ram Racing FSAE Aero Automation Suite</i> using Ansys Fluent Python automation.",
        styles["BodyText"]
    )
    flow.append(notes)

    # ------------------------------------------------------------
    # Build PDF
    # ------------------------------------------------------------
    doc.build(flow)

    return pdf_path
