# Evaluation Summary

Total cases: 300

## Composite Score
- average: 63.00

## Score Breakdown
- exact_match: 63.00
- f1: 71.29

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.029 | 0.613 | 1.633 |
| summarize_hop1 | 2.396 | 2.122 | 4.191 |
| query_hop2 | 1.113 | 1.028 | 1.563 |
| retrieve_hop2 | 1.153 | 1.317 | 1.584 |
| summarize_hop2 | 2.678 | 2.568 | 4.057 |
| answer | 1.102 | 1.039 | 1.573 |
| **Total** | **9.471** | **9.098** | **13.266** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 111 |
