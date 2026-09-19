# Rebuilding Personal Best

## 1. What it is

A single page about speedcubing, built from the World Cube Association's public results
export. It sets the world-record 3×3 average (14.52 s at the end of 2004 → 3.51 s in June
2026) against the first average each year's newcomers set in their first round with a judge.
That median has barely moved (38.8 s in 2005 → 34.0 s in 2026). The rest of the page explains
the gap between the two lines:

* only 48% of first-timers compete again within two years, and return rates fall steeply with
  first-day speed;
* people who went on to many competitions were already much faster on day one, so the field
  gets faster partly through practice and partly through who stays (a selection effect);
* the reader can type their own average and see where it falls;
* a country dot plot of newcomer medians, from Vietnam (20.3 s) to Mongolia (56.5 s);
* a coda on the five solves of a round: the first solve is most often the slowest, the fifth
  is the one most likely to be a DNF, and that jump is concentrated among the fastest solvers.

## 2. Data

One source: the WCA results export, TSV flavour.

* Discovery endpoint: `https://www.worldcubeassociation.org/api/v0/export/public` (JSON with
  `export_date`, `tsv_url`, `sql_url`). TSV zip: `https://www.worldcubeassociation.org/export/results/v2/tsv`
  (~377 MB zipped, ~1.6 GB unpacked). The export is regenerated daily. This build used the
  export dated **2026-09-18 00:00:16 UTC**, format **v2.0.2**.
* Files used: `results` (6,898,910 rows), `result_attempts` (31,797,590 rows), `competitions`,
  `persons`, `round_types`, `countries`, `metadata.json`.
* **Licence / attribution:** the export may be republished if readers are shown the WCA's
  notice. The page carries it verbatim in the method section (with "Assocation" corrected to
  "Association"). Keep it.

Quirks that will bite:

* **Format v2 moved the attempts out of `results`.** `value1..value5` no longer exist. Attempts
  are in `result_attempts` (`value`, `attempt_number`, `result_id` → `results.id`).
* Values are centiseconds. `-1` = DNF, `-2` = DNS, `0` = no result (e.g. the average of a
  best-of-N round). **A DNS average is `-2`, so a naive `min()` over averages returns `-2` as
  somebody's "personal best".** That happened in the first build and pulled every learning
  curve to nonsense. Filter to `average > 0` (or the DNF-as-infinity key below) before any min.
* Use `quoting=3` (QUOTE_NONE) and `keep_default_na=False`: names and competition text contain
  stray quotes, and the literal string `NULL` marks missing values.
* Competition date = `year/month/day` (start date). Round order within a competition is the
  `rank` column of `round_types`, not the id (`c` = Final has rank 90, `1` = First round 29,
  `d` = combined first round 20).
* `persons` has one row per `sub_id` (name/country changes). Use `sub_id == 1` for names.
* Record flags: `regional_average_record == "WR"`. A same-day tie is flagged too, so keep only
  strict improvements.
* On Windows, pandas prints CJK names through cp1252 and throws. Write with `encoding="utf-8"`
  and reconfigure stdout before printing names.

## 3. Processing decisions

All 3×3 (`event_id == "333"`).

* **First competition** = earliest competition (by start date) with any 3×3 result for that
  person. **First average** = the average from the round with the lowest round rank at that
  competition, skipping rounds with no average. This is their literal first judged average,
  not their best of the day; using the best of the day makes newcomers ~1–2 s faster and
  flatters people who advanced.
* **DNF averages are kept** as +∞ (`INF = 1e9`) so they rank as slowest and push quantiles the
  right way. Quantiles that land on a DNF are emitted as `null`.
* **Came back** = any WCA competition in *any* event within 730 days after the first one.
  Only people whose first competition is ≥ 730 days before the export date are scored
  (otherwise recent newcomers look like quitters). 2019 and 2020 cohorts are low because of
  the pandemic, and the page says so.
* **Career bins** (section 3) use total competitions in any event, restricted to people whose
  first competition is ≥ 3 years before the export.
* **Learning curves**: per person, per 3×3 competition, the best average there; the running
  minimum is the PB-to-date; median across people with at least N 3×3 competitions, N ∈
  {5, 10, 20, 40}.
* **Median competitor / top 100**: per year, each person's best average in that year; the
  median across everyone, and the median of the 100 fastest.
