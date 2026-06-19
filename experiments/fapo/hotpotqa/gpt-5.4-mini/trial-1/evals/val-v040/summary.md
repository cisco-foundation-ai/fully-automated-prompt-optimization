# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 77.14

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.130 | 0.002 | 0.105 |
| summarize_hop1 | 1.365 | 1.231 | 2.063 |
| query_hop2 | 1.181 | 1.067 | 2.044 |
| retrieve_hop2 | 0.365 | 0.002 | 1.479 |
| summarize_hop2 | 1.628 | 1.554 | 2.426 |
| answer | 0.818 | 0.744 | 1.358 |
| **Total** | **5.486** | **4.895** | **8.318** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
