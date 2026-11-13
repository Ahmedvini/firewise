#!/usr/bin/env python3
"""Download selected PSI files (public, no login) listed in derived/psi_files.csv.

Usage:
  python3 -I scripts/fetch_psi_files.py <psi_files.csv> <dest_root> [--folders "Experimental table,Reports"]
        [--accessions PSI-20,PSI-159] [--cap-mb 500] [--workers 4] [--dry-run]
        [--exclude-exts .ts,.zip,.mp4]   (e.g. "telemetry only": skip video/image archives)
        [--priority PSI-159,PSI-10]      (download these investigations first)
Files land in <dest_root>/<PSI-NN>/<folder>/<file_name>. Existing files with the expected size are skipped
(resumable). Every download is appended to <dest_root>/../sources.csv with sha256. Files larger than
--cap-mb are never fetched.
Download endpoint: GET https://psi.nasa.gov/geode-py/ws/studies/<PSI-NN>/download?file=<file_name>
(302 -> pre-signed S3 URL).
"""
import concurrent.futures as cf, csv, datetime, hashlib, os, sys, threading, time, urllib.parse, urllib.request

BASE = "https://psi.nasa.gov/geode-py/ws/studies"
UA = "firewise-research/0.1 (NASA Space Apps)"
lock = threading.Lock()


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def safe_name(s):
    return "".join(c if c not in '/\\\0' else "_" for c in s)


def download(row, dest_root, manifest_path):
    acc, folder, fname, size = row["accession"], row["folder"], row["file_name"], int(row["bytes"])
    out_dir = os.path.join(dest_root, acc, safe_name(folder))
    out = os.path.join(out_dir, safe_name(fname))
    if os.path.exists(out) and os.path.getsize(out) == size:
        return ("skip", fname, size)
    os.makedirs(out_dir, exist_ok=True)
    url = f"{BASE}/{acc}/download?file={urllib.parse.quote(fname)}"
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            h = hashlib.sha256()
            tmp = out + ".part"
            with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
                for chunk in iter(lambda: r.read(1 << 20), b""):
                    f.write(chunk)
                    h.update(chunk)
            got = os.path.getsize(tmp)
            if size and got != size:
                raise IOError(f"size mismatch: expected {size}, got {got}")
            os.replace(tmp, out)
            with lock, open(manifest_path, "a", newline="") as mf:
                csv.writer(mf).writerow([f"{acc}:{fname}", url, os.path.relpath(out, os.path.dirname(dest_root.rstrip('/')) + "/.."),
                                         got, h.hexdigest(),
                                         datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")])
            return ("ok", fname, got)
        except Exception as e:
            last = e
            time.sleep(5 * (attempt + 1))
    return ("FAIL", fname, repr(last))


def main():
    files_csv, dest_root = sys.argv[1], os.path.abspath(sys.argv[2])
    folders = set(filter(None, (arg("--folders", "") or "").split(","))) or None
    accs = set(filter(None, (arg("--accessions", "") or "").split(","))) or None
    cap = float(arg("--cap-mb", "500")) * 1024 * 1024
    excl = {e.strip().lower() for e in (arg("--exclude-exts", "") or "").split(",") if e.strip()}
    workers = int(arg("--workers", "4"))
    rows = [r for r in csv.DictReader(open(files_csv))
            if (folders is None or r["folder"] in folders) and (accs is None or r["accession"] in accs)
            and r["ext"].lower() not in excl]
    skipped_big = [r for r in rows if int(r["bytes"]) > cap]
    rows = [r for r in rows if int(r["bytes"]) <= cap and r.get("restricted") in ("False", "", None)]
    prio = [a for a in (arg("--priority", "") or "").split(",") if a]
    # priority investigations first, then smallest files first (metadata/test-parameter files arrive early)
    rows.sort(key=lambda r: (prio.index(r["accession"]) if r["accession"] in prio else len(prio), int(r["bytes"])))
    total = sum(int(r["bytes"]) for r in rows)
    print(f"selected {len(rows)} files, {total/1e9:.3f} GB; skipped {len(skipped_big)} files over cap "
          f"({sum(int(r['bytes']) for r in skipped_big)/1e9:.1f} GB)", flush=True)
    if "--dry-run" in sys.argv:
        return
    manifest_path = os.path.join(os.path.dirname(dest_root), "sources.csv")
    done = 0
    with cf.ThreadPoolExecutor(workers) as ex:
        futs = [ex.submit(download, r, dest_root, manifest_path) for r in rows]
        for fu in cf.as_completed(futs):
            status, fname, info = fu.result()
            done += 1
            if status != "skip":
                print(f"[{done}/{len(rows)}] {status} {fname} {info}", flush=True)
    print("done", flush=True)


if __name__ == "__main__":
    main()
