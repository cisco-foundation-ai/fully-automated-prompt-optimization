# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 77.48

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.002 | 0.091 |
| summarize_hop1 | 1.414 | 1.289 | 2.180 |
| query_hop2 | 1.239 | 1.086 | 2.100 |
| retrieve_hop2 | 1.209 | 1.065 | 1.669 |
| summarize_hop2 | 1.699 | 1.578 | 2.644 |
| answer | 0.898 | 0.770 | 1.548 |
| **Total** | **6.500** | **5.870** | **9.671** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
