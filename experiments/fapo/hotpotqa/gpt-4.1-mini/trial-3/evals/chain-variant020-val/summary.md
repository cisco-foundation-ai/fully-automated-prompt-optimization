# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 73.51

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.003 | 0.005 |
| summarize_hop1 | 4.662 | 4.130 | 8.896 |
| query_hop2 | 2.163 | 2.029 | 3.545 |
| retrieve_hop2 | 0.587 | 0.169 | 1.613 |
| summarize_hop2 | 4.276 | 3.871 | 7.130 |
| answer | 1.527 | 1.385 | 2.554 |
| **Total** | **13.218** | **12.508** | **20.453** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 104 |
