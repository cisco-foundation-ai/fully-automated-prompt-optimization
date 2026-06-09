# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.29

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.136 | 0.002 | 0.894 |
| summarize_hop1 | 1.360 | 1.280 | 2.103 |
| query_hop2 | 1.233 | 1.083 | 1.749 |
| retrieve_hop2 | 0.318 | 0.002 | 1.596 |
| summarize_hop2 | 1.732 | 1.575 | 2.427 |
| answer | 0.826 | 0.780 | 1.202 |
| **Total** | **5.604** | **4.950** | **10.103** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
