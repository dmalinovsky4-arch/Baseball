# Yankees Matchup Model

CLI model that projects the New York Yankees' nightly game against their
scheduled opponent. Matchup math combines four foundational inputs for every
batter-vs-pitcher pairing:

- **EV50** (median exit velocity on batted balls)
- **pwRC+** (park- and league-adjusted batting runs index)
- **xwOBA** (expected wOBA from Statcast)
- **wOBA** (actual wOBA from FanGraphs)

Outputs: Yankees win probability, projected run total, and per-batter prop
projections (hits, total bases, home runs).

## Data sources

- **MLB Stats API** (`statsapi.mlb.com/api/v1`) for schedule, probable
  pitchers, lineups, venue, and venue coordinates. Called directly, no wrapper.
- **Statcast** (via `pybaseball.statcast`) for xwOBA and exit velocity.
- **FanGraphs** season leaderboards (via `pybaseball.batting_stats` /
  `pitching_stats`) for wOBA, wRC+, FIP-, AVG/SLG/HR.
- **Open-Meteo** forecast API for game-time temperature and wind
  (no API key required).
- **Static park factors** in `data/park_factors.csv` (edit to tune).

Large Statcast and FanGraphs pulls are cached under `.cache/` after the first
run of each season.

## Model

1. For every batter and pitcher, each of the four stats is blended Marcel-style
   across current season, prior season, and league mean (weighted by PA / TBF).
2. Each foundational stat is mapped into a common "wOBA space":
   - xwOBA / wOBA → log5 vs pitcher's xwOBA-against / wOBA-against
   - EV50 → linearized to wOBA (+1 mph ≈ +0.006 wOBA), then log5
   - wRC+ × (pitcher FIP- / 100) → wOBA
3. Four components are equal-weighted into a matchup wOBA per batter.
4. Matchup wOBA → runs/PA via standard wRAA formula, summed across the lineup
   and multiplied by park factor and a weather multiplier.
5. Win probability via Pythagenpat (exponent = (R+RA)^0.287).
6. Per-batter props scale the batter's blended AVG/SLG/HR-rate by the matchup
   wOBA vs league wOBA.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python predict.py                       # tonight
python predict.py --date 2026-05-01
python predict.py --date 2026-05-01 --json
```

First run of a given season will take several minutes while Statcast pulls the
full season's pitch-level data. Subsequent runs are fast (pickle cache).

## Layout

```
predict.py                 # CLI entrypoint
src/
  constants.py             # league constants, endpoints
  orchestrator.py          # wires data + blending + model together
  data/
    schedule.py            # MLB Stats API client
    statcast.py            # Statcast aggregates via pybaseball
    fangraphs.py           # FanGraphs leaderboards via pybaseball
    park_factors.py        # CSV lookup
    weather.py             # Open-Meteo
    cache.py               # pickle cache helper
  model/
    blend.py               # Marcel-style blending
    matchup.py             # log5 + wOBA-space combination
    game.py                # team runs, Pythagenpat, props
  cli/
    report.py              # text formatter
data/
  park_factors.csv         # tunable park factors
```

## Tuning

- **Stat weights** are currently equal. To change, edit the final average in
  `src/model/matchup.py::matchup_woba`.
- **Blending weights** (prior-season credit, league regression PA) live in
  `src/model/blend.py`.
- **Park factors** live in `data/park_factors.csv` — edit freely.
- **Weather response** (temp/wind multipliers) lives in `src/data/weather.py`.

## Modeling choices

- **Bullpen weighting**: each batter's matchup wOBA is a 55/45 blend of
  "vs opposing SP" and "vs opposing bullpen" (team-aggregated relievers,
  TBF-weighted, defined as G − GS ≥ 10 and GS/G < 0.3).
- **Handedness splits**: Statcast batter/pitcher aggregates are produced
  three ways (overall, vs L, vs R). At matchup time we pick the split that
  matches the pitcher's throwing hand and the batter's stand (switch hitters
  use opposite). wOBA and wRC+ are scaled by the xwOBA split ratio since
  FanGraphs doesn't expose native splits via pybaseball. Falls back to
  overall if a split has <40 PA.
- **Park orientation**: `cf_bearing_deg` in `data/park_factors.csv` is the
  bearing from home plate to center field. Wind direction (from Open-Meteo)
  is projected onto that axis; positive dot product = tailwind (boost),
  negative = headwind (suppression). Every +10 mph of true tailwind ≈ +3%
  runs.

## Roadmap

- Backtest harness against last 1–3 seasons to tune stat weights.
- Per-reliever handedness mix for bullpens (currently treated as
  right-handed-bias overall).
- Sportsbook odds pull for +EV flagging.
