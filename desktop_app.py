"""
Traffic Counting Desktop App
Wraps the web GUI in a native desktop window using PyWebView
Run: python desktop_app.py
"""

import sys
import threading
import time
import webbrowser
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False
    print("=" * 60)
    print("WARNING: pywebview is not installed")
    print("=" * 60)
    print("Installing pywebview...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pywebview"])
        import webview
        HAS_WEBVIEW = True
        print("Successfully installed pywebview!")
    except:
        print("Failed to install pywebview automatically.")
        print("Please install it manually: pip install pywebview")
        print("Opening in browser instead...")

from web_app import app


def start_flask_server():
    """Start Flask server in background thread"""
    # Disable Flask's auto-reload in desktop mode
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False, threaded=True)


def main():
    """Launch desktop application"""
    # Start Flask server in background thread
    server_thread = threading.Thread(target=start_flask_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    print("Starting Traffic Counting Desktop App...")
    time.sleep(2)
    
    if HAS_WEBVIEW:
        try:
            # Create desktop window
            print("Opening native desktop window...")
            window = webview.create_window(
                title='Traffic Counting & Vehicle Categorization',
                url='http://127.0.0.1:5000',
                width=1280,
                height=900,
                resizable=True,
                fullscreen=False,
                min_size=(900, 700),
                background_color='#1a1d23',
            )
            
            # Start the GUI event loop
            webview.start(debug=False)
        except Exception as e:
            print(f"Error creating desktop window: {e}")
            print("Opening in browser instead...")
            webbrowser.open('http://127.0.0.1:5000')
            print("\nServer is running. Press Ctrl+C to stop.")
            # Keep the script running
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
    else:
        # Fallback to browser
        print("PyWebView not available. Opening in browser...")
        webbrowser.open('http://127.0.0.1:5000')
        print("\nServer is running at: http://127.0.0.1:5000")
        print("Press Ctrl+C to stop.")
        # Keep the script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nShutting down...")


if __name__ == '__main__':
    main()

