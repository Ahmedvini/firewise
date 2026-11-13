#!/usr/bin/env python3
"""Build the PSI-side file inventory from saved PSI investigation records (no network).

Usage: python3 -I scripts/inventory_psi.py <psi_api_dir> <out_prefix> [--cap-mb 500]
Writes <out_prefix>_files.csv (one row per PSI file) and <out_prefix>_summary.csv (one row per investigation).
Current file list = (added U modified) minus removed (by remote_path); compared against the record's totalFileSize.
"""
import collections, csv, glob, json, os, sys


def folder_of(remote_path):
    parts = (remote_path or "").strip("/").split("/")
    # /Home/psi-data/PSI-NN/<Folder>/... -> <Folder>
    return parts[3] if len(parts) > 4 else "(root)"


def main():
    psi_dir, out = sys.argv[1], sys.argv[2]
    cap_mb = float(sys.argv[sys.argv.index("--cap-mb") + 1]) if "--cap-mb" in sys.argv else 500.0
    cap = cap_mb * 1024 * 1024
    files_rows, summary_rows = [], []
    recs = sorted(glob.glob(os.path.join(psi_dir, "PSI-*.json")), key=lambda p: int(os.path.basename(p)[4:-5]))
    for p in recs:
        rec = json.load(open(p))
        acc, acr = rec.get("accession"), rec.get("investigationAcronym", "")
        removed = {f.get("remote_path") for f in rec.get("removed") or [] if isinstance(f, dict)}
        current = {}
        for key in ("added", "modified"):
            for f in rec.get(key) or []:
                if isinstance(f, dict) and f.get("remote_path") and f["remote_path"] not in removed:
                    current[f["remote_path"]] = f
        for t in rec.get("experimentalTable") or []:
            if isinstance(t, dict) and t.get("remote_path"):
                current.setdefault(t["remote_path"], t)
        by_folder = collections.Counter()
        listed = small_n = small_b = 0
        for rp, f in sorted(current.items()):
            size = float(f.get("file_size") or 0)
            fold = folder_of(rp)
            by_folder[fold] += 1
            listed += size
            under = size <= cap
            if under:
                small_n += 1
                small_b += size
            files_rows.append({
                "accession": acc, "acronym": acr, "folder": fold, "file_name": f.get("file_name"),
                "bytes": int(size), "ext": os.path.splitext(f.get("file_name") or "")[1].lower(),
                "restricted": f.get("restricted"), f"under_{int(cap_mb)}MB": under, "remote_path": rp,
            })
        total = float(rec.get("totalFileSize") or 0)
        summary_rows.append({
            "accession": acc, "acronym": acr, "title": rec.get("title", ""),
            "subResearchArea": rec.get("subResearchArea", ""), "projectType": rec.get("projectType", ""),
            "flightProgram": rec.get("flightProgram", ""), "hardware": rec.get("experimentHardware", ""),
            "start": rec.get("investigationStartDate", ""), "end": rec.get("investigationEndDate", ""),
            "doi": rec.get("doi", ""), "license": rec.get("licenseIdentifier", ""),
            "n_publications": len(rec.get("publications") or []),
            "n_files_listed": len(current), "listed_GB": round(listed / 1e9, 3),
            "totalFileSize_GB": round(total / 1e9, 3),
            "listing_complete": abs(listed - total) <= max(1e6, 0.001 * total),
            f"n_files_le_{int(cap_mb)}MB": small_n, f"GB_le_{int(cap_mb)}MB": round(small_b / 1e9, 3),
            "has_experimental_table": bool(rec.get("experimentalTable")),
            "folders": "; ".join(f"{k}:{v}" for k, v in by_folder.most_common()),
        })
    for rows, suffix in ((files_rows, "_files.csv"), (summary_rows, "_summary.csv")):
        if rows:
            with open(out + suffix, "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
    print(f"{len(summary_rows)} investigations, {len(files_rows)} files -> {out}_files.csv / {out}_summary.csv")
    print(f"{'acc':8s} {'acronym':22s} {'files':>6s} {'listed GB':>10s} {'total GB':>10s} complete  {'<=cap n':>8s} {'<=cap GB':>9s}")
    for r in summary_rows:
        print(f"{r['accession']:8s} {r['acronym'][:22]:22s} {r['n_files_listed']:6d} {r['listed_GB']:10.2f} "
              f"{r['totalFileSize_GB']:10.2f} {str(r['listing_complete']):8s} {r[f'n_files_le_{int(cap_mb)}MB']:8d} "
              f"{r[f'GB_le_{int(cap_mb)}MB']:9.2f}")


if __name__ == "__main__":
    main()