* **Where you stand**: 401 quantiles of (a) every person's lifetime PB average and (b) every
  first average. The page interpolates between quantiles. "Getting there" (6–90 s, 0.5 s grid):
  of newcomers (first comp ≥ 3 years ago) whose first average was slower than T, the share
  whose PB ever reached ≤ T, and the median/quartiles of the 3×3 competition index at which it
  first did (a later round at the first competition counts as k = 1).
* **Countries**: `person_country_id` on the person's first 3×3 result; countries with ≥ 500
  newcomers with a first average (62 countries).
* **Five solves**: only format `a` (average of 5) rounds with round types `0,1,2,3,b,c`. The
  combined/cutoff round types (`d,e,f,g,h`) are excluded because attempts 3–5 there are only
  taken by people who made the cutoff. That selection would bias the per-attempt rates. Rounds
  containing any DNS or empty attempt are dropped. The "gamble" table compares the DNF rate on
  solve 4 (given solves 1–3 clean) with solve 5 (given 1–4 clean), banded by the mean of those
  earlier clean solves.

## 4. The page

Fragment authored like an Artifact (`<title>` first, no doctype), finished by `inject.py`,
which runs `wrap_for_pages.py` and `add_catalog_link.py`.

* Identity: a competition **scorecard**. Each section is a card with an "Attempt 1–5" slot on
  the left, then "Extra" and "Judge ✓". Times are set in Share Tech Mono (LCD digits). Headings
  use Archivo Narrow and body text Archivo. The page background is a faint cube-mat grid.
  Colours are the six sticker colours, with dark-mode tokens under both
  `prefers-color-scheme` and `[data-theme]`.
* Hero: two stackmat-style LCD timers start together **in real time** when scrolled into view.
  The record timer stops at 3.51 and the first-timer timer runs on to the current median
  (~34 s). There is a "race again" button, and with reduced motion both timers show their
  final values.
* Charts are canvas with hover and touch tooltips, and redraw on resize and theme change.
  Section 1 has a log/linear toggle. Section 4 has a text input (accepts `ss.xx` or `m:ss.xx`),
  a log slider and preset chips.

## 5. Verification table

A rebuild on the same export should hit these exactly; on a later export they drift slightly.

| check | expected |
|---|---|
| people with a 3×3 result | 286,140 (282,645 with a first average) |
| 3×3 attempts (excluding 0/DNS) | 9,290,270 |
| competitions with 3×3 | 15,342 |
| WR average progression | 45 strict improvements; 14.52 Makisumi 2004-10-16; 7.91 Zemdegs 2010-11-13; 5.53 Zemdegs 2019-11-10; **3.51 Yiheng Wang 2026-06-17** |
| WR single | 2.76 Teodor Zajder 2026-02-07 |
| first-timer median (first round) | 2005 **38.76** · 2008 40.36 · 2021 **28.67** (pandemic restart) · 2026 **33.95** |
| newcomers per year | 2005: 185 · 2023: 36,405 (max) |
| median competitor (person-year best) | 2004 31.06 → 2026 19.92 |
| came back within 2 years, overall | 47.64% |
| return by first average | under 15 s 67.5% · 30–40 s 49.8% · 90–180 s 26.3% · over 3 min 34.3% · DNF 35.0% |
| first average by career length | 1 comp 41.45 · 20–49 comps 25.21 |
| PB median, 10+ comps | 26.04 after comp 1 → 13.37 after comp 10 |
| PB median, 40+ comps | 9.88 after comp 40 |
| lifetime PB median (all 280,164) | 28.42 |
| countries | Vietnam 20.33 (fastest) · United States 36.49 · Brazil 44.74 · Mongolia 56.52 |
| DNF rate by attempt | 2.03 / 2.04 / 2.02 / 1.98 / **2.27%** |
| slowest-of-five share | 21.2 / 20.3 / 19.8 / 19.4 / 19.2% |
| fifth-solve gamble, under 10 s | 4th 1.128% → 5th 1.665% (+48%) ; over 60 s: 3.85 → 3.87% |

## 6. What the page must say about its limits

* The WCA doesn't publish ages, so a slow eight-year-old and a slow adult look the same. The
  return-rate uptick for the slowest group can only be guessed at, and the page labels the
  guess as a guess.
* Only competitions are visible. Someone who stopped competing but kept cubing looks like a
  quitter.
* Country medians most likely show who a country's competitions attract. They are not a
  measure of national talent.
* The selection finding shows that the people who stayed started faster. It does **not** show
  that the people who left would have learned more slowly. An earlier draft said so, and that
  sentence was removed.
