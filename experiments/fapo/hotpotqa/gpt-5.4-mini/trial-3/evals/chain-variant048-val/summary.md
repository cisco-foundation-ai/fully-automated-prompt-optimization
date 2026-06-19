# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 77.36

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.048 | 0.002 | 0.012 |
| summarize_hop1 | 1.363 | 1.272 | 2.014 |
| query_hop2 | 1.139 | 1.025 | 1.695 |
| retrieve_hop2 | 0.302 | 0.002 | 1.578 |
| summarize_hop2 | 1.406 | 1.241 | 2.066 |
| answer | 1.067 | 0.892 | 1.552 |
| **Total** | **5.326** | **4.779** | **8.470** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 86 |
