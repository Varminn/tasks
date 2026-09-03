CUSTOMER_RECORDS: dict[str, dict] = {
    "CUST-00001": {
        "customer_id": "CUST-00001",
        "name": "Alice Chen",
        "email": "alice@example.com",
        "tier": "gold",
        "account_balance": 1250.75,
    },
    "CUST-00002": {
        "customer_id": "CUST-00002",
        "name": "Bob Martinez",
        "email": "bob@example.com",
        "tier": "silver",
        "account_balance": 340.20,
    },
    "CUST-00003": {
        "customer_id": "CUST-00003",
        "name": "Charlie Davis",
        "email": "charlie@example.com",
        "tier": "bronze",
        "account_balance": 89.99,
    },
}


def get_customer_record(customer_id: str) -> dict | None:
    return CUSTOMER_RECORDS.get(customer_id)


def trigger_refund(customer_id: str, amount: float, reason: str) -> dict:
    record = CUSTOMER_RECORDS.get(customer_id)
    if record is None:
        raise LookupError(f"Customer not found: {customer_id}")
    return {
        "status": "refund_initiated",
        "customer_id": customer_id,
        "amount": amount,
        "reason": reason,
        "refund_id": f"REF-{customer_id.split('-')[1]}-{id(amount) % 100000:05d}",
    }
