# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.67

## Score Breakdown
- exact_match: 71.67
- f1: 78.78

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.048 | 0.002 | 0.010 |
| summarize_hop1 | 1.443 | 1.258 | 2.136 |
| query_hop2 | 1.117 | 1.019 | 1.733 |
| retrieve_hop2 | 0.246 | 0.002 | 1.501 |
| summarize_hop2 | 1.350 | 1.220 | 2.031 |
| answer | 1.158 | 0.940 | 1.559 |
| **Total** | **5.361** | **4.672** | **8.529** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 85 |
