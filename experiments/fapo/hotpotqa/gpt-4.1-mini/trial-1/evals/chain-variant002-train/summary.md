# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.00

## Score Breakdown
- exact_match: 72.00
- f1: 79.20

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.017 | 0.002 | 0.009 |
| summarize_hop1 | 2.871 | 2.670 | 4.897 |
| query_hop2 | 1.684 | 1.638 | 2.369 |
| retrieve_hop2 | 1.210 | 0.639 | 1.763 |
| summarize_hop2 | 2.368 | 2.264 | 3.604 |
| answer | 1.307 | 1.216 | 2.183 |
| **Total** | **9.458** | **8.713** | **14.434** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 42 |
