# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 76.90

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.055 | 0.002 | 0.010 |
| summarize_hop1 | 1.278 | 1.248 | 1.731 |
| query_hop2 | 1.025 | 0.982 | 1.322 |
| retrieve_hop2 | 0.326 | 0.002 | 1.562 |
| summarize_hop2 | 1.318 | 1.238 | 1.733 |
| answer | 1.008 | 0.892 | 1.327 |
| **Total** | **5.010** | **4.596** | **6.548** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
