import os,sqlite3
from datetime import date
from flask import Flask,render_template,request,redirect,url_for,flash,Response,g
app=Flask(__name__); app.secret_key=os.getenv("SECRET_KEY","local-secret")
DB=os.path.join(os.path.dirname(__file__),"ledger.db")
def db():
    if "db" not in g:
        g.db=sqlite3.connect(DB);g.db.row_factory=sqlite3.Row
    return g.db
@app.teardown_appcontext
def close(e=None):
    x=g.pop("db",None)
    if x:x.close()
def init():
    x=sqlite3.connect(DB)
    x.executescript("""CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE NOT NULL,group_name TEXT NOT NULL,opening REAL DEFAULT 0,opening_type TEXT DEFAULT 'Dr',phone TEXT DEFAULT '',address TEXT DEFAULT '',gstin TEXT DEFAULT '',is_party INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS vouchers(id INTEGER PRIMARY KEY AUTOINCREMENT,vdate TEXT NOT NULL,vno TEXT NOT NULL,vtype TEXT NOT NULL,party_id INTEGER,amount REAL NOT NULL,narration TEXT DEFAULT '',mode TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS lines(id INTEGER PRIMARY KEY AUTOINCREMENT,voucher_id INTEGER,account_id INTEGER,debit REAL DEFAULT 0,credit REAL DEFAULT 0);""")
    for n,gp,typ,party in [("Cash","Cash-in-Hand","Dr",0),("Bank","Bank Accounts","Dr",0),("Sales","Sales Accounts","Cr",0),("Purchase","Purchase Accounts","Dr",0),("Capital","Capital Account","Cr",0)]:
        x.execute("INSERT OR IGNORE INTO accounts(name,group_name,opening,opening_type,is_party) VALUES(?,?,?,?,?)",(n,gp,0,typ,party))
    x.commit();x.close()
def n(v):
    try:return float(v or 0)
    except:return 0
def save_voucher(t):
    x=db(); amt=n(request.form.get("amount")); pid=int(request.form["party_id"]); mode=request.form.get("mode","Cash")
    no=f"{t[:3].upper()}-{x.execute('SELECT COUNT(*) FROM vouchers WHERE vtype=?',(t,)).fetchone()[0]+1:04d}"
    cur=x.execute("INSERT INTO vouchers(vdate,vno,vtype,party_id,amount,narration,mode) VALUES(?,?,?,?,?,?,?)",(request.form.get("vdate") or str(date.today()),no,t,pid,amt,request.form.get("narration",""),mode));vid=cur.lastrowid
    contra=x.execute("SELECT id FROM accounts WHERE name=?",(mode,)).fetchone()["id"]
    target={"Sales":"Sales","Purchase":"Purchase"}.get(t)
    if t=="Receipt": rows=[(pid,0,amt),(contra,amt,0)]
    elif t=="Payment": rows=[(pid,amt,0),(contra,0,amt)]
    elif t=="Sales": rows=[(pid,amt,0),(x.execute("SELECT id FROM accounts WHERE name='Sales'").fetchone()["id"],0,amt)]
    else: rows=[(x.execute("SELECT id FROM accounts WHERE name='Purchase'").fetchone()["id"],amt,0),(pid,0,amt)]
    for aid,dr,cr in rows:x.execute("INSERT INTO lines(voucher_id,account_id,debit,credit) VALUES(?,?,?,?)",(vid,aid,dr,cr))
    x.commit()
@app.route("/")
def home():
    x=db();return render_template("dashboard.html",parties=x.execute("SELECT COUNT(*) c FROM accounts WHERE is_party=1").fetchone()["c"],vouchers=x.execute("SELECT COUNT(*) c FROM vouchers").fetchone()["c"],sales=x.execute("SELECT COALESCE(SUM(amount),0) s FROM vouchers WHERE vtype='Sales'").fetchone()["s"],purchase=x.execute("SELECT COALESCE(SUM(amount),0) s FROM vouchers WHERE vtype='Purchase'").fetchone()["s"],recent=x.execute("SELECT v.*,a.name party FROM vouchers v LEFT JOIN accounts a ON a.id=v.party_id ORDER BY v.id DESC LIMIT 12").fetchall())
