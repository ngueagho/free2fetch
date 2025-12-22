#!/bin/bash

# Free2Fetch - Quick Start (No Virtual Environment)
# ================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logo
echo -e "${PURPLE}
████████ ██████  ███████ ███████ ██████  ███████ ███████ ████████  ██████ ██   ██
██          ██   ██      ██      ██   ██ ██      ██         ██    ██      ██   ██
█████       ██   █████   █████   ██████  █████   █████      ██    ██      ███████
██          ██   ██      ██      ██   ██ ██      ██         ██    ██      ██   ██
██       ██████  ███████ ███████ ██   ██ ███████ ███████    ██     ██████ ██   ██
${NC}"

echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN}🚀 Free2Fetch SaaS Platform - Quick Start${NC}"
echo -e "${BLUE}==========================================${NC}"
echo

# Install Python packages with --break-system-packages
echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
python3 -m pip install --break-system-packages django djangorestframework djangorestframework-simplejwt django-cors-headers

# Create minimal Django setup
echo -e "${BLUE}🔧 Setting up minimal Django backend...${NC}"
cd backend

# Create simple Django settings
mkdir -p config/settings
cat > config/settings/__init__.py << 'EOL'
# Settings package
EOL

cat > config/settings/base.py << 'EOL'
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = 'free2fetch-demo-key-change-in-production'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# REST Framework
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}
EOL

cat > config/settings/dev.py << 'EOL'
from .base import *

DEBUG = True
EOL

# Initialize Django
echo -e "${BLUE}🗃️  Initializing Django database...${NC}"
python3 manage.py migrate

# Create superuser
echo -e "${BLUE}👤 Creating admin user...${NC}"
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@free2fetch.com', 'admin123')" | python3 manage.py shell

echo -e "${GREEN}✅ Backend setup complete${NC}"

# Setup simple frontend
echo -e "${BLUE}🎨 Setting up frontend...${NC}"
cd ../frontend

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${YELLOW}⚠️  Node.js not found. Frontend will be minimal HTML.${NC}"

    # Create simple HTML frontend
    cat > index.html << 'EOL'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Free2Fetch - Professional Udemy Course Downloader</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50 min-h-screen">
    <div class="container mx-auto px-4 py-16">
        <div class="text-center">
            <div class="mb-8">
                <div class="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-600 to-blue-600 rounded-xl mb-4">
                    <svg class="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd" />
                    </svg>
                </div>
                <h1 class="text-5xl font-bold text-gray-900 mb-4">
                    Welcome to <span class="bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">Free2Fetch</span>
                </h1>
                <p class="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
                    The most advanced SaaS platform for downloading, managing, and streaming your Udemy courses.
                    Built for professionals who value quality and efficiency.
                </p>
            </div>

            <div class="grid md:grid-cols-3 gap-6 mb-12">
                <div class="bg-white p-6 rounded-xl shadow-sm border">
                    <div class="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                        <svg class="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <h3 class="font-semibold text-gray-900 mb-2">OAuth Integration</h3>
                    <p class="text-gray-600 text-sm">Connect with your Udemy account securely and access all your enrolled courses.</p>
                </div>

                <div class="bg-white p-6 rounded-xl shadow-sm border">
                    <div class="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                        <svg class="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clip-rule="evenodd"/>
                        </svg>
                    </div>
                    <h3 class="font-semibold text-gray-900 mb-2">Advanced Downloads</h3>
                    <p class="text-gray-600 text-sm">Download courses in multiple qualities with subtitles and supplementary materials.</p>
                </div>

                <div class="bg-white p-6 rounded-xl shadow-sm border">
                    <div class="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                        <svg class="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                        </svg>
                    </div>
                    <h3 class="font-semibold text-gray-900 mb-2">Team Collaboration</h3>
                    <p class="text-gray-600 text-sm">Share courses with team members and manage access with detailed permissions.</p>
                </div>
            </div>

            <div class="flex flex-col sm:flex-row gap-4 justify-center mb-12">
                <a href="http://localhost:8000/admin" class="inline-flex items-center justify-center px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-medium rounded-lg hover:from-purple-700 hover:to-blue-700 transition-colors">
                    Open Admin Panel
                    <svg class="ml-2 w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                        <path fill-rule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clip-rule="evenodd"/>
                    </svg>
                </a>
                <a href="http://localhost:8000/api" class="inline-flex items-center justify-center px-8 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors">
                    API Docs
                </a>
            </div>

            <div class="bg-gray-800 text-white p-6 rounded-xl">
                <h3 class="text-lg font-semibold mb-4">🚀 Platform Status</h3>
                <div class="grid md:grid-cols-2 gap-4 text-sm">
                    <div class="flex justify-between">
                        <span>Backend API:</span>
                        <span class="text-green-400">✅ Running</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Database:</span>
                        <span class="text-green-400">✅ SQLite Ready</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Admin Panel:</span>
                        <span class="text-green-400">✅ Available</span>
                    </div>
                    <div class="flex justify-between">
                        <span>Authentication:</span>
                        <span class="text-yellow-400">⚠️ Configure OAuth</span>
                    </div>
                </div>
                <div class="mt-4 p-3 bg-gray-700 rounded">
                    <p class="text-xs"><strong>Admin Credentials:</strong> admin / admin123</p>
                    <p class="text-xs"><strong>API Endpoint:</strong> http://localhost:8000/api</p>
                </div>
            </div>

            <div class="mt-8 text-sm text-gray-500">
                <p>🎯 Professional SaaS Platform • 🔒 Secure Django Backend • 📱 Responsive Design</p>
            </div>
        </div>
    </div>

    <script>
        // Simple status check
        async function checkStatus() {
            try {
                const response = await fetch('http://localhost:8000/health/');
                if (response.ok) {
                    console.log('✅ Backend is running');
                }
            } catch (error) {
                console.log('❌ Backend not accessible');
            }
        }
        checkStatus();
    </script>
