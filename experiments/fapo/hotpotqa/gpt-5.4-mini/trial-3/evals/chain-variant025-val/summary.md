# Evaluation Summary

Total cases: 300

## Composite Score
- average: 71.00

## Score Breakdown
- exact_match: 71.00
- f1: 78.77

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.054 | 0.688 | 1.679 |
| summarize_hop1 | 1.350 | 1.277 | 1.991 |
| query_hop2 | 1.108 | 1.027 | 1.632 |
| retrieve_hop2 | 1.382 | 1.521 | 1.635 |
| summarize_hop2 | 1.302 | 1.242 | 1.722 |
| answer | 0.975 | 0.893 | 1.417 |
| **Total** | **7.172** | **6.905** | **9.057** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 87 |
