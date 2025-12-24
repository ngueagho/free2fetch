# Udemy Downloader GUI - Django SaaS Version

A complete Django-based SaaS application for downloading Udemy courses, converted from the original Electron/JavaScript application while maintaining all functionalities.

## Features

### 🎓 Course Management
- **Course Synchronization**: Automatic sync with your Udemy account
- **Search & Filter**: Find courses quickly with advanced filtering
- **Business Account Support**: Works with Udemy Business accounts
- **Course Information**: Display course details, progress, and metadata

### 📥 Download Engine
- **Multi-threaded Downloads**: Concurrent downloads for faster speeds
- **Resume Capability**: Resume interrupted downloads automatically
- **Quality Selection**: Choose from multiple video qualities (240p to 4K)
- **Subtitle Support**: Download captions in multiple languages
- **M3U8 Support**: Handle HLS streams and playlists
- **DRM Detection**: Identify and skip DRM-protected content

### ⚡ Real-time Features
- **Live Progress Tracking**: WebSocket-based real-time updates
- **Download Speed Monitoring**: Track current download speeds
- **Queue Management**: Organize and prioritize downloads
- **System Notifications**: Desktop notifications for completed downloads

### 🌍 Internationalization
- **Multi-language Support**: Available in 24 languages
- **RTL Support**: Right-to-left language support
- **Dynamic Language Switching**: Change language without restart

### 🔧 Advanced Settings
- **Download Preferences**: Customize quality, format, and location
- **Concurrent Limits**: Control simultaneous downloads
- **Speed Limiting**: Set bandwidth limits
- **Auto-updates**: Automatic application updates

## Technology Stack

- **Backend**: Django 4.2+ with Django REST Framework
- **Database**: PostgreSQL with Redis for caching
- **Task Queue**: Celery for background processing
- **Real-time**: Django Channels for WebSocket support
- **Frontend**: Django templates with HTMX for dynamic updates
- **Styling**: Semantic UI with custom CSS
- **Authentication**: JWT-based with Udemy OAuth integration

## Installation

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- Node.js 16+ (for frontend assets)

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd python_saas
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your database and Redis settings
   ```

5. **Run setup test**
   ```bash
   python test_setup.py
   ```

6. **Set up database**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

7. **Compile translations**
   ```bash
   python manage.py compilemessages
   ```

8. **Collect static files**
   ```bash
   python manage.py collectstatic
   ```

### Running the Application

1. **Start Redis server**
   ```bash
   redis-server
   ```

2. **Start Celery worker**
   ```bash
   celery -A udemy_downloader worker --loglevel=info
   ```

3. **Start Django development server**
   ```bash
   python manage.py runserver
   ```

4. **Access the application**
   - Open http://localhost:8000 in your browser
   - Login with your Udemy credentials or access token

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgres://username:password@localhost:5432/udemy_downloader
POSTGRES_DB=udemy_downloader
POSTGRES_USER=username
POSTGRES_PASSWORD=password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CHANNEL_LAYERS_REDIS_URL=redis://localhost:6379/1

# Udemy API (optional - for OAuth)
UDEMY_CLIENT_ID=your-client-id
UDEMY_CLIENT_SECRET=your-client-secret

# Email (for notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-password

# Storage (for production)
USE_S3=False
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_STORAGE_BUCKET_NAME=your-bucket

# Logging
LOG_LEVEL=INFO
```

### Django Settings

Key settings can be customized in `udemy_downloader/settings.py`:

- **Download limits**: `MAX_CONCURRENT_DOWNLOADS`
- **File storage**: `DOWNLOAD_ROOT`
- **Cache timeout**: `CACHE_TTL`
- **Session timeout**: `SESSION_COOKIE_AGE`

## API Documentation

The application provides a comprehensive REST API:

### Authentication
- `POST /api/auth/login/` - Login with credentials
- `POST /api/auth/token/` - Login with access token
- `POST /api/auth/refresh/` - Refresh JWT token
- `POST /api/auth/logout/` - Logout

### Courses
- `GET /api/courses/` - List user courses
- `POST /api/courses/sync/` - Sync courses from Udemy
- `GET /api/courses/{id}/` - Get course details
- `POST /api/courses/{id}/export_m3u/` - Export M3U playlist

