# Evaluation Summary

Total cases: 150

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 73.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.013 | 0.002 | 0.016 |
| summarize_hop1 | 1.739 | 1.550 | 2.982 |
| query_hop2 | 0.995 | 0.944 | 1.470 |
| retrieve_hop2 | 1.101 | 0.295 | 1.704 |
| summarize_hop2 | 2.296 | 2.178 | 3.714 |
| answer | 1.020 | 0.999 | 1.491 |
| **Total** | **7.164** | **6.595** | **10.927** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 49 |
