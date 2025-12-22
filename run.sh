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
