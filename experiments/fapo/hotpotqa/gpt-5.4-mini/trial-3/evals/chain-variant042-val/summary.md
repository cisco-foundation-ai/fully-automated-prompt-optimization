# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.67

## Score Breakdown
- exact_match: 73.67
- f1: 79.31

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.066 | 0.002 | 0.008 |
| summarize_hop1 | 1.388 | 1.260 | 1.900 |
| query_hop2 | 1.150 | 1.074 | 1.624 |
| retrieve_hop2 | 0.330 | 0.002 | 1.531 |
| summarize_hop2 | 1.373 | 1.280 | 1.795 |
| answer | 1.025 | 0.917 | 1.420 |
| **Total** | **5.332** | **4.861** | **8.538** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 79 |
