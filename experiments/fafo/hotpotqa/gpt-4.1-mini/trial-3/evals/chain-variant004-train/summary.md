# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.67

## Score Breakdown
- exact_match: 70.67
- f1: 75.97

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.023 |
| summarize_hop1 | 5.552 | 3.601 | 7.651 |
| query_hop2 | 1.769 | 1.601 | 2.934 |
| retrieve_hop2 | 0.987 | 0.433 | 1.770 |
| summarize_hop2 | 2.681 | 2.314 | 5.121 |
| answer | 1.315 | 1.112 | 2.198 |
| **Total** | **12.343** | **10.019** | **18.057** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 44 |
