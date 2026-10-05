# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 76.85

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.141 | 0.002 | 0.109 |
| summarize_hop1 | 1.447 | 1.300 | 2.192 |
| query_hop2 | 1.168 | 1.059 | 2.001 |
| retrieve_hop2 | 0.393 | 0.002 | 1.544 |
| summarize_hop2 | 1.675 | 1.539 | 2.386 |
| answer | 0.861 | 0.777 | 1.319 |
| **Total** | **5.687** | **4.899** | **10.262** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
| query_hop2 | 1 |
