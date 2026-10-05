# Evaluation Summary

Total cases: 150

## Composite Score
- average: 74.00

## Score Breakdown
- exact_match: 74.00
- f1: 79.35

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.157 | 0.002 | 2.183 |
| summarize_hop1 | 1.504 | 1.421 | 2.024 |
| query_hop2 | 1.036 | 0.962 | 1.569 |
| retrieve_hop2 | 0.468 | 0.002 | 1.620 |
| summarize_hop2 | 1.242 | 1.184 | 1.783 |
| answer | 0.911 | 0.853 | 1.250 |
| **Total** | **5.318** | **4.724** | **8.146** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 39 |
