# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 70.73

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.988 | 1.073 | 1.586 |
| summarize_hop1 | 3.731 | 2.516 | 5.575 |
| query_hop2 | 3.522 | 1.222 | 3.368 |
| retrieve_hop2 | 1.110 | 1.226 | 1.571 |
| summarize_hop2 | 5.852 | 4.197 | 8.245 |
| answer | 3.003 | 1.308 | 3.747 |
| **Total** | **18.206** | **11.864** | **30.097** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 112 |
