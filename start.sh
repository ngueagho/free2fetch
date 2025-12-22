#!/bin/bash

# Free2Fetch - Professional SaaS Platform Launch Script
# =======================================================

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

echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}🚀 Free2Fetch SaaS Platform${NC}"
echo -e "${GREEN}   Professional Udemy Course Downloader${NC}"
echo -e "${BLUE}=========================================${NC}"
echo

# Project information
echo -e "${YELLOW}📋 Project Information:${NC}"
echo -e "   • Backend: Django REST API with Celery"
echo -e "   • Frontend: Next.js 14 with TypeScript"
echo -e "   • Database: SQLite (dev) → PostgreSQL (prod)"
echo -e "   • Features: OAuth, Downloads, Freemium, Admin Panel"
echo -e "   • Architecture: Production-ready SaaS platform"
echo

# Check Python
echo -e "${BLUE}🐍 Checking Python environment...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 not found. Please install Python 3.8+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "${GREEN}✅ Python $PYTHON_VERSION found${NC}"

# Check Node.js
echo -e "${BLUE}📦 Checking Node.js environment...${NC}"
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Node.js not found. Please install Node.js 18+${NC}"
    exit 1
fi
NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js $NODE_VERSION found${NC}"

# Setup backend
echo -e "${BLUE}🔧 Setting up Django Backend...${NC}"
cd backend

# Create virtual environment if not exists
if [ ! -d "venv" ]; then
    echo -e "   Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "   Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo -e "   Installing Python dependencies..."
cat > requirements.txt << 'EOL'
Django>=4.2,<5.0
djangorestframework>=3.14
djangorestframework-simplejwt>=5.3
django-cors-headers>=4.3
django-filter>=23.3
celery>=5.3
redis>=5.0
psycopg2-binary>=2.9
pillow>=10.0
requests>=2.31
python-decouple>=3.8
gunicorn>=21.2
whitenoise>=6.6
aiohttp>=3.9
aiofiles>=23.2
m3u8>=4.0
EOL

pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
if [ ! -f ".env" ]; then
    echo -e "   Creating environment configuration..."
    cat > .env << 'EOL'
# Django Settings
SECRET_KEY=your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Udemy OAuth
UDEMY_CLIENT_ID=your-udemy-client-id
UDEMY_CLIENT_SECRET=your-udemy-client-secret
UDEMY_REDIRECT_URI=http://localhost:3000/auth/callback

# Email
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=

# Storage
MEDIA_ROOT=./media
STATIC_ROOT=./static
EOL
fi

# Initialize Django
echo -e "   Initializing Django database..."
if [ -f "manage.py" ]; then
    python manage.py collectstatic --noinput --clear || true
    python manage.py migrate || echo "Migration will be done after models are complete"

    # Create superuser if not exists
    echo -e "   Creating admin user (admin/admin123)..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@free2fetch.com', 'admin123')
    print('Admin user created: admin/admin123')
else:
    print('Admin user already exists')
" || echo "User creation will be available after Django setup is complete"
fi

echo -e "${GREEN}✅ Backend setup complete${NC}"

# Setup frontend
echo -e "${BLUE}🎨 Setting up Next.js Frontend...${NC}"
cd ../frontend

# Install Node dependencies
echo -e "   Installing Node.js dependencies..."
if [ ! -f "package.json" ]; then
    npm init -y
    npm install next@latest react@latest react-dom@latest typescript@latest
    npm install @types/node @types/react @types/react-dom
    npm install tailwindcss@latest autoprefixer@latest postcss@latest
fi

# Create basic Next.js config
if [ ! -f "next.config.js" ]; then
    cat > next.config.js << 'EOL'
/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    appDir: true,
  },
  images: {
    domains: ['localhost'],
  },
}

module.exports = nextConfig
EOL
fi

# Create Tailwind config
if [ ! -f "tailwind.config.js" ]; then
    cat > tailwind.config.js << 'EOL'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
EOL
fi

# Create basic layout
mkdir -p app
if [ ! -f "app/layout.tsx" ]; then
    cat > app/layout.tsx << 'EOL'
import './globals.css'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })

