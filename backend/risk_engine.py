import csv
import io
import json
import sqlite3
from datetime import datetime
from statistics import median
from .database import get_db

RULE_WEIGHTS = {
    "Unusually Large Transfer": 25,
    "New Payee Burst": 20,
    "Payment Burst": 20,
    "Odd-Hours Activity": 15,
    "Customer Pattern Deviation": 15,
    "Transaction Correlation": 10,
}


def parse_transactions(raw, filename):
    suffix = filename.lower().rsplit(".", 1)[-1]
    if suffix == "json":
        records = json.loads(raw)
    elif suffix == "csv":
        records = list(csv.DictReader(io.StringIO(raw)))
    else:
        raise ValueError("Only JSON and CSV files are supported.")
    if not isinstance(records, list) or not records:
        raise ValueError("Transaction history must be a non-empty list.")
    required = {"transaction_id", "date_time", "description", "payee", "amount", "channel"}
    normalized = []
    for index, record in enumerate(records, 1):
        if not isinstance(record, dict) or not required.issubset(record):
            raise ValueError(f"Record {index} is missing a required field.")
        try:
            amount = float(record["amount"])
            datetime.fromisoformat(str(record["date_time"]).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            raise ValueError(f"Record {index} has an invalid amount or date/time.")
        if amount <= 0:
            raise ValueError(f"Record {index} amount must be greater than zero.")
        normalized.append({**record, "amount": amount})
    return normalized


def _level(score):
    if score >= 80:
        return "HIGH ATTENTION"
    if score >= 60:
        return "REVIEW"
    if score >= 30:
        return "LOW"
    return "NORMAL"


def investigate_customer(customer_id):
    db = get_db()
    customer = db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    transactions = db.execute("SELECT * FROM transactions WHERE customer_id = ? ORDER BY occurred_at", (customer_id,)).fetchall()
    if not customer:
        raise ValueError("Customer not found")
    tx = [dict(item) for item in transactions]
    typical = float(customer["typical_amount"])
    triggered = []
    involved = {}
    if len(tx) < 3:
        return _persist(customer_id, 0, "INSUFFICIENT EVIDENCE", "INSUFFICIENT EVIDENCE", [], [], {"typical": typical, "count": len(tx)})
    payees = {item["payee"] for item in tx[:max(1, len(tx) - 3)]}
    for item in tx:
        if item["amount"] >= max(typical * 5, typical + 15000):
            involved.setdefault(item["transaction_code"], set()).add("Unusually Large Transfer")
    new_payee_items = [item for item in tx if item["payee"] not in payees]
    new_payee_bursts = []
    for payee in {item["payee"] for item in new_payee_items}:
        payee_items = [item for item in new_payee_items if item["payee"] == payee]
        first = datetime.fromisoformat(payee_items[0]["occurred_at"])
        last = datetime.fromisoformat(payee_items[-1]["occurred_at"])
        if len(payee_items) >= 2 and (last - first).total_seconds() <= 2 * 60 * 60:
            new_payee_bursts.extend(payee_items)
    if new_payee_bursts:
        triggered.append("New Payee Burst")
        for item in new_payee_bursts:
            involved.setdefault(item["transaction_code"], set()).add("New Payee Burst")
    for item in tx:
        hour = int(item["occurred_at"][11:13])
        if hour < 7 or hour >= 22:
            involved.setdefault(item["transaction_code"], set()).add("Odd-Hours Activity")
    if any(len(rules) > 0 for rules in involved.values()):
        triggered.append("Customer Pattern Deviation")
    large_codes = {code for code, rules in involved.items() if "Unusually Large Transfer" in rules}
    if len(new_payee_bursts) >= 3:
        triggered.append("Payment Burst")
        for item in new_payee_bursts:
            involved.setdefault(item["transaction_code"], set()).add("Payment Burst")
    if large_codes and len(new_payee_bursts) >= 2:
        triggered.append("Transaction Correlation")
        for code in set(involved) & (large_codes | {item["transaction_code"] for item in new_payee_bursts}):
            involved[code].add("Transaction Correlation")
    triggered = list(dict.fromkeys(triggered + [rule for rules in involved.values() for rule in rules if rule in RULE_WEIGHTS]))
    score = min(100, sum(RULE_WEIGHTS[rule] for rule in triggered))
    relevant = [item for item in tx if item["transaction_code"] in involved]
    evidence = [{"transaction": item, "rules": sorted(involved[item["transaction_code"]])} for item in relevant]
    finding = "ATTENTION REQUIRED" if score >= 30 else "NO ATTENTION REQUIRED"
    baseline = {"typical": typical, "count": len(tx), "max": max(item["amount"] for item in tx), "median": median(item["amount"] for item in tx)}
    return _persist(customer_id, score, _level(score), finding, triggered, evidence, baseline)


def _persist(customer_id, score, level, finding, triggered, evidence, baseline):
    db = get_db()
    now = datetime.utcnow().isoformat(timespec="seconds")
    db.execute("INSERT INTO investigations (customer_id, score, level, finding, triggered_rules, created_at) VALUES (?, ?, ?, ?, ?, ?)", (customer_id, score, level, finding, json.dumps(triggered), now))
    investigation_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for item in evidence:
        row = item["transaction"]
        for rule in item["rules"]:
            db.execute("INSERT OR IGNORE INTO investigation_transactions (investigation_id, transaction_id, rule_name) SELECT ?, id, ? FROM transactions WHERE transaction_code = ?", (investigation_id, rule, row["transaction_code"]))
    db.commit()
    return {"investigation_id": investigation_id, "score": score, "level": level, "finding": finding, "triggered_rules": triggered, "evidence": evidence, "baseline": baseline, "explanation": _correlation(triggered, evidence)}


def _correlation(triggered, evidence):
    if not triggered:
        return "No configured risk rule was triggered. The customer's recent activity is consistent with their established transaction behaviour."
    names = ", ".join(triggered)
    return f"The connected signals are {names}. Review the evidence chronologically to determine whether the new payee, timing, amount, and repeated payments are expected business activity."
