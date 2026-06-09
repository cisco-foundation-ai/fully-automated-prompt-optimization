# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.33

## Score Breakdown
- exact_match: 62.33
- f1: 70.58

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.009 |
| summarize_hop1 | 2.253 | 2.141 | 3.722 |
| query_hop2 | 1.032 | 0.985 | 1.491 |
| retrieve_hop2 | 1.084 | 1.109 | 1.686 |
| summarize_hop2 | 2.565 | 2.463 | 3.910 |
| answer | 1.038 | 0.974 | 1.592 |
| **Total** | **7.988** | **7.823** | **11.147** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 113 |
