# Evaluation Summary

Total cases: 300

## Composite Score
- average: 58.33

## Score Breakdown
- exact_match: 58.33
- f1: 68.29

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.039 | 0.002 | 0.012 |
| summarize_hop1 | 2.153 | 1.875 | 3.820 |
| query_hop2 | 1.042 | 0.986 | 1.557 |
| retrieve_hop2 | 0.408 | 0.003 | 1.597 |
| summarize_hop2 | 3.790 | 3.570 | 7.019 |
| answer | 1.213 | 1.088 | 1.975 |
| **Total** | **8.644** | **8.139** | **13.920** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 125 |
