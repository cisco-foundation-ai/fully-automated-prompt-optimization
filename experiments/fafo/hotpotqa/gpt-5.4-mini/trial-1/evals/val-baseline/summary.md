# Evaluation Summary

Total cases: 300

## Composite Score
- average: 43.33

## Score Breakdown
- exact_match: 43.33
- f1: 52.46

## Step Timings

| Step | Avg (s) | P50 (s) | P95 (s) |
|------|---------|---------|---------|
| retrieve_hop1 | 1.264 | 0.946 | 1.746 |
| summarize_hop1 | 1.296 | 1.071 | 1.866 |
| query_hop2 | 1.544 | 1.104 | 2.105 |
| retrieve_hop2 | 1.079 | 1.312 | 1.670 |
| summarize_hop2 | 1.363 | 1.081 | 1.754 |
| answer | 1.153 | 1.015 | 1.647 |
| **Total** | **7.700** | **6.569** | **20.513** |

## Step Attribution

| Step | Failure Count |
|------|--------------|
| answer | 170 |
