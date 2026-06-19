# Evaluation Summary

Total cases: 300

## Composite Score
- average: 67.33

## Score Breakdown
- exact_match: 67.33
- f1: 75.35

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.115 | 0.002 | 0.116 |
| summarize_hop1 | 1.392 | 1.286 | 2.077 |
| query_hop2 | 1.146 | 1.048 | 1.925 |
| retrieve_hop2 | 0.509 | 0.002 | 1.578 |
| summarize_hop2 | 1.665 | 1.518 | 2.452 |
| answer | 1.260 | 1.050 | 1.611 |
| **Total** | **6.086** | **5.225** | **10.810** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 98 |
