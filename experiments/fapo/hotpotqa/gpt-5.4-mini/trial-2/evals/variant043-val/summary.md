# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 76.13

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.040 | 0.002 | 0.012 |
| summarize_hop1 | 2.517 | 2.202 | 3.761 |
| query_hop2 | 1.247 | 1.122 | 1.741 |
| retrieve_hop2 | 0.272 | 0.002 | 1.517 |
| summarize_hop2 | 1.780 | 1.534 | 2.786 |
| answer | 0.915 | 0.782 | 1.556 |
| **Total** | **6.771** | **6.015** | **11.190** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 98 |
