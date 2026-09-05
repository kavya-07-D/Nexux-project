import json
import os
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from backend.database import get_db, init_db, seed_db
from backend.risk_engine import investigate_customer, parse_transactions
from backend.gemini_service import explain_investigation

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("BANKGUARD_SECRET", "local-bankguard-demo-secret")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def query(sql, params=(), one=False):
    db = get_db()
    rows = db.execute(sql, params).fetchall()
    return (rows[0] if rows else None) if one else rows


def row_dict(row):
    return dict(row) if row else None


@app.before_request
def prepare_database():
    init_db()
    seed_db()


@app.teardown_appcontext
def close_database(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = query("SELECT * FROM users WHERE username = ?", (username,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Invalid investigator credentials.", "error")
    return render_template("login.html")


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/dashboard")
@login_required
def dashboard():
    stats = {
        "customers": query("SELECT COUNT(*) AS count FROM customers", one=True)["count"],
        "transactions": query("SELECT COUNT(*) AS count FROM transactions", one=True)["count"],
        "investigations": query("SELECT COUNT(*) AS count FROM investigations", one=True)["count"],
        "attention": query("SELECT COUNT(*) AS count FROM investigations WHERE level IN ('REVIEW', 'HIGH ATTENTION')", one=True)["count"],
    }
    customers = query("SELECT * FROM customers ORDER BY name")
    cases = []
    for customer in customers:
        report = investigate_customer(customer["id"])
        cases.append({"customer": customer, "report": report})
    recent = query("SELECT i.*, c.name FROM investigations i JOIN customers c ON c.id = i.customer_id ORDER BY i.created_at DESC LIMIT 6")
    return render_template("dashboard.html", stats=stats, cases=cases, recent=recent, page="dashboard")


@app.get("/customers")
@login_required
def customers():
    records = query("SELECT * FROM customers ORDER BY name")
    return render_template("customers.html", customers=records, selected=None, transactions=[] , page="customers")


@app.get("/customers/<int:customer_id>")
@login_required
def customer_detail(customer_id):
    selected = query("SELECT * FROM customers WHERE id = ?", (customer_id,), one=True)
    if not selected:
        return redirect(url_for("customers"))
    transactions = query("SELECT * FROM transactions WHERE customer_id = ? ORDER BY occurred_at DESC", (customer_id,))
    return render_template("customers.html", customers=query("SELECT * FROM customers ORDER BY name"), selected=selected, transactions=transactions, page="customers")


@app.get("/transactions")
@login_required
def transactions():
    records = query("SELECT t.*, c.name FROM transactions t JOIN customers c ON c.id = t.customer_id ORDER BY occurred_at DESC")
    return render_template("transactions.html", transactions=records, page="transactions")


@app.get("/investigations/<int:customer_id>")
@login_required
def investigation(customer_id):
    customer = query("SELECT * FROM customers WHERE id = ?", (customer_id,), one=True)
    if not customer:
        return redirect(url_for("dashboard"))
    report = investigate_customer(customer_id)
    ai_text, ai_status = explain_investigation(report)
    return render_template("investigation.html", customer=customer, report=report, ai_text=ai_text, ai_status=ai_status, page="investigations")


@app.post("/investigations/<int:customer_id>/decision")
@login_required
def decision(customer_id):
    action = request.form.get("action", "").strip()
    labels = {"reviewed": "MARKED REVIEWED", "escalated": "ESCALATED", "no_action": "NO FURTHER ACTION"}
    if action not in labels:
        flash("Unknown investigator action.", "error")
        return redirect(url_for("investigation", customer_id=customer_id))
    db = get_db()
    report = investigate_customer(customer_id)
    db.execute("INSERT INTO investigator_decisions (investigation_id, user_id, decision, created_at) VALUES (?, ?, ?, ?)", (report["investigation_id"], session["user_id"], labels[action], datetime.utcnow().isoformat()))
    db.commit()
    flash(f"Decision recorded: {labels[action]}.", "success")
    return redirect(url_for("investigation", customer_id=customer_id))


@app.get("/reports")
@login_required
def reports():
    records = query("SELECT i.*, c.name FROM investigations i JOIN customers c ON c.id = i.customer_id ORDER BY i.created_at DESC")
    return render_template("reports.html", reports=records, page="reports")


@app.get("/settings")
@login_required
def settings():
    return render_template("settings.html", page="settings")


@app.post("/api/import")
@login_required
def import_transactions():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Choose a JSON or CSV file."}), 400
    try:
        raw = uploaded.read().decode("utf-8")
        records = parse_transactions(raw, uploaded.filename)
    except (ValueError, UnicodeDecodeError) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"valid": len(records), "message": "Validated transaction records. Import is available from a customer context."})


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(host="0.0.0.0", port=8000, debug=False)
