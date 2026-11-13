#!/usr/bin/env python3
"""Integrity guard for the original NASA files.

Usage:
  python3 -I scripts/checksum_data.py Data derived/data_sha256.txt          # write baseline
  python3 -I scripts/checksum_data.py Data derived/data_sha256.txt --verify # compare to baseline
"""
import hashlib, os, sys


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root):
    rows = []
    for d, _, files in os.walk(root):
        for fn in sorted(files):
            p = os.path.join(d, fn)
            rows.append(f"{digest(p)}  {os.path.getsize(p)}  {os.path.relpath(p, root)}")
    return sorted(rows, key=lambda r: r.split("  ", 2)[2])


def main():
    root, out = sys.argv[1], sys.argv[2]
    rows = snapshot(root)
    if "--verify" in sys.argv:
        base = open(out).read().splitlines()
        if base == rows:
            print(f"OK: {len(rows)} files unchanged")
            return
        print("MISMATCH:")
        for r in sorted(set(base) ^ set(rows)):
            print("  ", r)
        sys.exit(1)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    with open(out, "w") as f:
        f.write("\n".join(rows) + "\n")
    print(f"baseline written: {len(rows)} files -> {out}")


if __name__ == "__main__":
    main()
