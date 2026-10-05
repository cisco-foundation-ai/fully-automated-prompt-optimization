# Evaluation Summary

Total cases: 150

## Composite Score
- average: 63.33

## Score Breakdown
- exact_match: 63.33
- f1: 70.51

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.042 | 0.002 | 0.054 |
| summarize_hop1 | 2.339 | 2.158 | 4.082 |
| query_hop2 | 1.266 | 1.208 | 1.795 |
| retrieve_hop2 | 0.855 | 0.003 | 1.700 |
| summarize_hop2 | 2.204 | 2.157 | 3.447 |
| answer | 0.805 | 0.754 | 1.134 |
| **Total** | **7.511** | **6.771** | **11.557** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 55 |
