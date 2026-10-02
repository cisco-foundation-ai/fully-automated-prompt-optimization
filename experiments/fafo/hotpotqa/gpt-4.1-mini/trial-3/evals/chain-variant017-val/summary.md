# Evaluation Summary

Total cases: 300

## Composite Score
- average: 65.33

## Score Breakdown
- exact_match: 65.33
- f1: 74.12

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.003 | 0.006 |
| summarize_hop1 | 3.386 | 2.985 | 6.369 |
| query_hop2 | 1.843 | 1.672 | 3.072 |
| retrieve_hop2 | 0.776 | 0.441 | 1.713 |
| summarize_hop2 | 3.151 | 2.670 | 6.051 |
| answer | 1.311 | 1.201 | 2.172 |
| **Total** | **10.469** | **9.729** | **17.127** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 104 |
