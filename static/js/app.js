/**
 * Main application JavaScript
 * Handles navigation, authentication, and global functionality
 */

// Global variables
window.currentSection = 'courses';
window.authToken = null;
window.websocketConnections = {};

// Application initialization
$(document).ready(function() {
    initializeApp();
});

function initializeApp() {
    // Initialize Semantic UI components
    $('.ui.dropdown').dropdown();
    $('.ui.checkbox').checkbox();
    $('.ui.progress').progress();
    $('.ui.modal').modal();

    // Initialize navigation
    initializeNavigation();

    // Initialize authentication handling
    initializeAuthentication();

    // Initialize global event handlers
    initializeGlobalEvents();

    // Initialize HTMX
    initializeHTMX();

    // Check if user is authenticated
    if (window.userData && window.userData.isAuthenticated) {
        initializeAuthenticatedFeatures();
    } else {
        showLoginSection();
    }
}

// Navigation handling
function initializeNavigation() {
    // Sidebar navigation
    $('.sidebar .item[data-section]').on('click', function(e) {
        e.preventDefault();
        const section = $(this).data('section');
        switchSection(section);
    });

    // Update active menu item
    function updateActiveMenuItem(section) {
        $('.sidebar .item').removeClass('active purple');
        $(`.sidebar .item[data-section="${section}"]`).addClass('active purple');
    }

    // Global section switching function
    window.switchSection = function(section) {
        if (window.currentSection === section) return;

        // Hide all sections
        $('.content .section').hide();

        // Show target section
        $(`.${section}.section`).show();

        // Update navigation
        updateActiveMenuItem(section);
        window.currentSection = section;

        // Load section-specific content
        loadSectionContent(section);

        // Cleanup previous section
        cleanupSection();

        // Update URL without page reload
        if (history.pushState) {
            history.pushState(null, null, `#${section}`);
        }
    };

    // Handle browser back/forward
    window.addEventListener('popstate', function() {
        const section = window.location.hash.substring(1) || 'courses';
        switchSection(section);
    });

    // Initialize with current hash or default
    const initialSection = window.location.hash.substring(1) || 'courses';
    switchSection(initialSection);
}

function loadSectionContent(section) {
    const $sectionContainer = $(`.${section}.section`);

    // Show loading indicator
    $sectionContainer.find('.dimmer').addClass('active');

    // Load content based on section
    switch(section) {
        case 'courses':
            loadCoursesContent();
            break;
        case 'downloads':
            loadDownloadsContent();
            break;
        case 'settings':
            loadSettingsContent();
            break;
        case 'logger':
            loadLoggerContent();
            break;
        case 'about':
            loadAboutContent();
            break;
    }

    // Hide loading indicator
    setTimeout(() => {
        $sectionContainer.find('.dimmer').removeClass('active');
    }, 500);
}

function cleanupSection() {
    // Cleanup WebSocket connections from previous section
    if (window.cleanupDownloadConnections) {
        window.cleanupDownloadConnections();
    }

    // Clear any intervals or timeouts
    if (window.sectionIntervals) {
        window.sectionIntervals.forEach(interval => clearInterval(interval));
        window.sectionIntervals = [];
    }
}

