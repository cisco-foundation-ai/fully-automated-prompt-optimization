# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.67

## Score Breakdown
- num_found: 2.75
- num_gold: 3.00
- num_missing: 0.25
- partial_recall: 91.56
- recall: 76.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.005 |
| summarize_hop1 | 3.852 | 3.236 | 8.011 |
| query_hop2 | 0.375 | 0.314 | 0.571 |
| retrieve_hop2 | 0.398 | 0.002 | 1.501 |
| summarize_hop2 | 6.267 | 5.922 | 9.317 |
| query_hop3 | 1.404 | 0.331 | 0.508 |
| retrieve_hop3 | 0.901 | 1.105 | 1.537 |
| summarize_hop3 | 7.199 | 6.652 | 13.455 |
| query_hop4 | 0.466 | 0.417 | 0.710 |
| retrieve_hop4 | 1.253 | 1.295 | 1.557 |
| query_hop5 | 0.428 | 0.377 | 0.734 |
| retrieve_hop5 | 1.276 | 1.307 | 1.584 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **23.822** | **22.032** | **32.325** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 70 |
