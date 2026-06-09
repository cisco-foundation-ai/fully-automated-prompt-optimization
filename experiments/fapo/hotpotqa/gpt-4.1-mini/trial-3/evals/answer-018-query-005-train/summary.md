# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 80.39

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.026 | 0.002 | 0.010 |
| summarize_hop1 | 5.221 | 4.575 | 9.271 |
| query_hop2 | 3.975 | 3.234 | 8.570 |
| retrieve_hop2 | 1.047 | 1.083 | 1.619 |
| summarize_hop2 | 7.787 | 4.966 | 27.066 |
| answer | 2.274 | 2.005 | 4.259 |
| **Total** | **20.330** | **17.868** | **39.722** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
