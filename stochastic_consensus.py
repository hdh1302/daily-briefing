"""
Stochastic Multi-Agent Consensus (Sử dụng Google Gemini)
=========================================================

Chạy song song N agent Gemini độc lập (cùng một câu hỏi, không chia sẻ ngữ cảnh)
để giải quyết vấn đề, sau đó tổng hợp các câu trả lời thành báo cáo đồng thuận:
- Phân tích điểm chung / quan điểm chiếm đa số (Consensus)
- Các điểm bất đồng thực sự (Divergences)
- Những ý tưởng độc đáo / hiếm gặp (Outliers)
- Chỉ số độ tin cậy (Confidence)

Yêu cầu:
    pip install google-genai python-dotenv

Sử dụng:
    export GEMINI_API_KEY=AIzaSy...
    python stochastic_consensus.py
"""

from __future__ import annotations

import concurrent.futures
from dataclasses import dataclass, field
import json
import os
import re
from typing import Any, Dict, List, Optional
import urllib.request

from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# Cấu hình Mô hình & Prompt
# ==============================================================================
DEFAULT_MODEL = "gemini-2.5-flash"

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
    """Trích xuất dòng 'FINAL ANSWER:', nếu không có thì lấy dòng cuối cùng."""
    for line in text.splitlines():
        if line.strip().upper().startswith("FINAL ANSWER:"):
            return line.split(":", 1)[1].strip()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[-1] if lines else ""


def _call_gemini(api_key: str, system_prompt: str, user_prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Gọi Gemini API hỗ trợ cả SDK lẫn REST API fallback."""
    # Cách 1: Thử gọi qua google-genai SDK
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        full_content = f"{system_prompt}\n\nTask:\n{user_prompt}"
        resp = client.models.generate_content(
            model=model,
            contents=full_content
        )
        if resp and resp.text:
            return resp.text
    except Exception:
        pass

    # Cách 2: Gọi qua REST API trực tiếp
    candidate_models = [model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]
    combined_prompt = f"{system_prompt}\n\nTask:\n{user_prompt}"
    payload = json.dumps({
        "contents": [{"parts": [{"text": combined_prompt}]}]
    }).encode("utf-8")

    for m in candidate_models:
        clean_m = m.replace("models/", "")
        for api_ver in ["v1beta", "v1"]:
            url = f"https://generativelanguage.googleapis.com/{api_ver}/models/{clean_m}:generateContent?key={api_key}"
            try:
                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=30) as response:
                    res_json = json.loads(response.read().decode("utf-8"))
                    candidates = res_json.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
            except Exception:
                continue

    raise RuntimeError("Không thể kết nối tới Gemini API. Vui lòng kiểm tra lại GEMINI_API_KEY.")


def _run_single_agent(api_key: str, problem: str, index: int, model: str) -> AgentResult:
    """Chạy 1 agent độc lập với bài toán được giao."""
    try:
        text = _call_gemini(api_key, AGENT_SYSTEM_PROMPT, problem, model=model)
    except Exception as e:
        text = f"Error: {e}"

    return AgentResult(
        index=index,
        full_response=text,
        final_answer=_extract_final_answer(text),
    )


def _aggregate(api_key: str, problem: str, results: List[AgentResult], model: str) -> str:
    """Gửi tất cả câu trả lời độc lập tới Aggregator để tổng hợp báo cáo."""
    joined = "\n\n".join(
        f"--- Agent {r.index + 1} ---\n{r.full_response}" for r in results
    )
    prompt = (
        f"Original problem given identically to every agent:\n{problem}\n\n"
        f"Independent agent responses ({len(results)} total):\n\n{joined}"
    )
    return _call_gemini(api_key, AGGREGATOR_SYSTEM_PROMPT, prompt, model=model)


def run_consensus(
    problem: str,
    n_agents: int = 10,
    max_workers: int = 10,
    model: str = DEFAULT_MODEL,
    api_key: Optional[str] = None
) -> ConsensusReport:
    """
    Quy trình chạy Stochastic Multi-Agent Consensus bằng Gemini.

    Args:
        problem: Câu hỏi hoặc bài toán cần phân tích.
        n_agents: Số lượng agent chạy song song (Mặc định: 5).
        max_workers: Số luồng chạy đồng thời.
        model: Model Gemini sử dụng (Mặc định: gemini-2.5-flash).
        api_key: Khóa API Gemini (Nếu None sẽ tự lấy từ biến môi trường GEMINI_API_KEY).

    Returns:
        ConsensusReport chứa kết quả của từng agent và báo cáo tổng hợp.
    """
    if n_agents < 3:
        raise ValueError("n_agents phải >= 3 để tạo sự đồng thuận chính xác.")

    key = (api_key or os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        raise ValueError("Thiếu GEMINI_API_KEY. Vui lòng thiết lập biến môi trường GEMINI_API_KEY.")

    results: List[AgentResult] = [None] * n_agents  # type: ignore
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_run_single_agent, key, problem, i, model): i
            for i in range(n_agents)
        }
        for future in concurrent.futures.as_completed(futures):
            i = futures[future]
            results[i] = future.result()

    report_markdown = _aggregate(key, problem, results, model=model)

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

    print("=== Đang khởi chạy Stochastic Multi-Agent Consensus với Gemini ===")
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[Lưu ý] Chưa thiết lập GEMINI_API_KEY trong .env. Vui lòng thêm GEMINI_API_KEY để chạy thực tế.")
    else:
        try:
            report = run_consensus(example_problem, n_agents=10)
            print(f"\n=== Kết quả từ {report.n_agents} Agents độc lập ===")
            for r in report.agent_results:
                print(f"Agent {r.index + 1}: {r.final_answer}")

            print("\n=== Báo cáo Tổng hợp Đồng thuận (Consensus Report) ===\n")
            print(report.report_markdown)
        except Exception as e:
            print(f"Lỗi: {e}")
