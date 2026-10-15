"""
Traffic Counting GUI – modern tabbed interface.
Run: python gui.py
"""

import sys
import threading
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional, Any

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import customtkinter as ctk
from tkinter import filedialog, messagebox

# Project imports
from config import (
    TrafficCountingConfig,
    ANNOTATED_VIDEO_DIR,
    ANALYTICS_DIR,
    REPORT_DIR,
    OUTPUT_DIR,
)
from video_processor import VideoProcessor
from analytics import compute_stats
from visualizer import draw_on_frame, generate_dashboard
from report_generator import generate_html_report


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLORS = {
    "surface": ("#ffffff", "#252a33"),
    "surface_hover": ("#e8eaed", "#2d333b"),
    "accent": "#3b82f6",
    "accent_hover": "#2563eb",
    "danger": "#ef4444",
    "danger_hover": "#dc2626",
    "success": "#22c55e",
    "text": ("#1a1d23", "#e5e7eb"),
    "text_secondary": ("#6b7280", "#9ca3af"),
    "border": ("#e5e7eb", "#374151"),
}


class TrafficCountingGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Traffic Counting")
        self.geometry("900x720")
        self.minsize(720, 600)
        self.grid_columnconfigure(0, weight=1)
        # Full screen (maximized) by default after window is shown
        self.after(100, self._maximize_window)

        self._video_path = ctk.StringVar(value="")
        self._line_y = ctk.DoubleVar(value=0.72)
        self._confidence = ctk.DoubleVar(value=0.5)
        self._write_annotated = ctk.BooleanVar(value=True)
        self._limit_frames = ctk.StringVar(value="0")
        self._stop_requested = threading.Event()
        self._processing = False
        self._last_report_path: Optional[Path] = None
        self._last_annotated_path: Optional[Path] = None
        self._last_stats: Optional[Any] = None

        self._build_ui()

    def _card(self, parent, **kwargs):
        return ctk.CTkFrame(
            parent,
            fg_color=COLORS["surface"],
            corner_radius=14,
            border_width=0,
            **kwargs,
        )

    def _label_section(self, parent, text: str):
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"],
        )

    def _maximize_window(self):
        """Maximize window (full screen by default)."""
        try:
            self.state("zoomed")
        except Exception:
            pass

    def _build_ui(self):
        # ---- Top header ----
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=28, pady=(24, 16))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            header,
            text="Traffic Counting",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=COLORS["text"],
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Detect vehicles, track crossings, and view results by tab",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w")

        # ---- Tabview ----
        self._tabview = ctk.CTkTabview(
            self,
            width=0,
            height=0,
            corner_radius=12,
            fg_color=COLORS["surface"],
            segmented_button_fg_color=COLORS["surface_hover"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
            segmented_button_unselected_hover_color=COLORS["surface_hover"],
            text_color=COLORS["text"][1],
        )
        self._tabview.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        self._tabview.grid_columnconfigure(0, weight=1)

        # Tab names
        self._tabview.add("Setup")
        self._tabview.add("Run")
        self._tabview.add("Results")
        self._tabview.add("Output")
        self._tabview.set("Setup")

        # ---- Tab: Setup ----
        setup_tab = self._tabview.tab("Setup")
        setup_tab.grid_columnconfigure(0, weight=1)
        setup_inner = ctk.CTkFrame(setup_tab, fg_color="transparent")
        setup_inner.pack(fill="both", expand=True, padx=24, pady=24)
        setup_inner.grid_columnconfigure(0, weight=1)

        # Video card
        video_card = self._card(setup_inner)
        video_card.pack(fill="x", pady=(0, 16))
        video_card.grid_columnconfigure(0, weight=1)
        v_inner = ctk.CTkFrame(video_card, fg_color="transparent")
        v_inner.pack(fill="x", padx=20, pady=18)
        v_inner.grid_columnconfigure(0, weight=1)
        self._label_section(v_inner, "VIDEO SOURCE").pack(anchor="w", pady=(0, 10))
        v_row = ctk.CTkFrame(v_inner, fg_color="transparent")
        v_row.pack(fill="x")
        v_row.grid_columnconfigure(0, weight=1)
        self._video_entry = ctk.CTkEntry(
            v_row,
            textvariable=self._video_path,
            placeholder_text="Path to traffic video...",
            height=42,
            width=400,
            corner_radius=10,
            font=ctk.CTkFont(size=13),
        )
        self._video_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._btn_browse = ctk.CTkButton(
            v_row,
            text="Browse",
            width=100,
            height=42,
            corner_radius=10,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._browse_video,
        )
        self._btn_browse.pack(side="left")

        # Counting line & detection card
        settings_card = self._card(setup_inner)
        settings_card.pack(fill="x", pady=(0, 16))
        settings_card.grid_columnconfigure(0, weight=1)
        s_inner = ctk.CTkFrame(settings_card, fg_color="transparent")
        s_inner.pack(fill="x", padx=20, pady=18)
        s_inner.grid_columnconfigure(0, weight=1)
        self._label_section(s_inner, "COUNTING LINE & DETECTION").pack(anchor="w", pady=(0, 14))

        line_row = ctk.CTkFrame(s_inner, fg_color="transparent")
        line_row.pack(fill="x", pady=6)
        line_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(line_row, text="Line position (Y)", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", padx=(0, 16))
        sl = ctk.CTkSlider(line_row, from_=0.1, to=0.9, variable=self._line_y, width=240, height=18, corner_radius=8)
        sl.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        self._line_label = ctk.CTkLabel(line_row, text="0.72", font=ctk.CTkFont(size=13, weight="bold"), width=40)
        self._line_label.grid(row=0, column=2, sticky="e")
        sl.configure(command=lambda v: self._line_label.configure(text=f"{float(v):.2f}"))

        conf_row = ctk.CTkFrame(s_inner, fg_color="transparent")
        conf_row.pack(fill="x", pady=6)
        conf_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(conf_row, text="Confidence", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w", padx=(0, 16))
        sl_conf = ctk.CTkSlider(conf_row, from_=0.2, to=0.95, variable=self._confidence, width=240, height=18, corner_radius=8)
        sl_conf.grid(row=0, column=1, sticky="ew", padx=(0, 12))
        self._conf_label = ctk.CTkLabel(conf_row, text="0.50", font=ctk.CTkFont(size=13, weight="bold"), width=40)
        self._conf_label.grid(row=0, column=2, sticky="e")
        sl_conf.configure(command=lambda v: self._conf_label.configure(text=f"{float(v):.2f}"))

        self._label_section(s_inner, "OPTIONS").pack(anchor="w", pady=(16, 10))
        opt_row = ctk.CTkFrame(s_inner, fg_color="transparent")
        opt_row.pack(fill="x", pady=4)
        opt_row.grid_columnconfigure(1, weight=1)
        ctk.CTkCheckBox(
            opt_row,
            text="Write annotated video",
            variable=self._write_annotated,
            font=ctk.CTkFont(size=13),
        ).grid(row=0, column=0, sticky="w", padx=(0, 24))
        ctk.CTkLabel(opt_row, text="Limit frames (0 = all)", font=ctk.CTkFont(size=13)).grid(row=0, column=1, sticky="w", padx=(0, 8))
        ctk.CTkEntry(opt_row, textvariable=self._limit_frames, width=80, height=34, corner_radius=8).grid(row=0, column=2, sticky="e")

        # Setup tab: Next → Run
        setup_btn_row = ctk.CTkFrame(setup_inner, fg_color="transparent")
        setup_btn_row.pack(fill="x", pady=(24, 0))
        setup_btn_row.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            setup_btn_row,
            text="Next → Run",
            height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=lambda: self._tabview.set("Run"),
        ).pack(side="right")

        # ---- Tab: Run ----
        run_tab = self._tabview.tab("Run")
        run_tab.grid_columnconfigure(0, weight=1)
        run_inner = ctk.CTkFrame(run_tab, fg_color="transparent")
        run_inner.pack(fill="both", expand=True, padx=24, pady=24)
        run_inner.grid_columnconfigure(0, weight=1)

        self._label_section(run_inner, "CONTROLS").pack(anchor="w", pady=(0, 12))
        btn_row = ctk.CTkFrame(run_inner, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 24))
        self._btn_start = ctk.CTkButton(
            btn_row,
            text="Start processing",
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=self._start_processing,
        )
        self._btn_start.pack(side="left", padx=(0, 12))
        self._btn_stop = ctk.CTkButton(
            btn_row,
            text="Stop",
            width=110,
            height=48,
            corner_radius=12,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=COLORS["danger"],
            hover_color=COLORS["danger_hover"],
            state="disabled",
            command=self._request_stop,
        )
        self._btn_stop.pack(side="left")

        self._label_section(run_inner, "PROGRESS").pack(anchor="w", pady=(0, 10))
        self._status_label = ctk.CTkLabel(
            run_inner,
            text="Ready. Choose a video in Setup, then start.",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
        )
        self._status_label.pack(anchor="w", pady=(0, 10))
        self._progress = ctk.CTkProgressBar(
            run_inner,
            height=10,
            corner_radius=5,
            progress_color=COLORS["accent"],
            fg_color=COLORS["border"][1],
        )
        self._progress.pack(fill="x", pady=(0, 8))
        self._progress.set(0)

        # ---- Tab: Results ----
        results_tab = self._tabview.tab("Results")
        results_tab.grid_columnconfigure(0, weight=1)
        res_inner = ctk.CTkScrollableFrame(results_tab, fg_color="transparent")
        res_inner.pack(fill="both", expand=True, padx=24, pady=24)
        res_inner.grid_columnconfigure(0, weight=1)

        self._label_section(res_inner, "SUMMARY").pack(anchor="w", pady=(0, 10))
        self._total_label = ctk.CTkLabel(
            res_inner,
            text="Total: —",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=COLORS["text"],
        )
        self._total_label.pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(
            res_inner,
            text="By category (counted = crossed line; adds up to total above)",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(0, 14))
        self._category_frame = ctk.CTkScrollableFrame(
            res_inner,
            fg_color="transparent",
            height=200,
            scrollbar_button_color=COLORS["surface"],
            scrollbar_button_hover_color=COLORS["surface_hover"],
        )
        self._category_frame.pack(fill="both", expand=True)
        self._category_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self._category_frame,
            text="Run processing to see category breakdown.",
            font=ctk.CTkFont(size=13),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w")

        # Results tab: Next → Output
        res_btn_row = ctk.CTkFrame(res_inner, fg_color="transparent")
        res_btn_row.pack(fill="x", pady=(24, 0))
        res_btn_row.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(
            res_btn_row,
            text="Next → Output",
            height=44,
            corner_radius=10,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=lambda: self._tabview.set("Output"),
        ).pack(side="right")

        # ---- Tab: Output ----
        output_tab = self._tabview.tab("Output")
        output_tab.grid_columnconfigure(0, weight=1)
        out_inner = ctk.CTkFrame(output_tab, fg_color="transparent")
        out_inner.pack(fill="both", expand=True, padx=24, pady=24)
        out_inner.grid_columnconfigure(0, weight=1)

        self._label_section(out_inner, "EXPORT & OPEN").pack(anchor="w", pady=(0, 16))
        out_card = self._card(out_inner)
        out_card.pack(fill="x", pady=(0, 16))
        out_card.grid_columnconfigure(0, weight=1)
        out_btn_inner = ctk.CTkFrame(out_card, fg_color="transparent")
        out_btn_inner.pack(fill="x", padx=20, pady=20)
        out_btn_inner.grid_columnconfigure(0, weight=1)
        out_btn_row = ctk.CTkFrame(out_btn_inner, fg_color="transparent")
        out_btn_row.pack(fill="x")
        self._btn_open_report = ctk.CTkButton(
            out_btn_row,
            text="Open report",
            width=140,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=13),
            state="disabled",
            command=self._open_report,
        )
        self._btn_open_report.pack(side="left", padx=(0, 12))
        self._btn_open_folder = ctk.CTkButton(
            out_btn_row,
            text="Open output folder",
            width=160,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=13),
            command=self._open_folder,
        )
        self._btn_open_folder.pack(side="left", padx=(0, 12))
        self._btn_open_video = ctk.CTkButton(
            out_btn_row,
            text="Play annotated video",
            width=180,
            height=40,
            corner_radius=10,
            font=ctk.CTkFont(size=13),
            state="disabled",
            command=self._play_annotated,
        )
        self._btn_open_video.pack(side="left")

        ctk.CTkLabel(
            out_inner,
            text="Report and annotated video are saved after each run. Use the buttons above to open them.",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        ).pack(anchor="w", pady=(8, 0))

    def _browse_video(self):
        path = filedialog.askopenfilename(
            parent=self,
            title="Select traffic video",
            filetypes=[
                ("Video files", "*.mp4 *.avi *.mkv *.mov *.wmv"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._video_path.set(path)
            self._video_entry.focus_set()

    def _start_processing(self):
        path = self._video_path.get().strip()
        if not path:
            messagebox.showwarning("No video", "Please select a video in the Setup tab.")
            return
        if not Path(path).exists() and not path.startswith(("http", "rtsp")):
            messagebox.showerror("File not found", f"Video not found:\n{path}")
            return

        try:
            max_f = int(self._limit_frames.get().strip() or "0")
            if max_f < 0:
                max_f = 0
        except ValueError:
            max_f = 0

        self._stop_requested.clear()
        self._processing = True
        self._btn_start.configure(state="disabled")
        self._btn_stop.configure(state="normal")
        self._status_label.configure(text="Opening video...")
        self._progress.set(0)
        self._tabview.set("Run")
        self.after(100, lambda: self._run_processing(path, max_f if max_f > 0 else None))

    def _run_processing(self, video_path: str, max_frames: Optional[int]):
        def work():
            try:
                config = TrafficCountingConfig.from_video_path(video_path)
                config.counting_line.line_start_rel = (0.0, self._line_y.get())
                config.counting_line.line_end_rel = (1.0, self._line_y.get())
                config.detection.confidence_threshold = self._confidence.get()

                processor = VideoProcessor(config)
                if not processor.open(video_path):
                    self.after(0, lambda: self._on_error("Could not open video."))
                    return
                duration_sec = processor.total_frames / processor.fps if processor.fps > 0 else 0
                total_f = max_frames or processor.total_frames

                write_annotated = self._write_annotated.get()
                if write_annotated:
                    out_video_path = ANNOTATED_VIDEO_DIR / f"annotated_{Path(video_path).stem}.mp4"
                    processor.start_annotated_writer(str(out_video_path))
                    self._last_annotated_path = out_video_path
                else:
                    self._last_annotated_path = None

                def progress_cb(frame_index: int, total: int, result: Any) -> bool:
                    if self._stop_requested.is_set():
                        return True
                    p = (frame_index + 1) / total if total > 0 else 0
                    cur, cnt = frame_index + 1, result.total_count_so_far
                    self.after(0, lambda c=cur, t=total, n=cnt, pr=p: self._update_progress(c, t, n, pr))
                    return False

                def draw_cb(frame, result):
                    draw_on_frame(frame, result, processor.counter)

                cross_events = processor.run(
                    progress_callback=progress_cb,
                    draw_callback=draw_cb if write_annotated else None,
                    max_frames=max_frames,
                )
                processor.close()

                stats = compute_stats(
                    cross_events,
                    config=config.analytics,
                    video_duration_sec=duration_sec,
                )
                total_detected = len(processor.counter.all_track_ids_seen) if processor.counter else 0
                detected_category_counts = processor.counter.get_detected_category_counts() if processor.counter else {}
                # Use counted-by-category so chart matches Results tab
                chart_paths = generate_dashboard(stats, ANALYTICS_DIR, detected_category_counts=None)
                report_path = generate_html_report(
                    stats,
                    video_name=Path(video_path).name,
                    duration_sec=duration_sec,
                    chart_paths=chart_paths,
                    output_path=REPORT_DIR / "traffic_report.html",
                    total_detected=total_detected,
                    detected_category_counts=detected_category_counts,
                )
                self._last_report_path = report_path
                self._last_stats = stats

                if stats.events:
                    import csv
                    csv_path = OUTPUT_DIR / "data" / "crossing_events.csv"
                    csv_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(csv_path, "w", newline="", encoding="utf-8") as f:
                        w = csv.writer(f)
                        w.writerow(["track_id", "category", "frame_index", "timestamp_sec"])
                        for e in stats.events:
                            w.writerow([e.track_id, e.category, e.frame_index, e.timestamp_sec])

                self.after(0, lambda: self._on_done(stats, total_detected, detected_category_counts))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: self._on_error(msg))

        threading.Thread(target=work, daemon=True).start()

    def _update_progress(self, current: int, total: int, count: int, p: float):
        if not self._processing:
            return
        self._progress.set(p)
        total_str = str(total) if total > 0 else "?"
        self._status_label.configure(text=f"Frame {current}/{total_str} · Count: {count}")

    def _on_done(self, stats, total_detected: int = 0, detected_category_counts: Optional[dict] = None):
        self._processing = False
        self._btn_start.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._progress.set(1)
        self._status_label.configure(text="Done.")
        self._total_label.configure(
            text=f"Detected (all green boxes): {total_detected}  ·  Counted (crossed line): {stats.total_count}"
        )
        for w in self._category_frame.winfo_children():
            w.destroy()
        counts = stats.category_counts
        for cat, count in counts.items():
            card = ctk.CTkFrame(
                self._category_frame,
                fg_color=COLORS["surface_hover"],
                corner_radius=10,
                height=48,
                border_width=0,
            )
            card.pack(fill="x", pady=4)
            card.grid_columnconfigure(0, weight=1)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="both", expand=True, padx=16, pady=10)
            inner.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(inner, text=cat if cat else "Unknown", font=ctk.CTkFont(size=13)).grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(
                inner,
                text=str(count),
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=COLORS["accent"],
            ).grid(row=0, column=1, sticky="e")
        self._btn_open_report.configure(state="normal")
        self._btn_open_video.configure(state="normal" if self._last_annotated_path and self._last_annotated_path.exists() else "disabled")
        self._tabview.set("Results")

    def _on_error(self, msg: str):
        self._processing = False
        self._btn_start.configure(state="normal")
        self._btn_stop.configure(state="disabled")
        self._status_label.configure(text="Error.")
        messagebox.showerror("Error", msg)

    def _request_stop(self):
        self._stop_requested.set()
        self._status_label.configure(text="Stopping...")

    def _open_report(self):
        if self._last_report_path and self._last_report_path.exists():
            webbrowser.open(self._last_report_path.as_uri())
        else:
            report_path = REPORT_DIR / "traffic_report.html"
            if report_path.exists():
                webbrowser.open(report_path.as_uri())
            else:
                messagebox.showinfo("Report", "No report generated yet. Run processing first.")

    def _open_folder(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        path = OUTPUT_DIR.resolve()
        if sys.platform == "win32":
            subprocess.run(["explorer", path], check=False)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)

    def _play_annotated(self):
        if self._last_annotated_path and self._last_annotated_path.exists():
            path = self._last_annotated_path.resolve()
            if sys.platform == "win32":
                subprocess.run(["start", "", str(path)], shell=True, check=False)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        else:
            messagebox.showinfo("Video", "No annotated video from last run. Enable 'Write annotated video' in Setup and run again.")


def main():
    app = TrafficCountingGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
