# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 78.75

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.005 | 0.002 | 0.009 |
| summarize_hop1 | 3.354 | 2.963 | 6.339 |
| query_hop2 | 1.989 | 1.875 | 3.343 |
| retrieve_hop2 | 0.836 | 0.088 | 1.706 |
| summarize_hop2 | 3.742 | 3.296 | 7.831 |
| answer | 1.647 | 1.541 | 2.548 |
| **Total** | **11.573** | **10.658** | **20.663** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
