# Evaluation Summary

Total cases: 300

## Composite Score
- average: 39.67

## Score Breakdown
- exact_match: 39.67
- f1: 45.49

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.090 | 0.692 | 1.728 |
| summarize_hop1 | 0.730 | 0.641 | 1.146 |
| query_hop2 | 1.127 | 1.093 | 1.555 |
| retrieve_hop2 | 1.311 | 1.566 | 1.698 |
| summarize_hop2 | 1.327 | 1.226 | 1.947 |
| answer | 0.942 | 0.831 | 1.253 |
| **Total** | **6.527** | **6.278** | **8.103** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 181 |
