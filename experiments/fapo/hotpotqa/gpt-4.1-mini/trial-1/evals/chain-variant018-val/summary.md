# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.67

## Score Breakdown
- exact_match: 67.67
- f1: 75.84

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.008 |
| summarize_hop1 | 3.833 | 3.359 | 6.865 |
| query_hop2 | 1.842 | 1.686 | 3.103 |
| retrieve_hop2 | 0.597 | 0.002 | 1.612 |
| summarize_hop2 | 3.333 | 3.013 | 5.677 |
| answer | 1.807 | 1.630 | 3.051 |
| **Total** | **11.439** | **10.823** | **16.890** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 97 |
