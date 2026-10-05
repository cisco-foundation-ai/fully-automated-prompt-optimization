# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 77.59

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.043 | 0.002 | 0.041 |
| summarize_hop1 | 3.243 | 2.710 | 5.426 |
| query_hop2 | 1.617 | 1.435 | 2.877 |
| retrieve_hop2 | 0.766 | 0.004 | 1.631 |
| summarize_hop2 | 2.744 | 2.461 | 4.975 |
| answer | 1.416 | 1.254 | 2.285 |
| **Total** | **9.829** | **9.154** | **15.473** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
