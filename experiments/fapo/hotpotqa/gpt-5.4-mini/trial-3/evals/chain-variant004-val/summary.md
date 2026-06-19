# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.33

## Score Breakdown
- exact_match: 70.33
- f1: 76.85

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.035 | 0.002 | 0.009 |
| summarize_hop1 | 1.545 | 1.371 | 2.003 |
| query_hop2 | 1.143 | 1.081 | 1.673 |
| retrieve_hop2 | 0.849 | 0.522 | 1.648 |
| summarize_hop2 | 1.355 | 1.248 | 1.800 |
| answer | 0.936 | 0.852 | 1.308 |
| **Total** | **5.864** | **5.559** | **7.781** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 89 |
