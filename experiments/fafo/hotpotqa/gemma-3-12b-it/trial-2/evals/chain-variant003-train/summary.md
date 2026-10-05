# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 78.07

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.058 | 0.003 | 0.035 |
| summarize_hop1 | 3.386 | 3.117 | 5.255 |
| query_hop2 | 1.176 | 1.152 | 1.665 |
| retrieve_hop2 | 0.496 | 0.007 | 1.592 |
| summarize_hop2 | 3.957 | 3.736 | 6.654 |
| answer | 1.049 | 0.952 | 1.571 |
| **Total** | **10.122** | **9.656** | **15.037** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
