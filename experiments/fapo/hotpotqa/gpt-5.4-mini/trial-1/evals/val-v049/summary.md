# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.24

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.095 | 0.002 | 0.112 |
| summarize_hop1 | 1.474 | 1.377 | 2.377 |
| query_hop2 | 1.284 | 1.132 | 2.133 |
| retrieve_hop2 | 0.649 | 0.002 | 1.625 |
| summarize_hop2 | 1.753 | 1.665 | 2.710 |
| answer | 0.837 | 0.762 | 1.242 |
| **Total** | **6.093** | **5.466** | **8.950** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
