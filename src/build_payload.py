"""
Build payload.json for Personal Best from the WCA results export in ../.cache/.

    python fetch.py && python build_payload.py && python inject.py

Needs pandas (and pyarrow is not required). Everything is 3x3x3 Cube ("333") unless noted.
Times are WCA centiseconds; the payload carries seconds rounded to 0.01.

Definitions that matter (see REBUILD.md for why):
  * A person's "first competition" is the first competition, by start date, in which they
    have a 3x3 result. Their "first average" is the average from the earliest round of that
    competition (the lowest round rank), not the best of that day's rounds.
  * DNF averages (-1) are kept and sort as slower than every time, so they pull quantiles
    the right way instead of vanishing. Rounds with no average (0, best-of-N formats) are
    skipped when looking for a first average.
  * "Came back" means any WCA competition, in any event, within 730 days of the first one.
    Only first competitions at least 730 days before the export date are scored.
"""
import json, os, sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
C = os.path.join(HERE, "..", ".cache")
INF = 10**9  # a DNF average, sorted after every real time


def tsv(name, **kw):
    return pd.read_csv(os.path.join(C, "WCA_export_%s.tsv" % name), sep="\t", quoting=3,
                       keep_default_na=False, na_values=["NULL"], **kw)


meta = json.load(open(os.path.join(C, "metadata.json"), encoding="utf-8"))
export_date = pd.Timestamp(meta["export_date"][:10])

comp = tsv("competitions", usecols=["id", "year", "month", "day", "cancelled"])
comp["date"] = pd.to_datetime(dict(year=comp.year, month=comp.month, day=comp.day))
comp = comp.rename(columns={"id": "competition_id"})[["competition_id", "date"]]

rt = tsv("round_types", dtype={"id": str}).rename(columns={"id": "round_type_id", "rank": "rrank"})
rt = rt[["round_type_id", "rrank", "final"]]

res = tsv("results", usecols=["id", "best", "average", "competition_id", "round_type_id",
                              "event_id", "person_id", "format_id", "person_country_id",
                              "regional_single_record", "regional_average_record"],
          dtype={"round_type_id": str, "format_id": str})
res = res.merge(comp, on="competition_id")
print("results", len(res))

# ---------------------------------------------------------------- every event: comp dates
pcomp_all = res[["person_id", "competition_id", "date"]].drop_duplicates()
ncomp_all = pcomp_all.groupby("person_id").size()

r3 = res[res.event_id == "333"].merge(rt, on="round_type_id").copy()
r3["year"] = r3.date.dt.year
r3["avgk"] = r3.average.where(r3.average != -1, INF)  # DNF sorts last; 0 = no average, -2 = DNS
print("3x3 results", len(r3))

# ---------------------------------------------------------------- first competition, first average
r3 = r3.sort_values(["person_id", "date", "competition_id", "rrank"])
firstcomp = r3.groupby("person_id", sort=False).head(1)[["person_id", "competition_id", "date", "person_country_id"]]
firstcomp = firstcomp.rename(columns={"competition_id": "fc", "date": "fdate", "person_country_id": "country"})
f = r3.merge(firstcomp, on="person_id")
f = f[(f.competition_id == f.fc) & (f.avgk > 0)]
firstavg = f.groupby("person_id", sort=False).head(1)[["person_id", "avgk"]].rename(columns={"avgk": "first"})
newc = firstcomp.merge(firstavg, on="person_id", how="left")
newc["fyear"] = newc.fdate.dt.year
print("people with a 3x3 result", len(newc), " with a first average", newc["first"].notna().sum())


def q(vals, ps):
    """quantiles with DNF (INF) kept in the ranking; returns seconds or None for a DNF"""
    v = np.sort(np.asarray(vals, dtype=float))
    out = []
    for p in ps:
        x = v[min(len(v) - 1, int(np.floor(p * (len(v) - 1) + 0.5)))]
        out.append(None if x >= INF else round(x / 100, 2))
    return out


P5 = [.1, .25, .5, .75, .9]

# ---------------------------------------------------------------- 1. the record and the rookie
years = list(range(2004, int(r3.year.max()) + 1))
nv = newc.dropna(subset=["first"])
rookie = []
for y in years:
    s = nv[nv.fyear == y]["first"]
    rookie.append([y, len(s)] + q(s, P5) + [round(float((s >= INF).mean()), 4)])

# the field: each active person's best average that year (DNF-only years sort last)
py = r3[r3.avgk > 0].groupby(["year", "person_id"]).avgk.min().reset_index()
field = []
for y in years:
    s = py[py.year == y].avgk.values
    top = np.sort(s)[:100]
    field.append([y, len(s)] + q(s, [.5]) + [round(float(np.median(top)) / 100, 2)])

