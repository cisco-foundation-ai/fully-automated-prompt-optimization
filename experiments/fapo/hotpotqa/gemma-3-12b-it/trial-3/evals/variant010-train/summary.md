# Evaluation Summary

Total cases: 150

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.03

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.013 |
| summarize_hop1 | 1.820 | 1.608 | 3.418 |
| query_hop2 | 1.796 | 0.945 | 1.381 |
| retrieve_hop2 | 0.971 | 0.004 | 1.670 |
| summarize_hop2 | 2.594 | 2.607 | 4.098 |
| answer | 0.998 | 0.986 | 1.404 |
| **Total** | **8.195** | **6.696** | **10.788** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 46 |
