# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.67

## Score Breakdown
- exact_match: 65.67
- f1: 72.55

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.002 | 0.008 |
| summarize_hop1 | 2.319 | 2.208 | 3.604 |
| query_hop2 | 1.175 | 1.095 | 1.700 |
| retrieve_hop2 | 0.352 | 0.002 | 1.596 |
| summarize_hop2 | 1.198 | 1.122 | 1.752 |
| answer | 0.858 | 0.809 | 1.355 |
| **Total** | **5.944** | **5.626** | **8.516** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 103 |
