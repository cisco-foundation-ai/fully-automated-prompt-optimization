# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 78.87

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.009 |
| summarize_hop1 | 1.402 | 1.277 | 2.253 |
| query_hop2 | 1.113 | 1.033 | 1.660 |
| retrieve_hop2 | 0.317 | 0.002 | 1.364 |
| summarize_hop2 | 1.351 | 1.277 | 1.762 |
| answer | 0.934 | 0.862 | 1.286 |
| **Total** | **5.150** | **4.669** | **7.587** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 84 |
