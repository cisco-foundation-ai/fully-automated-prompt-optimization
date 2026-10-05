# Evaluation Summary

Total cases: 300

## Composite Score
- average: 68.67

## Score Breakdown
- exact_match: 68.67
- f1: 75.44

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 0.117 | 0.002 | 0.120 |
| summarize_hop1 | 1.419 | 1.313 | 2.181 |
| query_hop2 | 1.168 | 1.069 | 1.865 |
| retrieve_hop2 | 0.529 | 0.002 | 1.632 |
| summarize_hop2 | 1.680 | 1.559 | 2.649 |
| answer | 0.828 | 0.758 | 1.186 |
| **Total** | **5.742** | **5.173** | **8.322** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 93 |
| query_hop2 | 1 |
