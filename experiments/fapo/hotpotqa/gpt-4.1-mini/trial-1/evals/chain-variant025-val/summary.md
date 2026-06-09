# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 75.32

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.011 | 0.002 | 0.010 |
| summarize_hop1 | 3.921 | 3.143 | 7.956 |
| query_hop2 | 1.968 | 1.698 | 3.251 |
| retrieve_hop2 | 0.414 | 0.002 | 1.609 |
| summarize_hop2 | 3.054 | 2.795 | 5.316 |
| answer | 1.500 | 1.351 | 2.185 |
| **Total** | **10.868** | **9.831** | **17.369** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
