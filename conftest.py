"""
pytest configuration for the API2Trade SDK test suite.

Sets up the PYTHONPATH so tests can import the package without installing it.
"""

import sys
import os

# Make the sdk root importable when running pytest from the repo root
sys.path.insert(0, os.path.dirname(__file__))
