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
    headers={"Authorization": f"Bearer {tok}"}
    apps=[]; giochi=[]; visti=set()
    # Cerca in 10 pagine (1000 offerte) finche' trova 10 App IT + 10 Giochi IT!
    for page in range(1, 11):
        if len(apps)>=10 and len(giochi)>=10:
            break
        try:
            r=requests.get(f"{BASE}/campaigns?page={page}&limit=100", headers=headers, timeout=20)
            print(f"GET /campaigns?page={page}&limit=100 -> {r.status_code}")
            if r.status_code!=200:
                print(f"Risposta: {r.text[:200]}")
                continue
            data=r.json()
            lst=[]
            if isinstance(data, list):
                lst=data
            elif isinstance(data, dict):
                d=data.get("data")
                if isinstance(d, list):
                    lst=d
                elif isinstance(d, dict):
                    for v in d.values():
                        if isinstance(v, list):
                            lst=v
                            break
                    if not lst:
                        lst=data.get("campaigns", data.get("offers",[]))
                else:
                    lst=data.get("campaigns", data.get("offers",[]))
            print(f"Pagina {page}: {len(lst)} offerte")
            for o in lst:
                if not isinstance(o,dict): continue
                oid=o.get("id")
                if oid in visti: continue
                visti.add(oid)
                nome=(o.get("name","") or o.get("title","") or "").strip()
                link=(o.get("preview_url","") or o.get("link","") or o.get("tracking_link","") or o.get("url","") or "").strip()
                if not nome or not link: continue
                # FILTRO ITALIA! Solo offerte per IT!
                countries=o.get("countries", [])
                country_str=""
                if isinstance(countries, list):
                    for c in countries:
                        if isinstance(c, dict):
                            country_str+=str(c.get("code",""))+" "+str(c.get("name",""))+" "
                        else:
                            country_str+=str(c)+" "
                elif isinstance(countries, dict):
                    country_str+=str(countries.get("code",""))+" "+str(countries.get("name",""))
                else:
                    country_str+=str(countries)
                # Anche description_lang e lingue
                lang_str=str(o.get("description_lang",""))+" "+str(o.get("short_description_lang",""))+" "+str(o.get("language",""))
                is_italia = "IT" in country_str.upper() or "ITAL" in country_str.upper() or "ITALY" in country_str.upper()
                # Se countries e' vuoto, accetta (alcune offerte sono worldwide)
                if countries and not is_italia:
                    continue
                # Se countries ha IT, ok. Se ha solo altre lingue, salta.
                # Payout da payments
                pay=0
                try:
                    pay=float(o.get("payout",0) or o.get("rate",0) or o.get("price",0) or o.get("epc",0) or 0)
                except:
                    pay=0
                pays=o.get("payments")
                if pays:
                    try:
                        if isinstance(pays, list):
                            for p in pays:
                                if isinstance(p, dict):
                                    for k in ["payout","amount","value","rate","price","commission","cpa"]:
                                        if k in p and p[k]:
                                            pay=max(pay, float(p[k]))
                        elif isinstance(pays, dict):
                            for k in ["payout","amount","value","rate","price"]:
                                if k in pays and pays[k]:
                                    pay=max(pay, float(pays[k]))
                    except:
                        pass
                # Categoria
                cats=o.get("categories", o.get("category",""))
                cat_str=""
                if isinstance(cats, list):
                    for c in cats:
                        if isinstance(c, dict):
                            cat_str+=str(c.get("name",""))+" "+str(c.get("slug",""))+" "
                        else:
                            cat_str+=str(c)+" "
                elif isinstance(cats, dict):
                    cat_str+=str(cats.get("name",""))
                else:
                    cat_str+=str(cats)
                cat=(cat_str+" "+str(o.get("type",""))+" "+nome).lower()
                is_gioco=any(k in cat for k in ["game","gioco","play","casino","gaming","bet","sport","poker","slot","gambling","scommesse","lottery","bingo","fantasy"])
                # Pulisci nome: togli " - PL", " - DE" etc. se rimane
                nome_pulito=nome
                item={"nome":nome_pulito,"link":link,"payout":pay}
                if is_gioco:
                    if len(giochi)<10 and nome not in [g["nome"] for g in giochi]:
                        giochi.append(item)
                else:
                    if len(apps)<10 and nome not in [a["nome"] for a in apps]:
                        apps.append(item)
            print(f"Dopo pagina {page}: {len(apps)} App IT, {len(giochi)} Giochi IT")
        except Exception as e:
            print(f"Errore pagina {page}: {e}")
    apps.sort(key=lambda x: x["payout"], reverse=True)
    giochi.sort(key=lambda x: x["payout"], reverse=True)
    # Se Giochi IT < 10, riempi con altre offerte IT non usate (per non lasciare Gioco 2, Gioco 3 vuoti)
    # Lo facciamo cercando tra tutte le offerte IT gia' viste - per ora se mancano, lascia cosi' ma logga
    print(f"Trovate FINALI: {len(apps)} App IT, {len(giochi)} Giochi IT")
    for p in apps[:3]: print(f"  APP IT TOP: {p['nome'][:50]} | {p['payout']}")
    for p in giochi[:3]: print(f"  GIOCO IT TOP: {p['nome'][:50]} | {p['payout']}")
    return apps[:10], giochi[:10]

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
