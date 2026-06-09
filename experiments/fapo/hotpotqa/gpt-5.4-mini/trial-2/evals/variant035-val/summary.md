# Evaluation Summary

Total cases: 300

## Composite Score
- average: 66.33

## Score Breakdown
- exact_match: 66.33
- f1: 74.45

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.032 | 0.002 | 0.009 |
| summarize_hop1 | 2.600 | 2.277 | 4.480 |
| query_hop2 | 1.495 | 1.175 | 2.596 |
| retrieve_hop2 | 0.319 | 0.002 | 1.581 |
| summarize_hop2 | 1.862 | 1.571 | 3.148 |
| answer | 1.271 | 1.062 | 2.650 |
| **Total** | **7.580** | **6.729** | **12.492** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 101 |
