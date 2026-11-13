#!/usr/bin/env python3
"""Assemble one evidence record per PSI combustion investigation (the FIREWISE seed data).

Usage: python3 -I scripts/build_records.py <NasaSA root>
Reads : sources/psi_api/*.json, derived/runs.csv, derived/runs_flags.csv, derived/psi_summary.csv,
        derived/inventory_local_files.json, derived/curated_facts.json
Writes: derived/investigations/PSI-NN.json and derived/investigations.json
Text fields from PSI are copied verbatim and tagged "PSI-rec"; nothing is paraphrased here.
"""
import collections, csv, glob, json, os, re, sys

ROOT = os.path.abspath(sys.argv[1])
P = lambda *a: os.path.join(ROOT, *a)


def clean(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def rng(rs, lo, hi, st):
    vals = [float(r[k]) for r in rs for k in (lo, hi) if r[k] not in ("", None)]
    return {"min": round(min(vals), 4) if vals else None, "max": round(max(vals), 4) if vals else None,
            "n_documented": sum(1 for r in rs if r[lo] not in ("", None)), "n_runs": len(rs),
            "statuses": dict(collections.Counter(r[st] for r in rs))}


def main():
    search = json.load(open(P("sources/psi_api/search_all.json")))["hits"]["hits"]
    related = {h["_source"]["Accession"]: [x for x in re.split(r"\s+", h["_source"].get("Related Investigations", "") or "") if x]
               for h in search}
    runs = list(csv.DictReader(open(P("derived/runs.csv"))))
    flags = list(csv.DictReader(open(P("derived/runs_flags.csv"))))
    summ = {r["accession"]: r for r in csv.DictReader(open(P("derived/psi_summary.csv")))}
    local = json.load(open(P("derived/inventory_local_files.json")))
    facts = json.load(open(P("derived/curated_facts.json")))
    os.makedirs(P("derived/investigations"), exist_ok=True)
    allrec = []
    for path in sorted(glob.glob(P("sources/psi_api/PSI-*.json")), key=lambda p: int(re.findall(r"\d+", os.path.basename(p))[0])):
        d = json.load(open(path))
        acc = d["accession"]
        rs = [r for r in runs if r["investigation"] == acc]
        fl = [f for f in flags if f["investigation"] == acc]
        s = summ.get(acc, {})
        rec = {
            "id": acc, "acronym": d.get("investigationAcronym", ""), "title": clean(d.get("title")),
            "doi": d.get("doi", ""), "doi_url": f"https://doi.org/{d['doi']}" if d.get("doi") else "",
            "psi_url": f"https://psi.nasa.gov/physci/repo/data/investigations/{acc}",
            "api_url": f"https://psi.nasa.gov/geode-py/ws/repo/investigations/{acc}",
            "license": d.get("licenseIdentifier", ""), "project_type": d.get("projectType", ""),
            "research_area": d.get("researchArea", ""), "sub_research_area": clean(d.get("subResearchArea")),
            "platform": clean(d.get("flightProgram")), "hardware": clean(d.get("experimentHardware")),
            "hardware_links": clean(d.get("experimentHardwareLink")), "managing_center": d.get("managingNasaCenter", ""),
            "dates": {"start": d.get("investigationStartDate", ""), "end": d.get("investigationEndDate", ""),
                      "psi_release": d.get("releaseDate", ""), "psi_modified": d.get("modifiedDate", "")},
            "text": {k: {"value": clean(d.get(src)), "tag": "PSI-rec", "source": f"{os.path.relpath(path, ROOT)}#{src}"}
                     for k, src in (("objective", "objective"), ("hypothesis", "hypothesis"), ("approach", "approach"),
                                    ("research_impacts", "researchImpacts"), ("proposal_title", "proposalTitle"))},
            "publications": [{"title": clean(p.get("title")), "authors": clean(p.get("authorList")),
                              "doi": clean(p.get("doi")), "status": (p.get("status") or {}).get("annotationValue", "")}
                             for p in d.get("publications") or []],
            "related_investigations": related.get(acc, []),
            "data_products": {
                "n_files_listed": int(s.get("n_files_listed") or 0), "listed_GB": float(s.get("listed_GB") or 0),
                "totalFileSize_GB": float(s.get("totalFileSize_GB") or 0),
                "listing_complete": s.get("listing_complete") == "True", "folders": s.get("folders", ""),
                "experimental_tables": [t.get("file_name") for t in d.get("experimentalTable") or []],
            },
            "runs_summary": {
                "n_runs": len(rs),
                "fuel_or_material": dict(collections.Counter(r["fuel_or_material"] for r in rs).most_common(15)),
                "fuel_class": dict(collections.Counter(r["fuel_class"] for r in rs)),
                "geometry_examples": list(dict.fromkeys(r["geometry"] for r in rs if r["geometry"]))[:8],
                "diluents": dict(collections.Counter(r["diluent"] for r in rs if r["diluent"])),
                "gravity_regime": dict(collections.Counter(r["gravity_regime"] for r in rs)),
                "platform": sorted({r["platform"] for r in rs}),
                "granularity": dict(collections.Counter(r["row_granularity"] for r in rs)),
                "duplicates": sum(1 for r in rs if r["duplicate_of"]),
                "o2_pct": rng(rs, "o2_min_pct", "o2_max_pct", "o2_status"),
                "pressure_atm": rng(rs, "p_min_atm", "p_max_atm", "p_status"),
                "flow_cm_s": rng(rs, "flow_min_cm_s", "flow_max_cm_s", "flow_status"),
            },
            "quality_flags": {"n_table_flags": len(fl),
                              "by_severity": dict(collections.Counter(f["severity"] for f in fl)),
                              "by_code": dict(collections.Counter(f["code"] for f in fl).most_common(15))},
            "local_files": [{"file": x["file"], "category": x.get("category"), "match": (x.get("psi_match") or [{}])[0].get("match")}
                            for x in local if re.search(rf"\b{acc}\b", json.dumps(x.get("psi_match")) + " " + str(x.get("investigation", "")))],
            "curated_facts": [f for f in facts if acc in f.get("investigations", [])],
        }
        if not rec["data_products"]["listing_complete"] and rec["data_products"]["totalFileSize_GB"] > 1:
            rec["quality_flags"]["record_level"] = [f"totalFileSize {rec['data_products']['totalFileSize_GB']:.0f} GB but only "
                                                    f"{rec['data_products']['n_files_listed']} files listed"]
        json.dump(rec, open(P(f"derived/investigations/{acc}.json"), "w"), indent=1, ensure_ascii=False)
        allrec.append(rec)
    json.dump(allrec, open(P("derived/investigations.json"), "w"), indent=1, ensure_ascii=False)
    print(f"{len(allrec)} investigation records -> derived/investigations/ and derived/investigations.json")
    for r in allrec:
        print(f"  {r['id']:8s} {r['acronym'][:20]:20s} runs={r['runs_summary']['n_runs']:4d} pubs={len(r['publications']):3d} "
              f"facts={len(r['curated_facts'])} local={len(r['local_files'])} related={r['related_investigations']}")


if __name__ == "__main__":
    main()
