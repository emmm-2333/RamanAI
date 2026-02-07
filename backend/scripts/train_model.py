import os
import sys
from pathlib import Path
import django

# Setup Django environment
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "raman_backend.settings")
django.setup()

from raman_api.ml_engine import MLEngine

def main():
    print("Triggering new training pipeline (Multi-Task CNN)...")
    result = MLEngine.train_new_version(description="Manually triggered training via script")
    print("Training Result:", result)

if __name__ == "__main__":
    main()
