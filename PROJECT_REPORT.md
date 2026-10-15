# Traffic Counting and Vehicle Categorization using Computer Vision

## Project Report

---

**Challenge:** Proof-of-concept computer vision system for traffic analysis using pre-recorded traffic/CCTV video  
**Date:** January 2025  

---

## 1. Core Solution Concept

The system is designed around a **modular pipeline** that takes a pre-recorded traffic or CCTV video as input and produces automated vehicle counts, category-wise distribution, and traffic density over time.

**Concept in brief:**

1. **Deep learning–based detection:** A YOLO (You Only Look Once) model identifies and classifies vehicles—**cars, motorcycles, buses, and trucks**—in each video frame. The model is pre-trained (e.g. COCO) and fine-tuned for vehicle classes only.

2. **Object tracking for accurate counting:** To avoid counting the same vehicle multiple times across frames, **object tracking** (ByteTrack) assigns a **unique ID** to each detected vehicle. The same vehicle keeps the same ID as it moves through the scene.

3. **Virtual counting line:** A **virtual line** is defined on the road (e.g. a horizontal line at a configurable height). A vehicle is **counted only once** when its **centroid crosses** this line in the chosen direction (up, down, or both). This mimics a real-world “gate” or sensor line.

4. **Statistics and outputs:** The system generates:
   - **Total vehicle count** (unique vehicles that crossed the line)
   - **Category-wise distribution** (Car, Bus, Truck, Motorcycle, etc.)
   - **Traffic density over time** (e.g. counts per 60-second window)
   - **Annotated video** (bounding boxes, track IDs, counting line)
   - **Visual analytics** (graphs/dashboards) and a **downloadable summary report** (HTML, optional PDF)

The solution is **modular** (detection, tracking, counting, analytics, and UI are separate components), **easy to understand**, and **suitable for extension** to real-time CCTV feeds by swapping the video source from file to stream (e.g. RTSP).

---

## 2. Unique Value Proposition

- **One count per vehicle:** Tracking + virtual line ensures each vehicle is counted exactly once when it crosses the line, avoiding double-counting common in frame-level detection-only approaches.

- **Stable category per vehicle:** Category is assigned using **majority vote** over the entire track lifetime (e.g. if a vehicle is seen as “car” in 8 frames and “truck” in 2, it is counted as “car”). This reduces misclassification from single-frame noise.

- **User-configurable line and thresholds:** The counting line position (Y), detection confidence, and direction (up/down/both) are configurable so the same code can adapt to different camera angles and use cases.

- **Dual interfaces:** Both a **desktop GUI** (CustomTkinter, tabbed: Setup → Run → Results → Output) and an **optional web interface** (Flask) are provided for different deployment and demo scenarios.

- **Clear, consistent analytics:** All analytics (total count, category breakdown, density over time) use the **same counted events**, so numbers in the dashboard, report, and charts always add up and match.

- **Extensible design:** The pipeline is input-agnostic; replacing the video file with an RTSP/HTTP stream and adding optional batching or sliding windows would allow the same logic to run on live CCTV feeds.

---

## 3. Key Technologies and Data Used

### 3.1 Technologies

| Technology | Purpose |
|------------|---------|
| **Python 3.8+** | Implementation language |
| **YOLO (Ultralytics)** | Deep learning–based object detection (e.g. YOLOv8n); identifies and classifies vehicles in each frame |
| **ByteTrack** | Multi-object tracking; assigns and maintains unique IDs across frames |
| **OpenCV (cv2)** | Video I/O (read/write), drawing bounding boxes and counting line on frames |
| **CustomTkinter** | Desktop GUI (tabs, cards, modern theme) |
| **Flask** | Web server for optional interactive web dashboard |
| **Pandas / NumPy** | Aggregation, time-window statistics, traffic density over time |
| **Matplotlib** | Visual analytics: category distribution, density over time, category-over-time charts |
| **Jinja2** | HTML report templating for downloadable summary report |

### 3.2 Data

- **Input:** Pre-recorded traffic or CCTV video (e.g. MP4, AVI) from publicly available sources (e.g. Pexels, Pixabay, or open traffic datasets). No custom training data is required; the system uses a pre-trained YOLO model (e.g. COCO-based) with vehicle classes (car, motorcycle, bus, truck, bicycle).
- **Output data:** Crossing events (track_id, category, timestamp), aggregated counts, category distribution, and time-window counts used for dashboards and reports.

---

## 4. Methodology

### 4.1 Detection

- **Model:** YOLOv8 (nano/small/medium as configured), pre-trained on a large-scale dataset (e.g. COCO).
- **Classes:** Filtered to vehicle classes only (car, motorcycle, bus, truck, bicycle as per config).
- **Per frame:** The model outputs bounding boxes, class labels, confidence scores, and (when tracking is enabled) a stable **track_id** per detection.

### 4.2 Object Tracking

- **Tracker:** ByteTrack (integrated with Ultralytics) associates detections across frames and assigns a **unique ID** to each vehicle.
- **Role:** Ensures the same physical vehicle is represented by the same ID over time, which is essential for counting each vehicle only once at the virtual line.

### 4.3 Virtual Counting Line

- **Definition:** A line is defined by two points (e.g. full width of frame at a configurable Y position, 0–1).
- **Centroid:** For each tracked vehicle, the centroid of its bounding box is computed.
- **Side of line:** A signed cross product determines whether the centroid is above or below the line.
- **Crossing:** When the centroid moves from one side to the other in the configured direction (up, down, or both), a **crossing event** is recorded (track_id, category, timestamp).
- **Single count:** Each `track_id` is added to a “counted” set so it is never counted again.

