# Evaluation Summary

Total cases: 300

## Composite Score
- average: 62.67

## Score Breakdown
- exact_match: 62.67
- f1: 71.14

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 2.786 | 2.551 | 4.919 |
| query_hop2 | 1.874 | 1.708 | 3.141 |
| retrieve_hop2 | 1.006 | 0.581 | 1.712 |
| summarize_hop2 | 2.376 | 2.190 | 3.653 |
| answer | 1.417 | 1.280 | 2.298 |
| **Total** | **9.462** | **8.979** | **13.672** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 112 |
