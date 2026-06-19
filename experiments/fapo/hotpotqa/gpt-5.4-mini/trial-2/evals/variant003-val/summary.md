# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.33

## Score Breakdown
- exact_match: 63.33
- f1: 71.03

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.005 |
| summarize_hop1 | 1.136 | 1.058 | 1.789 |
| query_hop2 | 0.981 | 0.937 | 1.361 |
| retrieve_hop2 | 1.159 | 1.297 | 1.720 |
| summarize_hop2 | 1.094 | 1.046 | 1.498 |
| answer | 0.848 | 0.793 | 1.195 |
| **Total** | **5.221** | **5.150** | **6.631** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 110 |
