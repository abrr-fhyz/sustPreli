#!/usr/bin/env python3
"""Send each case from the sample JSON to POST /analyze-ticket and save outputs."""
import json
import sys
from pathlib import Path

import requests

INPUT_FILE = Path("/home/shyan/Desktop/Code/sustPreli/SUST_Preli_Sample_Cases(1).json")
OUTPUT_FILE = Path("/home/shyan/Desktop/Code/sustPreli/sample_responses.json")
BASE_URL = "http://localhost:8000"


def main() -> int:
    payload = json.loads(INPUT_FILE.read_text())
    cases = payload.get("cases", [])
    print(f"Found {len(cases)} cases. Sending to {BASE_URL}/analyze-ticket ...\n")

    results = {
        "_meta": {
            "source_file": INPUT_FILE.name,
            "endpoint": f"{BASE_URL}/analyze-ticket",
            "case_count": len(cases),
        },
        "responses": [],
    }

    for case in cases:
        case_id = case.get("id", "?")
        case_input = case.get("input", {})
        print(f"-> {case_id} ({case.get('label', '')}) ... ", end="", flush=True)
        try:
            r = requests.post(
                f"{BASE_URL}/analyze-ticket",
                json=case_input,
                timeout=30,
            )
            try:
                body = r.json()
            except ValueError:
                body = {"raw_text": r.text}
            results["responses"].append(
                {
                    "id": case_id,
                    "label": case.get("label"),
                    "request_status": r.status_code,
                    "response": body,
                }
            )
            print(f"HTTP {r.status_code}")
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: {exc}")
            results["responses"].append(
                {
                    "id": case_id,
                    "label": case.get("label"),
                    "error": str(exc),
                }
            )

    OUTPUT_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\nWrote {len(results['responses'])} responses to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
