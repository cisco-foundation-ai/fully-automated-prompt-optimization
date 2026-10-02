# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 76.37

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.046 | 0.003 | 0.055 |
| summarize_hop1 | 1.811 | 1.644 | 3.338 |
| query_hop2 | 0.955 | 0.921 | 1.245 |
| retrieve_hop2 | 0.986 | 0.009 | 1.707 |
| summarize_hop2 | 2.628 | 2.522 | 4.124 |
| answer | 1.359 | 1.272 | 2.130 |
| **Total** | **7.784** | **7.261** | **11.357** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
