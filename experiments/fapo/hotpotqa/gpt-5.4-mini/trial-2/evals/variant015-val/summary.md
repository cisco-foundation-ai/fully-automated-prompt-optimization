# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 75.54

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.027 | 0.002 | 0.007 |
| summarize_hop1 | 2.120 | 2.015 | 3.074 |
| query_hop2 | 1.165 | 1.086 | 1.594 |
| retrieve_hop2 | 0.491 | 0.002 | 1.592 |
| summarize_hop2 | 1.531 | 1.480 | 2.121 |
| answer | 0.816 | 0.785 | 1.283 |
| **Total** | **6.151** | **5.756** | **8.817** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
