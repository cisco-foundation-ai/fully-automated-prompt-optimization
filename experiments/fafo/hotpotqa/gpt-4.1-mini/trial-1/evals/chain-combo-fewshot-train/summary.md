# Evaluation Summary

Total cases: 150

## Composite Score
- average: 71.33

## Score Breakdown
- exact_match: 71.33
- f1: 78.48

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.049 | 0.002 | 0.057 |
| summarize_hop1 | 3.744 | 3.113 | 7.370 |
| query_hop2 | 1.991 | 1.837 | 3.229 |
| retrieve_hop2 | 0.970 | 0.950 | 1.640 |
| summarize_hop2 | 2.971 | 2.748 | 4.627 |
| answer | 1.666 | 1.514 | 2.862 |
| **Total** | **11.392** | **10.307** | **18.127** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 43 |
