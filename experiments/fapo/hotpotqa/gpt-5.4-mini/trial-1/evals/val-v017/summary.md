# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- exact_match: 69.00
- f1: 75.66

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.095 | 0.002 | 0.120 |
| summarize_hop1 | 1.414 | 1.294 | 2.099 |
| query_hop2 | 1.219 | 1.036 | 1.770 |
| retrieve_hop2 | 0.458 | 0.002 | 1.558 |
| summarize_hop2 | 1.583 | 1.470 | 2.291 |
| answer | 0.890 | 0.767 | 1.306 |
| **Total** | **5.658** | **4.895** | **10.603** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
