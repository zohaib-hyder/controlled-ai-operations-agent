"""Measured authorized retrieval on a version-controlled independent expected-reference set."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import test_agents as agents

from app.agents.contracts import Evidence
from app.db.seed import stable_id
from app.services.evidence import EvidenceRetrievalService
from app.tools.contracts import Invocation

client = agents.client
executor = agents.executor
tool_db = agents.tool_db

ROOT = Path(__file__).resolve().parents[2]


def test_retrieval_evaluation(client, executor):
    cases = json.loads((ROOT / "docs/evaluations/phase5-cases.json").read_text())
    retrieval = EvidenceRetrievalService()
    hits = relevant = returned = policy_correct = policies = citations = unsupported = (
        leakage
    ) = 0
    rows = []
    for tenant in (0, 1):
        actor = agents.identity(client, tenant=tenant)
        for case in [c for c in cases if c["tenant"] == tenant]:
            args = {
                k: str(stable_id(v)) if k.endswith("_id") else v
                for k, v in case["arguments"].items()
            }
            result = asyncio.run(
                executor.execute(
                    Invocation(
                        tool_name=case["tool"], tool_version="1.0", arguments=args
                    ),
                    identity=actor,
                    correlation_id=uuid4(),
                )
            )
            if case.get("denied"):
                assert result.status == "error" and result.error.code == "not_found"
            else:
                assert result.status == "success"
            investigation = uuid4()
            sources = retrieval.normalize(result, investigation, actor.tenant_id)
            expected = {stable_id(ref) for ref in case["expected"]}
            actual = {s.source_resource_id for s in sources}
            hit = len(actual & expected)
            hits += hit
            relevant += len(expected)
            returned += len(actual)
            if case["tool"] == "search_policy":
                policies += 1
                policy_correct += (
                    {sources[0].source_resource_id} == expected
                    if sources
                    else not expected
                )
            leakage += sum(s.tenant_id != actor.tenant_id for s in sources)
            # Also compare against known foreign source IDs (tenant metadata alone is insufficient).
            foreign = (
                {stable_id(f"{1 - tenant}/account/{i}") for i in range(10)}
                | {stable_id(f"{1 - tenant}/ticket/{i}") for i in range(15)}
                | {
                    stable_id(f"{1 - tenant}/policy/{key}")
                    for key in (
                        "billing_block/1",
                        "security_review/1",
                        "duplicate_ticket/1",
                        "reactivation/1",
                        "reactivation/2",
                    )
                }
            )
            leakage += len(actual & foreign)
            envelopes = []
            if sources:
                envelopes = [
                    Evidence(
                        sources=sources,
                        evidence_id=uuid4(),
                        tool_execution_id=result.execution_id,
                        tool_name=result.tool_name,
                        tool_version=result.tool_version,
                        source_reference="evaluation",
                        source_references=(),
                        summary="Evaluation source collection",
                        collected_at=result.completed_at,
                    )
                ]
            reconciled = retrieval.reconcile(investigation, envelopes)
            for finding in reconciled.grounded_findings:
                try:
                    retrieval.validate_finding(finding, sources)
                    citations += 1
                except ValueError:
                    unsupported += 1
            rows.append(
                {
                    "id": case["id"],
                    "expected": sorted(map(str, expected)),
                    "retrieved": sorted(map(str, actual)),
                    "hits": hit,
                }
            )
    # Conflict recall uses actual authorized account+ledger retrieval for the disputed-payment fixture.
    actor = agents.identity(client, role="reviewer")
    investigation = uuid4()
    envelopes = []
    for name in ("get_account_status", "list_recent_transactions"):
        result = asyncio.run(
            executor.execute(
                Invocation(
                    tool_name=name,
                    tool_version="1.0",
                    arguments={"account_id": str(stable_id("0/account/4"))},
                ),
                identity=actor,
                correlation_id=uuid4(),
            )
        )
        assert result.status == "success"
        envelopes.append(
            Evidence(
                sources=retrieval.normalize(result, investigation, actor.tenant_id),
                evidence_id=uuid4(),
                tool_execution_id=result.execution_id,
                tool_name=name,
                tool_version="1.0",
                source_reference="evaluation",
                source_references=(),
                summary="Authorized conflict fixture",
                collected_at=result.completed_at,
            )
        )
    conflict_hits = int(
        "payment_unresolved"
        in {
            c.conflict_type
            for c in retrieval.reconcile(investigation, envelopes).conflicts
        }
    )
    metrics = {
        "cases": len(cases),
        "recall_at_k": hits / relevant,
        "precision_at_k": hits / returned,
        "hits": hits,
        "expected_references": relevant,
        "retrieved_references": returned,
        "policy_accuracy": policy_correct / policies,
        "policy_correct": policy_correct,
        "policy_cases": policies,
        "citation_validity": citations / (citations + unsupported),
        "citations": citations,
        "unsupported_factual_findings": unsupported,
        "conflict_recall": conflict_hits,
        "conflict_cases": 1,
        "cross_tenant_leakage": leakage,
        "k": "3 for policy, 1 for direct resources",
    }
    assert leakage == unsupported == 0
    assert (
        metrics["recall_at_k"]
        == metrics["policy_accuracy"]
        == metrics["conflict_recall"]
        == 1
    )
    # Explicit opt-in output prevents ordinary pytest from changing tracked reports.
    import os

    if os.getenv("PHASE5_EVALUATION_OUTPUT"):
        Path(os.environ["PHASE5_EVALUATION_OUTPUT"]).write_text(
            json.dumps({"metrics": metrics, "cases": rows}, indent=2) + "\n"
        )
