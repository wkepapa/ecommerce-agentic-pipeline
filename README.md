# Lab 5 – Multi-Agent E-Commerce Product Analysis & Recommendation Pipeline

Pure-Python (stdlib only, Python 3.9+) implementation of the Experiment 5 case study.

## Run
```bash
python main.py                                   # interactive human approval
python main.py --approval auto                   # unattended
python main.py --mode sequential                 # baseline execution
python main.py --inject-failure source_b:1       # one transient failure -> retry demo
python main.py --query "Find laptops under 60k with 16 GB RAM and 512 GB SSD, rating above 4.3"
python experiments/run_experiment.py             # full experiment + observation table
python -m unittest discover -s tests -t . -v     # all tests
```
Reports, traces and logs are written to `outputs/`.

## Requirement -> where it is implemented
| Lab requirement | File(s) |
|---|---|
| Query decomposition (Planner) | `agents/planner_agent.py`, `agents/query_parser.py` |
| Routing (dependency-aware) | `agents/router_agent.py` |
| Search / Filter / Comparison / Ranking | `agents/*_agent.py` + `mcp_layer/tools/*_tool.py` |
| Validator (checkpoint validation) | `agents/validator_agent.py`, `mcp_layer/tools/validation_tool.py` |
| Supervisor | `agents/supervisor_agent.py` |
| Shared workflow state | `core/state.py` |
| Inter-agent communication | `core/messages.py` (stored in `state.messages`) |
| Sequential + parallel execution | `orchestration/executor.py`, `orchestration/workflow.py` |
| Synchronization | `orchestration/synchronizer.py` |
| Conflict resolution | `orchestration/conflict_resolver.py` |
| Human-in-the-loop | `orchestration/human_approval.py` |
| Failure handling + controlled retry | `core/retry.py`, `agents/base_agent.py`, `core/exceptions.py` |
| Logging / tracing | `core/logger.py`, `core/tracer.py` |
| Performance + cost | `core/metrics.py` |
| MCP-style registry / authorization / execution | `mcp_layer/` |
| Security validation | `security/` |
| Observation table, report | `experiments/` |

> The MCP-style layer is a simplified teaching model, not the full MCP protocol.

## Notes / assumptions
- Rating rule is `>=` (matches the Filter Agent spec); out-of-stock products are filtered (`REQUIRE_IN_STOCK` in `config/settings.py`).
- Product data is three simulated JSON sources with deliberate conflicts, a missing rating, an out-of-stock item and over-budget items.
- The sanitizer drops whole sentences that look like injections; the Validator and the locked requirements are the second line of defence.

## Streamlit Web App

Install dependencies:
```bash
pip install -r requirements.txt
```

Run locally from the project root:
```bash
streamlit run streamlit_app/app.py
```

The dashboard contains:
- Recommendation page with query, execution mode and human approval control
- Agent workflow graph and detailed execution trace
- Validation checkpoints
- Security test suite and pass-rate display
- Evaluation metrics and cost/performance information
- Experiment table for sequential, parallel, retry and security runs

## Security experiment

The security suite contains 10 tests. Eight are expected to pass and two are deliberately hard adversarial cases that expose current design limitations:

1. Semantic budget-bypass wording is not recognized by the regex-only sanitizer.
2. The current `COMMON_KEYS` policy allows a legitimate agent role to write to the shared `messages` key.

The current measured result is **8/10 = 80%**. These are documented limitations, not artificially injected random failures.

## Streamlit Community Cloud deployment

1. Push the complete `ecommerce_agentic_pipeline` folder to a GitHub repository.
2. Open Streamlit Community Cloud and create a new app.
3. Select the GitHub repository and branch.
4. Set the main file to:
   `streamlit_app/app.py`
5. Deploy the app.
6. Streamlit installs packages from `requirements.txt`.
7. If you later add an API key, store it in Streamlit Secrets rather than committing it to GitHub.
