# Evaluation Summary

Total cases: 300

## Composite Score
- average: 59.67

## Score Breakdown
- exact_match: 59.67
- f1: 68.91

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.012 |
| summarize_hop1 | 1.986 | 1.823 | 3.360 |
| query_hop2 | 1.015 | 0.985 | 1.337 |
| retrieve_hop2 | 0.646 | 0.003 | 1.628 |
| summarize_hop2 | 3.308 | 3.106 | 5.184 |
| answer | 0.916 | 0.879 | 1.312 |
| **Total** | **7.904** | **7.665** | **11.822** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 121 |
