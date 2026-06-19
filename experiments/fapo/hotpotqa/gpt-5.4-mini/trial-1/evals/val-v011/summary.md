# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 77.30

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.127 | 0.002 | 0.113 |
| summarize_hop1 | 1.356 | 1.273 | 2.109 |
| query_hop2 | 1.116 | 1.043 | 1.606 |
| retrieve_hop2 | 0.628 | 0.002 | 1.661 |
| summarize_hop2 | 1.607 | 1.495 | 2.576 |
| answer | 0.807 | 0.745 | 1.173 |
| **Total** | **5.641** | **5.034** | **8.602** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
