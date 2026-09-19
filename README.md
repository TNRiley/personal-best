# ⏱️ Personal Best

**Every official Rubik's Cube competition since 2003. The world-record average got four times faster. A first-timer's average has barely moved, and half of first-timers never come back.**

→ **[Open it](https://tnriley.github.io/personal-best/)**

The World Cube Association's full results export: 286,140 people and 9.3 million timed 3×3 solves at 15,342 competitions. The world-record average fell from 14.52 seconds at the end of 2004 to 3.51 in June 2026. The median first average a newcomer sets in their first round went from 38.8 seconds in 2005 to 34.0, about a tenth of that improvement. Only 48% of first-timers enter another competition within two years, and the ones who stay were faster from the start: people who competed once started at a median of 41.5 seconds, and people who went on to twenty or more competitions started at 25.2. So a WCA field gets faster partly through practice and partly through who stays. Two hero timers race in real time, the record stopping at 3.51 while the typical first-timer keeps going. You can type your own average to see where it falls among every personal best and every first round. The last section looks at the five solves of a round. The first is most often the slowest, and the fifth is the one most likely to be a DNF. That jump is almost entirely among the fastest solvers: after four clean solves under ten seconds, the DNF rate goes from 1.13% on the fourth solve to 1.67% on the fifth. Slow solvers, the ones a time limit would catch, show no jump.

## Running it

One self-contained HTML file. No build step, no server, no network access at runtime — open `index.html` in a browser, or serve the directory with any static host.

```bash
python3 -m http.server 8000   # then visit http://localhost:8000
```

## Rebuilding it from scratch

[REBUILD.md](REBUILD.md) is written for an LLM with a shell and nothing else: the data sources and their quirks, the processing decisions, the page's structure and interactions, and a table of expected values to check the result against.

## Source

The full build pipeline is in [`src/`](src/), with a README describing how to regenerate the page from scratch.

## Data

- **[World Cube Association results export (TSV, format v2.0.2), as of 18 September 2026](https://www.worldcubeassociation.org/export/results)** — May be republished in whole or part with the WCA's attribution notice: "This information is based on competition results owned and maintained by the World Cube Association, published at https://worldcubeassociation.org/results as of September 18, 2026."

Every figure on the page is computed from the data shipped with it. Check the page's own methods panel for how each number is derived and where it should not be pushed.

## Built with

python 3 + pandas, quantile payload with DNF-as-slowest ranking, vanilla JS, canvas, real-time LCD race.

## Licence

Code is MIT (see [LICENSE](LICENSE)). Data keeps the licence of its source, listed above.

---

Part of [Quick Projects](https://github.com/TNRiley/quick-projects) — one self-contained thing, built in one session. First published 2026-09-19.
