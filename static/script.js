// State management
let uploadedVideoPath = null;
let statusPollInterval = null;

// DOM elements
const uploadArea = document.getElementById('uploadArea');
const videoInput = document.getElementById('videoInput');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const removeFileBtn = document.getElementById('removeFile');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const progressCard = document.getElementById('progressCard');
const resultsCard = document.getElementById('resultsCard');

// Settings
const lineYSlider = document.getElementById('lineY');
const lineYValue = document.getElementById('lineYValue');
const confidenceSlider = document.getElementById('confidence');
const confidenceValue = document.getElementById('confidenceValue');
const writeAnnotatedCheckbox = document.getElementById('writeAnnotated');
const maxFramesInput = document.getElementById('maxFrames');

// Progress elements
const statusText = document.getElementById('statusText');
const progressBar = document.getElementById('progressBar');
const frameCount = document.getElementById('frameCount');
const vehicleCount = document.getElementById('vehicleCount');

// Results elements
const totalCounted = document.getElementById('totalCounted');
const categoryBreakdown = document.getElementById('categoryBreakdown');
const viewReportBtn = document.getElementById('viewReportBtn');
const viewVideoBtn = document.getElementById('viewVideoBtn');
const openFolderBtn = document.getElementById('openFolderBtn');

// Event listeners
uploadArea.addEventListener('click', () => videoInput.click());
uploadArea.addEventListener('dragover', handleDragOver);
uploadArea.addEventListener('drop', handleDrop);
videoInput.addEventListener('change', handleFileSelect);
removeFileBtn.addEventListener('click', removeFile);

lineYSlider.addEventListener('input', (e) => {
    lineYValue.textContent = parseFloat(e.target.value).toFixed(2);
});

confidenceSlider.addEventListener('input', (e) => {
    confidenceValue.textContent = parseFloat(e.target.value).toFixed(2);
});

startBtn.addEventListener('click', startProcessing);
stopBtn.addEventListener('click', stopProcessing);
viewReportBtn.addEventListener('click', viewReport);
viewVideoBtn.addEventListener('click', viewVideo);
openFolderBtn.addEventListener('click', openFolder);

// File handling
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.style.borderColor = '#667eea';
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.style.borderColor = '';

    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

async function handleFile(file) {
    // Show file info
    fileName.textContent = file.name;
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';

    // Upload file
    const formData = new FormData();
    formData.append('video', file);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            uploadedVideoPath = data.path;
            startBtn.disabled = false;
            showNotification('Video uploaded successfully', 'success');
            // Auto-scroll to settings section
            setTimeout(() => {
                document.querySelector('.settings-card').scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300);
        } else {
            showNotification(data.error || 'Upload failed', 'error');
            removeFile();
        }
    } catch (error) {
        showNotification('Upload failed: ' + error.message, 'error');
        removeFile();
    }
}

function removeFile() {
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    fileName.textContent = '';
    uploadedVideoPath = null;
    startBtn.disabled = true;
    videoInput.value = '';
}

// Processing
async function startProcessing() {
    if (!uploadedVideoPath) {
        showNotification('Please upload a video first', 'error');
        return;
    }

    const settings = {
        video_path: uploadedVideoPath,
        line_y: parseFloat(lineYSlider.value),
        confidence: parseFloat(confidenceSlider.value),
        write_annotated: writeAnnotatedCheckbox.checked,
        max_frames: parseInt(maxFramesInput.value) || 0
    };

    try {
        const response = await fetch('/api/process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });

        const data = await response.json();

        if (response.ok) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
            progressCard.style.display = 'block';
            resultsCard.style.display = 'none';

            // Auto-scroll to progress section
            setTimeout(() => {
                progressCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }, 300);

            // Start polling for status
            statusPollInterval = setInterval(pollStatus, 500);
        } else {
            showNotification(data.error || 'Failed to start processing', 'error');
        }
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

async function stopProcessing() {
    try {
        await fetch('/api/stop', {
            method: 'POST'
        });
        stopBtn.disabled = true;
    } catch (error) {
        showNotification('Error: ' + error.message, 'error');
    }
}

async function pollStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();

        // Update UI
        statusText.textContent = data.status;
        progressBar.style.width = (data.progress * 100) + '%';
        frameCount.textContent = `${data.current_frame} / ${data.total_frames}`;
        vehicleCount.textContent = data.count;

        // Check if processing is complete
        if (!data.is_processing) {
            clearInterval(statusPollInterval);
            startBtn.disabled = false;
            stopBtn.disabled = true;

            if (data.error) {
                showNotification('Error: ' + data.error, 'error');
            } else if (data.results) {
                displayResults(data.results);
            }
        }
    } catch (error) {
        console.error('Status poll error:', error);
    }
}

