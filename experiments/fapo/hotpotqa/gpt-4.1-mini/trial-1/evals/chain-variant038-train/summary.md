# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 80.50

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.053 | 0.002 | 0.035 |
| summarize_hop1 | 3.057 | 2.684 | 5.985 |
| query_hop2 | 2.008 | 1.736 | 3.541 |
| retrieve_hop2 | 0.401 | 0.002 | 1.604 |
| summarize_hop2 | 2.916 | 2.497 | 5.772 |
| answer | 1.885 | 1.530 | 3.300 |
| **Total** | **10.320** | **9.441** | **16.527** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
