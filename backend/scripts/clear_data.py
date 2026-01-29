import os
import sys
import django

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'raman_backend.settings')
django.setup()

from raman_api.models import SpectrumRecord, Patient

def clear_data():
    print("Starting safe data cleanup...")
    
    # Delete Spectrum Records first (Foreign Key to Patient)
    record_count, _ = SpectrumRecord.objects.all().delete()
    print(f"Deleted {record_count} Spectrum Records.")
    
    # Delete Patients
    patient_count, _ = Patient.objects.all().delete()
    print(f"Deleted {patient_count} Patients.")
    
    print("Cleanup complete! User accounts are preserved.")

if __name__ == '__main__':
    clear_data()