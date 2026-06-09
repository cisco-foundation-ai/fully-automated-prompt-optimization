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
| retrieve_hop1 | 0.071 | 0.002 | 0.105 |
| summarize_hop1 | 1.426 | 1.317 | 2.298 |
| query_hop2 | 1.259 | 1.104 | 2.192 |
| retrieve_hop2 | 0.818 | 0.003 | 1.589 |
| summarize_hop2 | 1.671 | 1.574 | 2.420 |
| answer | 0.802 | 0.752 | 1.165 |
| **Total** | **6.047** | **5.388** | **9.007** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
| query_hop2 | 1 |
