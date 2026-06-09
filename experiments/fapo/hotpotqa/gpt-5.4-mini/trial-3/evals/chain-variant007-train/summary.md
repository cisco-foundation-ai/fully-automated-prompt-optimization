# Evaluation Summary

Total cases: 150

## Composite Score
- average: 75.33

## Score Breakdown
- exact_match: 75.33
- f1: 81.74

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.050 | 0.002 | 0.057 |
| summarize_hop1 | 1.415 | 1.352 | 2.000 |
| query_hop2 | 0.959 | 0.909 | 1.333 |
| retrieve_hop2 | 0.788 | 0.002 | 1.632 |
| summarize_hop2 | 1.236 | 1.165 | 1.794 |
| answer | 0.899 | 0.867 | 1.269 |
| **Total** | **5.347** | **4.673** | **7.328** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 37 |
