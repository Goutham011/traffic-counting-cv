"""
Flask web server for Traffic Counting Web GUI
Run: python web_app.py
Then open browser to http://localhost:5000
"""

import os
import sys
import threading
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = OUTPUT_DIR / 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Ensure upload folder exists
app.config['UPLOAD_FOLDER'].mkdir(parents=True, exist_ok=True)

# Processing state
processing_state = {
    'is_processing': False,
    'status': 'Ready',
    'progress': 0.0,
    'current_frame': 0,
    'total_frames': 0,
    'count': 0,
    'error': None,
    'results': None,
    'stop_requested': False,
}


@app.route('/')
def index():
    """Serve the main web GUI"""
    return render_template('index.html')


@app.route('/api/upload', methods=['POST'])
def upload_video():
    """Handle video file upload"""
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        filepath = app.config['UPLOAD_FOLDER'] / filename
        file.save(str(filepath))
        return jsonify({'path': str(filepath), 'filename': filename}), 200


@app.route('/api/process', methods=['POST'])
def start_processing():
    """Start video processing in background thread"""
    global processing_state
    
    if processing_state['is_processing']:
        return jsonify({'error': 'Already processing'}), 400
    
    data = request.json
    video_path = data.get('video_path')
    line_y = float(data.get('line_y', 0.72))
    confidence = float(data.get('confidence', 0.5))
    write_annotated = data.get('write_annotated', True)
    max_frames = int(data.get('max_frames', 0)) or None
    
    if not video_path or not Path(video_path).exists():
        return jsonify({'error': 'Video file not found'}), 400
    
    # Reset state
    processing_state.update({
        'is_processing': True,
        'status': 'Starting...',
        'progress': 0.0,
        'current_frame': 0,
        'total_frames': 0,
        'count': 0,
        'error': None,
        'results': None,
        'stop_requested': False,
    })
    
    # Start processing in background thread
    thread = threading.Thread(
        target=run_processing,
        args=(video_path, line_y, confidence, write_annotated, max_frames),
        daemon=True
    )
    thread.start()
    
    return jsonify({'status': 'started'}), 200


