# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.66

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.043 | 0.002 | 0.010 |
| summarize_hop1 | 1.612 | 1.537 | 2.260 |
| query_hop2 | 1.230 | 1.118 | 1.620 |
| retrieve_hop2 | 0.978 | 1.272 | 1.659 |
| summarize_hop2 | 1.379 | 1.259 | 1.842 |
| answer | 0.908 | 0.866 | 1.245 |
| **Total** | **6.149** | **5.964** | **7.810** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
