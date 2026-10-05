# Evaluation Summary

Total cases: 300

## Composite Score
- average: 60.00

## Score Breakdown
- exact_match: 60.00
- f1: 70.05

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.014 | 0.002 | 0.008 |
| summarize_hop1 | 2.015 | 1.853 | 3.316 |
| query_hop2 | 1.080 | 1.047 | 1.498 |
| retrieve_hop2 | 0.817 | 0.009 | 1.663 |
| summarize_hop2 | 3.395 | 3.198 | 5.464 |
| answer | 1.129 | 1.058 | 1.720 |
| **Total** | **8.450** | **8.104** | **12.554** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 120 |
