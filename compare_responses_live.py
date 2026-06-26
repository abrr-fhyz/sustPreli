#!/usr/bin/env python3
"""Compare live responses (sample_responses_live.json) against expected outputs
in the sample-cases JSON. Reports per-case pass/fail on the rubric-shaped fields.
"""
import json
import re
import sys
from pathlib import Path

INPUT_FILE = Path("/home/shyan/Desktop/Code/sustPreli/SUST_Preli_Sample_Cases(1).json")
ACTUAL_FILE = Path("/home/shyan/Desktop/Code/sustPreli/sample_responses_live.json")
OUTPUT_FILE = Path("/home/shyan/Desktop/Code/sustPreli/comparison_report_live.json")

EXACT_FIELDS = [
    "ticket_id",
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "department",
    "human_review_required",
]

SEVERITY_ORDER = ["low", "medium", "high", "critical"]

FORBIDDEN_CREDENTIAL = re.compile(
    r"\b(send|share|give|provide|tell|enter|type)\b[^.?!]{0,40}?\b(pin|otp|password|card\s*number|cvv)\b",
    re.IGNORECASE,
)
# Mirror app/utils/safety.py: negation context ("never", "do not", "keep ... private")
# makes a credential mention safe. Without this, "do not share your PIN" gets
# flagged as a credential request.
CRED_NEGATED = re.compile(
    r"\b(never|not|n't|do\s+not|don'?t|avoid|without|keep[^.?!]{0,20}private)\b"
    r"[^.?!]{0,40}?\b(share|send|provide|give|enter|tell|confirm|verify|ask|"
    r"disclose|reveal|request)\b[^.?!]{0,40}?\b(pin|otp|password|cvv|card\s*number)\b",
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


def severity_close(got: str, want: str) -> bool:
    if got == want:
        return True
    try:
        return abs(SEVERITY_ORDER.index(got) - SEVERITY_ORDER.index(want)) <= 1
    except ValueError:
        return False


def safety_check(reply: str) -> dict:
    # Mirror app/utils/safety.py: a credential mention is only a violation when
    # it sits next to a request verb AND is not in a negation context.
    cred_violation = bool(FORBIDDEN_CREDENTIAL.search(reply)) and not CRED_NEGATED.search(reply)
    return {
        "no_credential_ask": not cred_violation,
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

    field_results["severity"] = {
        "expected": exp_out.get("severity"),
        "got": act.get("severity"),
        "match": severity_close(act.get("severity", ""), exp_out.get("severity", "")),
    }

    soft_checks = {
        "agent_summary_present": bool((act.get("agent_summary") or "").strip()),
        "next_action_present": bool((act.get("recommended_next_action") or "").strip()),
        "customer_reply_present": bool((act.get("customer_reply") or "").strip()),
    }

    safety = safety_check(act.get("customer_reply", ""))

    return {
        "id": expected.get("id"),
        "label": expected.get("label"),
        "latency_ms": actual_resp.get("latency_ms"),
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
    latencies = []

    for case in cases:
        cid = case["id"]
        if cid not in actuals:
            report["cases"].append({"id": cid, "error": "no live response captured"})
            continue
        result = compare_case(case, actuals[cid])

        if result.get("latency_ms") is not None:
            latencies.append(result["latency_ms"])

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
        "latency_ms": {
            "min": min(latencies) if latencies else None,
            "max": max(latencies) if latencies else None,
            "avg": round(sum(latencies) / len(latencies), 1) if latencies else None,
        },
    }

    OUTPUT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    print(f"=== Live Comparison: {len(cases)} cases ===\n")
    for r in report["cases"]:
        if "error" in r:
            print(f"{r['id']}: ERROR — {r['error']}")
            continue
        bad = [k for k, v in r["field_results"].items() if not v["match"]]
        safety_bad = [k for k, v in r["safety_check"].items() if not v]
        status = "OK" if not bad and not safety_bad else "MISMATCH"
        lat = f" {r.get('latency_ms')} ms" if r.get("latency_ms") is not None else ""
        print(f"{r['id']}  [{status}]{lat}")
        if bad:
            for k in bad:
                fr = r["field_results"][k]
                print(f"   ✗ {k}: expected={fr['expected']!r}, got={fr['got']!r}")
        if safety_bad:
            for k in safety_bad:
                print(f"   ⚠ safety: {k} flagged in customer_reply")
        if not bad and not safety_bad:
            print("   ✓ all rubric fields match, customer_reply safety-clean")

    s = report["summary"]
    print(
        f"\nSummary: {s['passed_field_checks']}/{s['total_field_checks']} field checks passed "
        f"({s['field_pass_rate']*100:.1f}%), "
        f"{s['safety_pass_count']}/{len(cases)} cases safety-clean "
        f"({s['safety_pass_rate']*100:.1f}%)"
    )
    if s["latency_ms"]["avg"] is not None:
        print(
            f"Latency: min={s['latency_ms']['min']} ms, "
            f"avg={s['latency_ms']['avg']} ms, "
            f"max={s['latency_ms']['max']} ms"
        )
    print(f"\nFull report → {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())