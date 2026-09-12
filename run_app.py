#!/usr/bin/env python3
"""Entry point for audit-merge application."""

import sys
import os

# Add the package root to sys.path
package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from src.audit_merge.tui.app import main

if __name__ == "__main__":
    main()