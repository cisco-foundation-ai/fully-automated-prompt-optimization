# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.64

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.041 | 0.002 | 0.010 |
| summarize_hop1 | 2.520 | 2.369 | 3.901 |
| query_hop2 | 1.268 | 1.144 | 1.979 |
| retrieve_hop2 | 0.411 | 0.002 | 1.595 |
| summarize_hop2 | 2.447 | 1.821 | 2.917 |
| answer | 0.838 | 0.794 | 1.234 |
| **Total** | **7.525** | **6.595** | **9.606** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
