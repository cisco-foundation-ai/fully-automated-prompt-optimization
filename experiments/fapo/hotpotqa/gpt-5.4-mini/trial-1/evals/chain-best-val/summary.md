# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.40

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.141 | 0.002 | 0.121 |
| summarize_hop1 | 1.664 | 1.246 | 1.978 |
| query_hop2 | 1.086 | 1.029 | 1.524 |
| retrieve_hop2 | 0.449 | 0.002 | 1.624 |
| summarize_hop2 | 1.561 | 1.441 | 2.277 |
| answer | 0.768 | 0.726 | 1.099 |
| **Total** | **5.669** | **4.787** | **8.943** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
