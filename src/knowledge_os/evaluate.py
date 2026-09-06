import hashlib
import json
from pathlib import Path

from knowledge_os.dependencies import get_graph
from knowledge_os.ids import access_fingerprint
from knowledge_os.models import RetrievalEvaluationSuite


def suite_fingerprint(suite: RetrievalEvaluationSuite) -> str:
    suite_payload = suite.model_dump(mode="json")
    for case in suite_payload["cases"]:
        if not case["excluded_document_ids"]:
            case.pop("excluded_document_ids")
        if not case["expected_no_results"]:
            case.pop("expected_no_results")
    payload = json.dumps(
        suite_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _unique_in_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def run_suite(graph, suite: RetrievalEvaluationSuite) -> dict:
    fingerprint = suite_fingerprint(suite)
    case_results = []
    for case in suite.cases:
        retrieval_request = (
            case.request.model_copy(update={"limit": 100})
            if case.excluded_document_ids
            else case.request
        )
        response = graph.retrieve(retrieval_request)
        raw_results = response["results"]
        excluded = set(case.excluded_document_ids)
        results = [result for result in raw_results if result["document_id"] not in excluded][
            : case.request.limit
        ]
        excluded_result_ids = _unique_in_order(
            [result["document_id"] for result in raw_results if result["document_id"] in excluded]
        )
        if case.expected_no_results:
            expected = set()
            ranked = _unique_in_order([result["document_id"] for result in results])
            target = "result_count"
            matched = set()
            recall = None
            reciprocal_rank = None
            policy_pass = not results
            score = 1.0 if policy_pass else 0.0
        elif case.expected_chunk_ids:
            expected = set(case.expected_chunk_ids)
            ranked = [result["chunk_id"] for result in results]
            target = "chunk_id"
            matched = expected.intersection(ranked)
            recall = len(matched) / len(expected)
            first_rank = next(
                (rank for rank, identifier in enumerate(ranked, start=1) if identifier in expected),
                None,
            )
            reciprocal_rank = 1.0 / first_rank if first_rank else 0.0
            policy_pass = None
            score = recall
        else:
            expected = set(case.expected_document_ids)
            ranked = _unique_in_order([result["document_id"] for result in results])
            target = "document_id"
            matched = expected.intersection(ranked)
            recall = len(matched) / len(expected)
            first_rank = next(
                (rank for rank, identifier in enumerate(ranked, start=1) if identifier in expected),
                None,
            )
            reciprocal_rank = 1.0 / first_rank if first_rank else 0.0
            policy_pass = None
            score = recall
        actual = {
            "target": target,
            "ranked_ids": ranked,
            "matched_ids": sorted(matched),
            "recall_at_k": recall,
            "reciprocal_rank": reciprocal_rank,
            "excluded_document_ids": case.excluded_document_ids,
            "excluded_result_ids": excluded_result_ids,
            "candidate_limit": retrieval_request.limit,
            "policy_pass": policy_pass,
        }
        evaluation_id = graph.ops.record_evaluation(
            case.question or case.request.query,
            {
                "suite_id": suite.suite_id,
                "suite_fingerprint": fingerprint,
                "case_id": case.id,
                "target": target,
                "relevant_ids": sorted(expected),
                "expected_result_count": 0 if case.expected_no_results else None,
                "excluded_document_ids": case.excluded_document_ids,
            },
            actual,
            score,
            suite.evaluator_version,
            response["trace_id"],
            workspace_id=case.request.access.workspace_id,
            access_fingerprint=access_fingerprint(
                case.request.access.workspace_id, case.request.access.principals
            ),
        )
        case_results.append(
            {
                "case_id": case.id,
                "evaluation_id": evaluation_id,
                "trace_id": response["trace_id"],
                **actual,
            }
        )
    quality_cases = [case for case in case_results if case["recall_at_k"] is not None]
    policy_cases = [case for case in case_results if case["policy_pass"] is not None]
    mean_recall = (
        sum(case["recall_at_k"] for case in quality_cases) / len(quality_cases)
        if quality_cases
        else None
    )
    mean_reciprocal_rank = (
        sum(case["reciprocal_rank"] for case in quality_cases) / len(quality_cases)
        if quality_cases
        else None
    )
    policy_pass_rate = (
        sum(case["policy_pass"] for case in policy_cases) / len(policy_cases)
        if policy_cases
        else 1.0
    )
    return {
        "suite_version": suite.suite_version,
        "suite_id": suite.suite_id,
        "suite_fingerprint": fingerprint,
        "evaluator_version": suite.evaluator_version,
        "case_count": len(case_results),
        "minimum_mean_recall": suite.minimum_mean_recall,
        "mean_recall_at_k": mean_recall,
        "mean_reciprocal_rank": mean_reciprocal_rank,
        "policy_case_count": len(policy_cases),
        "policy_pass_rate": policy_pass_rate,
        "passed": (mean_recall is None or mean_recall >= suite.minimum_mean_recall)
        and policy_pass_rate == 1.0,
        "cases": case_results,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Run a versioned local Knowledge OS retrieval evaluation suite"
    )
    parser.add_argument("suite", type=Path, help="Path to a retrieval evaluation suite v1 JSON")
    args = parser.parse_args()
    suite = RetrievalEvaluationSuite.model_validate_json(args.suite.read_text(encoding="utf-8"))
    graph = get_graph()
    try:
        graph.verify()
        report = run_suite(graph, suite)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    finally:
        graph.close()
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
