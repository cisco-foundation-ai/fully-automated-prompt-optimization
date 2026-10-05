# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 76.59

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.159 | 0.002 | 0.133 |
| summarize_hop1 | 1.292 | 1.147 | 1.974 |
| query_hop2 | 1.274 | 1.059 | 1.917 |
| retrieve_hop2 | 0.370 | 0.002 | 1.641 |
| summarize_hop2 | 1.832 | 1.497 | 2.435 |
| answer | 0.880 | 0.770 | 1.524 |
| **Total** | **5.808** | **4.930** | **12.470** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 94 |