export const metadata = {
  title: 'Free2Fetch - Professional Udemy Course Downloader',
  description: 'Transform your Udemy learning experience with our professional SaaS platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
EOL
fi

# Create home page
if [ ! -f "app/page.tsx" ]; then
    cat > app/page.tsx << 'EOL'
import Link from 'next/link'

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-purple-50 via-blue-50 to-indigo-50">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center">
          <div className="mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-600 to-blue-600 rounded-xl mb-4">
              <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </div>
            <h1 className="text-5xl font-bold text-gray-900 mb-4">
              Welcome to <span className="bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">Free2Fetch</span>
            </h1>
            <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
              The most advanced SaaS platform for downloading, managing, and streaming your Udemy courses.
              Built for professionals who value quality and efficiency.
            </p>
          </div>

          <div className="space-y-4 mb-12">
            <div className="grid md:grid-cols-3 gap-6 text-left">
              <div className="bg-white p-6 rounded-xl shadow-sm border">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">OAuth Integration</h3>
                <p className="text-gray-600 text-sm">Connect with your Udemy account securely and access all your enrolled courses.</p>
              </div>

              <div className="bg-white p-6 rounded-xl shadow-sm border">
                <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm3.293-7.707a1 1 0 011.414 0L9 10.586V3a1 1 0 112 0v7.586l1.293-1.293a1 1 0 111.414 1.414l-3 3a1 1 0 01-1.414 0l-3-3a1 1 0 010-1.414z" clipRule="evenodd"/>
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Advanced Downloads</h3>
                <p className="text-gray-600 text-sm">Download courses in multiple qualities with subtitles and supplementary materials.</p>
              </div>

              <div className="bg-white p-6 rounded-xl shadow-sm border">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                  <svg className="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z"/>
                  </svg>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Team Collaboration</h3>
                <p className="text-gray-600 text-sm">Share courses with team members and manage access with detailed permissions.</p>
              </div>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/dashboard" className="inline-flex items-center justify-center px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-medium rounded-lg hover:from-purple-700 hover:to-blue-700 transition-colors">
              Open Dashboard
              <svg className="ml-2 w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10.293 3.293a1 1 0 011.414 0l6 6a1 1 0 010 1.414l-6 6a1 1 0 01-1.414-1.414L14.586 11H3a1 1 0 110-2h11.586l-4.293-4.293a1 1 0 010-1.414z" clipRule="evenodd"/>
              </svg>
            </Link>
            <Link href="/admin" className="inline-flex items-center justify-center px-8 py-3 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition-colors">
              Admin Panel
            </Link>
          </div>

          <div className="mt-12 text-sm text-gray-500">
            <p>🚀 Professional SaaS Platform • 🔒 Secure & Scalable • 📱 Mobile Ready</p>
          </div>
        </div>
      </div>
    </main>
  )
}
EOL
fi

# Create globals.css
if [ ! -f "app/globals.css" ]; then
    cat > app/globals.css << 'EOL'
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 0, 0, 0;
  --background-start-rgb: 214, 219, 220;
  --background-end-rgb: 255, 255, 255;
}

* {
  box-sizing: border-box;
  padding: 0;
  margin: 0;
}

html,
body {
  max-width: 100vw;
  overflow-x: hidden;
}

body {
  color: rgb(var(--foreground-rgb));
  background: linear-gradient(
      to bottom,
      transparent,
      rgb(var(--background-end-rgb))
    )
    rgb(var(--background-start-rgb));
}
EOL
fi

echo -e "${GREEN}✅ Frontend setup complete${NC}"

# Create launch scripts
echo -e "${BLUE}🔧 Creating launch scripts...${NC}"
cd ..

# Backend launch script
cat > start-backend.sh << 'EOL'
#!/bin/bash
echo "🚀 Starting Free2Fetch Backend..."
cd backend
source venv/bin/activate
export DJANGO_SETTINGS_MODULE=config.settings.dev
python manage.py runserver 8000
EOL

# Frontend launch script
cat > start-frontend.sh << 'EOL'
#!/bin/bash
echo "🎨 Starting Free2Fetch Frontend..."
cd frontend
npm run dev
EOL

# Combined launch script
cat > launch.sh << 'EOL'
#!/bin/bash

# Free2Fetch Platform Launcher
echo "🚀 Launching Free2Fetch SaaS Platform..."

# Function to kill processes on exit
cleanup() {
    echo "🛑 Shutting down Free2Fetch..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "🔧 Starting Django Backend on http://localhost:8000..."
cd backend && source venv/bin/activate && python manage.py runserver 8000 &
BACKEND_PID=$!

# Wait a moment
sleep 3

# Start frontend
echo "🎨 Starting Next.js Frontend on http://localhost:3000..."
cd ../frontend && npm run dev &
FRONTEND_PID=$!

# Keep script running
echo "✅ Free2Fetch is running!"
echo "   • Frontend: http://localhost:3000"
echo "   • Backend API: http://localhost:8000"
echo "   • Admin Panel: http://localhost:8000/admin"
echo ""
echo "Press Ctrl+C to stop all services"

wait
EOL

chmod +x start-backend.sh start-frontend.sh launch.sh

echo -e "${GREEN}✅ Launch scripts created${NC}"

# Final summary
echo
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}🎉 Free2Fetch SaaS Platform Ready!${NC}"
echo -e "${BLUE}=========================================${NC}"
echo
echo -e "${YELLOW}🚀 Quick Start:${NC}"
echo -e "   ${GREEN}./launch.sh${NC}           - Start both frontend and backend"
echo -e "   ${GREEN}./start-backend.sh${NC}    - Start Django backend only"
echo -e "   ${GREEN}./start-frontend.sh${NC}   - Start Next.js frontend only"
echo
echo -e "${YELLOW}📖 Access Points:${NC}"
echo -e "   • Main App:    ${BLUE}http://localhost:3000${NC}"
echo -e "   • API:         ${BLUE}http://localhost:8000/api${NC}"
echo -e "   • Admin:       ${BLUE}http://localhost:8000/admin${NC}"
echo -e "   • Health:      ${BLUE}http://localhost:8000/health${NC}"
echo
echo -e "${YELLOW}🔐 Default Admin Credentials:${NC}"
echo -e "   • Username:    ${GREEN}admin${NC}"
echo -e "   • Password:    ${GREEN}admin123${NC}"
echo
echo -e "${YELLOW}📁 Project Structure:${NC}"
echo -e "   • backend/     - Django REST API + Celery"
echo -e "   • frontend/    - Next.js 14 + TypeScript"
echo -e "   • README.md    - Complete documentation"
echo
echo -e "${PURPLE}Ready to transform Udemy course downloading! 🎯${NC}"
echo