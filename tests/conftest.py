"""Pytest configuration — adds tool directories to sys.path."""

import os
import sys

# Add tools directory so tests can import crossref, duplicates, fmt directly
_tools_dir = os.path.join(os.path.dirname(__file__), "..", "skills", "bibtidy", "tools")
if _tools_dir not in sys.path:
    sys.path.insert(0, os.path.abspath(_tools_dir))

# Add tests directory so validate.py is importable
_tests_dir = os.path.dirname(__file__)
if _tests_dir not in sys.path:
    sys.path.insert(0, os.path.abspath(_tests_dir))
