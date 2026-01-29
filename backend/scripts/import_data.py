import os
import sys
import django
import pandas as pd
import json
from pathlib import Path

# Setup Django environment
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "raman_backend.settings")
django.setup()

from raman_api.models import Patient, SpectrumRecord
from django.contrib.auth.models import User

def import_data(file_path):
    print(f"Reading {file_path}...")
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Identify spectral columns (integers from 400 to 2200 approx)
    # We assume columns that are integers are wavenumbers
    spectral_cols = [c for c in df.columns if isinstance(c, int)]
    spectral_cols.sort()
    
    print(f"Found {len(spectral_cols)} spectral columns from {spectral_cols[0]} to {spectral_cols[-1]}")

    # Ensure a default user exists for upload
    admin_user, _ = User.objects.get_or_create(username='admin', defaults={'email': 'admin@example.com'})

    count = 0
    for index, row in df.iterrows():
        # Extract Patient Info
        name = row.get('姓名', f"Unknown-{index}")
        medical_record_no = row.get('病历号', str(index))
        # Handle case where medical_record_no might be float
        if pd.notna(medical_record_no):
            medical_record_no = str(int(medical_record_no)) if isinstance(medical_record_no, float) else str(medical_record_no)
        
        # Try to find existing patient or create new
        # We use name + medical_record_no as unique identifier logic here
        # But Patient model doesn't have medical_record_no field yet, only name/age/gender.
        # We will put medical_record_no in name for now or just use name.
        # Wait, Patient model is simple. Let's just create a patient.
        
        patient, created = Patient.objects.get_or_create(
            name=name,
            defaults={
                'age': 0, # Default
                'gender': 'F' # Most are breast cancer patients
            }
        )

        # Extract Target
        target_val = row.get('良恶性0：良性1.恶性')
        diagnosis = 'Malignant' if target_val == 1 else 'Benign' if target_val == 0 else 'Unknown'

        # Extract Metadata
        metadata = {
            'ER': row.get('ER'),
            'HER2': row.get('HER2'),
            'Ki67': row.get('Ki67'),
            'PR': row.get('PR'),
            'Subtype': row.get('分型'),
            'Category': row.get('分类'),
            'Image': row.get('影像'),
            'Date': str(row.get('收集日期')),
            'RecordNo': medical_record_no,
            'Label': row.get('Label')
        }
        
        # Clean metadata (handle NaN)
        metadata = {k: (v if pd.notna(v) else None) for k, v in metadata.items()}

        # Extract Spectral Data
        # Format: {'x': [400, 401...], 'y': [123.4, 567.8...]}
        intensities = row[spectral_cols].fillna(0).tolist()
        spectral_data = {
            'x': spectral_cols,
            'y': intensities
        }

        # Create Record
        record = SpectrumRecord.objects.create(
            patient=patient,
            file_path=file_path, # Point to source file
            diagnosis_result=diagnosis,
            confidence_score=1.0, # Ground truth
            uploaded_by=admin_user,
            spectral_data=spectral_data,
            metadata=metadata,
            is_training_data=True
        )
        count += 1
        if count % 100 == 0:
            print(f"Imported {count} records...")

    print(f"Successfully imported {count} records.")

if __name__ == "__main__":
    DATA_PATH = r"d:\studio\RamanAI\data\data.xlsx"
    import_data(DATA_PATH)
