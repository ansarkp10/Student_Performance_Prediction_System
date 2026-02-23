import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'student_performance.settings')
django.setup()

from django.contrib.auth.models import User
from performance_app.models import UserProfile

# Create admin user if not exists
if not User.objects.filter(username='admin').exists():
    admin_user = User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='admin123'
    )
    
    # Create admin profile
    UserProfile.objects.create(
        user=admin_user,
        role='admin',
        institution='Administration',
        phone=''
    )
    print("Admin user created successfully!")
    print("Username: admin")
    print("Password: admin123")
else:
    print("Admin user already exists.")