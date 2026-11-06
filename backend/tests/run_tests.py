import sys
import os
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import pytest

if __name__ == "__main__":
    tests_dir = str(Path(__file__).parent)
    print(f"Running automated tests across: {tests_dir}")
    # run pytest with minimal flags
    exit_code = pytest.main([tests_dir, "-v", "--tb=short", "-s"])
    print(f"\nPytest exited with code: {exit_code}")
    sys.exit(exit_code)

