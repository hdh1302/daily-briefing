"""
Stochastic Multi-Agent Consensus
=================================

Spawns N independent parallel agents (same prompt, no shared context) to
answer the same question, then aggregates their answers into a consensus
report: the dominant answer (mode), genuine divergences, rare-but-interesting
outliers, and a confidence signal based on agreement rate.

Requires:
    pip install anthropic

Usage:
    export ANTHROPIC_API_KEY=sk-...
    python stochastic_consensus.py

Or import and call `run_consensus(...)` directly from your own code.
"""

from __future__ import annotations

import os
import concurrent.futures
from dataclasses import dataclass, field
from typing import List

import anthropic


MODEL = "claude-sonnet-4-6"

AGENT_SYSTEM_PROMPT = """You are one independent analyst among several being \
asked to solve the same problem separately. You cannot see any other \
analyst's answer, and none of them can see yours.

Think through the problem briefly, then commit to ONE clear, concrete \
recommendation. Do not hedge with "it depends" unless the problem is \
genuinely underspecified. End your response with a single line starting \
exactly with:

FINAL ANSWER: <your concise recommendation in one sentence>
"""

AGGREGATOR_SYSTEM_PROMPT = """You are aggregating the independent answers of \
several analysts who each answered the same question without seeing each \
other's work. Produce a structured consensus report.

Cluster semantically equivalent answers together before counting — different \
phrasing of the same idea is ONE consensus point, not several. Then output \
exactly this markdown structure:

## Consensus
(The dominant answer / cluster, with the agreement count out of total \
agents, and a short synthesis of the shared reasoning behind it.)

## Divergences
(Genuine points of disagreement — a real judgment call, not just wording \
differences. Say which position how many agents took, and what the actual \
disagreement is about.)

## Outliers
(Ideas raised by only one or two agents that are creative or worth a second \
look, even without consensus. Skip this section if there are none worth \
noting.)

## Confidence
(High / Medium / Low, with the agreement fraction and a one-line rationale \
for why that level of confidence is warranted.)
"""


@dataclass
class AgentResult:
    index: int
    full_response: str
    final_answer: str = ""


@dataclass
class ConsensusReport:
    problem: str
    n_agents: int
    agent_results: List[AgentResult] = field(default_factory=list)
    report_markdown: str = ""


def _extract_final_answer(text: str) -> str:
    """Pull out the 'FINAL ANSWER:' line, falling back to the last line."""
    for line in text.splitlines():
        if line.strip().upper().startswith("FINAL ANSWER:"):
            return line.split(":", 1)[1].strip()
    # Fallback: last non-empty line
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[-1] if lines else ""


def _run_single_agent(client: anthropic.Anthropic, problem: str, index: int) -> AgentResult:
    """Run one independent agent against the frozen problem statement."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=AGENT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": problem}],
    )
    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )
    return AgentResult(
        index=index,
        full_response=text,
        final_answer=_extract_final_answer(text),
    )


def _aggregate(client: anthropic.Anthropic, problem: str, results: List[AgentResult]) -> str:
    """Send all independent answers to an aggregator call to build the report."""
    joined = "\n\n".join(
        f"--- Agent {r.index + 1} ---\n{r.full_response}" for r in results
    )
    prompt = (
        f"Original problem given identically to every agent:\n{problem}\n\n"
        f"Independent agent responses ({len(results)} total):\n\n{joined}"
    )
    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=AGGREGATOR_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    )


def run_consensus(problem: str, n_agents: int = 10, max_workers: int = 10) -> ConsensusReport:
    """
    Run the full stochastic multi-agent consensus pipeline.

    Args:
        problem: The frozen, self-contained problem statement. Every agent
            receives this exact text — no agent gets extra or different
            context than any other.
        n_agents: How many independent agents to spawn. Default 10.
            Use 5 for lower-stakes calls, 15-20 for high-stakes/ambiguous
            ones. Never go below 3.
        max_workers: Max parallel API calls in flight at once.

    Returns:
        ConsensusReport with all raw agent outputs plus the aggregated
        markdown report.
    """
    if n_agents < 3:
        raise ValueError("n_agents must be >= 3 to distinguish consensus from coincidence")

    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    results: List[AgentResult] = [None] * n_agents  # type: ignore
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_run_single_agent, client, problem, i): i
            for i in range(n_agents)
        }
        for future in concurrent.futures.as_completed(futures):
            i = futures[future]
            results[i] = future.result()

    report_markdown = _aggregate(client, problem, results)

    return ConsensusReport(
        problem=problem,
        n_agents=n_agents,
        agent_results=results,
        report_markdown=report_markdown,
    )


if __name__ == "__main__":
    example_problem = (
        "Should we use a monorepo or separate repos for a 3-service startup "
        "(web frontend, API backend, background worker) with a 4-person "
        "engineering team? Give one clear recommendation."
    )

    report = run_consensus(example_problem, n_agents=10)

    print(f"\n=== {report.n_agents} independent agents ran on: ===")
    print(report.problem)

    print("\n=== Individual final answers ===")
    for r in report.agent_results:
        print(f"Agent {r.index + 1}: {r.final_answer}")

    print("\n=== Aggregated Consensus Report ===\n")
    print(report.report_markdown)