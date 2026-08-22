---
name: stochastic-consensus
description: >-
  Spawns N independent parallel Gemini agents to solve the same complex question or architectural decision without shared context, then aggregates their independent answers into a structured consensus report (Consensus, Divergences, Outliers, Confidence). Use this skill whenever facing high-stakes decisions, ambiguous technical trade-offs, or when multiple diverse AI perspectives are needed.
---

# Stochastic Multi-Agent Consensus Skill

This skill allows the agent to run a multi-agent consensus pipeline using Google Gemini to resolve complex, underspecified, or high-stakes problems.

## When to Use
- High-stakes architectural choices (e.g. monorepo vs microservices, choosing tech stack).
- Tough debugging or root-cause hypotheses where multiple independent angles prevent anchoring bias.
- Evaluating trade-offs where a single agent might produce an idiosyncratic answer.

## How It Works
1. **Parallel Execution**: Spawns $N$ independent agent calls with the exact same frozen problem statement.
2. **Strict Answer Commitment**: Each agent must commit to a single concrete `FINAL ANSWER:` without hedging.
3. **Semantic Aggregation**: An aggregator model clusters equivalent answers, extracts genuine divergences, notes valuable outliers, and outputs a confidence score based on agreement rate.

## Quick CLI Usage

```bash
# Run consensus with default 5 agents
python stochastic_consensus.py

# Or import in Python:
from stochastic_consensus import run_consensus

report = run_consensus(
    problem="Should we use PostgreSQL or MongoDB for our analytics time-series data?",
    n_agents=5
)
print(report.report_markdown)
```
