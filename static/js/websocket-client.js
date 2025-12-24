/**
 * WebSocket client for real-time updates
 * Handles download progress, notifications, and system updates
 */

class WebSocketManager {
    constructor() {
        this.connections = {};
        this.reconnectAttempts = {};
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000; // Start with 1 second
        this.maxReconnectDelay = 30000; // Max 30 seconds
    }

    /**
     * Create a WebSocket connection
     */
    connect(name, url, options = {}) {
        if (this.connections[name]) {
            this.connections[name].close();
        }

        const websocket = new WebSocket(url);
        this.connections[name] = websocket;
        this.reconnectAttempts[name] = 0;

        websocket.onopen = () => {
            console.log(`WebSocket ${name} connected`);
            this.reconnectAttempts[name] = 0;
            this.reconnectDelay = 1000; // Reset delay

            if (options.onOpen) {
                options.onOpen();
            }

            // Send ping to keep connection alive
            this.startPingInterval(name);
        };

        websocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'pong') {
                    // Handle pong response
                    return;
                }

                if (options.onMessage) {
                    options.onMessage(data);
                }
            } catch (error) {
                console.error(`WebSocket ${name} message parse error:`, error);
            }
        };

        websocket.onclose = (event) => {
            console.log(`WebSocket ${name} disconnected:`, event.code, event.reason);

            if (options.onClose) {
                options.onClose(event);
            }

            // Attempt to reconnect if not manually closed
            if (event.code !== 1000 && event.code !== 1001) {
                this.scheduleReconnect(name, url, options);
            }

            this.clearPingInterval(name);
        };

        websocket.onerror = (error) => {
            console.error(`WebSocket ${name} error:`, error);

            if (options.onError) {
                options.onError(error);
            }
        };

        return websocket;
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect(name, url, options) {
        if (this.reconnectAttempts[name] >= this.maxReconnectAttempts) {
            console.log(`Max reconnection attempts reached for ${name}`);
            return;
        }

        this.reconnectAttempts[name]++;
        const delay = Math.min(
            this.reconnectDelay * Math.pow(2, this.reconnectAttempts[name] - 1),
            this.maxReconnectDelay
        );

        console.log(`Reconnecting ${name} in ${delay}ms (attempt ${this.reconnectAttempts[name]})`);

        setTimeout(() => {
            if (!this.connections[name] || this.connections[name].readyState === WebSocket.CLOSED) {
                this.connect(name, url, options);
            }
        }, delay);
    }

    /**
     * Send message to WebSocket
     */
    send(name, data) {
        const websocket = this.connections[name];
        if (websocket && websocket.readyState === WebSocket.OPEN) {
            websocket.send(JSON.stringify(data));
            return true;
        }
        return false;
    }

    /**
     * Close WebSocket connection
     */
    close(name) {
        if (this.connections[name]) {
            this.connections[name].close(1000, 'Manual close');
            delete this.connections[name];
            delete this.reconnectAttempts[name];
            this.clearPingInterval(name);
        }
    }

    /**
     * Close all WebSocket connections
     */
    closeAll() {
        Object.keys(this.connections).forEach(name => {
            this.close(name);
        });
    }

    /**
     * Start ping interval to keep connection alive
     */
    startPingInterval(name) {
        const interval = setInterval(() => {
            this.send(name, {
                type: 'ping',
                timestamp: Date.now()
            });
        }, 30000); // Ping every 30 seconds

        this.connections[name]._pingInterval = interval;
    }

    /**
     * Clear ping interval
     */
    clearPingInterval(name) {
        if (this.connections[name] && this.connections[name]._pingInterval) {
            clearInterval(this.connections[name]._pingInterval);
            delete this.connections[name]._pingInterval;
        }
    }

    /**
     * Get connection status
     */
    getStatus(name) {
        const websocket = this.connections[name];
        if (!websocket) return 'disconnected';

        switch (websocket.readyState) {
            case WebSocket.CONNECTING:
                return 'connecting';
            case WebSocket.OPEN:
                return 'connected';
            case WebSocket.CLOSING:
                return 'closing';
            case WebSocket.CLOSED:
                return 'closed';
            default:
                return 'unknown';
        }
    }
}

// Global WebSocket manager instance
window.wsManager = new WebSocketManager();

/**
 * Download Progress WebSocket Handler
 */
