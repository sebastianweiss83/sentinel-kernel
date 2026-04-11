"""Allow `python -m sentinel` to invoke the Sentinel CLI.

This mirrors the `sentinel` console_script entry point so Sentinel is
usable on systems where the entry point is not on PATH (common on
macOS after `pip3 install --user`, and in sandboxed CI runners).
"""

from __future__ import annotations

import sys

from sentinel.cli import main

if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
