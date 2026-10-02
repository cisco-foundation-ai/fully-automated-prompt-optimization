# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.00

## Score Breakdown
- exact_match: 64.00
- f1: 71.55

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.013 |
| summarize_hop1 | 2.384 | 2.223 | 4.013 |
| query_hop2 | 1.084 | 1.025 | 1.600 |
| retrieve_hop2 | 0.484 | 0.003 | 1.588 |
| summarize_hop2 | 2.335 | 2.181 | 3.868 |
| answer | 1.076 | 1.031 | 1.528 |
| **Total** | **7.402** | **7.247** | **10.185** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 108 |