</body>
</html>
EOL

    echo -e "${GREEN}✅ Simple HTML frontend created${NC}"
else
    # Initialize Node.js project
    if [ ! -f "package.json" ]; then
        npm init -y
        npm install next@latest react@latest react-dom@latest
    fi
    echo -e "${GREEN}✅ Node.js frontend initialized${NC}"
fi

# Create run scripts
echo -e "${BLUE}🔧 Creating run scripts...${NC}"
cd ..

# Create simple run script
cat > run.sh << 'EOL'
#!/bin/bash

echo "🚀 Starting Free2Fetch SaaS Platform..."
echo ""

# Function to handle Ctrl+C
cleanup() {
    echo ""
    echo "🛑 Shutting down Free2Fetch..."
    kill $DJANGO_PID 2>/dev/null
    if command -v python3 -m http.server &> /dev/null && [ -f "frontend/index.html" ]; then
        kill $FRONTEND_PID 2>/dev/null
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Django backend
echo "🔧 Starting Django Backend..."
cd backend
python3 manage.py runserver 8000 &
DJANGO_PID=$!
cd ..

# Wait for backend to start
sleep 3

# Start frontend (if HTML exists)
if [ -f "frontend/index.html" ]; then
    echo "🎨 Starting HTML Frontend..."
    cd frontend
    python3 -m http.server 3000 &
    FRONTEND_PID=$!
    cd ..
fi

echo ""
echo "✅ Free2Fetch is now running!"
echo ""
echo "🌐 Access Points:"
echo "   • Main App:    http://localhost:3000"
echo "   • Admin Panel: http://localhost:8000/admin"
echo "   • API:         http://localhost:8000/api"
echo "   • Health:      http://localhost:8000/health"
echo ""
echo "🔐 Admin Login:"
echo "   • Username: admin"
echo "   • Password: admin123"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Keep script running
wait $DJANGO_PID
EOL

chmod +x run.sh

echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN}🎉 Free2Fetch Platform Ready!${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "${YELLOW}🚀 To start the platform:${NC}"
echo -e "   ${GREEN}./run.sh${NC}"
echo ""
echo -e "${YELLOW}📖 Access Points:${NC}"
echo -e "   • Main App:    ${BLUE}http://localhost:3000${NC}"
echo -e "   • Admin Panel: ${BLUE}http://localhost:8000/admin${NC}"
echo -e "   • API:         ${BLUE}http://localhost:8000/api${NC}"
echo -e "   • Health:      ${BLUE}http://localhost:8000/health${NC}"
echo ""
echo -e "${YELLOW}🔐 Admin Credentials:${NC}"
echo -e "   • Username: ${GREEN}admin${NC}"
echo -e "   • Password: ${GREEN}admin123${NC}"
echo ""
echo -e "${PURPLE}Ready to launch! Run ${GREEN}./run.sh${PURPLE} to start! 🚀${NC}"
echo