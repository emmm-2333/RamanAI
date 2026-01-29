import os
import sys
import django

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raman_backend.settings')
django.setup()

from django.db import connection

def drop_tables():
    tables = [
        'raman_api_diagnosisfeedback',
        'raman_api_modelversion',
        'raman_api_spectrumrecord',
        'raman_api_patient',
        'raman_api_userprofile',
    ]
    
    with connection.cursor() as cursor:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        for table in tables:
            try:
                print(f"Dropping table {table}...")
                cursor.execute(f"DROP TABLE IF EXISTS {table};")
                print(f"Dropped {table}")
            except Exception as e:
                print(f"Error dropping {table}: {e}")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

if __name__ == '__main__':
    drop_tables()