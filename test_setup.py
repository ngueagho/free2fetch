#!/usr/bin/env python3
"""
Test script to verify the Django project setup and basic functionality.
Run this to ensure all components are properly configured.
"""

import os
import sys
import django
from pathlib import Path

# Add the project directory to Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'udemy_downloader.settings')

def test_django_setup():
    """Test basic Django setup."""
    print("🔍 Testing Django setup...")

    try:
        django.setup()
        print("✅ Django setup successful")
        return True
    except Exception as e:
        print(f"❌ Django setup failed: {e}")
        return False

def test_apps_import():
    """Test that all Django apps can be imported."""
    print("🔍 Testing app imports...")

    apps_to_test = [
        'apps.users',
        'apps.core',
        'apps.courses',
        'apps.downloads',
        'apps.api'
    ]

    success = True
    for app in apps_to_test:
        try:
            __import__(app)
            print(f"✅ {app} imported successfully")
        except Exception as e:
            print(f"❌ Failed to import {app}: {e}")
            success = False

    return success

def test_models():
    """Test that models can be imported."""
    print("🔍 Testing model imports...")

    try:
        from apps.users.models import User, UserSettings
        from apps.courses.models import Course, UserCourse
        from apps.downloads.models import DownloadTask
        print("✅ All models imported successfully")
        return True
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        return False

def test_services():
    """Test that services can be imported."""
    print("🔍 Testing service imports...")

    try:
        from apps.core.services.udemy_service import UdemyService
        from apps.core.services.download_engine import DownloadEngine
        from apps.core.services.m3u8_service import M3U8Service
        print("✅ All services imported successfully")
        return True
    except Exception as e:
        print(f"❌ Service import failed: {e}")
        return False

def test_api_views():
    """Test that API views can be imported."""
    print("🔍 Testing API view imports...")

    try:
        from apps.api.views import (
            CourseViewSet, DownloadTaskViewSet,
            AuthViewSet, SettingsViewSet
        )
        print("✅ All API views imported successfully")
        return True
    except Exception as e:
        print(f"❌ API view import failed: {e}")
        return False

def test_consumers():
    """Test that WebSocket consumers can be imported."""
    print("🔍 Testing WebSocket consumer imports...")

    try:
        from apps.core.consumers import (
            DownloadProgressConsumer, UserNotificationConsumer,
            DownloadControlConsumer, GlobalStatsConsumer
        )
        print("✅ All consumers imported successfully")
        return True
    except Exception as e:
        print(f"❌ Consumer import failed: {e}")
        return False

def test_tasks():
    """Test that Celery tasks can be imported."""
    print("🔍 Testing Celery task imports...")

    try:
        from apps.downloads.tasks import download_course_task
        print("✅ All tasks imported successfully")
        return True
    except Exception as e:
        print(f"❌ Task import failed: {e}")
        return False

def test_file_structure():
    """Test that all required files exist."""
    print("🔍 Testing file structure...")

    required_files = [
        'manage.py',
        'requirements.txt',
        'udemy_downloader/settings.py',
        'udemy_downloader/urls.py',
        'udemy_downloader/asgi.py',
        'udemy_downloader/wsgi.py',
        'udemy_downloader/celery.py',
        'templates/base.html',
        'templates/partials/course_card.html',
        'static/js/app.js',
        'static/js/websocket-client.js',
        'static/css/app.css',
        'locale/en/LC_MESSAGES/django.po',
        'locale/es/LC_MESSAGES/django.po',
        'locale/fr/LC_MESSAGES/django.po',
    ]

    success = True
    for file_path in required_files:
        full_path = project_dir / file_path
        if full_path.exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")
            success = False

    return success

def test_settings():
    """Test Django settings configuration."""
    print("🔍 Testing Django settings...")

    try:
        from django.conf import settings

        # Check required settings
        required_settings = [
            'SECRET_KEY', 'DATABASES', 'INSTALLED_APPS',
            'MIDDLEWARE', 'TEMPLATES', 'CELERY_BROKER_URL',
            'CHANNEL_LAYERS', 'LANGUAGES'
        ]

        success = True
        for setting in required_settings:
            if hasattr(settings, setting):
                print(f"✅ {setting} is configured")
            else:
                print(f"❌ {setting} is missing")
                success = False

        return success
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False

def check_dependencies():
    """Check that all required dependencies are available."""
    print("🔍 Checking dependencies...")

    required_packages = [
        'django', 'djangorestframework', 'channels', 'celery',
        'redis', 'aiohttp', 'cryptography', 'requests',
        'psycopg2', 'pillow', 'httpx'
    ]

    success = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package} is available")
        except ImportError:
            print(f"❌ {package} is missing - run: pip install {package}")
            success = False

    return success

def main():
    """Run all tests."""
    print("🚀 Starting Django Project Tests")
    print("=" * 50)

    tests = [
        ("Dependencies", check_dependencies),
        ("File Structure", test_file_structure),
        ("Django Setup", test_django_setup),
        ("App Imports", test_apps_import),
        ("Models", test_models),
        ("Services", test_services),
        ("API Views", test_api_views),
        ("Consumers", test_consumers),
        ("Tasks", test_tasks),
        ("Settings", test_settings),
    ]

    results = {}
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} test...")
        results[test_name] = test_func()

    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)

    passed = sum(results.values())
    total = len(results)

    for test_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The Django project is ready.")
        print("\nNext steps:")
        print("1. Set up your database: python manage.py migrate")
        print("2. Create a superuser: python manage.py createsuperuser")
        print("3. Start Redis server for Celery and Channels")
        print("4. Start Celery worker: celery -A udemy_downloader worker --loglevel=info")
        print("5. Start Django server: python manage.py runserver")
    else:
        print("⚠️  Some tests failed. Please fix the issues before proceeding.")
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())