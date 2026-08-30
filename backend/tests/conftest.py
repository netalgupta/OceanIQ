import os
import sys
from pathlib import Path

# Add backend root to sys.path so `src.*` imports always resolve cleanly
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# The ML suite must stay deterministic and offline: force the synthetic data
# path even when a developer's backend/.env enables live Supabase archives.
# (Individual tests may opt in via VARUNA_TEST_ALLOW_REAL_DATA=1 + argo_store
# monkeypatching; see test_ml_models.py.)
os.environ.setdefault("VARUNA_ML_REAL_DATA", "0")
