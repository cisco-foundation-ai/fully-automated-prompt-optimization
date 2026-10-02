# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 75.65

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.117 | 0.002 | 0.121 |
| summarize_hop1 | 1.305 | 1.210 | 1.938 |
| query_hop2 | 1.108 | 0.996 | 1.662 |
| retrieve_hop2 | 0.742 | 0.003 | 1.677 |
| summarize_hop2 | 1.070 | 1.018 | 1.527 |
| answer | 0.810 | 0.754 | 1.205 |
| **Total** | **5.152** | **4.557** | **7.477** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
