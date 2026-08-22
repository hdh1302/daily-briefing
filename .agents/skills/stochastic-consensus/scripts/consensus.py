"""
Script helper cho Custom Skill stochastic-consensus trong Antigravity.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Thêm root vào sys.path để có thể tái sử dụng stochastic_consensus.py
root_path = Path(__file__).resolve().parents[3]
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

from stochastic_consensus import run_consensus, ConsensusReport

if __name__ == "__main__":
    if len(sys.argv) > 1:
        problem = " ".join(sys.argv[1:])
    else:
        problem = "Should we adopt Rust or Go for our high-throughput backend service?"

    print(f"Running consensus for: {problem}")
    report = run_consensus(problem, n_agents=5)
    print(report.report_markdown)
