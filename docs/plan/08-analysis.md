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

## Honest caveats (say these in the video)
- The quantiles are fitted on the same January data they are evaluated on, so they are in-sample.
  The production version would use a rolling, leakage-free window.
- Only national wind data is used. There is no demand, solar, or embedded generation. In GB, much wind
  is embedded or curtailed, and BMRS actuals are metered transmission-connected output.
- Hourly forecasts are compared with the half-hourly actual at the matching start time.

## Optional notebook
`docs/analysis.ipynb` (or `backend/scripts/analysis.py`) reproduces the headline numbers with the
same service functions. It gives the tech lead one place to verify the maths.