// Authentication handling
function initializeAuthentication() {
    // Business account checkbox
    $('#business').on('change', function() {
        if ($(this).is(':checked')) {
            $('#divsubdomain').show();
        } else {
            $('#divsubdomain').hide();
        }
    });

    // How to get token link
    $('.how-get-token').on('click', function(e) {
        e.preventDefault();
        showTokenHelpModal();
    });

    // Global authentication functions
    window.loginWithUdemy = function() {
        // Redirect to OAuth login
        window.location.href = '/api/auth/udemy-login/';
    };

    window.loginWithAccessToken = function() {
        showAccessTokenModal();
    };

    window.logout = function() {
        if (confirm(window.translate('confirm_logout') || 'Are you sure you want to logout?')) {
            fetch('/api/auth/logout/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            })
            .then(() => {
                window.location.reload();
            });
        }
    };
}

function showLoginSection() {
    $('#loginSection').show();
    $('.dashboard').hide();
}

function showDashboard() {
    $('#loginSection').hide();
    $('.dashboard').show();
    initializeAuthenticatedFeatures();
}

function initializeAuthenticatedFeatures() {
    // Start WebSocket connections for notifications
    initializeNotificationWebSocket();

    // Start periodic updates
    startPeriodicUpdates();

    // Load initial content
    if (window.currentSection) {
        loadSectionContent(window.currentSection);
    }
}

// Global event handlers
function initializeGlobalEvents() {
    // Global error handler
    window.addEventListener('error', function(event) {
        console.error('Global error:', event.error);
        showAlert('An unexpected error occurred', 'negative');
    });

    // CSRF token refresh
    setInterval(refreshCsrfToken, 30 * 60 * 1000); // Every 30 minutes

    // Connection status monitoring
    window.addEventListener('online', function() {
        showAlert(window.translate('connection_restored') || 'Connection restored', 'positive');
    });

    window.addEventListener('offline', function() {
        showAlert(window.translate('connection_lost') || 'Connection lost', 'negative');
    });
}

// HTMX initialization
function initializeHTMX() {
    // Global HTMX configuration
    htmx.config.globalViewTransitions = true;
    htmx.config.defaultSwapStyle = 'innerHTML';

    // HTMX event handlers
    document.body.addEventListener('htmx:beforeRequest', function(evt) {
        // Add loading indicators
        const target = evt.target;
        if (target.classList.contains('ui') && target.classList.contains('button')) {
            target.classList.add('loading');
        }
    });

    document.body.addEventListener('htmx:afterRequest', function(evt) {
        // Remove loading indicators and reinitialize components
        const target = evt.target;
        if (target.classList.contains('ui') && target.classList.contains('button')) {
            target.classList.remove('loading');
        }

        // Reinitialize Semantic UI components in the updated content
        initializeSemanticComponents(evt.detail.target);
    });

    document.body.addEventListener('htmx:responseError', function(evt) {
        console.error('HTMX error:', evt.detail);
        showAlert('Request failed. Please try again.', 'negative');
    });
}

function initializeSemanticComponents(container = document) {
    // Reinitialize Semantic UI components in the given container
    $(container).find('.ui.dropdown').dropdown();
    $(container).find('.ui.checkbox').checkbox();
    $(container).find('.ui.progress').progress();
    $(container).find('.ui.modal').modal();
    $(container).find('.ui.accordion').accordion();
    $(container).find('.ui.popup').popup();
}

// WebSocket handling
function initializeNotificationWebSocket() {
    if (!window.userData || !window.userData.isAuthenticated) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/user-notifications/${window.userData.id}/`;

    const websocket = new WebSocket(wsUrl);

    websocket.onopen = function() {
        console.log('Notification WebSocket connected');
    };

    websocket.onmessage = function(event) {
        const data = JSON.parse(event.data);
        handleNotification(data);
    };

    websocket.onclose = function() {
        console.log('Notification WebSocket disconnected');
        // Attempt to reconnect after 5 seconds
        setTimeout(initializeNotificationWebSocket, 5000);
    };

    websocket.onerror = function(error) {
        console.error('Notification WebSocket error:', error);
    };

    // Store reference for cleanup
    window.websocketConnections.notifications = websocket;
}

function handleNotification(data) {
    switch(data.type) {
        case 'download_completed':
            showDownloadCompletedNotification(data);
            break;
        case 'system_notification':
            showSystemNotification(data);
            break;
        case 'update_available':
            showUpdateNotification(data);
            break;
    }

    // Update badge counts
    updateBadgeCounts();
}

function showDownloadCompletedNotification(data) {
    // Show browser notification if permission granted
    if (Notification.permission === 'granted') {
        new Notification(data.title, {
            body: data.message,
            icon: data.course_image || '/static/images/icon.png'
        });
    }

    // Show in-app notification
    showAlert(data.message, 'positive');

    // Update downloads section if visible
    if (window.currentSection === 'downloads') {
        loadDownloadsContent();
    }
}

function showSystemNotification(data) {
    const level = data.level === 'error' ? 'negative' : data.level === 'warning' ? 'warning' : 'info';
    showAlert(data.message, level);

    // Update logger badge
    const $badge = $('#badge-logger');
    const currentCount = parseInt($badge.text()) || 0;
    $badge.text(currentCount + 1).show();
}

function showUpdateNotification(data) {
    $('.ui.update-available.modal .content p').html(
        `Version ${data.version} is available. Would you like to download it?`
    );

    $('.ui.update-available.modal').modal({
        onApprove: function() {
            window.open(data.download_url, '_blank');
        }
    }).modal('show');
}

// Section content loading
function loadCoursesContent() {
    // Load courses via HTMX if container is empty
    const $container = $('#coursesContainer');
    if ($container.children().length === 0) {
        htmx.ajax('GET', '/api/courses/', {target: '#coursesContainer'});
    }
}

function loadDownloadsContent() {
    // Load downloads via HTMX
    const $container = $('#downloadsContainer');
    htmx.ajax('GET', '/api/downloads/', {target: '#downloadsContainer'});
}

function loadSettingsContent() {
    // Settings are loaded with the template
    initializeSettingsForm();
}

function loadLoggerContent() {
    // Logger content is loaded with the template
    // Additional initialization happens in logger.html
}

function loadAboutContent() {
    // About content is static
    // Load system info
    loadSystemInfo();
}

// Utility functions
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
           document.querySelector('meta[name=csrf-token]')?.content ||
           $('input[name="csrfmiddlewaretoken"]').val();
}

function refreshCsrfToken() {
    fetch('/api/auth/csrf-token/')
        .then(response => response.json())
        .then(data => {
            $('input[name="csrfmiddlewaretoken"]').val(data.csrf_token);
            $('meta[name="csrf-token"]').attr('content', data.csrf_token);
        })
        .catch(error => {
            console.error('Failed to refresh CSRF token:', error);
        });
}

window.showAlert = function(message, type = 'info') {
    // Remove existing alerts
    $('.ui.message.alert').remove();

    // Create alert element
    const alertClass = type === 'positive' ? 'positive' :
                      type === 'negative' ? 'negative' :
                      type === 'warning' ? 'warning' : 'info';

    const $alert = $(`
        <div class="ui ${alertClass} message alert" style="position: fixed; top: 70px; right: 20px; z-index: 9999; max-width: 400px;">
            <i class="close icon"></i>
            <div class="header">${message}</div>
        </div>
    `);

    // Add to page
    $('body').append($alert);

    // Handle close button
    $alert.find('.close.icon').on('click', function() {
        $alert.remove();
    });

    // Auto-hide after 5 seconds
    setTimeout(() => {
        $alert.fadeOut(300, function() {
            $(this).remove();
        });
    }, 5000);
};

function updateBadgeCounts() {
    // Update download count
    const activeDownloads = $('.course.item[data-download-status="downloading"]').length;
    const $downloadBadge = $('#downloadCount');
    if (activeDownloads > 0) {
        $downloadBadge.text(activeDownloads).show();
    } else {
        $downloadBadge.hide();
    }
}

function startPeriodicUpdates() {
    // Update badges every 30 seconds
    window.sectionIntervals = window.sectionIntervals || [];
    window.sectionIntervals.push(
        setInterval(updateBadgeCounts, 30000)
    );
}

// Modal functions
function showTokenHelpModal() {
    const $modal = $(`
        <div class="ui modal" id="tokenHelpModal">
            <div class="header">${window.translate('how_to_get_token') || 'How to get Access Token'}</div>
            <div class="content">
                <div class="ui ordered list">
                    <div class="item">
                        <div class="content">
                            <div class="header">Login to Udemy</div>
                            <div class="description">Go to udemy.com and login to your account</div>
                        </div>
                    </div>
                    <div class="item">
                        <div class="content">
                            <div class="header">Open Developer Tools</div>
                            <div class="description">Press F12 or right-click and select "Inspect"</div>
                        </div>
                    </div>
                    <div class="item">
                        <div class="content">
                            <div class="header">Go to Application/Storage Tab</div>
                            <div class="description">Find the "Application" or "Storage" tab in developer tools</div>
                        </div>
                    </div>
                    <div class="item">
                        <div class="content">
                            <div class="header">Find Cookies</div>
                            <div class="description">Expand "Cookies" and click on "udemy.com"</div>
                        </div>
                    </div>
                    <div class="item">
                        <div class="content">
                            <div class="header">Copy Access Token</div>
                            <div class="description">Find "access_token" and copy its value</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="actions">
                <div class="ui cancel button">Close</div>
            </div>
        </div>
    `);

    $modal.modal('show');
}

function showAccessTokenModal() {
    const $modal = $(`
        <div class="ui modal" id="accessTokenModal">
            <div class="header">Login with Access Token</div>
            <div class="content">
                <form class="ui form" id="tokenLoginForm">
                    <div class="field">
                        <div class="ui checkbox">
                            <input type="checkbox" id="modalBusiness">
                            <label>Business Account</label>
                        </div>
                    </div>
                    <div class="field" id="modalSubdomainField" style="display: none;">
                        <label>Business Subdomain</label>
                        <div class="ui labeled input">
                            <div class="ui label">https://</div>
                            <input type="text" id="modalSubdomain" placeholder="your-company">
                            <div class="ui label">.udemy.com</div>
                        </div>
                    </div>
                    <div class="field">
                        <label>Access Token</label>
                        <input type="password" id="modalAccessToken" placeholder="Paste your access token here">
                    </div>
                </form>
            </div>
            <div class="actions">
                <div class="ui cancel button">Cancel</div>
                <div class="ui primary button" id="submitToken">Login</div>
            </div>
        </div>
    `);

    // Handle business checkbox
    $modal.find('#modalBusiness').on('change', function() {
        if ($(this).is(':checked')) {
            $modal.find('#modalSubdomainField').show();
        } else {
            $modal.find('#modalSubdomainField').hide();
        }
    });

    // Handle form submission
    $modal.find('#submitToken').on('click', function() {
        const accessToken = $modal.find('#modalAccessToken').val();
        const subdomain = $modal.find('#modalSubdomain').val() || 'www';

        if (!accessToken.trim()) {
            showAlert('Please enter an access token', 'negative');
            return;
        }

        $(this).addClass('loading disabled');

        fetch('/api/auth/token-login/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify({
                access_token: accessToken,
                subdomain: subdomain
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                $modal.modal('hide');
                showDashboard();
                showAlert('Login successful!', 'positive');
            } else {
                showAlert('Login failed: ' + data.error, 'negative');
                $(this).removeClass('loading disabled');
            }
        })
        .catch(error => {
            showAlert('Login failed: ' + error.message, 'negative');
            $(this).removeClass('loading disabled');
        });
    });

    $modal.modal('show');
}

function initializeSettingsForm() {
    // Settings form initialization is handled in settings.html
}

function loadSystemInfo() {
    // System info loading is handled in about.html
}

// Request notification permission
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

// Export global functions
window.initializeApp = initializeApp;
window.switchSection = switchSection;
window.loadSectionContent = loadSectionContent;