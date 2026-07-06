# Mietspiegel Alert Monitor
#
# This script checks for changes in Mietspiegel data files and sends email alerts
# to subscribers when a city's Mietspiegel values change beyond configured thresholds.
#
# Usage: python3 scripts/alert-monitor.py
# Scheduled via: cronjob every 24h
#
# For production, configure SMTP settings below or use SendGrid/Mailgun API.

import json
import os
import smtplib
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

# === Configuration ===
DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'processed'
ALERTS_DIR = Path(__file__).resolve().parent.parent / 'data' / 'alerts'
ALERTS_FILE = ALERTS_DIR / 'subscriptions.json'
HASHES_FILE = ALERTS_DIR / '.data_hashes.json'

# Email delivery (configure for production)
SMTP_HOST = os.environ.get('MIETSPIEGEL_SMTP_HOST', '')
SMTP_PORT = int(os.environ.get('MIETSPIEGEL_SMTP_PORT', '587'))
SMTP_USER = os.environ.get('MIETSPIEGEL_SMTP_USER', '')
SMTP_PASS = os.environ.get('MIETSPIEGEL_SMTP_PASS', '')
FROM_EMAIL = os.environ.get('MIETSPIEGEL_FROM_EMAIL', 'alerts@mietspiegel.digital')


def load_json(path):
    """Load JSON file, return {} if not found."""
    if not path.exists():
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(path, data):
    """Save JSON file, creating dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def compute_data_hash(data):
    """Compute a hash of the meaningful data fields to detect changes."""
    content = json.dumps(data.get('current_edition', {}), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def detect_changes():
    """
    Compare current data file hashes against stored hashes.
    Returns list of (city_name, city_slug, old_hash, new_hash) for changed cities.
    """
    changes = []
    stored_hashes = load_json(HASHES_FILE)
    current_hashes = {}

    for fpath in DATA_DIR.glob('*.json'):
        if fpath.name == 'stadt-index.json':
            continue
        data = load_json(fpath)
        if not data or 'city_slug' not in data:
            continue
        slug = data['city_slug']
        h = compute_data_hash(data)
        current_hashes[slug] = h
        if slug in stored_hashes and stored_hashes[slug] != h:
            changes.append((data.get('city', slug), slug, stored_hashes[slug], h))
        elif slug not in stored_hashes:
            changes.append((data.get('city', slug), slug, None, h))

    save_json(HASHES_FILE, current_hashes)
    return changes


def compute_rent_changes(data):
    """For a changed city, compute the rent changes vs previous edition from history."""
    history = data.get('history', [])
    if len(history) < 2:
        return None
    last = history[-1]
    prev = history[-2]
    changes = {}
    for key in ['base_rent_mittel_60_90', 'base_rent_mittel_1919_1949']:
        if key in last and key in prev and prev[key] > 0:
            pct = ((last[key] - prev[key]) / prev[key]) * 100
            changes[key] = {
                'old': prev[key],
                'new': last[key],
                'pct_change': round(pct, 1)
            }
    return changes


def send_email(to_email, subject, html_body):
    """Send an email. Returns True on success."""
    if not SMTP_HOST:
        print(f"[DRY RUN] Would send email to {to_email}")
        print(f"Subject: {subject}")
        print(f"Body: {html_body[:200]}...")
        return True

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False


def check_and_notify():
    """Main function: detect changes and notify subscribers."""
    changes = detect_changes()

    if not changes:
        print(f"[{datetime.now().isoformat()}] No Mietspiegel changes detected.")
        return

    print(f"[{datetime.now().isoformat()}] Changes detected: {len(changes)} city/cities")

    subscriptions = load_json(ALERTS_FILE)
    subscribers = subscriptions.get('subscriptions', [])

    if not subscribers:
        print("No subscribers to notify.")
        return

    for city_name, slug, old_hash, new_hash in changes:
        data = load_json(DATA_DIR / f'{slug}.json')
        rent_changes = compute_rent_changes(data)

        # Find subscribers interested in this city (or all cities)
        for sub in subscribers:
            email = sub.get('email', '')
            sub_city = sub.get('city', '')
            max_rent = sub.get('max_rent', 0)
            change_pct = sub.get('change_pct', 0)

            if sub_city and sub_city != slug and sub_city != '':
                continue  # Subscriber only wants specific city

            # Check thresholds
            if rent_changes and change_pct > 0:
                exceed = any(
                    abs(v['pct_change']) >= change_pct
                    for v in rent_changes.values()
                )
                if not exceed:
                    print(f"  Skipping {email} for {city_name}: change below {change_pct}% threshold")
                    continue

            if rent_changes and max_rent > 0:
                exceed = any(
                    v['new'] >= max_rent for v in rent_changes.values()
                )
                if not exceed:
                    print(f"  Skipping {email} for {city_name}: rent below {max_rent}€ threshold")
                    continue

            # Build notification email
            subject = f"🔔 Mietspiegel-Änderung: {city_name}"
            html = f"""
            <html><body style="font-family:sans-serif;background:#f5f5f5;padding:20px">
            <div style="max-width:600px;margin:auto;background:white;border-radius:8px;padding:30px">
            <h2 style="color:#1a73e8">🔔 Mietspiegel geändert: {city_name}</h2>
            <p>Der offizielle Mietspiegel für <strong>{city_name}</strong> wurde aktualisiert.</p>
            """

            if rent_changes:
                html += '<table style="width:100%;border-collapse:collapse;margin:15px 0">'
                html += '<tr style="background:#f0f0f0"><th>Kategorie</th><th>Alt</th><th>Neu</th><th>Änderung</th></tr>'
                labels = {'base_rent_mittel_60_90': 'Mittelwert 60-90m²', 'base_rent_mittel_1919_1949': 'Mittelwert 1919-1949'}
                for key, info in rent_changes.items():
                    label = labels.get(key, key)
                    color = 'red' if info['pct_change'] > 0 else 'green'
                    html += f'<tr><td>{label}</td><td>{info["old"]:.2f} €</td><td>{info["new"]:.2f} €</td><td style="color:{color};font-weight:bold">{info["pct_change"]:+.1f}%</td></tr>'
                html += '</table>'

            html += f"""
            <p>Details im Dashboard: <a href="https://mietspiegel.vercel.app">mietspiegel.vercel.app</a></p>
            <hr style="border:none;border-top:1px solid #eee">
            <p style="color:#888;font-size:0.85em">
            Dies ist eine automatische Benachrichtigung vom Mietspiegel Digital Alert-Service.<br>
            <a href="https://mietspiegel.vercel.app?unsubscribe={email}">Abmelden</a>
            </p>
            </div></body></html>
            """

            send_email(email, subject, html)
            print(f"  ✓ Alert sent to {email} for {city_name}")


if __name__ == '__main__':
    check_and_notify()
