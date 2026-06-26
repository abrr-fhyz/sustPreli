import requests
import json

BASE_URL = "http://localhost:8000"

test_cases = [
    {
        "ticket_id": "TEST-001",
        "complaint": (
            "I sent 5000 taka to a wrong number."
        ),
        "language": "en",
        "transaction_history": [
            {
                "transaction_id": "TXN-1",
                "timestamp": "2026-06-26T12:00:00Z",
                "type": "transfer",
                "amount": 5000,
                "counterparty": "+8801712345678",
                "status": "completed"
            }
        ]
    },

    {
        "ticket_id": "TEST-002",
        "complaint": (
            "Someone called and asked for my OTP."
        ),
        "language": "en",
        "transaction_history": []
    },

    {
        "ticket_id": "TEST-003",
        "complaint": (
            "I paid 1200 taka but the payment failed "
            "and my balance was deducted."
        ),
        "language": "en",
        "transaction_history": [
            {
                "transaction_id": "TXN-2",
                "timestamp": "2026-06-26T10:00:00Z",
                "type": "payment",
                "amount": 1200,
                "counterparty": "MERCHANT-123",
                "status": "failed"
            }
        ]
    },

    {
        "ticket_id": "TEST-004",
        "complaint": (
            "আমি ২০০০ টাকা ক্যাশ ইন করেছি কিন্তু "
            "ব্যালেন্সে আসেনি।"
        ),
        "language": "bn",
        "transaction_history": [
            {
                "transaction_id": "TXN-3",
                "timestamp": "2026-06-26T09:00:00Z",
                "type": "cash_in",
                "amount": 2000,
                "counterparty": "AGENT-1",
                "status": "pending"
            }
        ]
    }
]


for case in test_cases:

    print(f"\nTesting {case['ticket_id']}")

    response = requests.post(
        f"{BASE_URL}/analyze-ticket",
        json=case
    )

    print("Status:", response.status_code)

    try:
        print(
            json.dumps(
                response.json(),
                indent=2,
                ensure_ascii=False
            )
        )
    except:
        print(response.text)

    print("-" * 60)
