# Evaluation Summary

Total cases: 300

## Composite Score
- average: 72.67

## Score Breakdown
- exact_match: 72.67
- f1: 78.49

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.062 | 0.002 | 0.008 |
| summarize_hop1 | 1.276 | 1.154 | 1.732 |
| query_hop2 | 1.100 | 1.014 | 1.578 |
| retrieve_hop2 | 0.296 | 0.002 | 1.528 |
| summarize_hop2 | 1.338 | 1.215 | 1.852 |
| answer | 1.040 | 0.903 | 1.470 |
| **Total** | **5.112** | **4.478** | **7.693** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 82 |
