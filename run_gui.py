#!/usr/bin/env python3
"""Entry point for Audit Merge GUI application."""

import os
import sys

package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if package_root not in sys.path:
    sys.path.insert(0, package_root)

from audit_merge.gui.app import main  # noqa: E402

if __name__ == "__main__":
    main()