@app.route("/parties",methods=["GET","POST"])
def parties():
    x=db()
    if request.method=="POST":
        try:x.execute("INSERT INTO accounts(name,group_name,opening,opening_type,phone,address,gstin,is_party) VALUES(?,?,?,?,?,?,?,1)",(request.form["name"],request.form.get("group_name","Sundry Debtors"),n(request.form.get("opening")),request.form.get("opening_type","Dr"),request.form.get("phone",""),request.form.get("address",""),request.form.get("gstin","")));x.commit();flash("Party added","success")
        except:flash("Party already exists","error")
        return redirect(url_for("parties"))
    return render_template("parties.html",parties=x.execute("SELECT * FROM accounts WHERE is_party=1 ORDER BY name").fetchall())
@app.route("/accounts",methods=["GET","POST"])
def accounts():
    x=db()
    if request.method=="POST":
        try:x.execute("INSERT INTO accounts(name,group_name,opening,opening_type) VALUES(?,?,?,?)",(request.form["name"],request.form.get("group_name","Other"),n(request.form.get("opening")),request.form.get("opening_type","Dr")));x.commit();flash("Account added","success")
        except:flash("Account already exists","error")
        return redirect(url_for("accounts"))
    return render_template("accounts.html",accounts=x.execute("SELECT * FROM accounts ORDER BY group_name,name").fetchall())
@app.route("/voucher/<t>",methods=["GET","POST"])
def voucher(t):
    if t not in ["Sales","Purchase","Receipt","Payment"]:return "Invalid",404
    if request.method=="POST":
        try:save_voucher(t);flash(t+" voucher saved","success");return redirect("/daybook")
        except Exception as e:flash(str(e),"error")
    return render_template("voucher.html",vtype=t,parties=db().execute("SELECT id,name FROM accounts WHERE is_party=1 ORDER BY name").fetchall(),today=str(date.today()))
@app.route("/daybook")
def daybook():
    x=db();return render_template("daybook.html",rows=x.execute("SELECT v.*,a.name party FROM vouchers v LEFT JOIN accounts a ON a.id=v.party_id ORDER BY v.vdate DESC,v.id DESC").fetchall())
@app.route("/ledger/<int:aid>")
def ledger(aid):
    x=db();a=x.execute("SELECT * FROM accounts WHERE id=?",(aid,)).fetchone()
    rows=x.execute("SELECT v.vdate,v.vno,v.vtype,v.narration,l.debit,l.credit FROM lines l JOIN vouchers v ON v.id=l.voucher_id WHERE l.account_id=? ORDER BY v.vdate,v.id",(aid,)).fetchall()
    bal=(a["opening"] if a["opening_type"]=="Dr" else -a["opening"]);out=[]
    for r in rows:bal+=r["debit"]-r["credit"];out.append(dict(r,balance=bal))
    return render_template("ledger.html",account=a,rows=out)
@app.route("/reports")
def reports():
    x=db();out=[]
    for a in x.execute("SELECT * FROM accounts ORDER BY name"):
        t=x.execute("SELECT COALESCE(SUM(debit),0) dr,COALESCE(SUM(credit),0) cr FROM lines WHERE account_id=?",(a["id"],)).fetchone();b=(a["opening"] if a["opening_type"]=="Dr" else -a["opening"])+t["dr"]-t["cr"];out.append((a,b))
    return render_template("reports.html",data=out)
@app.route("/outstanding")
def outstanding():
    x=db();out=[]
    for a in x.execute("SELECT * FROM accounts WHERE is_party=1 ORDER BY name"):
        b=(a["opening"] if a["opening_type"]=="Dr" else -a["opening"])+x.execute("SELECT COALESCE(SUM(debit-credit),0) b FROM lines WHERE account_id=?",(a["id"],)).fetchone()["b"];out.append((a,b))
    return render_template("outstanding.html",rows=out)
@app.route("/export")
def export():
    x=db();rows=x.execute("SELECT vdate,vno,vtype,amount,mode,narration FROM vouchers ORDER BY vdate,id").fetchall()
    s="Date,Voucher,Type,Amount,Mode,Narration\n"+"\n".join(",".join('"'+str(v or "").replace('"','""')+'"' for v in r) for r in rows)
    return Response(s,mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=ledger.csv"})
@app.route("/health")
def health():return {"status":"ok"}
init()
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.getenv("PORT",5000)))