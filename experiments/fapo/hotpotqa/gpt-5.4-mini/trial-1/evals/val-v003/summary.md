# Evaluation Summary

Total cases: 300

## Composite Score
- average: 64.67

## Score Breakdown
- exact_match: 64.67
- f1: 72.01

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.099 | 0.002 | 0.119 |
| summarize_hop1 | 1.199 | 1.093 | 1.857 |
| query_hop2 | 1.083 | 0.927 | 1.763 |
| retrieve_hop2 | 0.770 | 0.002 | 1.676 |
| summarize_hop2 | 1.114 | 1.060 | 1.595 |
| answer | 0.926 | 0.836 | 1.286 |
| **Total** | **5.190** | **4.390** | **8.965** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 106 |
