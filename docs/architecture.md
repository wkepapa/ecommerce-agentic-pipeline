# Architecture

```
User query
   |
[Security screen]  -> strips prompt-injection sentences, logs SECURITY event
   |
Planner  -> structured requirements (LOCKED + hashed) + task plan (DAG)
   |
Router   -> task->agent assignment + dependency layers (stages)
   |
Stage 0 (parallel): Search A | Search B | Search C | Validate(requirements)
   |  ---- Synchronizer barrier + conflict resolution ----
Stage 1: Filter
Stage 2 (parallel): Compare | Validate(filtering)
Stage 3: Rank
Stage 4: Validate(ranking)
   |
Supervisor (monitors every stage, assesses, escalates)
   |
Human approval (approve / reject / re-analyse / view / flag)
   |
Final recommendation + report + trace + metrics + cost
```

Cross-cutting: shared `SharedWorkflowState` (guarded writes), `ToolRegistry` + `ToolAuthorizer`
(least privilege), `Tracer`, `WorkflowLogger`, `MetricsCollector`.

## Least-privilege tables
| Agent | Tools | State keys it may write |
|---|---|---|
| planner | none | requirements, plan |
| router | none | routing |
| search_agent | search_tool | raw_search_results |
| filter_agent | filter_tool | filtered_results, rejected_results |
| comparison_agent | comparison_tool | comparison |
| ranking_agent | ranking_tool | ranking |
| validator_agent | validation_tool | validation |
| supervisor_agent | workflow_control_tool | human_approval, final_recommendation, status |
