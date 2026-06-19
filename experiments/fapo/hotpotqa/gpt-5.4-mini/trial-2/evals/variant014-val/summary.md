# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.67

## Score Breakdown
- exact_match: 69.67
- f1: 76.69

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.035 | 0.002 | 0.009 |
| summarize_hop1 | 2.091 | 1.976 | 2.941 |
| query_hop2 | 1.152 | 1.056 | 1.808 |
| retrieve_hop2 | 0.621 | 0.002 | 1.611 |
| summarize_hop2 | 1.570 | 1.451 | 2.275 |
| answer | 0.858 | 0.798 | 1.272 |
| **Total** | **6.328** | **5.933** | **8.786** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 91 |
