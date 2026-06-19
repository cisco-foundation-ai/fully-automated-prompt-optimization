# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 72.52

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.009 |
| summarize_hop1 | 2.281 | 2.125 | 3.757 |
| query_hop2 | 1.047 | 1.002 | 1.457 |
| retrieve_hop2 | 0.668 | 0.008 | 1.628 |
| summarize_hop2 | 3.755 | 3.537 | 6.439 |
| answer | 1.118 | 1.085 | 1.717 |
| **Total** | **8.906** | **8.715** | **12.877** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 112 |
