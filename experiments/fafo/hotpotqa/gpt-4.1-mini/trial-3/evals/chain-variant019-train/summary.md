# Evaluation Summary

Total cases: 150

## Composite Score
- average: 70.00

## Score Breakdown
- exact_match: 70.00
- f1: 76.14

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.050 | 0.002 | 0.034 |
| summarize_hop1 | 2.996 | 2.790 | 5.080 |
| query_hop2 | 1.899 | 1.652 | 3.288 |
| retrieve_hop2 | 0.569 | 0.003 | 1.710 |
| summarize_hop2 | 3.035 | 2.865 | 4.905 |
| answer | 1.255 | 1.153 | 1.906 |
| **Total** | **9.805** | **9.334** | **14.906** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 45 |
