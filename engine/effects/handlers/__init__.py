"""Effect handlers package.

This package auto-imports all `op*.py` modules to ensure opcode handlers register themselves.
"""

from __future__ import annotations

import importlib
import pkgutil

# Auto-discover handler modules (opXXXX_*.py)
for m in pkgutil.iter_modules(__path__):
    if m.name.startswith("op"):
        importlib.import_module(f"{__name__}.{m.name}")
