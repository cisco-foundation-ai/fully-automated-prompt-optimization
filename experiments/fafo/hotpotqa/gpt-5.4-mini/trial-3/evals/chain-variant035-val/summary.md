# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 77.51

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.047 | 0.002 | 0.011 |
| summarize_hop1 | 1.219 | 1.175 | 1.736 |
| query_hop2 | 1.240 | 1.018 | 1.559 |
| retrieve_hop2 | 0.244 | 0.002 | 1.284 |
| summarize_hop2 | 1.219 | 1.163 | 1.728 |
| answer | 0.952 | 0.901 | 1.339 |
| **Total** | **4.919** | **4.421** | **6.677** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
