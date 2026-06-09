# Evaluation Summary

Total cases: 150

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 77.92

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.073 | 0.003 | 0.058 |
| summarize_hop1 | 2.286 | 2.189 | 3.462 |
| query_hop2 | 1.246 | 1.161 | 1.852 |
| retrieve_hop2 | 0.473 | 0.002 | 1.616 |
| summarize_hop2 | 1.767 | 1.635 | 2.662 |
| answer | 1.080 | 0.882 | 1.947 |
| **Total** | **6.924** | **6.196** | **10.792** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 41 |
