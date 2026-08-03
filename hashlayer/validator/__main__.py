#!/usr/bin/env python3

"""
HashLayer Validator Main Entry Point

This module serves as the main entry point for the HashLayer validator
when run as a Python module using: python -m hashlayer.validator.validator
"""

import os
import sys

# Add the parent directory to the Python path to ensure proper imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

if __name__ == "__main__":
    from hashlayer.validator.validator import main

    main()
