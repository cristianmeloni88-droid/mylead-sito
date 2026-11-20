"""
SHARDAN - MyLead -> Sito: 10 App + 10 Giochi OGNI ORA, i piu pagati in alto!
FIX TOKEN: cerca il token in TUTTI i campi possibili!
"""
import os, re, requests, json
BASE="https://api.mylead.global/api/external/v1"

def trova_token(data):
    # Cerca il token in tutti i campi possibili, anche annidati!
    if isinstance(data, str):
        return data if len(data)>20 else None
    if not isinstance(data, dict):
        return None
    # Chiavi dirette - prova TUTTE le varianti
    for k in ["token","access_token","accessToken","auth_token","authToken","jwt","api_token","apiToken","session_token","sessionToken","key","access"]:
        if k in data and isinstance(data[k], str) and len(data[k])>10:
            print(f"Token trovato in campo: {k}")
            return data[k]
    # Cerca dentro data / result / payload
    for k in ["data","result","payload","response","auth"]:
        if k in data:
            t=trova_token(data[k])
            if t:
                return t
    # Cerca in qualsiasi valore stringa lungo che sembra un token
    for k,v in data.items():
        if isinstance(v, str) and len(v)>30 and "." in v:
            print(f"Token trovato in campo generico: {k}")
            return v
    return None

def login():
    user=os.environ.get("MYLEAD_USERNAME","").strip()
    pwd=os.environ.get("MYLEAD_PASSWORD","").strip()
    if not user or not pwd:
        print("Manca MYLEAD_USERNAME o MYLEAD_PASSWORD!")
        return None
    print(f"Login MyLead come {user}...")
    for payload in [{"username":user,"password":pwd},{"email":user,"password":pwd},{"login":user,"password":pwd}]:
        try:
            r=requests.post(f"{BASE}/auth/login", json=payload, timeout=20)
            print(f"POST /auth/login con {list(payload.keys())} -> {r.status_code}")
            if r.status_code==200:
                try:
                    data=r.json()
                except:
                    print(f"Risposta non JSON: {r.text[:200]}")
                    continue
                print(f"Chiavi risposta login: {list(data.keys()) if isinstance(data,dict) else type(data)}")
                tok=trova_token(data)
                if tok:
                    print(f"Login OK! Token preso! Lunghezza: {len(tok)}")
                    return tok
                else:
                    print(f"Token NON trovato in risposta! Risposta (primi 300 caratteri, senza token completo): {str(data)[:300]}")
                    continue
            else:
                print(f"Risposta: {r.text[:200]}")
        except Exception as e:
            print(f"Errore login: {e}")
    print("Login fallito - controlla username/password!")
    return None

def prendi_offerte(tok):
    # Prova diversi modi di mandare il token
    header_variants=[
        {"Authorization": f"Bearer {tok}"},
        {"Authorization": tok},
        {"X-Auth-Token": tok},
        {"Api-Key": tok},
        {"X-API-Key": tok},
    ]
    for headers in header_variants:
        for ep in ["/campaigns","/offers"]:
            try:
                r=requests.get(f"{BASE}{ep}", headers=headers, timeout=20)
                print(f"GET {ep} con {list(headers.keys())} -> {r.status_code}")
                if r.status_code!=200:
                    print(f"Risposta: {r.text[:200]}")
                    continue
                data=r.json()
                lst=data if isinstance(data,list) else data.get("campaigns", data.get("data", data.get("offers",[])))
                if not isinstance(lst, list):
                    print(f"Formato strano: {type(lst)} - chiavi: {list(data.keys()) if isinstance(data,dict) else ''}")
                    continue
                print(f"Ricevute {len(lst)} offerte totali!")
                if len(lst)>0:
                    print(f"Esempio prima offerta - chiavi: {list(lst[0].keys()) if isinstance(lst[0],dict) else type(lst[0])}")
                apps=[]; giochi=[]
                for o in lst:
                    if not isinstance(o,dict): continue
                    nome=(o.get("name","") or o.get("title","") or "").strip()
                    link=(o.get("link","") or o.get("tracking_link","") or o.get("trackingLink","") or o.get("url","") or o.get("offer_url","") or "").strip()
                    if not nome or not link: continue
                    try:
                        pay=float(o.get("payout",0) or o.get("rate",0) or o.get("price",0) or o.get("payout_rate",0) or 0)
                    except:
                        pay=0
                    cat=(str(o.get("category",""))+" "+str(o.get("type",""))+" "+nome).lower()
                    is_gioco=any(k in cat for k in ["game","gioco","play","casino","gaming"])
                    item={"nome":nome,"link":link,"payout":pay}
                    if is_gioco: giochi.append(item)
                    else: apps.append(item)
                apps.sort(key=lambda x: x["payout"], reverse=True)
                giochi.sort(key=lambda x: x["payout"], reverse=True)
                print(f"Trovate: {len(apps)} App, {len(giochi)} Giochi")
                for p in apps[:3]: print(f"  APP TOP: {p['nome'][:50]} | {p['payout']}")
                for p in giochi[:3]: print(f"  GIOCO TOP: {p['nome'][:50]} | {p['payout']}")
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
    print(f"Sito aggiornato! 10 App + 10 Giochi!")

if __name__=="__main__":
    tok=login()
    if not tok: exit()
    apps, giochi=prendi_offerte(tok)
    if not apps and not giochi:
        print("Nessuna offerta - sito invariato")
        exit()
    aggiorna_html(apps, giochi)