pnames = tsv("persons", usecols=["name", "wca_id", "sub_id"])
pnames = pnames[pnames.sub_id == 1].set_index("wca_id").name


def recs(col, val):
    w = r3[r3[col] == "WR"].sort_values(["date", "rrank"])
    out = []
    for _, r in w.iterrows():
        out.append([r.date.strftime("%Y-%m-%d"), round(r[val] / 100, 2), pnames.get(r.person_id, r.person_id),
                    r.person_country_id])
    # keep only strict improvements; a tie with the standing record is not a new one
    keep, best = [], 1e9
    for o in out:
        if o[1] < best:
            keep.append(o); best = o[1]
    return keep


wr_avg = recs("regional_average_record", "average")
wr_single = recs("regional_single_record", "best")

# ---------------------------------------------------------------- 2. who comes back
cut = export_date - pd.Timedelta(days=730)
pc = pcomp_all.merge(newc[["person_id", "fdate"]], on="person_id")
later = pc[(pc.date > pc.fdate) & (pc.date <= pc.fdate + pd.Timedelta(days=730))].person_id.unique()
newc["back"] = newc.person_id.isin(later)
elig = newc[newc.fdate <= cut]
ret_year = [[int(y), len(g), round(float(g.back.mean()), 4)] for y, g in elig.groupby("fyear") if y >= 2004]
bands = [0, 15, 20, 25, 30, 40, 60, 90, 180, INF / 100 + 1]
bl = ["under 15", "15-20", "20-25", "25-30", "30-40", "40-60", "60-90", "90-180", "over 3 min"]
e2 = elig.assign(fs=elig["first"] / 100)
e2["band"] = pd.cut(e2.fs, bands, labels=bl, right=False)
ret_band = [[b, int(len(g)), round(float(g.back.mean()), 4)] for b, g in e2.dropna(subset=["band"]).groupby("band", observed=False)]
dnfg = elig[elig["first"] >= INF]
ret_band.append(["DNF", int(len(dnfg)), round(float(dnfg.back.mean()), 4)])
ret_all = round(float(elig.back.mean()), 4)

# ---------------------------------------------------------------- 3. survivors were already fast
cut3 = export_date - pd.Timedelta(days=3 * 365)
car = newc[(newc.fdate <= cut3)].dropna(subset=["first"]).copy()
car["n"] = car.person_id.map(ncomp_all)
cb = [(1, 1, "1"), (2, 2, "2"), (3, 4, "3-4"), (5, 9, "5-9"), (10, 19, "10-19"), (20, 49, "20-49"), (50, 10**6, "50+")]
career = []
for lo, hi, lab in cb:
    s = car[(car.n >= lo) & (car.n <= hi)]["first"]
    career.append([lab, len(s)] + q(s, [.25, .5, .75]))

# learning curves: PB-to-date after the k-th 3x3 competition, for people with at least N of them
pcs = r3[r3.avgk > 0].groupby(["person_id", "competition_id"], sort=False).agg(
    date=("date", "first"), a=("avgk", "min")).reset_index().sort_values(["person_id", "date"])
pcs["k"] = pcs.groupby("person_id").cumcount() + 1
pcs["pb"] = pcs.groupby("person_id").a.cummin()
n3 = pcs.groupby("person_id").k.max()
curves = {}
for N in (2, 5, 10, 20, 40):
    ids = n3[n3 >= N].index
    s = pcs[pcs.person_id.isin(ids) & (pcs.k <= N)]
    curves[str(N)] = {"n": int(len(ids)), "pb": [q(g.pb.values, [.5])[0] for _, g in s.groupby("k")]}

# ---------------------------------------------------------------- 4. where you stand
pbs = pcs[pcs.pb < INF].groupby("person_id").pb.min().values
qs = np.linspace(0, 1, 401)
stand = {"pb": q(pbs, qs), "first": q(nv["first"].values, qs), "npb": int(len(pbs)), "nfirst": int(len(nv))}

# reach: of newcomers slower than T at their first competition (first comp >= 3 years ago),
# the share whose PB ever got to T or better, and how many 3x3 competitions it took
el4 = newc[newc.fdate <= cut3].dropna(subset=["first"])
pcs4 = pcs[pcs.person_id.isin(el4.person_id)]
firstk = el4.set_index("person_id")["first"]
grid = [round(x, 1) for x in np.arange(6, 90.01, 0.5)]
reach = []
for T in grid:
    c = int(T * 100)
    base = firstk[firstk > c].index
    hit = pcs4[(pcs4.pb <= c) & pcs4.person_id.isin(base)].groupby("person_id").k.min()
    reach.append([T, int(len(base)), round(len(hit) / max(1, len(base)), 4),
                  int(hit.median()) if len(hit) else None,
                  int(hit.quantile(.25)) if len(hit) else None, int(hit.quantile(.75)) if len(hit) else None])

