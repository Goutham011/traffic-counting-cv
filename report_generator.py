"""
Summary report generation (HTML). Downloadable and human-readable.
"""

from pathlib import Path
from datetime import datetime
from typing import Optional

from config import REPORT_DIR
from analytics import TrafficStats


REPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Traffic Counting Report</title>
  <style>
    body { 
      font-family: system-ui, -apple-system, sans-serif; 
      max-width: 900px; 
      margin: 2rem auto; 
      padding: 0 1rem; 
      background: #ffffff;
      color: #1a1a1a;
    }
    h1 { 
      color: #1a1a2e; 
      border-bottom: 3px solid #3b82f6; 
      padding-bottom: 0.5rem; 
      margin-bottom: 1rem;
    }
    h2 { 
      color: #1e40af; 
      margin-top: 2rem; 
      padding-bottom: 0.3rem;
      border-bottom: 2px solid #e5e7eb;
    }
    table { 
      border-collapse: collapse; 
      width: 100%; 
      margin: 1rem 0; 
      background: white;
      box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    th, td { 
      border: 1px solid #d1d5db; 
      padding: 0.75rem 1rem; 
      text-align: left; 
    }
    th { 
      background: #3b82f6; 
      color: white; 
      font-weight: 600;
    }
    tr:nth-child(even) { 
      background: #f9fafb; 
    }
    tr:hover {
      background: #f3f4f6;
    }
    .summary { 
      background: #eff6ff; 
      padding: 1.5rem; 
      border-radius: 12px; 
      margin: 1.5rem 0; 
      border: 2px solid #3b82f6;
    }
    .metric { 
      font-size: 1.5rem; 
      font-weight: bold; 
      color: #1e40af; 
    }
    img { 
      max-width: 100%; 
      height: auto; 
      border-radius: 8px; 
      box-shadow: 0 2px 8px rgba(0,0,0,0.15);
      border: 1px solid #e5e7eb;
    }
    .fig { 
      margin: 2rem 0; 
      text-align: center;
    }
    .meta { 
      color: #6b7280; 
      font-size: 0.9rem; 
    }
    
    /* Button container */
    .button-container {
      display: flex;
      gap: 1rem;
      margin: 2rem 0;
      padding-bottom: 1rem;
      border-bottom: 2px solid #e5e7eb;
    }
    
    /* Button styles */
    .btn {
      padding: 0.75rem 1.5rem;
      border-radius: 8px;
      font-weight: 600;
      text-decoration: none;
      cursor: pointer;
      border: none;
      font-size: 1rem;
      transition: all 0.3s ease;
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
    }
    
    .btn-primary {
      background: #3b82f6;
      color: white;
    }
    
    .btn-primary:hover {
      background: #2563eb;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
    }
    
    .btn-secondary {
      background: #10b981;
      color: white;
    }
    
    .btn-secondary:hover {
      background: #059669;
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }
    
    /* Hide buttons when printing */
    @media print {
      .button-container {
        display: none;
      }
      body {
        margin: 0;
        padding: 1rem;
      }
    }
  </style>
</head>
<body>
  <!-- Print Button -->
  <div class="button-container">
    <button onclick="window.print()" class="btn btn-secondary">
      <span>🖨</span> Print Report
    </button>
  </div>

  <h1>Traffic Counting & Vehicle Categorization Report</h1>
  <p class="meta">Generated: {{ report_time }} | Video: {{ video_name }} | Duration: {{ duration_sec }} s</p>

  <div class="summary">
    <h2 style="margin-top: 0; border: none;">Summary</h2>
    <p><span class="metric">Vehicles detected (all green boxes):</span> {{ total_detected }}</p>
    <p><span class="metric">Vehicles counted (crossed line):</span> {{ total_count }}</p>
    <p>Detected = every unique vehicle seen in the video (matches the green boxes). Counted = those whose centroid crossed the counting line.</p>
  </div>

  <h2>Category-wise distribution (all detected vehicles)</h2>
  <p class="meta">Breakdown of every vehicle shown in the annotated video (green boxes).</p>
  {% if detected_category_rows %}
  <table>
    <thead><tr><th>Category</th><th>Count</th><th>Share</th></tr></thead>
    <tbody>
      {% for cat, count in detected_category_rows %}
      <tr><td>{{ cat }}</td><td>{{ count }}</td><td>{{ ((count / total_detected * 100) | round(1)) if total_detected else 0 }}%</td></tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="meta">No vehicles detected.</p>
  {% endif %}

  <h2>Category-wise distribution (counted – crossed line only)</h2>
  {% if category_rows %}
  <table>
    <thead><tr><th>Category</th><th>Count</th><th>Share</th></tr></thead>
    <tbody>
      {% for cat, count in category_rows %}
      <tr><td>{{ cat }}</td><td>{{ count }}</td><td>{{ ((count / total_count * 100) | round(1)) if total_count else 0 }}%</td></tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="meta">No vehicles crossed the counting line. The table above shows all detected vehicles.</p>
  {% endif %}

  {% if chart_paths %}
  <h2>Analytics</h2>
  {% for path in chart_paths %}
  <div class="fig">
    <img src="{{ path }}" alt="Chart" style="max-width: 600px;" />
  </div>
  {% endfor %}
  {% endif %}

  <h2>Crossing events (sample)</h2>
  {% if sample_events %}
  <p>First 50 crossing events (track_id, category, time in seconds).</p>
  <table>
    <thead><tr><th>#</th><th>Track ID</th><th>Category</th><th>Time (s)</th></tr></thead>
    <tbody>
      {% for evt in sample_events %}
      <tr><td>{{ loop.index }}</td><td>{{ evt.track_id }}</td><td>{{ evt.category }}</td><td>{{ (evt.timestamp_sec | round(2)) }}</td></tr>
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="meta">No crossing events. Vehicles were detected but none crossed the counting line.</p>
  {% endif %}

  <p class="meta">End of report. Annotated video and raw data are in the output folder.</p>
</body>
</html>
"""


def generate_html_report(
    stats: TrafficStats,
    video_name: str = "input_video",
    duration_sec: float = 0,
    chart_paths: Optional[list] = None,
    output_path: Optional[Path] = None,
    total_detected: Optional[int] = None,
    detected_category_counts: Optional[dict] = None,
) -> Path:
    """
    Generate an HTML summary report. chart_paths are paths to PNGs (will be referenced by name).
    total_detected = number of unique vehicle tracks seen (for "detected" in report).
    """
    try:
        from jinja2 import Template
    except ImportError:
        output_path = output_path or REPORT_DIR / "traffic_report.html"
        with open(output_path, "w") as f:
            f.write(f"<html><body><h1>Traffic Report</h1><p>Total count: {stats.total_count}</p>")
            f.write("<p>Install jinja2 for full report.</p></body></html>")
        return output_path

    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_count = stats.total_count
    total_detected = total_detected if total_detected is not None else total_count
    detected_category_rows = list((detected_category_counts or {}).items())
    category_rows = list(stats.category_counts.items())
    sample_events = stats.events[:50]
    chart_paths = chart_paths or []
    # Paths relative to report file (report in output/reports/, charts in output/analytics/)
    chart_refs = [f"../analytics/{Path(p).name}" for p in chart_paths]

    template = Template(REPORT_TEMPLATE)
    html = template.render(
        report_time=report_time,
        video_name=video_name,
        duration_sec=round(duration_sec, 1),
        total_count=total_count,
        total_detected=total_detected,
        detected_category_rows=detected_category_rows,
        category_rows=category_rows,
        sample_events=sample_events,
        chart_paths=chart_refs,
    )

    output_path = output_path or REPORT_DIR / "traffic_report.html"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    # If charts are in a different folder, copy or ensure report can find them
    # Here we assume report is saved in REPORT_DIR and charts in ANALYTICS_DIR;
    # we reference by name, so either save report next to charts or use same dir
    return output_path
