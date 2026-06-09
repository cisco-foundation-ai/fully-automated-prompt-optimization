# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.67

## Score Breakdown
- exact_match: 74.67
- f1: 81.71

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.060 | 0.002 | 0.055 |
| summarize_hop1 | 1.519 | 1.328 | 2.151 |
| query_hop2 | 1.204 | 1.087 | 1.707 |
| retrieve_hop2 | 0.537 | 0.002 | 1.572 |
| summarize_hop2 | 1.407 | 1.300 | 2.097 |
| answer | 1.141 | 0.985 | 1.744 |
| **Total** | **5.869** | **5.148** | **10.005** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 38 |
