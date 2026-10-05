# Evaluation Summary

Total cases: 300

## Composite Score
- average: 56.33

## Score Breakdown
- exact_match: 56.33
- f1: 67.31

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 2.029 | 1.482 | 4.865 |
| query_hop2 | 1.583 | 1.218 | 3.317 |
| retrieve_hop2 | 1.358 | 1.266 | 1.644 |
| summarize_hop2 | 2.802 | 1.379 | 3.981 |
| answer | 1.780 | 1.186 | 3.867 |
| **Total** | **9.555** | **7.257** | **16.775** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 131 |
