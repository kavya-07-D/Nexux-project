import os
import requests


def explain_investigation(report):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "AI explanation unavailable.\nDeterministic investigation results are still available.", "unavailable"
    prompt = f"""You are assisting a human banking investigator. Never claim fraud occurred. Use only the supplied evidence. Never invent transactions, amounts, dates, payees, or rules. Cite only transaction IDs present below. State when evidence is insufficient. The final decision belongs to the human investigator.\n\nFinding: {report['finding']}\nRisk score: {report['score']}\nTriggered rules: {report['triggered_rules']}\nEvidence: {report['evidence']}\nBaseline: {report['baseline']}\n\nWrite a concise investigation explanation and three review priorities."""
    try:
        response = requests.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent", params={"key": api_key}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=8)
        response.raise_for_status()
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        return text, "available"
    except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
        return "AI explanation unavailable.\nDeterministic investigation results are still available.", "unavailable"