class DownloadProgressHandler {
    constructor(downloadId) {
        this.downloadId = downloadId;
        this.connectionName = `download_progress_${downloadId}`;
        this.callbacks = {};
    }

    connect() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${wsProtocol}//${window.location.host}/ws/download-progress/${this.downloadId}/`;

        return window.wsManager.connect(this.connectionName, url, {
            onMessage: (data) => this.handleMessage(data),
            onOpen: () => this.handleOpen(),
            onClose: (event) => this.handleClose(event),
            onError: (error) => this.handleError(error)
        });
    }

    handleMessage(data) {
        switch (data.type) {
            case 'progress_update':
                this.updateProgress(data);
                break;
            case 'status_change':
                this.updateStatus(data);
                break;
            case 'speed_update':
                this.updateSpeed(data);
                break;
            case 'error':
                this.handleDownloadError(data);
                break;
            case 'current_status':
                this.updateCurrentStatus(data);
                break;
        }

        // Call registered callbacks
        Object.values(this.callbacks).forEach(callback => {
            if (typeof callback === 'function') {
                callback(data);
            }
        });
    }

    handleOpen() {
        console.log(`Download progress WebSocket connected for ${this.downloadId}`);
        // Request current status
        this.send({
            type: 'request_status'
        });
    }

    handleClose(event) {
        console.log(`Download progress WebSocket closed for ${this.downloadId}`);
    }

    handleError(error) {
        console.error(`Download progress WebSocket error for ${this.downloadId}:`, error);
    }

    updateProgress(data) {
        const $course = $(`.course.item[course-id="${this.downloadId}"]`);

        // Update individual progress bar
        const $individualProgress = $course.find('.individual.progress');
        $individualProgress.show().progress('set percent', data.percentage);

        // Update combined progress if available
        if (data.details && data.details.combined_progress !== undefined) {
            const $combinedProgress = $course.find('.combined.progress');
            $combinedProgress.show().progress('set percent', data.details.combined_progress);
            $combinedProgress.find('.label').text(data.message || 'Downloading...');
        }

        // Update download info
        if (data.details && data.details.current_file) {
            $course.find('.info-downloaded').show().text(
                `Downloading: ${data.details.current_file} (${data.details.current_index}/${data.details.total_files})`
            );
        }
    }

    updateStatus(data) {
        const $course = $(`.course.item[course-id="${this.downloadId}"]`);

        // Update UI based on status
        switch (data.status) {
            case 'downloading':
                $course.find('.download.button').addClass('disabled');
                $course.find('.pause.button').removeClass('disabled');
                $course.find('.resume.button').addClass('disabled');
                $course.find('.prepare-downloading').hide();
                $course.find('.individual.progress, .combined.progress').show();
                break;

            case 'paused':
                $course.find('.pause.button').addClass('disabled');
                $course.find('.resume.button').removeClass('disabled');
                break;

            case 'completed':
                $course.find('.download.button').removeClass('disabled');
                $course.find('.pause.button, .resume.button').addClass('disabled');
                $course.find('.individual.progress, .combined.progress').hide();
                $course.find('.download-success').show();
                $course.find('.download-status').hide();
                $course.find('.open-dir.button').show();
                $course.attr('course-completed', 'true');

                // Show success notification
                if (window.showAlert) {
                    window.showAlert('Download completed successfully!', 'positive');
                }
                break;

            case 'failed':
                $course.find('.download.button').removeClass('disabled');
                $course.find('.pause.button, .resume.button').addClass('disabled');
                $course.find('.individual.progress, .combined.progress').hide();
                $course.find('.download-error').show();
                $course.find('.download-status').hide();
                break;

            case 'cancelled':
                $course.find('.download.button').removeClass('disabled');
                $course.find('.pause.button, .resume.button').addClass('disabled');
                $course.find('.individual.progress, .combined.progress').hide();
                $course.find('.download-status').show();
                break;
        }

        // Update status attribute
        $course.attr('data-download-status', data.status);
    }

    updateSpeed(data) {
        const $course = $(`.course.item[course-id="${this.downloadId}"]`);
        $course.find('.download-speed .value').text(Math.round(data.speed));
        $course.find('.download-speed').show();
    }

    updateCurrentStatus(data) {
        if (data.download_task) {
            this.updateStatus({ status: data.download_task.status });
            if (data.download_task.progress) {
                this.updateProgress({
                    percentage: data.download_task.progress,
                    details: data.download_task
                });
            }
        }
    }

    handleDownloadError(data) {
        const $course = $(`.course.item[course-id="${this.downloadId}"]`);
        $course.find('.download-error').show();
        $course.find('.download-status').hide();

        if (window.showAlert) {
            window.showAlert(`Download failed: ${data.error_message}`, 'negative');
        }
    }

    send(data) {
        return window.wsManager.send(this.connectionName, data);
    }

    addCallback(name, callback) {
        this.callbacks[name] = callback;
    }

    removeCallback(name) {
        delete this.callbacks[name];
    }

    disconnect() {
        window.wsManager.close(this.connectionName);
    }
}

