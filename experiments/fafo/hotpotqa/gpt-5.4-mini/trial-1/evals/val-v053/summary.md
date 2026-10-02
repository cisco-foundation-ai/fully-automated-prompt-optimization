# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 75.74

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.151 | 0.002 | 0.127 |
| summarize_hop1 | 1.410 | 1.310 | 2.147 |
| query_hop2 | 1.136 | 1.043 | 1.617 |
| retrieve_hop2 | 0.452 | 0.002 | 1.617 |
| summarize_hop2 | 1.656 | 1.538 | 2.418 |
| answer | 0.811 | 0.740 | 1.200 |
| **Total** | **5.617** | **4.996** | **8.470** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
