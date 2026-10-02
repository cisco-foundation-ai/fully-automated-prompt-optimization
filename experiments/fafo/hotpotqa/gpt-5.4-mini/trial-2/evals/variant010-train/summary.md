# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 77.65

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.008 |
| summarize_hop1 | 2.120 | 2.038 | 3.242 |
| query_hop2 | 1.235 | 1.163 | 1.796 |
| retrieve_hop2 | 1.137 | 0.618 | 1.714 |
| summarize_hop2 | 1.639 | 1.579 | 2.356 |
| answer | 0.842 | 0.790 | 1.236 |
| **Total** | **6.988** | **6.601** | **8.830** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
