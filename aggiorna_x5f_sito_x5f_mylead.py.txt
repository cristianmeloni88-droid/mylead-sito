"""
SHARDAN - MyLead -> Sito: 10 App + 10 Giochi OGNI ORA, i più pagati in alto!
Fa login con MYLEAD_USERNAME / MYLEAD_PASSWORD
Ordina per payout (più pagati prima) e aggiorna index.html
NON mostra payout, NON posta su Telegram!
"""
import os, re, requests
BASE="https://api.mylead.global/api/external/v1"

def login():
    user=os.environ.get("MYLEAD_USERNAME","").strip()
    pwd=os.environ.get("MYLEAD_PASSWORD","").strip()
    if not user or not pwd:
        print("Manca MYLEAD_USERNAME o MYLEAD_PASSWORD nei Secrets!")
        return None
    print(f"Login MyLead come {user}...")
    for payload in [{"username":user,"password":pwd},{"email":user,"password":pwd},{"login":user,"password":pwd}]:
        try:
            r=requests.post(f"{BASE}/auth/login", json=payload, timeout=20)
            print(f"POST /auth/login -> {r.status_code}")
            if r.status_code==200:
                data=r.json()
                tok=data.get("token") or data.get("access_token") or (data.get("data",{}).get("token") if isinstance(data,dict) else None)
                if tok:
                    print("Login OK!")
                    return tok
        except Exception as e:
            print(f"Errore login: {e}")
    return None

def prendi_offerte(tok):
    headers={"Authorization": f"Bearer {tok}"}
    for ep in ["/campaigns","/offers"]:
        try:
            r=requests.get(f"{BASE}{ep}", headers=headers, timeout=20)
            print(f"GET {ep} -> {r.status_code}")
            if r.status_code!=200:
                continue
            data=r.json()
            lst=data if isinstance(data,list) else data.get("campaigns", data.get("data", data.get("offers",[])))
            apps=[]; giochi=[]
            for o in lst:
                if not isinstance(o,dict): continue
                nome=(o.get("name","") or "").strip()
                link=(o.get("link","") or o.get("tracking_link","") or o.get("url","") or "").strip()
                if not nome or not link: continue
                try:
                    pay=float(o.get("payout",0) or o.get("rate",0) or o.get("price",0) or 0)
                except:
                    pay=0
                cat=(str(o.get("category",""))+" "+str(o.get("type",""))+" "+nome).lower()
                is_gioco=any(k in cat for k in ["game","gioco","play","casino","gaming"])
                item={"nome":nome,"link":link,"payout":pay}
                if is_gioco:
                    giochi.append(item)
                else:
                    apps.append(item)
            # ORDINA PER PAYOUT: i più pagati in alto!
            apps.sort(key=lambda x: x["payout"], reverse=True)
            giochi.sort(key=lambda x: x["payout"], reverse=True)
            print(f"Trovate: {len(apps)} App, {len(giochi)} Giochi - Top per payout:")
            for p in apps[:10]:
                print(f"  APP: {p['nome'][:50]} | payout {p['payout']}")
            for p in giochi[:10]:
                print(f"  GIOCO: {p['nome'][:50]} | payout {p['payout']}")
            return apps[:10], giochi[:10]
        except Exception as e:
            print(f"Errore {ep}: {e}")
    return [], []

def aggiorna_html(apps, giochi):
    path="index.html"
    t=open(path,encoding="utf-8").read()
    for i, p in enumerate(apps,1):
        t=re.sub(rf'(<span class="tag">APP • #{i}</span><b>)[^<]+(</b>)', rf'\g<1>{p["nome"][:70]}\g<2>', t)
    for i, p in enumerate(giochi,1):
        t=re.sub(rf'(<span class="tag">GIOCO • #{i}</span><b>)[^<]+(</b>)', rf'\g<1>{p["nome"][:70]}\g<2>', t)
    links=[p["link"] for p in apps]+[p["link"] for p in giochi]
    idx=0
    def repl(m):
        nonlocal idx
        if idx < len(links):
            v=f'href="{links[idx]}"'
            idx+=1
            return v
        return m.group(0)
    t=re.sub(r'href="#"', repl, t)
    open(path,"w",encoding="utf-8").write(t)
    print(f"Sito aggiornato! 10 App + 10 Giochi, i più pagati in alto!")

if __name__=="__main__":
    tok=login()
    if not tok: exit()
    apps, giochi=prendi_offerte(tok)
    if not apps and not giochi:
        print("Nessuna offerta - sito invariato")
        exit()
    aggiorna_html(apps, giochi)
