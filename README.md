# Free2Fetch - Professional Course Downloader SaaS

A modern, scalable SaaS platform for downloading and managing Udemy courses with advanced features.

## 🚀 Features

- **OAuth Udemy Integration**: Secure authentication with Udemy accounts
- **Freemium Model**: Configurable download limits
- **Admin Dashboard**: Complete control panel with analytics and logs
- **Course Management**: Download, stream, and share courses
- **Professional UI**: Modern, responsive design with excellent SEO
- **Real-time Monitoring**: Comprehensive logging and analytics

## 📁 Project Structure

```
free2fetch/
├── backend/          # Django REST API
│   ├── apps/         # Django applications
│   ├── config/       # Settings and configuration
│   ├── requirements/ # Dependencies
│   └── manage.py     # Django management script
├── frontend/         # Next.js Frontend
│   ├── components/   # React components
│   ├── pages/        # Next.js pages
│   ├── styles/       # CSS/Tailwind styles
│   ├── utils/        # Utility functions
│   └── types/        # TypeScript definitions
├── storage/          # Course files storage
├── docs/             # Documentation
└── docker-compose.yml # Development environment
```

## 🛠 Tech Stack

**Backend:**
- Django 4.2 + Django REST Framework
- PostgreSQL (Production) / SQLite (Development)
- Redis (Caching & Celery)
- Celery (Background tasks)
- OAuth2 (Udemy integration)

**Frontend:**
- Next.js 14 + TypeScript
- Tailwind CSS + Shadcn/ui
- React Query (State management)
- Framer Motion (Animations)

## 🚦 Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Redis
- PostgreSQL (for production)

### Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd free2fetch
```

2. **Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

3. **Frontend Setup**
```bash
cd frontend
npm install
npm run dev
```

4. **Start Background Services**
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: Celery Worker
cd backend
celery -A config worker -l info

# Terminal 3: Celery Beat
cd backend
celery -A config beat -l info
```

## 🔧 Environment Variables

Create `.env` files in both backend and frontend directories:

**Backend (.env)**
```env
SECRET_KEY=your-secret-key
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379
UDEMY_CLIENT_ID=your-udemy-client-id
UDEMY_CLIENT_SECRET=your-udemy-client-secret
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

**Frontend (.env.local)**
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_SECRET=your-nextauth-secret
NEXTAUTH_URL=http://localhost:3000
```

## 📱 API Documentation

API documentation is available at `/api/docs/` when running the backend.

## 🚀 Deployment

### Production Setup

1. **Environment Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install python3-pip python3-venv postgresql redis-server nginx
```

2. **Database Setup**
```bash
sudo -u postgres createdb free2fetch
sudo -u postgres createuser free2fetch_user
```

3. **Application Deployment**
```bash
# Clone and setup
git clone <repository-url> /var/www/free2fetch
cd /var/www/free2fetch

# Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/prod.txt
python manage.py migrate
python manage.py collectstatic

# Frontend
cd ../frontend
npm install
npm run build

# Setup services
sudo systemctl enable redis
sudo systemctl start redis
```

## 📊 Monitoring & Logs

- **Admin Dashboard**: `/admin/` - Complete system overview
- **API Logs**: Real-time API usage and performance
- **User Analytics**: Download statistics and usage patterns
- **System Health**: Server performance and error tracking

## 🔒 Security Features

- OAuth2 secure authentication
- Rate limiting on all endpoints
- CORS protection
- SQL injection protection
- XSS protection
- CSRF protection
- Secure file handling

## 📈 Scalability

- Horizontal scaling with load balancer
- Redis caching for performance
- Celery for background processing
- CDN integration ready
- Database optimization

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Legal Notice

This software is intended for downloading courses you have legally purchased or enrolled in. Users are responsible for complying with Udemy's Terms of Service and applicable copyright laws.

---

**Built with ❤️ for the learning community**