# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.13

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.035 | 0.002 | 0.007 |
| summarize_hop1 | 2.420 | 2.221 | 3.628 |
| query_hop2 | 1.290 | 1.174 | 2.081 |
| retrieve_hop2 | 0.239 | 0.002 | 1.294 |
| summarize_hop2 | 1.836 | 1.509 | 2.941 |
| answer | 1.046 | 0.865 | 1.524 |
| **Total** | **6.865** | **6.110** | **10.464** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
