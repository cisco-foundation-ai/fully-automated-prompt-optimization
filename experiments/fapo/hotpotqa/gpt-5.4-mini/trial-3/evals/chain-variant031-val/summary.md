# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.00

## Score Breakdown
- exact_match: 73.00
- f1: 79.43

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.037 | 0.002 | 0.010 |
| summarize_hop1 | 1.290 | 1.192 | 1.849 |
| query_hop2 | 1.068 | 1.015 | 1.507 |
| retrieve_hop2 | 0.309 | 0.002 | 1.491 |
| summarize_hop2 | 1.326 | 1.258 | 1.781 |
| answer | 0.944 | 0.910 | 1.292 |
| **Total** | **4.973** | **4.542** | **7.255** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 81 |
