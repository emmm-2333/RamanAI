import os
import sys
import django
import joblib
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Setup Django environment
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "raman_backend.settings")
django.setup()

from raman_api.models import SpectrumRecord, ModelVersion
from raman_api.preprocessing import RamanPreprocessor

def train_initial_model():
    print("Fetching training data...")
    # Fetch data where is_training_data=True
    records = SpectrumRecord.objects.filter(is_training_data=True)
    
    if not records.exists():
        print("No training data found!")
        return

    X = []
    y = []
    
    print(f"Processing {records.count()} records...")
    for record in records:
        if not record.spectral_data or 'y' not in record.spectral_data:
            continue
            
        # Get Y intensity data
        intensities = record.spectral_data['y']
        
        # Apply Preprocessing (Consistent with Inference)
        # 1. Smooth
        processed = RamanPreprocessor.smooth_savgol(intensities)
        # 2. Baseline
        # Note: We need X axis (wavenumbers) for polyfit baseline
        wavenumbers = record.spectral_data['x']
        processed = RamanPreprocessor.baseline_correction_poly(wavenumbers, processed)
        # 3. Normalize
        processed = RamanPreprocessor.normalize_minmax(processed)
        
        X.append(processed)
        
        # Label mapping
        label = 1 if record.diagnosis_result == 'Malignant' else 0
        y.append(label)

    X = np.array(X)
    y = np.array(y)
    
    print(f"Data shape: X={X.shape}, y={y.shape}")

    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Initialize Model (Random Forest)
    print("Training Random Forest Classifier...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluate
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)
    
    print(f"Model Accuracy: {acc:.4f}")
    
    # Save Model
    models_dir = Path(__file__).resolve().parent.parent / "models_storage"
    models_dir.mkdir(exist_ok=True)
    
    model_filename = "rf_v1.0.0.pkl"
    model_path = models_dir / model_filename
    
    joblib.dump(clf, model_path)
    print(f"Model saved to {model_path}")
    
    # Register in Database
    ModelVersion.objects.create(
        version="v1.0.0",
        file_path=str(model_path),
        accuracy=acc,
        metrics=report,
        is_active=True,
        description="Initial Random Forest model trained on imported data."
    )
    
    # Deactivate other models (if any)
    ModelVersion.objects.exclude(version="v1.0.0").update(is_active=False)
    
    print("Model v1.0.0 registered and activated.")

if __name__ == "__main__":
    train_initial_model()