/**
 * User Notifications WebSocket Handler
 */
class NotificationHandler {
    constructor(userId) {
        this.userId = userId;
        this.connectionName = 'user_notifications';
    }

    connect() {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${wsProtocol}//${window.location.host}/ws/user-notifications/${this.userId}/`;

        return window.wsManager.connect(this.connectionName, url, {
            onMessage: (data) => this.handleMessage(data),
            onOpen: () => this.handleOpen(),
            onClose: (event) => this.handleClose(event),
            onError: (error) => this.handleError(error)
        });
    }

    handleMessage(data) {
        switch (data.type) {
            case 'download_completed':
                this.handleDownloadCompleted(data);
                break;
            case 'system_notification':
                this.handleSystemNotification(data);
                break;
            case 'update_available':
                this.handleUpdateNotification(data);
                break;
        }
    }

    handleOpen() {
        console.log('User notifications WebSocket connected');
    }

    handleClose(event) {
        console.log('User notifications WebSocket closed');
    }

    handleError(error) {
        console.error('User notifications WebSocket error:', error);
    }

    handleDownloadCompleted(data) {
        // Show browser notification
        if (Notification.permission === 'granted') {
            new Notification(data.title, {
                body: data.message,
                icon: data.course_image || '/static/images/icon.png'
            });
        }

        // Show in-app notification
        if (window.showAlert) {
            window.showAlert(data.message, 'positive');
        }

        // Update download count badge
        this.updateDownloadBadge();
    }

    handleSystemNotification(data) {
        const type = data.level === 'error' ? 'negative' :
                    data.level === 'warning' ? 'warning' : 'info';

        if (window.showAlert) {
            window.showAlert(data.message, type);
        }

        // Update logger badge if it's an error/warning
        if (data.level === 'error' || data.level === 'warning') {
            this.updateLoggerBadge();
        }
    }

    handleUpdateNotification(data) {
        // Show update modal
        $('.ui.update-available.modal .content p').html(
            `Version ${data.version} is available. Would you like to download it?`
        );

        $('.ui.update-available.modal').modal({
            onApprove: function() {
                window.open(data.download_url, '_blank');
            }
        }).modal('show');
    }

    updateDownloadBadge() {
        // Count active downloads
        const activeCount = $('.course.item[data-download-status="downloading"]').length;
        const $badge = $('#downloadCount');

        if (activeCount > 0) {
            $badge.text(activeCount).show();
        } else {
            $badge.hide();
        }
    }

    updateLoggerBadge() {
        const $badge = $('#badge-logger');
        const currentCount = parseInt($badge.text()) || 0;
        $badge.text(currentCount + 1).show();
    }

    send(data) {
        return window.wsManager.send(this.connectionName, data);
    }

    disconnect() {
        window.wsManager.close(this.connectionName);
    }
}

// Global functions for download progress tracking
window.initializeDownloadProgress = function(downloadId) {
    const handler = new DownloadProgressHandler(downloadId);
    handler.connect();
    return handler;
};

window.initializeNotifications = function(userId) {
    const handler = new NotificationHandler(userId);
    handler.connect();
    return handler;
};

// Cleanup function for when switching sections or leaving page
window.cleanupWebSocketConnections = function() {
    window.wsManager.closeAll();
};

// Auto cleanup on page unload
window.addEventListener('beforeunload', () => {
    window.cleanupWebSocketConnections();
});

// Export classes for advanced usage
window.WebSocketManager = WebSocketManager;
window.DownloadProgressHandler = DownloadProgressHandler;
window.NotificationHandler = NotificationHandler;