import sys
from pathlib import Path


# Project modules in `ingestion/` use absolute imports like `extractors.*`.
# Add that directory to sys.path so tests run from repo root consistently.
INGESTION_DIR = Path(__file__).resolve().parents[1]
if str(INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(INGESTION_DIR))