# ---------------------------------------------------------------- 5. countries
cn = tsv("countries", usecols=["id", "name", "continent_id", "iso2"]).set_index("id")
cty = []
for c, g in nv.groupby("country"):
    if len(g) >= 500:
        ge = newc[(newc.country == c) & (newc.fdate <= cut)]
        cty.append([cn.name.get(c, c), cn.continent_id.get(c, ""), len(g)] + q(g["first"], [.25, .5, .75])
                   + [round(float(ge.back.mean()), 4) if len(ge) else None])
cty.sort(key=lambda r: r[4])

# ---------------------------------------------------------------- 6. five attempts
att = pd.read_csv(os.path.join(C, "WCA_export_result_attempts.tsv"), sep="\t",
                  dtype={"value": np.int32, "attempt_number": np.int8, "result_id": np.int64})
plain = r3[(r3.format_id == "a") & r3.round_type_id.isin(["0", "1", "2", "3", "b", "c"])]
a = att[att.result_id.isin(plain.id.values)]
v = a.pivot(index="result_id", columns="attempt_number", values="value")
v = v[v.notna().all(axis=1) & (v != 0).all(axis=1) & (v != -2).all(axis=1)]
dnf = [round(float((v[k] == -1).mean()), 5) for k in range(1, 6)]
ok = v[(v > 0).all(axis=1)]
rel = ok.div(ok.mean(axis=1), axis=0)
attempts = {
    "rounds": int(len(v)), "clean": int(len(ok)),
    "dnf": dnf,
    "rel_median": [round(float(rel[k].median()), 4) for k in range(1, 6)],
    "slowest": [round(float(x), 4) for x in ok.idxmax(axis=1).value_counts(normalize=True).sort_index()],
    "fastest": [round(float(x), 4) for x in ok.idxmin(axis=1).value_counts(normalize=True).sort_index()],
}
# DNF on the fifth solve, by how the first four went: is the last attempt a gamble?
four = v[(v[[1, 2, 3, 4]] > 0).all(axis=1)]
attempts["dnf5_after_clean4"] = round(float((four[5] == -1).mean()), 5)
attempts["dnf4_after_clean3"] = round(float((v[(v[[1, 2, 3]] > 0).all(axis=1)][4] == -1).mean()), 5)
# ...split by how fast those clean solves were. A time-limit artefact would hit slow solvers;
# a gamble would show up among fast ones.
three = v[(v[[1, 2, 3]] > 0).all(axis=1)]
sb = [0, 10, 15, 20, 30, 60, 1e9]
sl = ["under 10", "10-15", "15-20", "20-30", "30-60", "over 60"]
b3 = pd.cut(three[[1, 2, 3]].mean(axis=1) / 100, sb, labels=sl)
b4 = pd.cut(four[[1, 2, 3, 4]].mean(axis=1) / 100, sb, labels=sl)
attempts["gamble"] = [[lab, int((b4 == lab).sum()),
                       round(float((three[4][b3 == lab] == -1).mean()), 5),
                       round(float((four[5][b4 == lab] == -1).mean()), 5)] for lab in sl]

n_attempts = int(((att.value != 0) & (att.value != -2) & att.result_id.isin(r3.id.values)).sum())

payload = {
    "export": meta["export_date"][:10],
    "facts": {"people": int(len(newc)), "attempts333": n_attempts, "competitions": int(r3.competition_id.nunique()),
              "countries": int(newc.country.nunique()), "returnAll": ret_all},
    "rookie": rookie, "field": field, "wrAvg": wr_avg, "wrSingle": wr_single,
    "retYear": ret_year, "retBand": ret_band,
    "career": career, "curves": curves,
    "stand": stand, "reach": reach,
    "countries": cty, "attempts": attempts,
}
out = os.path.join(HERE, "payload.json")
with open(out, "w", encoding="utf-8", newline="\n") as fh:
    json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
print("wrote", out, os.path.getsize(out) // 1024, "KB")
sys.stdout.reconfigure(encoding="utf-8")
print(json.dumps({k: payload[k] for k in ("facts", "career", "retBand", "attempts")}, ensure_ascii=False, indent=0)[:3000])
for r in rookie: print(r)
for r in field[-5:]: print(r)
print(wr_avg[-3:], wr_single[-3:])
