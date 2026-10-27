"""Execute the KN189 synthetic SDTM -> ADaM -> Define-XML development build."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / '.github/scripts'))
from validate_synthetic import validate

if __name__ == '__main__':
    raise SystemExit(int(validate('kn189', ROOT)['status'] != 'succeeded'))
