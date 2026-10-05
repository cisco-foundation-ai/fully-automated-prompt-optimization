# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 72.89

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.003 | 0.005 |
| summarize_hop1 | 5.205 | 4.421 | 10.028 |
| query_hop2 | 2.167 | 1.987 | 3.643 |
| retrieve_hop2 | 0.605 | 0.109 | 1.645 |
| summarize_hop2 | 4.336 | 3.804 | 8.194 |
| answer | 1.606 | 1.411 | 2.885 |
| **Total** | **13.922** | **13.111** | **23.249** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 104 |
