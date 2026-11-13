#!/usr/bin/env python3
"""Harvest NASA PSI combustion-investigation metadata (JSON records) via the public PSI API.

Usage:  python3 -I scripts/harvest_psi.py <out_dir>
Writes:
  <out_dir>/search_all.json          raw search listing (all PSI investigations)
  <out_dir>/PSI-NN.json              raw record per Combustion Science investigation
  <out_dir>/../sources.csv           manifest rows appended (url, path, sha256, fetched_utc)
Raw responses are saved verbatim; nothing is transformed here.
"""
import csv, datetime, gzip, hashlib, json, os, sys, time, urllib.request

BASE = "https://psi.nasa.gov/geode-py/ws/repo"
UA = "firewise-research/0.1 (NASA Space Apps)"


def fetch(url, retries=3, timeout=900):
    last = None
    for i in range(retries):
        try:
            # gzip matters: large records (e.g. PSI-23, 8 MB) time out uncompressed but arrive in minutes gzipped
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json",
                                                      "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
                return gzip.decompress(body) if r.headers.get("Content-Encoding") == "gzip" else body
        except Exception as e:  # network flakiness: retry with backoff
            last = e
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"failed {url}: {last}")


def save(out_dir, name, data, url, manifest):
    path = os.path.join(out_dir, name)
    with open(path, "wb") as f:
        f.write(data)
    manifest.append({
        "source_id": name.rsplit(".", 1)[0],
        "url": url,
        "path": os.path.relpath(path, os.path.dirname(os.path.dirname(out_dir))),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "fetched_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    })


def write_manifest(out_dir, rows):
    if not rows:
        return
    man_path = os.path.join(os.path.dirname(out_dir), "sources.csv")
    new = not os.path.exists(man_path)
    with open(man_path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        if new:
            w.writeheader()
        w.writerows(rows)


def main():
    out_dir = os.path.abspath(sys.argv[1])
    os.makedirs(out_dir, exist_ok=True)
    url = f"{BASE}/search?source=psi&type=investigation&size=500"
    search_path = os.path.join(out_dir, "search_all.json")
    if os.path.exists(search_path):  # resume: reuse saved listing
        raw = open(search_path, "rb").read()
    else:
        manifest = []
        raw = fetch(url)
        save(out_dir, "search_all.json", raw, url, manifest)
        write_manifest(out_dir, manifest)
    hits = json.loads(raw)["hits"]["hits"]
    combustion = sorted(
        (h["_source"]["Accession"] for h in hits if h["_source"].get("Research Area", "").strip() == "Combustion Science"),
        key=lambda a: int(a.split("-")[1]),
    )
    # Records listing thousands of files (ACME Flame Design, s-Flame, CFI-G, CFI) are slow to serve: fetch last.
    LARGE = ("PSI-10", "PSI-23", "PSI-159", "PSI-39")
    combustion = [a for a in combustion if a not in LARGE] + [a for a in LARGE if a in combustion]
    print(f"{len(hits)} investigations, {len(combustion)} Combustion Science: {combustion}")
    failed = []
    for acc in combustion:
        if os.path.exists(os.path.join(out_dir, f"{acc}.json")):
            print(f"  {acc}: already saved, skipping", flush=True)
            continue
        u = f"{BASE}/investigations/{acc}"
        try:
            t0 = time.time()
            data = fetch(u)
            json.loads(data)  # validate JSON before saving
        except Exception as e:
            failed.append(acc)
            print(f"  {acc}: FAILED ({e})", flush=True)
            continue
        manifest = []
        save(out_dir, f"{acc}.json", data, u, manifest)
        write_manifest(out_dir, manifest)
        print(f"  {acc}: {len(data):,} bytes in {time.time()-t0:.0f}s", flush=True)
    print("FAILED:", failed if failed else "none")


if __name__ == "__main__":
    main()
