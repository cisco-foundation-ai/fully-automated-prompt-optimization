# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.67

## Score Breakdown
- exact_match: 57.67
- f1: 67.71

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.035 | 0.002 | 0.010 |
| summarize_hop1 | 2.021 | 1.877 | 3.539 |
| query_hop2 | 1.071 | 1.053 | 1.425 |
| retrieve_hop2 | 1.157 | 1.308 | 1.430 |
| summarize_hop2 | 3.671 | 2.870 | 5.373 |
| answer | 1.159 | 1.078 | 1.774 |
| **Total** | **9.113** | **8.161** | **12.931** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 127 |
