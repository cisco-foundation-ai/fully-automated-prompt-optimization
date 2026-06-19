# Evaluation Summary

Total cases: 300

## Composite Score
- average: 76.67

## Score Breakdown
- num_found: 2.73
- num_gold: 3.00
- num_missing: 0.27
- partial_recall: 91.11
- recall: 76.67

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.003 | 0.002 | 0.004 |
| summarize_hop1 | 3.554 | 2.928 | 7.734 |
| query_hop2 | 0.406 | 0.315 | 0.980 |
| retrieve_hop2 | 0.709 | 0.005 | 1.611 |
| summarize_hop2 | 6.969 | 6.012 | 10.566 |
| query_hop3 | 0.438 | 0.340 | 1.071 |
| retrieve_hop3 | 1.063 | 1.498 | 1.653 |
| summarize_hop3 | 7.242 | 6.763 | 12.254 |
| query_hop4 | 0.533 | 0.423 | 0.839 |
| retrieve_hop4 | 1.446 | 1.565 | 1.690 |
| query_hop5 | 0.553 | 0.466 | 0.931 |
| retrieve_hop5 | 2.815 | 3.093 | 3.280 |
| combine_retrievals | 0.000 | 0.000 | 0.001 |
| **Total** | **25.733** | **23.968** | **36.306** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| retrieve_hop5 | 70 |
