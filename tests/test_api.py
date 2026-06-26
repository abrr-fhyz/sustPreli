import json
import requests

BASE_URL = "https://sustpreli.onrender.com/analyze-ticket"

# Load test cases
with open("tests/sample_cases.json", "r", encoding="utf-8") as f:
    data = json.load(f)

cases = data["cases"]

passed = 0
failed = 0

for case in cases:
    case_id = case["id"]
    payload = case["input"]
    expected = case["expected_output"]

    print(f"\n=== Running {case_id}: {case['label']} ===")

    try:
        response = requests.post(BASE_URL, json=payload, timeout=30)

        if response.status_code != 200:
            print(response)
            print(f"❌ HTTP {response.status_code}")
            continue

        actual = response.json()

        print("Differences:")
        print("\nExpected:")
        print(json.dumps(expected, indent=2, ensure_ascii=False))
        print("\nActual:")
        print(json.dumps(actual, indent=2, ensure_ascii=False))

    except Exception as e:
        print(f"❌ ERROR: {e}")


print("\n" + "=" * 50)