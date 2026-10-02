# Evaluation Summary

Total cases: 150

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.62

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.010 |
| summarize_hop1 | 1.627 | 1.437 | 2.728 |
| query_hop2 | 1.142 | 1.028 | 1.830 |
| retrieve_hop2 | 1.446 | 1.512 | 1.732 |
| summarize_hop2 | 1.111 | 1.036 | 1.653 |
| answer | 0.795 | 0.767 | 1.138 |
| **Total** | **6.138** | **5.696** | **10.245** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 47 |