function displayResults(results) {
    resultsCard.style.display = 'block';

    // Auto-scroll to results section
    setTimeout(() => {
        resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 300);

    // Update only crossed line count
    totalCounted.textContent = results.total_counted;

    // Category breakdown
    categoryBreakdown.innerHTML = '';
    if (results.categories) {
        Object.entries(results.categories).forEach(([category, count]) => {
            const item = document.createElement('div');
            item.className = 'category-item';
            item.innerHTML = `
                <span class="category-name">${category}</span>
                <span class="category-count">${count}</span>
            `;
            categoryBreakdown.appendChild(item);
        });
    }

    // Enable/disable buttons
    viewReportBtn.disabled = !results.report_path;
    viewVideoBtn.disabled = !results.annotated_video;

    // Store paths for later use
    viewReportBtn.dataset.path = results.report_path;
    viewVideoBtn.dataset.path = results.annotated_video;

    // Save results to localStorage for persistence
    localStorage.setItem('lastProcessingResults', JSON.stringify(results));

    showNotification('Processing complete!', 'success');
}

// Actions
function viewReport() {
    const path = viewReportBtn.dataset.path;
    console.log('Opening report:', path);
    if (path) {
        // Open in same window for better desktop app experience
        window.location.href = `/output/${path}`;
    }
}

async function viewVideo() {
    const path = viewVideoBtn.dataset.path;
    console.log('Opening video:', path);
    if (path) {
        try {
            const response = await fetch('/api/download-video', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: path })
            });
            const data = await response.json();
            if (response.ok) {
                showNotification('Video opened with default player', 'success');
            } else {
                showNotification(data.message || 'Failed to open video', 'error');
            }
        } catch (error) {
            console.error('Error opening video:', error);
            showNotification('Error opening video', 'error');
        }
    } else {
        console.error('No video path available');
        showNotification('No video path available', 'error');
    }
}

async function openFolder() {
    try {
        const response = await fetch('/api/open-folder', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        if (response.ok) {
            showNotification('Output folder opened', 'success');
        } else {
            showNotification(data.message || 'Failed to open folder', 'error');
        }
    } catch (error) {
        console.error('Error opening folder:', error);
        showNotification('Error opening folder', 'error');
    }
}

// Notifications
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 2rem;
        right: 2rem;
        padding: 1rem 1.5rem;
        background: ${type === 'success' ? 'rgba(79, 172, 254, 0.2)' : 'rgba(245, 87, 108, 0.2)'};
        border: 1px solid ${type === 'success' ? 'rgba(79, 172, 254, 0.5)' : 'rgba(245, 87, 108, 0.5)'};
        border-radius: 12px;
        color: white;
        font-weight: 500;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        animation: slideInRight 0.3s ease-out;
        z-index: 1000;
    `;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            opacity: 0;
            transform: translateX(100px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }
    
    @keyframes slideOutRight {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100px);
        }
    }
`;
document.head.appendChild(style);

// Restore results on page load
document.addEventListener('DOMContentLoaded', () => {
    const savedResults = localStorage.getItem('lastProcessingResults');
    if (savedResults) {
        try {
            const results = JSON.parse(savedResults);
            // Only restore if we don't have active processing
            if (!statusPollInterval) {
                displayResults(results);
                // Show results card
                resultsCard.classList.remove('hidden');
                // Scroll to results
                setTimeout(() => {
                    resultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 300);
            }
        } catch (e) {
            console.error('Error restoring results:', e);
        }
    }
});
