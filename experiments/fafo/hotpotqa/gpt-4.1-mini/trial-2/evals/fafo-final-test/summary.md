# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 78.10

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.143 | 1.278 | 1.655 |
| summarize_hop1 | 2.785 | 2.537 | 4.627 |
| query_hop2 | 1.819 | 1.312 | 2.577 |
| retrieve_hop2 | 1.423 | 1.474 | 1.616 |
| summarize_hop2 | 2.619 | 2.190 | 3.606 |
| answer | 1.020 | 0.843 | 1.387 |
| **Total** | **10.809** | **9.482** | **19.318** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
