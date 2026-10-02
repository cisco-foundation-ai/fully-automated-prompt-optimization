# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 76.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.004 | 0.002 | 0.007 |
| summarize_hop1 | 1.640 | 1.571 | 2.265 |
| query_hop2 | 1.264 | 1.089 | 1.626 |
| retrieve_hop2 | 1.336 | 1.334 | 1.700 |
| summarize_hop2 | 1.358 | 1.292 | 1.817 |
| answer | 0.981 | 0.818 | 1.440 |
| **Total** | **6.582** | **6.152** | **8.836** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
