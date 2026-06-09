# Evaluation Summary

Total cases: 300

## Composite Score
- average: 69.00

## Score Breakdown
- exact_match: 69.00
- f1: 76.25

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.016 | 0.002 | 0.010 |
| summarize_hop1 | 3.724 | 3.245 | 7.302 |
| query_hop2 | 2.130 | 1.802 | 4.422 |
| retrieve_hop2 | 0.307 | 0.002 | 1.580 |
| summarize_hop2 | 3.206 | 2.833 | 5.617 |
| answer | 1.772 | 1.584 | 3.144 |
| **Total** | **11.155** | **10.258** | **17.324** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
