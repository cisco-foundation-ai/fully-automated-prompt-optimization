# Evaluation Summary

Total cases: 150

## Composite Score
- average: 76.67

## Score Breakdown
- exact_match: 76.67
- f1: 82.18

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.112 | 0.002 | 0.067 |
| summarize_hop1 | 1.623 | 1.368 | 2.154 |
| query_hop2 | 0.983 | 0.954 | 1.306 |
| retrieve_hop2 | 0.457 | 0.002 | 1.548 |
| summarize_hop2 | 1.260 | 1.198 | 1.829 |
| answer | 0.894 | 0.849 | 1.228 |
| **Total** | **5.329** | **4.614** | **8.064** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 35 |
