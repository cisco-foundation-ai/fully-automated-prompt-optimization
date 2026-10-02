# Evaluation Summary

Total cases: 300

## Composite Score
- average: 57.00

## Score Breakdown
- exact_match: 57.00
- f1: 66.21

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.009 | 0.002 | 0.009 |
| summarize_hop1 | 2.225 | 2.023 | 3.593 |
| query_hop2 | 1.038 | 0.968 | 1.479 |
| retrieve_hop2 | 1.474 | 1.306 | 1.572 |
| summarize_hop2 | 3.881 | 3.665 | 6.618 |
| answer | 1.129 | 1.010 | 2.016 |
| **Total** | **9.755** | **9.422** | **13.739** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 129 |
