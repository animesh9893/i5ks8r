# 10: Video Script and Submission

Total length 10 min or less. Upload to YouTube as **Unlisted**. Record the screen at 1080p with the
browser zoom set so that charts are readable.

## Part 1: Client pitch (up to 5 min)
| Time | Content |
|---|---|
| 0:00–0:30 | The problem: "Every morning before 11:00 you commit to tomorrow's power. Wind can swing by GWs. How much can you trust the forecast?" |
| 0:30–2:00 | **Day-Ahead Planner**: pick a calm day, then a stormy day. Show the forecast at the gate, the P10–P90 band, and "firm wind" P10. Toggle the actual line to show the band holding. |
| 2:00–3:30 | **Accuracy**: headline day-ahead MAE and P90 for January. The horizon curve (error roughly halves from 36 h to 4 h, so re-trade intraday). Hour-of-day pattern and worst days. |
| 3:30–4:30 | Forecast vs Actual explorer: slide the horizon and watch the forecast converge on the actual line. |
| 4:30–5:00 | Value and next steps: add demand and solar to get residual demand, live data, alerts when the band is wide, and a cost model. |

## Part 2: Tech lead review (up to 5 min)
| Time | Content |
|---|---|
| 0:00–0:45 | Architecture diagram: Vercel SPA → Railway FastAPI container → Elexon, with the in-memory store and snapshot fallback. Why there is no DB (static historical data, about 40k rows). |
| 0:45–2:00 | Core algorithm in code: `merge_asof` for the latest forecast at horizon, the day-ahead gate and time zone handling, and dropping negative horizons. |
| 2:00–2:45 | Metrics module and its definitions, plus the in-sample caveat. |
| 2:45–3:30 | Repo tour: layering (clients/data/services/api), schemas mirrored in TS, URL-synced filters, TanStack Query. |
| 3:30–4:15 | Practices: unit tests on hand-built fixtures, ruff, typed code, CI, Docker multi-stage with a non-root user, env config, `/docs`. |
| 4:15–5:00 | Deploy flow (push to main → CI → Railway and Vercel auto-deploy), AI usage, and what you'd do next (DB + scheduled ingestion, leakage-free quantiles, auth). |

## Submission checklist
- [ ] Repo is public with an anonymous name, and contains no secrets (`.env` is gitignored)
- [ ] README contains: files/dirs, how to start, **Vercel link**, AI-tools disclosure
- [ ] Vercel app and Railway API are live; opening them in incognito works
- [ ] YouTube video is **Unlisted** (not Private) and plays in incognito
- [ ] Form submitted with repo URL, app URL, and video URL
