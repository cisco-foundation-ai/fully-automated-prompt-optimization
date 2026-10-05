# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.33

## Score Breakdown
- exact_match: 69.33
- f1: 76.57

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.009 |
| summarize_hop1 | 4.299 | 3.815 | 7.489 |
| query_hop2 | 2.312 | 2.034 | 4.456 |
| retrieve_hop2 | 0.265 | 0.002 | 1.538 |
| summarize_hop2 | 3.147 | 2.861 | 5.006 |
| answer | 1.864 | 1.709 | 2.926 |
| **Total** | **11.915** | **11.256** | **18.264** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
