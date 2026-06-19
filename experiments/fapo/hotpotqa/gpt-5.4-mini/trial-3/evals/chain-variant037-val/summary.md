# Evaluation Summary

Total cases: 300

## Composite Score
- average: 73.67

## Score Breakdown
- exact_match: 73.67
- f1: 79.00

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.057 | 0.002 | 0.012 |
| summarize_hop1 | 1.311 | 1.227 | 1.908 |
| query_hop2 | 1.077 | 0.983 | 1.488 |
| retrieve_hop2 | 0.278 | 0.002 | 1.524 |
| summarize_hop2 | 1.321 | 1.274 | 1.787 |
| answer | 0.941 | 0.900 | 1.313 |
| **Total** | **4.985** | **4.563** | **6.925** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 79 |
