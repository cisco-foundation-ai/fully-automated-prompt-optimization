# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.00

## Score Breakdown
- exact_match: 68.00
- f1: 74.53

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.053 | 0.670 | 1.682 |
| summarize_hop1 | 1.100 | 1.045 | 1.559 |
| query_hop2 | 0.944 | 0.915 | 1.286 |
| retrieve_hop2 | 1.299 | 1.339 | 1.627 |
| summarize_hop2 | 1.116 | 1.000 | 1.371 |
| answer | 0.843 | 0.796 | 1.139 |
| **Total** | **6.354** | **6.042** | **7.709** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 96 |
