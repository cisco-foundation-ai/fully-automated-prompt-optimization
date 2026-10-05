# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.40

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.009 |
| summarize_hop1 | 1.425 | 1.388 | 1.853 |
| query_hop2 | 1.030 | 0.940 | 1.502 |
| retrieve_hop2 | 0.526 | 0.002 | 1.577 |
| summarize_hop2 | 1.272 | 1.216 | 1.784 |
| answer | 0.920 | 0.851 | 1.185 |
| **Total** | **5.191** | **4.767** | **6.925** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 86 |
