"""Regenerate derived/twin/validation.json (Digital Twin model verification/validation records).

Usage: python3 -I scripts/twin_validate.py <repo-root>
Deterministic: the same code and reference data always give the same file (checked by tests).
"""
import json
import os
import sys

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
sys.path.insert(0, ROOT)

from api.twin import validation  # noqa: E402

out = validation.write()
for r in out["records"]:
    m = r["metrics"]
    tail = f"max |rel err| {m['max_abs_rel_error_pct']:.3f}%  MAE {m['mae']:.4g} {r['unit']}" if m else "no metric"
    print(f"{r['status']:15s} {r['model_id']:30s} {r['output']:28s} {tail}")
print(f"wrote {os.path.relpath(validation.OUT_PATH, ROOT)} ({len(out['records'])} records)")
bad = [r for r in out["records"] if r["status"] == "failed"]
sys.exit(1 if bad else 0)
