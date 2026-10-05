# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.46

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.019 | 0.002 | 0.009 |
| summarize_hop1 | 4.134 | 3.649 | 6.644 |
| query_hop2 | 1.864 | 1.701 | 2.874 |
| retrieve_hop2 | 1.004 | 1.059 | 1.586 |
| summarize_hop2 | 2.915 | 2.620 | 4.866 |
| answer | 1.400 | 1.258 | 2.360 |
| **Total** | **11.336** | **10.713** | **16.166** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 84 |
