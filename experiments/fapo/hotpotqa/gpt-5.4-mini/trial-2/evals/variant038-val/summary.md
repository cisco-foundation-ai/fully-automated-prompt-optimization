# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.51

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.044 | 0.002 | 0.010 |
| summarize_hop1 | 2.330 | 2.182 | 3.456 |
| query_hop2 | 1.258 | 1.109 | 1.633 |
| retrieve_hop2 | 0.282 | 0.002 | 1.440 |
| summarize_hop2 | 1.491 | 1.384 | 2.176 |
| answer | 0.919 | 0.805 | 1.363 |
| **Total** | **6.324** | **5.814** | **8.989** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
