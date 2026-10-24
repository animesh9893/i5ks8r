# 08: Analysis Method (what to compute and how to explain it)

## Definitions (copy these into the README)
- `error = forecast − actual` (MW). Positive means wind was **over-forecast**, so the utility is
  **short** and must buy more at short notice, which is the costly direction.
- **MAE**: mean |error|, the typical miss. **RMSE**: penalises big misses. **Bias**: mean error, the systematic tilt.
- **nMAE**: MAE / mean actual, which lets you compare across periods.
- **P90 |error|**: 90 % of hours miss by less than this. It is the number to size a risk buffer with.
- **MAPE**: reported, but excluding hours with actual < 500 MW, because it blows up at low output.

## Headline analyses
1. **Day-ahead accuracy (January 2026)**: metrics where each delivery hour uses the forecast at the
   D−1 11:00 gate. This answers "how much can we trust the number we bought on?"
2. **Error against horizon (0 to 48 h)**: shows how much accuracy improves as delivery gets closer.
   This argues for intraday re-trading.
3. **Error by hour of day**: whether some delivery hours are harder to forecast.
4. **Distribution and tails**: is the error symmetric? How fat are the tails? (Storm days in January.)
5. **Worst days**: top 5 delivery days by MAE (cheap to add, and a strong demo moment: "here's the
   storm on X Jan, and the band warned you").
6. **Band calibration**: share of hours where the actual landed inside the P10–P90 band (target about 80 %).

## Findings on January 2026 (computed in T3 from the committed snapshot)
| Metric | h = 1 h | h = 24 h | h = 36 h | Day-ahead (D−1 11:00 gate) |
|---|---|---|---|---|
| MAE (MW) | 1,801 | 2,050 | 2,258 | 1,996 |
| Bias (MW, forecast − actual) | +1,596 | +1,854 | +1,951 | +1,728 |
| nMAE | 15.6 % | 17.7 % | 19.5 % | 17.7 % |
| P90 abs error (MW) | 3,798 | 4,129 | 4,263 | 4,184 |

- **Large systematic over-forecast.** WINDFOR exceeds FUELHH WIND in 84 % of day-ahead hours, by
  about 1.7 GW on average, and the gap barely shrinks at short horizons. So most of the "error" is
  **bias, not noise**. A likely cause is that the forecast is of unconstrained or potential output,
  while FUELHH is metered output after curtailment and constraint actions (January had heavy
  constraints). This is a hypothesis, not verified. Present it as "the raw forecast should be
  bias-corrected before trading on it", which is a strong, actionable pitch point.
- Error grows steadily with horizon: MAE goes from 1.8 GW at 1 h to 2.4 GW at 48 h.
- Day-ahead lead times range from **14.5 h to 37.5 h** (the 09:30 D−1 run is the last one before the 11:00 gate).
- **Band calibration:** the actual fell inside the P10–P90 band in **79 %** of day-ahead hours (target 80 %, in-sample).
- **Worst delivery days by MAE:** 28 Jan (5.3 GW), 11 Jan, 12 Jan, 21 Jan, 27 Jan. Use these in the demo.

## Honest caveats (say these in the video)
- The quantiles are fitted on the same January data they are evaluated on, so they are in-sample.
  The production version would use a rolling, leakage-free window.
- Only national wind data is used. There is no demand, solar, or embedded generation. In GB, much wind
  is embedded or curtailed, and BMRS actuals are metered transmission-connected output.
- Hourly forecasts are compared with the half-hourly actual at the matching start time.

## Optional notebook
`docs/analysis.ipynb` (or `backend/scripts/analysis.py`) reproduces the headline numbers with the
same service functions. It gives the tech lead one place to verify the maths.
