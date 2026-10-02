from flask import Flask,render_template,request,redirect,url_for,flash
import os,sqlite3
from datetime import date
BASE=os.path.dirname(os.path.abspath(__file__)); DB=os.path.join(BASE,"ledger.db")
app=Flask(__name__); app.secret_key=os.environ.get("SECRET_KEY","change-this-secret")
def db():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
    c=db()
    c.executescript("""CREATE TABLE IF NOT EXISTS customers(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE NOT NULL,name TEXT NOT NULL,mobile TEXT,address TEXT,opening REAL DEFAULT 0,opening_type TEXT DEFAULT 'Debit',created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS transactions(id INTEGER PRIMARY KEY AUTOINCREMENT,customer_id INTEGER NOT NULL,txn_date TEXT NOT NULL,voucher TEXT,particulars TEXT NOT NULL,debit REAL DEFAULT 0,credit REAL DEFAULT 0,payment_mode TEXT,notes TEXT,FOREIGN KEY(customer_id) REFERENCES customers(id));""")
    c.commit(); c.close()
@app.route("/")
def dashboard():
    c=db(); customers=c.execute("SELECT * FROM customers ORDER BY name").fetchall()
    td=c.execute("SELECT COALESCE(SUM(debit),0)v FROM transactions").fetchone()["v"]
    tc=c.execute("SELECT COALESCE(SUM(credit),0)v FROM transactions").fetchone()["v"]
    op=c.execute("SELECT COALESCE(SUM(CASE WHEN opening_type='Debit' THEN opening ELSE -opening END),0)v FROM customers").fetchone()["v"]
    c.close(); return render_template("dashboard.html",customers=customers,total_debit=td,total_credit=tc,opening=op,balance=op+td-tc)
@app.route("/customers",methods=["GET","POST"])
def customers():
    c=db()
    if request.method=="POST":
        try:
            c.execute("INSERT INTO customers(code,name,mobile,address,opening,opening_type) VALUES(?,?,?,?,?,?)",(request.form["code"].strip(),request.form["name"].strip(),request.form.get("mobile",""),request.form.get("address",""),float(request.form.get("opening") or 0),request.form.get("opening_type","Debit")))
            c.commit(); flash("Customer added.","success")
        except sqlite3.IntegrityError: flash("Customer ID already exists.","error")
    rows=c.execute("SELECT * FROM customers ORDER BY name").fetchall(); c.close()
    return render_template("customers.html",customers=rows)
@app.route("/customer/<int:cid>")
def ledger(cid):
    c=db(); customer=c.execute("SELECT * FROM customers WHERE id=?",(cid,)).fetchone()
    if not customer: c.close(); return "Customer not found",404
    txns=c.execute("SELECT * FROM transactions WHERE customer_id=? ORDER BY txn_date,id",(cid,)).fetchall()
    opening=customer["opening"] if customer["opening_type"]=="Debit" else -customer["opening"]; running=opening; ledger=[]
    for x in txns: running+=x["debit"]-x["credit"]; ledger.append((x,running))
    c.close(); return render_template("ledger.html",customer=customer,ledger=ledger,opening=opening,balance=running)
@app.route("/entry/<int:cid>",methods=["GET","POST"])
def entry(cid):
    c=db(); customer=c.execute("SELECT * FROM customers WHERE id=?",(cid,)).fetchone()
    if not customer: c.close(); return "Customer not found",404
    if request.method=="POST":
        debit=float(request.form.get("debit") or 0); credit=float(request.form.get("credit") or 0)
        if (debit and credit) or (not debit and not credit): flash("Enter either Debit or Credit.","error")
        else:
            c.execute("INSERT INTO transactions(customer_id,txn_date,voucher,particulars,debit,credit,payment_mode,notes) VALUES(?,?,?,?,?,?,?,?)",(cid,request.form["txn_date"],request.form.get("voucher",""),request.form["particulars"],debit,credit,request.form.get("payment_mode",""),request.form.get("notes","")))
            c.commit(); c.close(); return redirect(url_for("ledger",cid=cid))
    c.close(); return render_template("entry.html",customer=customer,today=date.today().isoformat())
@app.post("/delete_txn/<int:tid>/<int:cid>")
def delete_txn(tid,cid):
    c=db(); c.execute("DELETE FROM transactions WHERE id=?",(tid,)); c.commit(); c.close(); return redirect(url_for("ledger",cid=cid))
@app.get("/health")
def health(): return {"status":"ok"}
init_db()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")),debug=False)
