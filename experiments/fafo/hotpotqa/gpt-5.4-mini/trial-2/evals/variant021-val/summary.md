# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 76.18

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.013 |
| summarize_hop1 | 2.293 | 2.172 | 3.174 |
| query_hop2 | 1.176 | 1.119 | 1.675 |
| retrieve_hop2 | 0.375 | 0.002 | 1.581 |
| summarize_hop2 | 1.856 | 1.761 | 2.775 |
| answer | 0.779 | 0.710 | 1.266 |
| **Total** | **6.517** | **6.097** | **9.089** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
