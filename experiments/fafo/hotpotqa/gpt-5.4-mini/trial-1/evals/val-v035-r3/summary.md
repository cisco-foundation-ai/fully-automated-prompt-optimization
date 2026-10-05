# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.33

## Score Breakdown
- exact_match: 70.33
- f1: 77.61

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.107 | 0.002 | 0.122 |
| summarize_hop1 | 1.517 | 1.320 | 2.377 |
| query_hop2 | 1.302 | 1.098 | 1.907 |
| retrieve_hop2 | 0.426 | 0.002 | 1.631 |
| summarize_hop2 | 1.719 | 1.633 | 2.565 |
| answer | 0.840 | 0.774 | 1.242 |
| **Total** | **5.912** | **5.318** | **8.764** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 89 |
