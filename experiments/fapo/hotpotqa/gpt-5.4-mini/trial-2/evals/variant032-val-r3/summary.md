# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 76.86

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.029 | 0.002 | 0.008 |
| summarize_hop1 | 2.416 | 2.151 | 3.155 |
| query_hop2 | 1.300 | 1.147 | 2.050 |
| retrieve_hop2 | 0.322 | 0.002 | 1.515 |
| summarize_hop2 | 1.698 | 1.519 | 2.687 |
| answer | 0.930 | 0.815 | 1.358 |
| **Total** | **6.694** | **6.071** | **10.445** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