### 4.4 Category Assignment

- **Per track:** Each time a vehicle is detected, its class (e.g. car, bus) is accumulated in a per-track histogram.
- **At crossing:** The category for that track is set to the **majority vote** (most frequently observed class) over the track’s lifetime.
- **Normalization:** Category names are normalized (e.g. “bus” / “Bus” → “Bus”) so that reports and dashboards show consistent, merged counts.

### 4.5 Analytics

- **Total count:** Number of crossing events (= number of unique vehicles that crossed the line).
- **Category-wise distribution:** Count of events per category (Car, Bus, Truck, etc.); these sum to the total count.
- **Traffic density over time:** Events are binned into fixed time windows (e.g. 60 s); counts per window and per category are used for time-series charts.

---

## 5. Documentation of Dashboard Functionalities and Analytical Outputs

### 5.1 Desktop Dashboard (CustomTkinter GUI)

- **Setup tab:** Select video file (browse), set counting line position (Y slider), detection confidence, options (write annotated video, limit frames). **Next** moves to Run.
- **Run tab:** Start / Stop processing; progress bar and status (e.g. “Frame 120/500 · Count: 8”). When finished, user can switch to Results.
- **Results tab:** Total vehicles (detected vs counted); category-wise breakdown (counted only, so counts add up to total). **Next** moves to Output.
- **Output tab:** Buttons to open HTML report, open output folder, and play annotated video.

### 5.2 Web Dashboard (Flask)

- **Upload:** User uploads a traffic video.
- **Settings:** Line position (Y), confidence, optional frame limit.
- **Processing:** Progress (frame index, count) is shown; processing runs in the background.
- **Results:** Total counted, category breakdown (same logic as desktop); links to view report and annotated video.

### 5.3 Analytical Outputs

- **Total vehicle count:** Number of unique vehicles that crossed the virtual line.
- **Category-wise distribution:** Count per vehicle type (Car, Bus, Truck, Motorcycle, etc.); consistent with total (no double-counting, same event set).
- **Traffic density over time:** Bar or line chart of vehicle count per time window (e.g. per 60 s).
- **Category over time:** Stacked or grouped chart of count per time window per category.
- **Annotated video:** Each frame shows bounding boxes, track IDs, the counting line, and on-screen total count.
- **Downloadable summary report (HTML):** Summary (detected vs counted), tables (all detected; counted only), embedded charts, sample crossing events (e.g. first 50). Optional PDF export via separate script.

---

## 6. Policy and Architectural Recommendations

### 6.1 Policy Recommendations

- **Privacy and compliance:** Use only videos that you have rights to use (e.g. public domain, licensed, or internal CCTV with appropriate policies). For real-time CCTV, ensure compliance with local data protection and surveillance laws.
- **Transparency:** When deploying for real traffic monitoring, document what is counted (e.g. “vehicles crossing the virtual line”) and how (detection model, tracking, line position) so results are interpretable and auditable.
- **Human oversight:** Treat automated counts as decision support; critical applications (e.g. tolling, enforcement) should retain human review where required by policy.

### 6.2 Architectural Recommendations

- **Modularity:** Keep detection, tracking, counting, analytics, and UI in separate modules (as in this project) so that models or trackers can be swapped without rewriting the whole system.
- **Configuration:** Use a central config (e.g. `config.py`) for model path, line position, confidence, time-window size, and paths so the same code can be tuned per camera or deployment.
- **Extensibility for real-time:** Design the “video source” as an abstraction (file vs stream); use the same frame-by-frame pipeline for both. For live CCTV, add buffering, optional batching, and secure access (e.g. authentication, HTTPS) for web dashboards.
- **Scalability:** For many cameras or long runs, consider offloading detection/tracking to a GPU server, storing events in a database, and serving dashboards via a separate front-end (e.g. REST API + web app).

---

## 7. Interactive Dashboard / Source Code / URL (if applicable)

- **Source code:** The full solution is provided as a Python project (modular, with clear separation of detection, tracking, counting, analytics, and UI). No proprietary binaries; dependencies are listed in `requirements.txt`.
- **Desktop dashboard:** Run locally with `python gui.py` (CustomTkinter). No URL; suitable for offline or air-gapped demos.
- **Web dashboard (optional):** Run with `python web_gui.py` and open `http://localhost:5000` in a browser. For a shared demo, the URL would be the machine’s IP and port (e.g. `http://<host>:5000`) or a deployed URL if hosted on a server.
- **Repository / URL:** *(You can add your repository link or hosted demo URL here, e.g. GitHub/GitLab link or deployed app URL.)*

---

## 8. Final Presentation (PPT / Short Demo Video)

- **PPT:** A short slide deck is recommended covering: (1) title and challenge statement, (2) core solution concept, (3) unique value proposition, (4) key technologies and data, (5) methodology (detection → tracking → line counting → analytics), (6) dashboard and analytical outputs (screenshots), (7) policy and architectural recommendations, (8) live or recorded demo, (9) conclusion and future work (e.g. real-time CCTV).
- **Short demo video:** A 3–5 minute screen recording showing: selecting a traffic video, setting the counting line and confidence, running processing, viewing results (total + category breakdown), opening the report and annotated video, and briefly showing the analytics charts. Optionally show the web UI if used.

*(You can add the actual link to your PPT or demo video here once created.)*

---

## References

- Ultralytics YOLO: https://github.com/ultralytics/ultralytics  
- ByteTrack: Multi-Object Tracking by Associating Every Detection Box  
- OpenCV: https://opencv.org/  
- CustomTkinter: https://github.com/TomSchimansky/CustomTkinter  

---

*End of Project Report*
