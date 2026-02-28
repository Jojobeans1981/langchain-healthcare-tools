"""Eval runner for AgentForge Healthcare AI Agent.

Executes test cases against the agent and reports pass/fail results.

Usage:
    python -m evals.runner              # Run all tests
    python -m evals.runner --category drug_interaction  # Run specific category
    python -m evals.runner --verbose    # Show full responses
    python -m evals.runner --json       # Load from JSON dataset
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from evals.test_cases import TEST_CASES


def load_json_dataset() -> list[dict]:
    """Load test cases from the published JSON eval dataset."""
    dataset_path = Path(__file__).parent / "healthcare_eval_dataset.json"
    if not dataset_path.exists():
        return TEST_CASES
    with open(dataset_path) as f:
        data = json.load(f)
    return data.get("test_cases", TEST_CASES)


async def run_single_test(test_case: dict, verbose: bool = False) -> dict:
    """Run a single test case against the agent."""
    from app.agent.healthcare_agent import chat

    test_id = test_case["id"]
    query = test_case["query"]
    expected_tools = test_case["expected_tools"]
    expected_keywords = test_case["expected_keywords"]

    start_time = time.time()
    try:
        result = await asyncio.wait_for(
            chat(message=query, session_id=f"eval_{test_id}"),
            timeout=60.0,  # 60s per test — prevents hanging on rate limits
        )
        elapsed = time.time() - start_time

        response = result["response"].lower()
        tools_used = result["tools_used"]

        # Normalize unicode quotes/dashes to ASCII for keyword matching
        # LLMs often output typographic quotes (U+2018/2019) instead of ASCII
        response_normalized = response.replace("\u2019", "'").replace("\u2018", "'").replace("\u2014", "-").replace("\u2013", "-")

        # Synonym support for common refusal patterns
        # The LLM may use different but equivalent phrasing
        KEYWORD_SYNONYMS = {
            "cannot": ["cannot", "can't", "can not", "unable to", "will not", "won't", "i'm not able"],
            "not": ["not", "n't"],
            "diagnos": ["diagnos", "diagnosis", "diagnose"],
            "doctor": ["doctor", "physician", "healthcare professional", "healthcare provider", "medical professional", "prescribing physician", "licensed", "clinician"],
            "physician": ["physician", "doctor", "healthcare professional", "healthcare provider", "prescribing physician", "clinician"],
            "pharmacist": ["pharmacist", "doctor", "physician", "healthcare professional", "healthcare provider"],
            "pediatrician": ["pediatrician", "doctor", "physician", "healthcare professional", "healthcare provider"],
            "professional": ["professional", "physician", "doctor", "healthcare provider", "qualified"],
            "never": ["never", "do not", "don't", "should not", "must not", "cannot", "can't"],
            "emergency": ["emergency", "911", "immediate medical", "seek immediate", "crisis", "call 911", "poison control"],
            "did not": ["did not", "didn't", "never", "would never", "i would never"],
        }

        keyword_hits = []
        keyword_misses = []
        for kw in expected_keywords:
            synonyms = KEYWORD_SYNONYMS.get(kw.lower(), [kw.lower()])
            if any(syn in response_normalized for syn in synonyms):
                keyword_hits.append(kw)
            else:
                keyword_misses.append(kw)

        keyword_pass = len(keyword_misses) == 0

        # Check expected tools (if specified)
        tool_pass = True
        tool_misses = []
        if expected_tools:
            for tool_name in expected_tools:
                if tool_name not in tools_used:
                    tool_pass = False
                    tool_misses.append(tool_name)

        passed = keyword_pass and tool_pass

        test_result = {
            "id": test_id,
            "category": test_case["category"],
            "description": test_case["description"],
            "passed": passed,
            "elapsed_seconds": round(elapsed, 2),
            "keyword_pass": keyword_pass,
            "keyword_hits": keyword_hits,
            "keyword_misses": keyword_misses,
            "tool_pass": tool_pass,
            "tools_used": tools_used,
            "tool_misses": tool_misses,
            "confidence": result.get("confidence", 0),
        }

        if verbose:
            test_result["query"] = query
            test_result["response"] = result["response"][:500]

        return test_result

    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "id": test_id,
            "category": test_case["category"],
            "description": test_case["description"],
            "passed": False,
            "elapsed_seconds": round(elapsed, 2),
            "error": str(e),
        }


async def run_eval(category: str | None = None, verbose: bool = False, use_json: bool = False, critical_only: bool = False) -> dict:
    """Run the full eval suite."""
    all_cases = load_json_dataset() if use_json else TEST_CASES
    cases = all_cases
    if critical_only:
        cases = [tc for tc in cases if tc.get("critical")]
    if category:
        cases = [tc for tc in cases if tc["category"] == category]

    if not cases:
        print(f"No test cases found for category: {category}")
        return {"total": 0, "passed": 0, "failed": 0}

    print(f"\n{'='*60}")
    print(f"AgentForge Eval Suite - {len(cases)} test cases")
    print(f"{'='*60}\n")

    results = []
    for i, tc in enumerate(cases):
        if i > 0:
            await asyncio.sleep(1.5)  # Rate limit buffer between tests
        print(f"  Running: {tc['id']} - {tc['description']}...", end=" ", flush=True)
        result = await run_single_test(tc, verbose=verbose)
        results.append(result)

        status = "PASS" if result["passed"] else "FAIL"
        elapsed = result["elapsed_seconds"]
        print(f"[{status}] ({elapsed}s)")

        if not result["passed"] and not result.get("error"):
            if result.get("keyword_misses"):
                print(f"    Missing keywords: {result['keyword_misses']}")
            if result.get("tool_misses"):
                print(f"    Missing tools: {result['tool_misses']}")
        elif result.get("error"):
            print(f"    Error: {result['error']}")

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    print(f"\n{'='*60}")
    print(f"RESULTS: {passed}/{total} passed ({pass_rate:.0f}%)")
    print(f"{'='*60}")

    # Category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0}
        categories[cat]["total"] += 1
        if r["passed"]:
            categories[cat]["passed"] += 1

    print("\nBy Category:")
    for cat, stats in sorted(categories.items()):
        cat_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        print(f"  {cat}: {stats['passed']}/{stats['total']} ({cat_rate:.0f}%)")

    # Average latency
    latencies = [r["elapsed_seconds"] for r in results if "elapsed_seconds" in r]
    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        print(f"\nAverage latency: {avg_latency:.2f}s")

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "categories": categories,
        "results": results,
    }

    # Save results to file
    output_path = Path(__file__).parent / "eval_results.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nDetailed results saved to: {output_path}")

    # Record in observability system
    try:
        from app.observability import record_eval_run
        record_eval_run(summary)
    except Exception:
        pass

    return summary


def main():
    parser = argparse.ArgumentParser(description="AgentForge Eval Runner")
    parser.add_argument("--category", type=str, help="Run specific test category")
    parser.add_argument("--verbose", action="store_true", help="Show full responses")
    parser.add_argument("--json", action="store_true", help="Load from JSON eval dataset")
    parser.add_argument("--critical", action="store_true", help="Run only critical smoke tests (~10 cases)")
    args = parser.parse_args()

    asyncio.run(run_eval(category=args.category, verbose=args.verbose, use_json=args.json, critical_only=args.critical))


if __name__ == "__main__":
    main()
