TRACK_ID=PS6

# BankGuard

BankGuard is a local banking transaction risk investigation assistant. It combines transparent Python risk rules with an investigator-first dashboard and optional Gemini explanations. It flags activity for review; it never confirms fraud.

## Stack

Python 3.11, Flask, SQLite, HTML5, CSS3, vanilla JavaScript, Chart.js, and the Gemini API.

## Install and run

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:8000. Demo login: `investigator` / `bankguard-demo`.

Set `GEMINI_API_KEY` to enable Gemini explanations and local embedding retrieval. The application remains fully usable when the key is absent.

## Sample data

The seed data includes a routine customer and a difficult case with a new payee, repeated payments, large transfers, and odd-hours activity.

## Rules and policies

Local Markdown files under `data/rules/` and `data/policies/` describe the rule and escalation evidence used by the investigator workflow.

## Architecture

`app.py` owns the Flask routes and session flow. `backend/database.py` initializes and seeds SQLite, `backend/risk_engine.py` computes explainable deterministic findings, and `backend/gemini_service.py` optionally requests an evidence-bounded explanation. Templates and static assets provide the responsive interface.

## AI and local RAG

Gemini is called only after deterministic analysis. The prompt contains the customer baseline, triggered rules, transaction evidence, risk score, and retrieved local policy text. No hosted vector database is used. The fallback report remains available if Gemini fails.

## Risk rules

Large transfer +25, new payee +20, payment burst +20, odd hours +15, pattern deviation +15, and correlation +10. Scores are normalized to 0-100 and mapped to NORMAL, LOW, REVIEW, or HIGH ATTENTION.

## Demo video

Video link placeholder: `https://example.com/bankguard-demo`

## Known limitations

The demo uses a local SQLite database, simplified customer baselines, and a local demo account. Gemini availability depends on network access, model access, and `GEMINI_API_KEY`. It is not a production banking decision system.
