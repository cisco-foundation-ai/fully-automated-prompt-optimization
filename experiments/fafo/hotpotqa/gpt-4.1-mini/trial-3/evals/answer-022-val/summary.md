# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 78.31

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.007 |
| summarize_hop1 | 5.744 | 5.144 | 11.217 |
| query_hop2 | 2.352 | 2.122 | 3.873 |
| retrieve_hop2 | 0.553 | 0.002 | 1.573 |
| summarize_hop2 | 4.201 | 3.776 | 7.183 |
| answer | 1.608 | 1.406 | 2.584 |
| **Total** | **14.474** | **13.913** | **22.754** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
