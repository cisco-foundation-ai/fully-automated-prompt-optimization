# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.67

## Score Breakdown
- num_found: 2.70
- num_gold: 3.00
- num_missing: 0.30
- partial_recall: 90.00
- recall: 73.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.996 | 0.563 | 1.618 |
| summarize_hop1 | 3.956 | 3.117 | 8.484 |
| query_hop2 | 0.361 | 0.317 | 0.588 |
| retrieve_hop2 | 0.393 | 0.006 | 1.482 |
| summarize_hop2 | 6.990 | 5.902 | 10.645 |
| query_hop3 | 0.389 | 0.337 | 0.743 |
| retrieve_hop3 | 0.881 | 1.266 | 1.524 |
| summarize_hop3 | 7.729 | 6.681 | 13.562 |
| query_hop4 | 0.502 | 0.434 | 0.957 |
| retrieve_hop4 | 1.304 | 1.422 | 1.565 |
| summarize_hop4 | 8.426 | 6.748 | 14.170 |
| query_hop5 | 0.444 | 0.378 | 0.780 |
| retrieve_hop5 | 1.329 | 1.437 | 1.563 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **33.700** | **30.451** | **48.549** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 79 |
