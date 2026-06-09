# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.04

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.038 | 0.002 | 0.005 |
| summarize_hop1 | 2.330 | 2.204 | 3.641 |
| query_hop2 | 1.202 | 1.127 | 1.625 |
| retrieve_hop2 | 0.373 | 0.002 | 1.636 |
| summarize_hop2 | 1.685 | 1.607 | 2.296 |
| answer | 0.936 | 0.857 | 1.604 |
| **Total** | **6.564** | **6.123** | **9.387** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
