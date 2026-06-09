# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 77.28

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.018 | 0.002 | 0.018 |
| summarize_hop1 | 3.204 | 2.899 | 5.592 |
| query_hop2 | 2.033 | 1.873 | 3.557 |
| retrieve_hop2 | 1.077 | 0.233 | 1.738 |
| summarize_hop2 | 3.218 | 2.874 | 5.428 |
| answer | 1.676 | 1.498 | 2.837 |
| **Total** | **11.226** | **10.448** | **17.691** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
