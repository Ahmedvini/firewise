#!/usr/bin/env python3
"""Reproducible inventory of the original downloaded NASA files (read-only; archives are read in memory).

Usage: python3 -I scripts/inventory_local.py <data_dir> <psi_api_dir> <out_prefix>
Writes <out_prefix>.csv (one row per top-level file and per archive member) and <out_prefix>_files.json
(one summary per top-level file, incl. PSI provenance match when the file name/size appears in a PSI record).
"""
import collections, csv, glob, json, os, sys, zipfile

MAGIC = [
    (b"%PDF", "pdf"), (b"\xff\xd8\xff", "jpeg"), (b"HOBJ", "hobj (MVTec HALCON serialized iconic object)"),
    (b"PK\x03\x04", "zip"), (b"\x47", "mpeg-ts?"),
]
EXT_FMT = {".hobj": "hobj (MVTec HALCON serialized iconic object)", ".mdipsug": "csv (frame index)",
           ".next": "text (next frame counter)", ".jpeg": "jpeg", ".jpg": "jpeg", ".pdf": "pdf",
           ".txt": "text (camera EXIF dump)", ".ts": "mpeg-ts (H.264 video)", ".zip": "zip"}

# Manual, evidence-backed classification of each local top-level file (see docs/DATASET_AUDIT.md for sources).
CLASSIFY = {
    "PSI-159_Raw Data_21265C3_ACME.zip": dict(
        investigation="PSI-159 ACME CFI-G", category="raw camera frames + frame index",
        measurements="raw imagery only (no O2/P/flow/T in files)", parseable="partial: .hobj needs validated reader",
        value="high (only real ACME flame imagery we hold)"),
    "PSI-159_Raw Data_ACME_21265H1.mdipsug": dict(
        investigation="PSI-159 ACME CFI-G", category="frame index (frames absent)",
        measurements="none (camera timing/exposure metadata)", parseable="yes (CSV)", value="low"),
    "ACME_drawings_igniter.zip": dict(
        investigation="ACME (shared hardware; PSI record to confirm)", category="engineering drawings",
        measurements="none (hardware documentation)", parseable="partial: 5/14 have text layer, 9 need OCR",
        value="medium (shared-hardware evidence)"),
    "SAFFIRE_II_F1C1-BIT_jpeg.zip": dict(
        investigation="Saffire-II (PSI-99) — inferred: not in PSI listings; frame timestamps 2016-11-21 = Saffire-II burn day",
        category="camera built-in-test frames",
        measurements="none (static frames, no fire)", parseable="yes (JPEG)", value="low"),
    "SAFFIRE-III_F1C1_1200x920.zip": dict(
        investigation="PSI-100 Saffire-III", category="camera distortion-grid calibration",
        measurements="calibration only (30 mm grid -> pixel scale)", parseable="yes (JPEG)", value="medium"),
    "4 lampwick vlc-record-2010-09-08-12h10m02s-udp___233.1.14.5 _50000-.zip": dict(
        investigation="PSI-101 SAME-R", category="downlink video (cotton lamp wick smoke run)",
        measurements="video only (no calibration/metadata)", parseable="needs ffmpeg", value="medium"),
    "2013_04_16_txt.zip": dict(
        investigation="PSI-26 BASS (session 2013-04-16)", category="crew-photo EXIF text (images absent)",
        measurements="none", parseable="yes (text)", value="low"),
}


def sniff(head, name):
    ext = os.path.splitext(name)[1].lower()
    if ext in EXT_FMT:
        return EXT_FMT[ext]
    for m, fmt in MAGIC:
        if head.startswith(m):
            return fmt
    return "unknown"


def psi_index(psi_dir):
    """Map file_name -> list of (accession, file_size, remote_path) across all saved PSI records."""
    idx = collections.defaultdict(list)
    for p in glob.glob(os.path.join(psi_dir, "PSI-*.json")):
        rec = json.load(open(p))
        for key in ("added", "modified", "experimentalTable", "files"):
            for f in rec.get(key) or []:
                if isinstance(f, dict) and f.get("file_name"):
                    idx[f["file_name"]].append((rec.get("accession"), f.get("file_size"), f.get("remote_path")))
    return idx


def match_psi(idx, name, size):
    """Match by file name (PSI prefixes '<PSI-NN>_<Folder>_' on download) and fall back to exact byte size."""
    hits = []
    for fname, recs in idx.items():
        if fname == name or fname.endswith("_" + name) or fname.endswith(name):
            for acc, fsize, rpath in recs:
                hits.append({"accession": acc, "psi_file_name": fname, "psi_size": fsize, "match": "name",
                             "size_match": fsize == size, "remote_path": rpath})
    if not hits:
        for fname, recs in idx.items():
            for acc, fsize, rpath in recs:
                if fsize == size:
                    hits.append({"accession": acc, "psi_file_name": fname, "psi_size": fsize, "match": "size-only",
                                 "size_match": True, "remote_path": rpath})
    return hits


def main():
    data_dir, psi_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    idx = psi_index(psi_dir)
    rows, summaries = [], []
    for name in sorted(os.listdir(data_dir)):
        path = os.path.join(data_dir, name)
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(16)
        meta = CLASSIFY.get(name, dict(investigation="UNCLASSIFIED", category="", measurements="", parseable="", value=""))
        summary = {"file": name, "bytes": size, "format": sniff(head, name), **meta,
                   "psi_match": match_psi(idx, name, size), "members": 0, "member_formats": {}}
        rows.append({"level": "file", "container": "", "path": name, "bytes": size, "format": summary["format"], **meta})
        if zipfile.is_zipfile(path):
            try:
                z = zipfile.ZipFile(path)
                bad = z.testzip()  # CRC check of every member (reads archive; does not modify it)
                summary["zip_crc_ok"] = bad is None
                fmts = collections.Counter()
                for zi in z.infolist():
                    if zi.is_dir():
                        continue
                    with z.open(zi) as m:
                        mhead = m.read(16)
                    fmt = sniff(mhead, zi.filename)
                    fmts[fmt] += 1
                    rows.append({"level": "member", "container": name, "path": zi.filename, "bytes": zi.file_size,
                                 "format": fmt, **meta})
                summary["members"] = sum(fmts.values())
                summary["member_formats"] = dict(fmts)
            except Exception as e:  # never silently ignore unreadable archives
                summary["error"] = repr(e)
        summaries.append(summary)
    with open(out + ".csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    with open(out + "_files.json", "w") as f:
        json.dump(summaries, f, indent=2)
    n_members = sum(s["members"] for s in summaries)
    print(f"{len(summaries)} files, {n_members} archive members -> {out}.csv / {out}_files.json")
    for s in summaries:
        pm = "; ".join(f"{h['accession']} via {h['match']} size_match={h['size_match']}" for h in s["psi_match"]) \
            or "NOT in any PSI file listing"
        print(f"  {s['file'][:60]:60s} {s['members']:4d} members  crc_ok={s.get('zip_crc_ok','n/a')}  {pm}")


if __name__ == "__main__":
    main()
