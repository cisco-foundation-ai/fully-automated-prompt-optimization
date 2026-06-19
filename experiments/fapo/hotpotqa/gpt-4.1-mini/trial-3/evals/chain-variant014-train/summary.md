# Evaluation Summary

Total cases: 150

## Composite Score
- average: 73.33

## Score Breakdown
- exact_match: 73.33
- f1: 79.27

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.051 | 0.003 | 0.024 |
| summarize_hop1 | 3.864 | 3.303 | 7.483 |
| query_hop2 | 2.205 | 1.940 | 4.027 |
| retrieve_hop2 | 0.636 | 0.062 | 1.627 |
| summarize_hop2 | 3.273 | 2.907 | 6.447 |
| answer | 1.415 | 1.275 | 2.240 |
| **Total** | **11.444** | **10.592** | **18.979** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 40 |
