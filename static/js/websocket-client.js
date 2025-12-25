/**
 * WebSocket client for real-time updates
 * Handles download progress, notifications, and system updates
 */

// WebSocket connection management
let wsConnections = {};
let wsReconnectInterval = 5000; // 5 seconds

function initWebSocketConnections() {
    if (!window.userData || !window.userData.isAuthenticated) {
        console.log('User not authenticated, skipping WebSocket initialization');
        return;
    }

    // Initialize different WebSocket connections based on needs
    initDownloadProgressWebSocket();
    initUserNotificationsWebSocket();
}

function initDownloadProgressWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/download-progress/`;

    if (wsConnections.downloadProgress) {
        wsConnections.downloadProgress.close();
    }

    try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = function() {
            console.log('Download progress WebSocket connected');
            // Send authentication if needed
            ws.send(JSON.stringify({
                type: 'authenticate',
                token: localStorage.getItem('access_token')
            }));
        };

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleDownloadProgressMessage(data);
        };

        ws.onclose = function(event) {
            console.log('Download progress WebSocket disconnected:', event.code);
            wsConnections.downloadProgress = null;

            // Reconnect after delay
            setTimeout(() => {
                if (window.userData && window.userData.isAuthenticated) {
                    initDownloadProgressWebSocket();
                }
            }, wsReconnectInterval);
        };

        ws.onerror = function(error) {
            console.error('Download progress WebSocket error:', error);
        };

        wsConnections.downloadProgress = ws;

    } catch (error) {
        console.error('Failed to create download progress WebSocket:', error);
    }
}

function initUserNotificationsWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/user-notifications/${window.userData.id}/`;

    if (wsConnections.notifications) {
        wsConnections.notifications.close();
    }

    try {
        const ws = new WebSocket(wsUrl);

        ws.onopen = function() {
            console.log('User notifications WebSocket connected');
        };

        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleNotificationMessage(data);
        };

        ws.onclose = function(event) {
            console.log('User notifications WebSocket disconnected:', event.code);
            wsConnections.notifications = null;

            // Reconnect after delay
            setTimeout(() => {
                if (window.userData && window.userData.isAuthenticated) {
                    initUserNotificationsWebSocket();
                }
            }, wsReconnectInterval);
        };

        ws.onerror = function(error) {
            console.error('User notifications WebSocket error:', error);
        };

        wsConnections.notifications = ws;

    } catch (error) {
        console.error('Failed to create user notifications WebSocket:', error);
    }
}

function handleDownloadProgressMessage(data) {
    switch (data.type) {
        case 'download_progress':
            updateDownloadProgress(data.download_id, data.progress, data.status);
            break;
        case 'download_completed':
            handleDownloadCompleted(data.download_id, data.success, data.message);
            break;
        case 'download_started':
            handleDownloadStarted(data.download_id, data.course_title);
            break;
        case 'download_failed':
            handleDownloadFailed(data.download_id, data.error);
            break;
        default:
            console.log('Unknown download progress message type:', data.type);
    }
}

function handleNotificationMessage(data) {
    switch (data.type) {
        case 'system_notification':
            showAlert(data.message, data.level || 'info');
            break;
        case 'update_available':
            handleUpdateAvailable(data.version, data.download_url);
            break;
        case 'quota_warning':
            showAlert(`Storage quota warning: ${data.message}`, 'warning');
            break;
        default:
            console.log('Unknown notification message type:', data.type);
    }
}

function updateDownloadProgress(downloadId, progress, status) {
    const progressElement = document.getElementById(`progress-${downloadId}`);
    if (progressElement) {
        progressElement.style.width = `${progress}%`;
        progressElement.setAttribute('aria-valuenow', progress);
    }

    const statusElement = document.getElementById(`status-${downloadId}`);
    if (statusElement) {
        statusElement.textContent = status;
    }

    // Update progress bar if using Semantic UI
    const progressBar = $(`#download-${downloadId} .progress`);
    if (progressBar.length > 0) {
        progressBar.progress({
            percent: progress,
            text: {
                active: `${progress}% - ${status}`,
                success: 'Download completed!'
            }
        });
    }
}

function handleDownloadCompleted(downloadId, success, message) {
    if (success) {
        showAlert(`Download completed: ${message}`, 'positive');

        // Show browser notification if permission granted
        if (Notification.permission === 'granted') {
            new Notification('Download Completed', {
                body: message,
                icon: '/static/images/icon.svg'
            });
        }

        // Update UI
        const downloadElement = document.getElementById(`download-${downloadId}`);
        if (downloadElement) {
            downloadElement.classList.add('completed');
            downloadElement.classList.remove('downloading');
        }
    } else {
        showAlert(`Download failed: ${message}`, 'negative');
    }

    // Refresh downloads list if we're on that section
    if (window.currentSection === 'downloads') {
        loadDownloadsContent();
    }
}

function handleDownloadStarted(downloadId, courseTitle) {
    showAlert(`Download started: ${courseTitle}`, 'info');

    // Update downloads counter
    updateDownloadCounter();
}

function handleDownloadFailed(downloadId, error) {
    showAlert(`Download failed: ${error}`, 'negative');

    const downloadElement = document.getElementById(`download-${downloadId}`);
    if (downloadElement) {
        downloadElement.classList.add('failed');
        downloadElement.classList.remove('downloading');
    }
}

function handleUpdateAvailable(version, downloadUrl) {
    $('.ui.update-available.modal .content p').html(
        `Version ${version} is available. Would you like to download it?`
    );

    $('.ui.update-available.modal').modal({
        onApprove: function() {
            window.open(downloadUrl, '_blank');
        }
    }).modal('show');
}

function updateDownloadCounter() {
    // Count active downloads
    const activeDownloads = document.querySelectorAll('.download-item.downloading').length;
    const counterElement = document.getElementById('downloadCount');

    if (counterElement) {
        if (activeDownloads > 0) {
            counterElement.textContent = activeDownloads;
            counterElement.style.display = 'inline';
        } else {
            counterElement.style.display = 'none';
        }
    }
}

// Cleanup function
function cleanupWebSocketConnections() {
    Object.keys(wsConnections).forEach(key => {
        if (wsConnections[key]) {
            wsConnections[key].close();
            wsConnections[key] = null;
        }
    });
}

// Global cleanup function for section switching
window.cleanupDownloadConnections = cleanupWebSocketConnections;

// Initialize WebSocket connections when user authenticates
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for authentication to complete
    setTimeout(() => {
        if (window.userData && window.userData.isAuthenticated) {
            initWebSocketConnections();
        }
    }, 1000);
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    cleanupWebSocketConnections();
});