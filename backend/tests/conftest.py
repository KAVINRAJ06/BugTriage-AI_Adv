import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SECRET_KEY", "test-secret-key-with-at-least-thirty-two-chars")
os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("SMTP_PASSWORD", "")
