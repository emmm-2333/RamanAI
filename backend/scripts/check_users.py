import os
import sys
import django

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raman_backend.settings')
django.setup()

from django.contrib.auth.models import User

def check_users():
    users = User.objects.all()
    print(f"Total Users: {users.count()}")
    for u in users:
        print(f"- {u.username} (email: {u.email}, is_staff: {u.is_staff})")

if __name__ == '__main__':
    check_users()