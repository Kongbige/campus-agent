import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DEMO_TODAY"] = "2026-11-02"
os.environ["FORCE_MOCK"] = "1"
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