@app.route('/api/stop', methods=['POST'])
def stop_processing():
    """Request to stop processing"""
    global processing_state
    processing_state['stop_requested'] = True
    processing_state['status'] = 'Stopping...'
    return jsonify({'status': 'stop requested'}), 200


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current processing status"""
    return jsonify(processing_state), 200


@app.route('/output/<path:filename>')
def serve_output(filename):
    """Serve files from output directory"""
    # Set proper MIME type for videos
    mimetype = None
    if filename.lower().endswith('.mp4'):
        mimetype = 'video/mp4'
    elif filename.lower().endswith('.avi'):
        mimetype = 'video/x-msvideo'
    
    return send_from_directory(OUTPUT_DIR, filename, mimetype=mimetype, as_attachment=False)


@app.route('/videos')
def video_list():
    """List all available annotated videos"""
    video_dir = ANNOTATED_VIDEO_DIR
    videos = []
    
    if video_dir.exists():
        # Include both .mp4 and .avi files
        for video_file in list(video_dir.glob('*.mp4')) + list(video_dir.glob('*.avi')):
            size_bytes = video_file.stat().st_size
            size_mb = round(size_bytes / (1024 * 1024), 2)
            is_valid = size_bytes >= 1000  # At least 1KB
            
            videos.append({
                'name': video_file.name,
                'size_mb': size_mb,
                'is_valid': is_valid
            })
    
    return render_template('video_list.html', videos=videos)


@app.route('/test-videos')
def test_videos():
    """Simple test page for video playback"""
    return render_template('video_test.html')


@app.route('/api/open-folder', methods=['POST'])
def open_folder():
    """Open output folder in file explorer"""
    try:
        import subprocess
        import platform
        
        folder_path = str(OUTPUT_DIR.resolve())
        
        if platform.system() == 'Windows':
            os.startfile(folder_path)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', folder_path])
        else:  # Linux
            subprocess.run(['xdg-open', folder_path])
        
        return jsonify({'status': 'success', 'message': 'Folder opened'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/download-video', methods=['POST'])
def download_video():
    """Trigger video download/open with default player"""
    try:
        data = request.json
        video_path = data.get('path', '')
        
        if not video_path:
            return jsonify({'status': 'error', 'message': 'No video path provided'}), 400
        
        full_path = (OUTPUT_DIR / video_path).resolve()
        
        if not full_path.exists():
            return jsonify({'status': 'error', 'message': 'Video file not found'}), 404
        
        # Open video with default application
        import subprocess
        import platform
        
        if platform.system() == 'Windows':
            os.startfile(str(full_path))
        elif platform.system() == 'Darwin':  # macOS
            subprocess.run(['open', str(full_path)])
        else:  # Linux
            subprocess.run(['xdg-open', str(full_path)])
        
        return jsonify({'status': 'success', 'message': 'Video opened'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500




@app.route('/video-player')
def video_player():
    """Serve video player page"""
    video_path = request.args.get('video', '')
    if not video_path:
        return "No video specified", 400
    
    # Normalize path separators
    video_path = video_path.replace('\\', '/')
    
    # Verify video file exists
    full_path = OUTPUT_DIR / video_path
    if not full_path.exists():
        return f"Video file not found: {video_path}", 404
    
    # Check if file is valid (not empty or corrupted)
    if full_path.stat().st_size < 1000:  # Less than 1KB is likely corrupted
        return f"Video file appears to be corrupted or empty: {video_path}", 400
    
    return render_template('video_player.html', video_url=f'/output/{video_path}')



def run_processing(video_path: str, line_y: float, confidence: float, write_annotated: bool, max_frames: int):
    """Run video processing (executed in background thread)"""
    global processing_state
    
    try:
        # Create config
        config = TrafficCountingConfig.from_video_path(video_path)
        config.counting_line.line_start_rel = (0.0, line_y)
        config.counting_line.line_end_rel = (1.0, line_y)
        config.detection.confidence_threshold = confidence
        
        # Open video
        processor = VideoProcessor(config)
        if not processor.open(video_path):
            processing_state['error'] = 'Could not open video'
            processing_state['is_processing'] = False
            return
        
        duration_sec = processor.total_frames / processor.fps if processor.fps > 0 else 0
        processing_state['total_frames'] = max_frames or processor.total_frames
        processing_state['status'] = 'Processing...'
        
        # Setup annotated video writer
        annotated_path = None
        if write_annotated:
            # Use AVI format with MJPG codec for better OpenCV compatibility
            annotated_path = ANNOTATED_VIDEO_DIR / f"annotated_{Path(video_path).stem}.avi"
            processor.start_annotated_writer(str(annotated_path))
        
        # Progress callback
        def progress_cb(frame_index: int, total: int, result):
            if processing_state['stop_requested']:
                return True  # Stop processing
            processing_state['current_frame'] = frame_index + 1
            processing_state['progress'] = (frame_index + 1) / total if total > 0 else 0
            processing_state['count'] = result.total_count_so_far
            return False
        
        # Draw callback
        def draw_cb(frame, result):
            draw_on_frame(frame, result, processor.counter)
        
        # Run processing
        cross_events = processor.run(
            progress_callback=progress_cb,
            draw_callback=draw_cb if write_annotated else None,
            max_frames=max_frames,
        )
        processor.close()
        
        # Compute statistics
        stats = compute_stats(
            cross_events,
            config=config.analytics,
            video_duration_sec=duration_sec,
        )
        
        # Get detected category counts
        total_detected = len(processor.counter.all_track_ids_seen) if processor.counter else 0
        detected_category_counts = processor.counter.get_detected_category_counts() if processor.counter else {}
        
        # Generate dashboard charts (only counted vehicles)
        chart_paths = generate_dashboard(stats, ANALYTICS_DIR, detected_category_counts=None)
        
        # Generate HTML report
        report_path = generate_html_report(
            stats,
            video_name=Path(video_path).name,
            duration_sec=duration_sec,
            chart_paths=chart_paths,
            output_path=REPORT_DIR / "traffic_report.html",
            total_detected=total_detected,
            detected_category_counts=detected_category_counts,
        )
        
        # Save CSV events
        if stats.events:
            import csv
            csv_path = OUTPUT_DIR / "data" / "crossing_events.csv"
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["track_id", "category", "frame_index", "timestamp_sec"])
                for e in stats.events:
                    w.writerow([e.track_id, e.category, e.frame_index, e.timestamp_sec])
        
        # Update results
        processing_state['status'] = 'Complete'
        processing_state['results'] = {
            'total_counted': stats.total_count,
            'categories': stats.category_counts,
            'report_path': str(report_path.relative_to(OUTPUT_DIR)),
            'annotated_video': str(annotated_path.relative_to(OUTPUT_DIR)) if annotated_path and annotated_path.exists() else None,
        }
        
    except Exception as e:
        processing_state['error'] = str(e)
        processing_state['status'] = 'Error'
    
    finally:
        processing_state['is_processing'] = False


if __name__ == '__main__':
    print("=" * 60)
    print("Traffic Counting Web Interface")
    print("=" * 60)
    print(f"Starting server at http://localhost:5000")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    app.run(debug=True, port=5000, use_reloader=False)
