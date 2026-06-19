# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 78.04

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.001 | 0.631 | 1.688 |
| summarize_hop1 | 1.445 | 1.291 | 2.350 |
| query_hop2 | 1.195 | 1.031 | 1.717 |
| retrieve_hop2 | 1.194 | 1.134 | 1.619 |
| summarize_hop2 | 1.350 | 1.272 | 1.742 |
| answer | 0.954 | 0.908 | 1.323 |
| **Total** | **7.140** | **6.662** | **9.786** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 88 |
