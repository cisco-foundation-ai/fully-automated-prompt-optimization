# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 79.74

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.002 | 0.028 |
| summarize_hop1 | 2.954 | 2.724 | 4.451 |
| query_hop2 | 2.044 | 1.611 | 3.390 |
| retrieve_hop2 | 0.618 | 0.002 | 1.651 |
| summarize_hop2 | 3.258 | 2.733 | 7.287 |
| answer | 1.606 | 1.498 | 2.634 |
| **Total** | **10.522** | **9.523** | **20.341** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
