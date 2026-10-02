# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 76.26

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.066 | 0.002 | 0.055 |
| summarize_hop1 | 2.521 | 2.266 | 4.272 |
| query_hop2 | 1.069 | 1.016 | 1.449 |
| retrieve_hop2 | 0.539 | 0.002 | 1.700 |
| summarize_hop2 | 2.187 | 2.095 | 3.143 |
| answer | 0.947 | 0.917 | 1.335 |
| **Total** | **7.327** | **6.946** | **10.982** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
