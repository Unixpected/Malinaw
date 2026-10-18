"""Check DPWH projects against rules.json and write docs/data.json.

Only fields that exist in the data are used. A flag is a reason to look closer, not evidence
of wrongdoing.
"""
import json, re, tarfile, datetime
import numpy as np
import pandas as pd

cfg = json.load(open("config.json"))
rules = json.load(open("rules.json"))

rows = []
with tarfile.open(cfg["archive_path"]) as t:
    for m in t.getmembers():
        if m.isfile() and m.name.endswith(".json") and "dump-page" in m.name:
            rows += json.load(t.extractfile(m))["data"]["data"]
raw = pd.DataFrame(rows)

df = raw.drop_duplicates("contractId").reset_index(drop=True)
df["province"] = df["location"].map(lambda x: (x or {}).get("province"))
df["region"] = df["location"].map(lambda x: (x or {}).get("region"))
df["budget_m"] = pd.to_numeric(df["budget"], errors="coerce") / 1e6
df["progress"] = pd.to_numeric(df["progress"], errors="coerce")
df["report_count"] = pd.to_numeric(df["reportCount"], errors="coerce").fillna(0)
df["has_coords"] = (df["latitude"].notna() & df["longitude"].notna()).astype(int)
df["year"] = pd.to_numeric(df["infraYear"], errors="coerce")

df["dup_desc_count"] = df.groupby(["province", "description"])["contractId"].transform("count")

ex = df[["contractId", "province", "year", "budget_m", "contractor"]].copy()
ex["contractor"] = ex["contractor"].fillna("").str.split(" / ")
ex = ex.explode("contractor")
ex["contractor"] = ex["contractor"].str.replace(r"\s*\(\d+\)\s*$", "", regex=True).str.strip()
ex = ex[(ex["contractor"] != "") & ex["budget_m"].notna()]
ex["w"] = ex["budget_m"] / ex.groupby("contractId")["contractor"].transform("count")
tot = ex.groupby(["province", "year"])["w"].transform("sum")
mine = ex.groupby(["province", "year", "contractor"])["w"].transform("sum")
ex["share"] = mine / tot * 100
share = ex.groupby("contractId")["share"].max()
df["contractor_share"] = df["contractId"].map(share)
g = df.groupby(["province", "year"])["budget_m"]
df["office_year_total_m"] = g.transform("sum")
df["office_year_n"] = g.transform("count")

score = np.zeros(len(df))
hits, flagmap, rule_counts = {}, {}, []
for rule in rules:
    hit = df.eval(rule["expr"], engine="python").fillna(False).astype(bool).to_numpy()
    hits[rule["name"]] = hit
    score += hit * rule["weight"]
    for i in np.flatnonzero(hit):
        flagmap.setdefault(int(i), []).append(rule["name"])
    rule_counts.append({"name": rule["name"], "expr": rule["expr"], "weight": rule["weight"],
                        "verify": rule["verify"], "count": int(hit.sum())})
df["score"] = np.minimum(score, 100)
df["flagged"] = df["score"] > 0
df["_sv"] = df["score"] * df["budget_m"].fillna(0)
df["_fv"] = np.where(df["flagged"], df["budget_m"].fillna(0), 0.0)

ent = df.groupby("province").agg(n=("contractId", "count"), value_m=("budget_m", "sum"),
      sv=("_sv", "sum"), flagged=("flagged", "sum"), flagged_value_m=("_fv", "sum"))
ent["score"] = ent["sv"] / ent["value_m"]
ent = ent[(ent["n"] >= cfg["min_office_projects"]) & (ent["value_m"] > 0)].sort_values("score", ascending=False)
levels = {"entity_high": float(np.percentile(ent["score"], cfg["entity_high_percentile"])),
          "entity_medium": float(np.percentile(ent["score"], cfg["entity_medium_percentile"])),
          "item_high": cfg["item_high"], "item_medium": cfg["item_medium"]}
offices = []
for name, r in ent.head(25).iterrows():
    m = (df["province"] == name).to_numpy()
    reasons = sorted([[k, int((v & m).sum())] for k, v in hits.items()], key=lambda x: -x[1])
    offices.append({"name": name, "score": round(float(r["score"]), 1), "n": int(r["n"]),
        "flagged": int(r["flagged"]), "value_m": round(float(r["value_m"]), 1),
        "flagged_value_m": round(float(r["flagged_value_m"]), 1),
        "reasons": [x for x in reasons if x[1] > 0][:3]})

top = df[df["flagged"]].sort_values(["score", "budget_m"], ascending=False).head(1000)
projects = [{"id": r.contractId, "desc": str(r.description)[:160], "office": r.province, "region": r.region,
    "category": r.category, "status": r.status, "budget_m": round(float(r.budget_m), 2),
    "progress": None if pd.isna(r.progress) else float(r.progress),
    "year": None if pd.isna(r.year) else int(r.year), "reports": int(r.report_count),
    "score": round(float(r.score), 1), "flags": flagmap[int(i)]} for i, r in top.iterrows()]

out = {
    "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
    "totals": {"projects": int(len(df)), "budget_bn": round(float(df["budget_m"].sum()) / 1e3, 1),
               "flagged": int(df["flagged"].sum()),
               "flood_projects": int(df["category"].fillna("").str.contains("Flood").sum())},
    "levels": levels, "rules": rule_counts, "offices": offices, "projects": projects,
    "gaps": {"repeated_ids": int(len(raw) - len(df)),
             "amount_paid_zero": int((pd.to_numeric(df["amountPaid"], errors="coerce").fillna(0) == 0).sum()),
             "budget_missing": int((df["budget_m"].fillna(0) <= 0).sum()),
             "no_coords": int((df["has_coords"] == 0).sum()),
             "no_completion_date": int(df["completionDate"].isna().sum()),
             "negative_progress": int((df["progress"] < 0).sum())},
    "sources": json.load(open("sources.json")),
}
json.dump(out, open("docs/data.json", "w"), ensure_ascii=False)
print(out["totals"], out["gaps"])
print(rule_counts and [(r["name"], r["count"]) for r in rule_counts])
print(levels)
for o in offices[:5]: print(o["name"], o["score"], o["n"], o["reasons"])
