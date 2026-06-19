# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.33

## Score Breakdown
- exact_match: 68.33
- f1: 77.39

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.029 | 0.002 | 0.009 |
| summarize_hop1 | 1.790 | 1.684 | 2.525 |
| query_hop2 | 1.186 | 1.087 | 1.698 |
| retrieve_hop2 | 0.384 | 0.002 | 1.586 |
| summarize_hop2 | 1.786 | 1.571 | 2.307 |
| answer | 0.932 | 0.797 | 1.340 |
| **Total** | **6.107** | **5.474** | **8.755** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 95 |
