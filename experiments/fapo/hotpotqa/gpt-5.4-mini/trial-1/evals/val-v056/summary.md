# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- exact_match: 69.00
- f1: 77.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.100 | 0.002 | 0.112 |
| summarize_hop1 | 1.477 | 1.319 | 2.217 |
| query_hop2 | 1.292 | 1.071 | 2.069 |
| retrieve_hop2 | 0.541 | 0.002 | 1.646 |
| summarize_hop2 | 1.683 | 1.510 | 2.467 |
| answer | 0.854 | 0.760 | 1.147 |
| **Total** | **5.946** | **5.042** | **10.345** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 92 |
| query_hop2 | 1 |
