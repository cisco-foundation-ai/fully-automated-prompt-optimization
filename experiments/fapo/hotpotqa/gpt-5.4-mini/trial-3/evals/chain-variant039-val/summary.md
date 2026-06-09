# Evaluation Summary

Total cases: 300

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 76.68

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.071 | 0.002 | 0.015 |
| summarize_hop1 | 1.402 | 1.273 | 2.105 |
| query_hop2 | 1.134 | 1.034 | 1.638 |
| retrieve_hop2 | 0.285 | 0.002 | 1.339 |
| summarize_hop2 | 1.410 | 1.300 | 2.034 |
| answer | 1.084 | 0.952 | 1.746 |
| **Total** | **5.387** | **4.946** | **7.994** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 90 |
