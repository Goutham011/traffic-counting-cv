"""
Generate PROJECT_REPORT.pdf aligned with the challenge expected report structure.
Run: python generate_project_report_pdf.py
Output: PROJECT_REPORT.pdf (in project root)
"""

from pathlib import Path

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
except ImportError:
    print("Install reportlab: pip install reportlab")
    raise

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = PROJECT_ROOT / "PROJECT_REPORT.pdf"


def build_pdf(path: Path) -> None:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        rightMargin=inch,
        leftMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Section", fontSize=14, spaceAfter=12, textColor=colors.HexColor("#16213e")))
    styles.add(ParagraphStyle(name="SubSection", fontSize=12, spaceAfter=6, spaceBefore=12, textColor=colors.HexColor("#1a1a2e")))
    styles.add(ParagraphStyle(name="Body", fontSize=10, spaceAfter=6, leading=14))

    story = []

    # Title
    story.append(Paragraph("Traffic Counting and Vehicle Categorization using Computer Vision", styles["Title"]))
    story.append(Paragraph("Project Report", styles["Heading1"]))
    story.append(Spacer(1, 0.15 * inch))
    story.append(Paragraph("Challenge: Proof-of-concept computer vision system for traffic analysis using pre-recorded traffic/CCTV video", styles["Body"]))
    story.append(Paragraph("Date: January 2025", styles["Body"]))
    story.append(Spacer(1, 0.3 * inch))

    # 1. Core Solution Concept
    story.append(Paragraph("1. Core Solution Concept", styles["Section"]))
    story.append(Paragraph(
        "The system is a modular pipeline that takes a pre-recorded traffic or CCTV video as input and produces "
        "automated vehicle counts, category-wise distribution, and traffic density over time."
    , styles["Body"]))
    story.append(Paragraph(
        "<b>Deep learning–based detection:</b> A YOLO model identifies and classifies vehicles (cars, motorcycles, "
        "buses, trucks) in each frame. <b>Object tracking:</b> ByteTrack assigns a unique ID to each vehicle to avoid "
        "duplicate counts. <b>Virtual counting line:</b> A vehicle is counted only once when its centroid crosses a "
        "user-defined line. <b>Outputs:</b> Total count, category-wise distribution, traffic density over time, "
        "annotated video with bounding boxes and IDs, visual analytics (graphs/dashboards), and a downloadable summary report. "
        "The solution is modular and suitable for extension to real-time CCTV feeds.",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    # 2. Unique Value Proposition
    story.append(Paragraph("2. Unique Value Proposition", styles["Section"]))
    story.append(Paragraph(
        "• <b>One count per vehicle:</b> Tracking + virtual line ensures each vehicle is counted exactly once.<br/>"
        "• <b>Stable category:</b> Majority-vote category over the track lifetime reduces misclassification.<br/>"
        "• <b>User-configurable line and thresholds:</b> Line position (Y), confidence, and direction (up/down/both) are configurable.<br/>"
        "• <b>Dual interfaces:</b> Desktop GUI (CustomTkinter, tabbed) and optional web interface (Flask).<br/>"
        "• <b>Consistent analytics:</b> All outputs use the same counted events so numbers add up.<br/>"
        "• <b>Extensible design:</b> Same pipeline can be extended to live CCTV (RTSP/HTTP stream).",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    # 3. Key Technologies and Data Used
    story.append(Paragraph("3. Key Technologies and Data Used", styles["Section"]))
    story.append(Paragraph("3.1 Technologies", styles["SubSection"]))
    data_tech = [
        ["Technology", "Purpose"],
        ["Python 3.8+", "Implementation language"],
        ["YOLO (Ultralytics)", "Deep learning object detection; vehicle classification"],
        ["ByteTrack", "Multi-object tracking; unique IDs across frames"],
        ["OpenCV (cv2)", "Video I/O, drawing bounding boxes and counting line"],
        ["CustomTkinter", "Desktop GUI (tabs, cards, modern theme)"],
        ["Flask", "Web server for interactive web dashboard"],
        ["Pandas / NumPy", "Aggregation, time-window statistics"],
        ["Matplotlib", "Visual analytics (category, density, over time)"],
        ["Jinja2", "HTML report templating"],
    ]
    t = Table(data_tech, colWidths=[2 * inch, 4 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(Paragraph("3.2 Data", styles["SubSection"]))
    story.append(Paragraph(
        "Input: Pre-recorded traffic or CCTV video (MP4, AVI) from publicly available sources. Pre-trained YOLO (e.g. COCO) "
        "with vehicle classes (car, motorcycle, bus, truck, bicycle). No custom training data required. "
        "Output: Crossing events (track_id, category, timestamp), aggregated counts, category distribution, time-window counts.",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    # 4. Methodology
    story.append(Paragraph("4. Methodology", styles["Section"]))
    story.append(Paragraph(
        "<b>Detection:</b> YOLOv8 (nano/small/medium) pre-trained on COCO; vehicle classes only; outputs bounding box, class, confidence, track_id.<br/>"
        "<b>Tracking:</b> ByteTrack assigns and maintains unique ID per vehicle across frames.<br/>"
        "<b>Virtual counting line:</b> Line defined by two points (e.g. full width at Y). Centroid of each vehicle tested; "
        "crossing = centroid moves from one side to the other in configured direction. Each track_id counted at most once.<br/>"
        "<b>Category:</b> Per-track histogram; at crossing, category = majority vote. Names normalized (e.g. bus/Bus → Bus).<br/>"
        "<b>Analytics:</b> Total = crossing events; category distribution = events per category; density over time = events per time window (e.g. 60 s).",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    # 5. Documentation of Dashboard Functionalities and Analytical Outputs
    story.append(Paragraph("5. Documentation of Dashboard Functionalities and Analytical Outputs", styles["Section"]))
    story.append(Paragraph("5.1 Desktop Dashboard (CustomTkinter)", styles["SubSection"]))
    story.append(Paragraph(
        "Setup: Select video, line position (Y), confidence, options (annotated video, frame limit). Next → Run. "
        "Run: Start/Stop, progress bar, status. Results: Total (detected vs counted), category breakdown (counted). Next → Output. "
        "Output: Open report, open folder, play annotated video.",
        styles["Body"],
    ))
    story.append(Paragraph("5.2 Web Dashboard (Flask)", styles["SubSection"]))
    story.append(Paragraph(
        "Upload video; set line Y, confidence, frame limit; run processing; view total and category breakdown; view report and annotated video.",
        styles["Body"],
    ))
    story.append(Paragraph("5.3 Analytical Outputs", styles["SubSection"]))
    story.append(Paragraph(
        "Total vehicle count; category-wise distribution (Car, Bus, Truck, etc.); traffic density over time; category over time; "
        "annotated video (boxes, IDs, line); downloadable HTML report (summary, tables, charts, sample events). Optional PDF report.",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    # 6. Policy and Architectural Recommendations
    story.append(Paragraph("6. Policy and Architectural Recommendations", styles["Section"]))
    story.append(Paragraph("6.1 Policy", styles["SubSection"]))
    story.append(Paragraph(
        "Privacy and compliance: Use only videos with appropriate rights; for CCTV, comply with local data protection and surveillance laws. "
        "Transparency: Document what is counted and how. Human oversight: Treat automated counts as decision support where policy requires.",
        styles["Body"],
    ))
    story.append(Paragraph("6.2 Architecture", styles["SubSection"]))
    story.append(Paragraph(
        "Modularity: Keep detection, tracking, counting, analytics, UI separate. Configuration: Central config for model, line, confidence, paths. "
        "Extensibility: Design video source as abstraction (file vs stream) for real-time CCTV. Scalability: GPU server, database for events, REST + web for dashboards.",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    # 7. Interactive Dashboard / Source Code / URL
    story.append(Paragraph("7. Interactive Dashboard / Source Code / URL (if applicable)", styles["Section"]))
    story.append(Paragraph(
        "Source code: Full Python project (modular). Desktop: python gui.py. Web: python web_gui.py → http://localhost:5000. "
        "Repository / URL: (Add your GitHub/GitLab or deployed demo URL here.)",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    # 8. Final Presentation (PPT / Short Demo Video)
    story.append(Paragraph("8. Final Presentation (PPT / Short Demo Video)", styles["Section"]))
    story.append(Paragraph(
        "PPT: Title, core concept, value proposition, technologies, methodology, dashboard outputs, policy/architecture, demo, conclusion. "
        "Demo video: 3–5 min screen recording (select video, set line, run, view results, report, annotated video, charts). "
        "(Add link to PPT or demo video here.)",
        styles["Body"],
    ))
    story.append(Spacer(1, 0.2 * inch))

    # References
    story.append(Paragraph("References", styles["Section"]))
    story.append(Paragraph("Ultralytics YOLO: https://github.com/ultralytics/ultralytics", styles["Body"]))
    story.append(Paragraph("ByteTrack: Multi-Object Tracking by Associating Every Detection Box", styles["Body"]))
    story.append(Paragraph("OpenCV: https://opencv.org/", styles["Body"]))
    story.append(Paragraph("CustomTkinter: https://github.com/TomSchimansky/CustomTkinter", styles["Body"]))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph("End of Project Report", styles["Body"]))

    doc.build(story)


def main():
    path = OUTPUT_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    build_pdf(path)
    print(f"PDF saved: {path}")


if __name__ == "__main__":
    main()