### Downloads
- `GET /api/downloads/` - List downloads
- `POST /api/downloads/start/` - Start download
- `POST /api/downloads/{id}/pause/` - Pause download
- `POST /api/downloads/{id}/resume/` - Resume download
- `DELETE /api/downloads/{id}/` - Cancel download

### Settings
- `GET /api/settings/` - Get user settings
- `PUT /api/settings/` - Update settings
- `POST /api/settings/reset/` - Reset to defaults

## WebSocket Events

Real-time updates are provided via WebSocket connections:

### Download Progress
```javascript
// Connect to download progress
ws://localhost:8000/ws/download-progress/{download_id}/

// Events received:
{
  "type": "progress_update",
  "percentage": 45,
  "speed": "2.5 MB/s",
  "eta": "00:05:30"
}
```

### User Notifications
```javascript
// Connect to user notifications
ws://localhost:8000/ws/user-notifications/{user_id}/

// Events received:
{
  "type": "download_completed",
  "title": "Course Download Complete",
  "message": "Python Masterclass has finished downloading"
}
```

## Development

### Project Structure

```
python_saas/
├── udemy_downloader/          # Django project settings
├── apps/
│   ├── users/                 # User management
│   ├── core/                  # Core functionality and services
│   ├── courses/               # Course models and views
│   ├── downloads/             # Download management
│   └── api/                   # API endpoints
├── templates/                 # Django templates
│   ├── base.html             # Base template
│   └── partials/             # Template components
├── static/                    # Static files
│   ├── css/                  # Stylesheets
│   ├── js/                   # JavaScript files
│   └── images/               # Images and icons
├── locale/                    # Translation files
├── requirements.txt           # Python dependencies
├── manage.py                  # Django management script
└── test_setup.py             # Setup verification script
```

### Key Components

#### Services (`apps/core/services/`)
- **UdemyService**: Handles Udemy API interactions
- **DownloadEngine**: Manages file downloads with progress tracking
- **M3U8Service**: Processes HLS streams and playlists

#### Models
- **User**: Extended user model with Udemy integration
- **Course**: Course information and metadata
- **DownloadTask**: Download tracking and management

#### Tasks (`apps/downloads/tasks.py`)
- **download_course_task**: Celery task for course downloading
- **cleanup_old_downloads**: Maintenance task for cleanup

#### WebSocket Consumers (`apps/core/consumers.py`)
- **DownloadProgressConsumer**: Real-time download updates
- **UserNotificationConsumer**: User notifications
- **DownloadControlConsumer**: Download control commands

### Testing

Run the test suite:

```bash
# Test project setup
python test_setup.py

# Run Django tests
python manage.py test

# Run specific app tests
python manage.py test apps.downloads

# Run with coverage
coverage run manage.py test
coverage report
coverage html
```

### Adding New Languages

1. **Generate translation files**
   ```bash
   python manage.py makemessages -l de  # German example
   ```

2. **Translate strings**
   - Edit `locale/de/LC_MESSAGES/django.po`
   - Add translations for all msgid entries

3. **Compile translations**
   ```bash
   python manage.py compilemessages
   ```

4. **Update settings**
   - Add language to `LANGUAGES` in settings.py

## Deployment

### Docker Deployment

1. **Build containers**
   ```bash
   docker-compose build
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

3. **Run migrations**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

### Manual Deployment

1. **Set up production environment**
   ```bash
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic
   python manage.py compilemessages
   ```

2. **Configure web server (nginx/apache)**
3. **Set up process manager (systemd/supervisor)**
4. **Configure SSL/TLS certificates**
5. **Set up monitoring and logging**

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

- **Documentation**: Check the wiki for detailed guides
- **Issues**: Report bugs or request features on GitHub
- **Email**: Contact support@udeler.app for help

## Acknowledgments

- Based on the original Udemy Downloader GUI by FaisalUmair
- Built with Django, Celery, and Django Channels
- UI components from Semantic UI
- Icons from Font Awesome

---

**Note**: This software is for educational purposes only. Please respect content creators' rights and Udemy's terms of service.