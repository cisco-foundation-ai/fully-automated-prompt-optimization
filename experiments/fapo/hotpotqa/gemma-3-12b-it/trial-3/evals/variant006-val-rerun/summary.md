# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.67

## Score Breakdown
- exact_match: 60.67
- f1: 68.54

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.024 | 0.002 | 0.009 |
| summarize_hop1 | 1.774 | 1.565 | 3.099 |
| query_hop2 | 0.980 | 0.943 | 1.384 |
| retrieve_hop2 | 0.734 | 0.004 | 1.644 |
| summarize_hop2 | 2.784 | 2.680 | 4.485 |
| answer | 1.060 | 1.011 | 1.547 |
| **Total** | **7.355** | **7.050** | **10.879** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 118 |
