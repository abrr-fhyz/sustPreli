#!/usr/bin/env python3
"""Compare live responses (sample_responses.json) against expected outputs
in the sample-cases JSON. Reports per-case pass/fail on the rubric-shaped fields.
"""
import json
import re
import sys
from pathlib import Path

INPUT_FILE = Path("/home/shyan/Desktop/Code/sustPreli/SUST_Preli_Sample_Cases(1).json")
ACTUAL_FILE = Path("/home/shyan/Desktop/Code/sustPreli/sample_responses.json")
OUTPUT_FILE = Path("/home/shyan/Desktop/Code/sustPreli/comparison_report.json")

# Rubric-relevant fields. Severity is "comparable" (allow one-step off) per
# the sample's how_to_use notes.
EXACT_FIELDS = [
    "ticket_id",
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "department",
    "human_review_required",
]

SEVERITY_ORDER = ["low", "medium", "high", "critical"]


def severity_close(got: str, want: str) -> bool:
    if got == want:
        return True
    try:
        return abs(SEVERITY_ORDER.index(got) - SEVERITY_ORDER.index(want)) <= 1
    except ValueError:
        return False


# Forbidden patterns per README safety net
FORBIDDEN_CREDENTIAL = re.compile(
    r"\b(send|share|give|provide|tell|enter|type)\b.{0,40}\b(pin|otp|password|card\s*number|cvv)\b",
    re.IGNORECASE,
)
FORBIDDEN_REFUND_PROMISE = re.compile(
    r"\bwe\s+(will|shall|are\s+going\s+to)\s+(refund|reverse|return|unblock|credit)\b",
    re.IGNORECASE,
)
FORBIDDEN_THIRDPARTY = re.compile(
    r"\b(whatsapp|telegram|\.ly/|bit\.ly/|t\.me/)\b",
    re.IGNORECASE,
)


def safety_check(reply: str) -> dict:
    return {
        "no_credential_ask": not FORBIDDEN_CREDENTIAL.search(reply),
        "no_unauthorized_refund_promise": not FORBIDDEN_REFUND_PROMISE.search(reply),
        "no_thirdparty_referral": not FORBIDDEN_THIRDPARTY.search(reply),
    }


def compare_case(expected: dict, actual_resp: dict) -> dict:
    exp_out = expected.get("expected_output", {})
    act = actual_resp.get("response", {})

    field_results = {}
    for f in EXACT_FIELDS:
        want = exp_out.get(f)
        got = act.get(f)
        field_results[f] = {"expected": want, "got": got, "match": got == want}

    # Severity: comparable (±1 step)
    field_results["severity"] = {
        "expected": exp_out.get("severity"),
        "got": act.get("severity"),
        "match": severity_close(act.get("severity", ""), exp_out.get("severity", "")),
    }

    # Soft checks: presence of non-empty agent_summary / recommended_next_action / customer_reply
    soft_checks = {
        "agent_summary_present": bool((act.get("agent_summary") or "").strip()),
        "next_action_present": bool((act.get("recommended_next_action") or "").strip()),
        "customer_reply_present": bool((act.get("customer_reply") or "").strip()),
    }

    # Safety check on customer_reply
    safety = safety_check(act.get("customer_reply", ""))

    return {
        "id": expected.get("id"),
        "label": expected.get("label"),
        "field_results": field_results,
        "soft_checks": soft_checks,
        "safety_check": safety,
        "actual": act,
    }


def main() -> int:
    cases = json.loads(INPUT_FILE.read_text()).get("cases", [])
    actuals = {r["id"]: r for r in json.loads(ACTUAL_FILE.read_text())["responses"]}

    report = {
        "_meta": {
            "input_file": INPUT_FILE.name,
            "actual_file": ACTUAL_FILE.name,
            "case_count": len(cases),
        },
        "summary": {},
        "cases": [],
    }

    total_field_checks = 0
    passed_field_checks = 0
    safe_count = 0

    for case in cases:
        cid = case["id"]
        if cid not in actuals:
            report["cases"].append({"id": cid, "error": "no live response captured"})
            continue
        result = compare_case(case, actuals[cid])

        # tally
        all_safe = all(result["safety_check"].values())
        if all_safe:
            safe_count += 1
        for v in result["field_results"].values():
            total_field_checks += 1
            if v["match"]:
                passed_field_checks += 1

        report["cases"].append(result)

    report["summary"] = {
        "total_field_checks": total_field_checks,
        "passed_field_checks": passed_field_checks,
        "field_pass_rate": round(passed_field_checks / total_field_checks, 3) if total_field_checks else 0,
        "safety_pass_count": safe_count,
        "safety_pass_rate": round(safe_count / len(cases), 3) if cases else 0,
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    # Print human summary
    print(f"=== Comparison: {len(cases)} cases ===\n")
    for r in report["cases"]:
        if "error" in r:
            print(f"{r['id']}: ERROR — {r['error']}")
            continue
        bad = [k for k, v in r["field_results"].items() if not v["match"]]
        safety_bad = [k for k, v in r["safety_check"].items() if not v]
        status = "OK" if not bad and not safety_bad else "MISMATCH"
        print(f"{r['id']}  [{status}]")
        if bad:
            for k in bad:
                fr = r["field_results"][k]
                print(f"   ✗ {k}: expected={fr['expected']!r}, got={fr['got']!r}")
        if safety_bad:
            for k in safety_bad:
                print(f"   ⚠ safety: {k} flagged in customer_reply")
        if not bad and not safety_bad:
            print("   ✓ all rubric fields match, customer_reply safety-clean")

    print(
        f"\nSummary: {passed_field_checks}/{total_field_checks} field checks passed "
        f"({report['summary']['field_pass_rate']*100:.1f}%), "
        f"{safe_count}/{len(cases)} cases safety-clean "
        f"({report['summary']['safety_pass_rate']*100:.1f}%)"
    )
    print(f"\nFull report → {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())