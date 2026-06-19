# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- exact_match: 69.00
- f1: 76.48

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.028 | 0.002 | 0.011 |
| summarize_hop1 | 3.915 | 3.455 | 7.273 |
| query_hop2 | 1.958 | 1.611 | 3.579 |
| retrieve_hop2 | 0.226 | 0.002 | 1.277 |
| summarize_hop2 | 3.166 | 2.884 | 5.476 |
| answer | 1.660 | 1.474 | 2.788 |
| **Total** | **10.952** | **10.304** | **15.882** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
