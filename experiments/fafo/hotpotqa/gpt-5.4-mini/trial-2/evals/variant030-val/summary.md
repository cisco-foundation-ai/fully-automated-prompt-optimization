# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.67

## Score Breakdown
- exact_match: 66.67
- f1: 75.18

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.011 |
| summarize_hop1 | 2.413 | 2.285 | 3.712 |
| query_hop2 | 1.251 | 1.136 | 1.795 |
| retrieve_hop2 | 0.400 | 0.002 | 1.616 |
| summarize_hop2 | 1.724 | 1.644 | 2.368 |
| answer | 0.967 | 0.864 | 1.671 |
| **Total** | **6.771** | **6.315** | **9.374** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 100 |
