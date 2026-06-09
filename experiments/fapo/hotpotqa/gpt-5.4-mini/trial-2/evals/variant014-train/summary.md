# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 79.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.082 | 0.002 | 0.057 |
| summarize_hop1 | 2.048 | 1.967 | 3.166 |
| query_hop2 | 1.184 | 1.071 | 1.989 |
| retrieve_hop2 | 0.518 | 0.002 | 1.615 |
| summarize_hop2 | 1.551 | 1.415 | 2.244 |
| answer | 0.831 | 0.776 | 1.269 |
| **Total** | **6.214** | **5.743** | **9.055** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
