"""
Traffic Counting and Vehicle Categorization - Main entry point.

Usage:
  python main.py --video path/to/traffic_video.mp4
  python main.py --video path/to/video.mp4 --no-annotate   # skip annotated video
  python main.py --video path/to/video.mp4 --max-frames 500 # process first 500 frames

For a sample video, use any public traffic/CCTV clip (e.g. from Pexels, Pixabay)
or place your file in the project folder and pass its path.
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    TrafficCountingConfig,
    VideoConfig,
    ANNOTATED_VIDEO_DIR,
    ANALYTICS_DIR,
    REPORT_DIR,
)
from video_processor import VideoProcessor
from analytics import compute_stats
from visualizer import draw_on_frame, generate_dashboard
from report_generator import generate_html_report


def main():
    parser = argparse.ArgumentParser(
        description="Traffic counting and vehicle categorization using YOLO and line-crossing logic."
    )
    parser.add_argument(
        "--video",
        "-v",
        required=True,
        help="Path to input traffic/CCTV video file (or URL for future real-time).",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory for all outputs (default: project output/).",
    )
    parser.add_argument(
        "--no-annotate",
        action="store_true",
        help="Do not write annotated video (faster run).",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=None,
        help="Process only the first N frames (useful for quick tests).",
    )
    parser.add_argument(
        "--line-y",
        type=float,
        default=0.72,
        help="Relative Y position of counting line (0-1, default 0.72).",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.5,
        help="Detection confidence threshold (default 0.5).",
    )
    args = parser.parse_args()

    video_path = args.video
    if not Path(video_path).exists() and not video_path.startswith(("http", "rtsp")):
        print(f"Error: Video file not found: {video_path}")
        print("Use a local file path or a public URL. For testing, download a short traffic clip (e.g. from Pexels).")
        sys.exit(1)

    # Build config
    config = TrafficCountingConfig.from_video_path(video_path)
    config.video.video_path = video_path
    config.counting_line.line_start_rel = (0.0, args.line_y)
    config.counting_line.line_end_rel = (1.0, args.line_y)
    config.detection.confidence_threshold = args.confidence

    if args.output_dir:
        out_root = Path(args.output_dir)
        config.video.output_video_name = out_root / "annotated_traffic"
        # We'll still use module-level OUTPUT_DIR for analytics/reports unless we add overrides
        # For simplicity we keep writing to PROJECT output/; override can copy later
        pass

    print("Opening video...")
    processor = VideoProcessor(config)
    if not processor.open(video_path):
        print("Failed to open video.")
        sys.exit(1)

    video_name = Path(video_path).name
    duration_sec = processor.total_frames / processor.fps if processor.fps > 0 else 0
    print(f"Video: {video_name} | Frames: {processor.total_frames} | FPS: {processor.fps:.1f}")

    # Optional: write annotated video
    if not args.no_annotate:
        out_video_path = ANNOTATED_VIDEO_DIR / f"annotated_{Path(video_path).stem}.mp4"
        if processor.start_annotated_writer(str(out_video_path)):
            print(f"Writing annotated video to: {out_video_path}")
        else:
            print("Warning: Could not create output video writer.")

    def draw_cb(frame, result):
        draw_on_frame(frame, result, processor.counter)

    print("Processing frames (detection + tracking + counting)...")
    cross_events = processor.run(
        progress_callback=lambda i, total, res: (
            print(f"\r  Frame {i + 1}" + (f"/{total}" if total else ""), end="", flush=True)
        ),
        draw_callback=draw_cb if not args.no_annotate else None,
        max_frames=args.max_frames,
    )
    processor.close()
    print("\nDone.")

    # Statistics
    stats = compute_stats(
        cross_events,
        config=config.analytics,
        video_duration_sec=duration_sec,
    )
    print(f"\nTotal vehicles counted: {stats.total_count}")
    print("By category:", stats.category_counts)

    # Dashboard (graphs) – show only counted vehicles (crossed the line), matching customtkinter GUI
    detected_category_counts = processor.counter.get_detected_category_counts() if processor.counter else {}
    chart_paths = generate_dashboard(stats, ANALYTICS_DIR, detected_category_counts=None)
    print(f"Analytics charts saved to: {ANALYTICS_DIR}")

    # HTML report: include all detected vehicles (green boxes) with category breakdown
    total_detected = len(processor.counter.all_track_ids_seen) if processor.counter else 0
    report_path = generate_html_report(
        stats,
        video_name=video_name,
        duration_sec=duration_sec,
        chart_paths=chart_paths,
        output_path=REPORT_DIR / "traffic_report.html",
        total_detected=total_detected,
        detected_category_counts=detected_category_counts,
    )
    print(f"Report saved to: {report_path}")

    # Optional: save raw events to CSV for further analysis
    if stats.events:
        import csv
        csv_path = PROJECT_ROOT / "output" / "data" / "crossing_events.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["track_id", "category", "frame_index", "timestamp_sec"])
            for e in stats.events:
                w.writerow([e.track_id, e.category, e.frame_index, e.timestamp_sec])
        print(f"Events CSV: {csv_path}")

    print("\nSummary: annotated video, analytics charts, HTML report, and CSV are in the output folder.")


if __name__ == "__main__":
    main()
