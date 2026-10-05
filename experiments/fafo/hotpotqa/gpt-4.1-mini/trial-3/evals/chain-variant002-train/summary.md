# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 76.77

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.033 | 0.002 | 0.023 |
| summarize_hop1 | 4.312 | 3.821 | 7.614 |
| query_hop2 | 1.865 | 1.764 | 3.041 |
| retrieve_hop2 | 0.740 | 0.084 | 1.734 |
| summarize_hop2 | 2.932 | 2.684 | 4.534 |
| answer | 1.359 | 1.205 | 2.328 |
| **Total** | **11.241** | **10.430** | **16.412** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
