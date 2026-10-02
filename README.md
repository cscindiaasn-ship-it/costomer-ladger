# Customer Ledger — Tally-style Accounting

A server-ready Flask accounting application for small businesses.

## Included
- Dashboard
- Party Master with opening balance, phone, address and GSTIN
- Chart of Accounts
- Sales / Purchase / Receipt / Payment vouchers
- Automatic voucher numbers
- Cash / Bank mode
- Double-entry transaction lines
- Day Book
- Individual Party/Account Ledger
- Outstanding report
- Trial Balance
- CSV export
- Print-friendly reports
- Health endpoint for deployment

## Run locally
python3 -m pip install -r requirements.txt
python3 app.py

Open http://127.0.0.1:5000

## Deployment
The repository contains render.yaml for a Render web service. SQLite is suitable for a simple single-instance setup; for production multi-user accounting, PostgreSQL, login/authentication, backups, audit trail and GST/tax workflows should be added.
