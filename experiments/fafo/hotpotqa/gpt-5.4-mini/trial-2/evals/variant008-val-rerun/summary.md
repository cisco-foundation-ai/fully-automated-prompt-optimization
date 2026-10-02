# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 75.94

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.013 |
| summarize_hop1 | 2.092 | 1.990 | 2.998 |
| query_hop2 | 1.291 | 1.040 | 1.799 |
| retrieve_hop2 | 0.567 | 0.003 | 1.617 |
| summarize_hop2 | 1.791 | 1.560 | 2.599 |
| answer | 0.845 | 0.785 | 1.375 |
| **Total** | **6.624** | **5.968** | **9.774** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
