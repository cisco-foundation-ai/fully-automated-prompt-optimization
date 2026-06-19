# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 74.68

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.041 | 0.002 | 0.009 |
| summarize_hop1 | 2.302 | 2.155 | 3.680 |
| query_hop2 | 1.226 | 1.131 | 1.847 |
| retrieve_hop2 | 0.250 | 0.002 | 1.479 |
| summarize_hop2 | 1.832 | 1.756 | 2.772 |
| answer | 0.878 | 0.814 | 1.497 |
| **Total** | **6.529** | **6.076** | **9.413** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
