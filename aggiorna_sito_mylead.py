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
    import os as _os, json as _json
    headers={"Authorization": f"Bearer {tok}"}
    apps=[]; giochi=[]; visti=set()
    apps_backup=[]; giochi_backup=[]
    # Cerca in 10 pagine (1000 offerte). Prima IT, poi resto mondo per riempire!
    for page in range(1, 31):  # 30 pagine = 3000 offerte! Cerca piu' Giochi IT!
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
                # LOCANDINA GIUSTA AL POSTO GIUSTO: legata a QUESTA offerta, mai a caso!
                img=""
                # 1. PRIMA la tua in locandine.json (vince sempre!)
                try:
                    loc_map={}
                    if _os.path.exists("locandine.json"):
                        loc_map=_json.load(open("locandine.json",encoding="utf-8"))
                    # Cerca per nome esatto E per link (cosi' non si scambia mai!)
                    if nome in loc_map:
                        img=loc_map[nome]
                        print(f"  IMG TUA per {nome[:30]} -> {img}")
                    elif link in loc_map:
                        img=loc_map[link]
                        print(f"  IMG TUA per link {nome[:30]} -> {img}")
                except Exception as e:
                    print(f"  Errore locandine.json: {e}")
                if not img:
                    # Cerca in TUTTI i campi possibili di MyLead, solo se e' un'immagine vera!
                    def is_img(url):
                        if not isinstance(url,str): return False
                        u=url.lower()
                        return u.startswith("http") and (".jpg" in u or ".jpeg" in u or ".png" in u or ".webp" in u or ".gif" in u or "image" in u or "logo" in u or "icon" in u or "cdn" in u or "media" in u)
                    for k in ["image","icon","logo","banner","preview_image","previewImage","thumbnail","cover","picture","creative","image_url","icon_url","logo_url","imageUrl","logoUrl","app_icon","appIcon","offer_image"]:
                        v=o.get(k)
                        if is_img(v):
                            img=v; break
                        if isinstance(v,dict):
                            for kk in ["url","src","link","href"]:
                                if is_img(v.get(kk)):
                                    img=str(v.get(kk)); break
                            if img: break
                        if isinstance(v,list) and len(v)>0:
                            for it2 in v:
                                if is_img(it2):
                                    img=it2; break
                                if isinstance(it2,dict) and is_img(it2.get("url")):
                                    img=str(it2.get("url")); break
                            if img: break
                    # Anche dentro creatives / details / info
                    if not img:
                        for kk in ["creatives","details","info","media","assets"]:
                            vv=o.get(kk)
                            if isinstance(vv,list):
                                for c in vv:
                                    if isinstance(c,dict):
                                        for k2 in ["url","image","src","link"]:
                                            if is_img(c.get(k2)):
                                                img=str(c.get(k2)); break
                                    if img: break
                            if img: break
                    if img:
                        print(f"  IMG MyLead per {nome[:30]} -> {img[:80]}")
                    else:
                        print(f"  NESSUNA IMG per {nome[:30]} -> lascio icona, non metto immagine a caso!")
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
                # NUOVA REGOLA PIU' LARGA: IT + Mondiale + Europa = OK per Italia!
                # Perche' molti Giochi sono mondiali e funzionano anche in Italia!
                up=country_str.upper()
                is_italia = ("IT" in up or "ITAL" in up or "ITALY" in up or "WW" in up or "WORLDWIDE" in up or "WORLD" in up or "EU" in up or "EUROPE" in up or "ALL" in up or "GLOBAL" in up)
                # Se countries e' vuoto = mondiale = OK
                if not countries:
                    is_italia=True
                # FILTRO NOME: se il nome finisce con - DE, - PL, - FR, - ES, - VN, - CZ, - SK, - RO, - HU... NON e' italiano!
                nome_upper=nome.upper()
                suffissi_stranieri=[" - DE"," - PL"," - FR"," - ES"," - VN"," - CZ"," - SK"," - RO"," - HU"," - BG"," - HR"," - RS"," - UA"," - RU"," - TR"," - BR"," - MX"," - PT"," - NL"," - BE"," - AT"," - CH"," - GR"," - DK"," - SE"," - NO"," - FI"," - LT"," - LV"," - EE"]
                # Se nome ha - DE / - PL MA countries ha IT, tienilo (e' versione italiana!)
                # Se nome ha - DE e countries NON ha IT, scarta (e' solo tedesco!)
                has_it_esplicito = "IT" in up or "ITAL" in up or "ITALY" in up
                if any(s in nome_upper for s in suffissi_stranieri) and not has_it_esplicito:
                    is_italia=False
                    print(f"  SCARTATO (APP o GIOCO) per nome straniero: {nome}")
                # Se countries e' vuoto ma nome ha suffisso straniero, e' straniero lo stesso!
                # REGOLA UGUALE PER APP E GIOCHI: se non e' IT, e' backup = da buttare!
                # Prima lo mettevamo in backup per riempire, ora lo scartiamo per entrambi!
                is_backup = bool(countries) and not is_italia
                if is_backup:
                    print(f"  SCARTATO (APP o GIOCO) non IT: {nome} - paesi: {country_str[:80]}")
                    continue
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
                # GIOCO ALLARGATO: prima controllava solo categoria Game, ora anche nome!
                # Perche' MyLead mette molti Giochi sotto Entertainment / Adult!
                parole_gioco=["game","gioco","play","casino","gaming","bet","sport","poker","slot","gambling","scommesse","lottery","bingo","fantasy","esport","esports","arcade","rpg","shooter","racing","football","soccer","basket","chess","scacchi","war","battle","quest","adventure","avventura","corsa","corse","calcio","slot","spin","jackpot","vegas","cards","carte","dadi","tombola","gratta","win","vincita"]
                is_gioco=any(k in cat for k in parole_gioco)
                # Se categoria e' Entertainment/Adult ma nome sembra gioco, conta come gioco!
                if not is_gioco and any(k in cat for k in ["entertainment","adult","intrattenimento"]):
                    if any(k in nome.lower() for k in ["game","play","sport","bet","casino","slot","poker","esport","fantasy","race","war","battle","quest"]):
                        is_gioco=True
                        print(f"  GIOCO trovato in Entertainment/Adult: {nome}")
                # Pulisci nome: togli " - PL", " - DE" etc. se rimane
                nome_pulito=nome
                item={"nome":nome_pulito,"link":link,"payout":pay,"img":img}
                if is_gioco:
                    if is_backup:
                        if nome not in [g["nome"] for g in giochi_backup]:
                            giochi_backup.append(item)
                    else:
                        if len(giochi)<10 and nome not in [g["nome"] for g in giochi]:
                            giochi.append(item)
                else:
                    if is_backup:
                        if nome not in [a["nome"] for a in apps_backup]:
                            apps_backup.append(item)
                    else:
                        if len(apps)<10 and nome not in [a["nome"] for a in apps]:
                            apps.append(item)
            print(f"Dopo pagina {page}: {len(apps)} App IT, {len(giochi)} Giochi IT")
        except Exception as e:
            print(f"Errore pagina {page}: {e}")
    # NO BACKUP STRANIERO! Solo italiani! Meglio 3 italiani veri che 10 stranieri!
    # apps_backup e giochi_backup li buttiamo via, non li usiamo piu'!
    print(f"Backup stranieri scartati: {len(giochi_backup)} giochi, {len(apps_backup)} app straniere NON usate!")
    apps.sort(key=lambda x: x["payout"], reverse=True)
    giochi.sort(key=lambda x: x["payout"], reverse=True)
    # Se Giochi IT < 10, riempi con altre offerte IT non usate (per non lasciare Gioco 2, Gioco 3 vuoti)
    # Lo facciamo cercando tra tutte le offerte IT gia' viste - per ora se mancano, lascia cosi' ma logga
    print(f"Trovate FINALI IT + MONDIALI + EU (compatibili Italia): {len(apps)} App, {len(giochi)} Giochi (cercate in 3000 offerte!)")
    for p in apps[:3]: print(f"  APP IT TOP: {p['nome'][:50]} | {p['payout']}")
    for p in giochi[:3]: print(f"  GIOCO IT TOP: {p['nome'][:50]} | {p['payout']}")
    return apps[:10], giochi[:10]

def aggiorna_html(nuove_apps, nuovi_giochi):
    # ARCHIVIO: le nuove in alto, le vecchie restano! Mai cancellare!
    import json as _json, os as _os, re as _re
    arch_path="archivio.json"
    arch={"apps":[],"giochi":[]}
    if _os.path.exists(arch_path):
        try:
            arch=_json.load(open(arch_path,encoding="utf-8"))
        except:
            arch={"apps":[],"giochi":[]}
    # Se archivio vuoto ma index.html vecchio ha dati, non serve: partiamo da vuoto
    # Unisci: nuove prima, poi vecchie, senza duplicati per link
    def unisci(nuove, vecchie):
        out=[]; visti=set()
        # PULIZIA ARCHIVIO UGUALE PER APP E GIOCHI: butta via i vecchi stranieri gia' salvati prima!
        suffissi=[" - DE"," - PL"," - FR"," - ES"," - VN"," - CZ"," - SK"," - RO"," - HU"," - BG"," - HR"," - RS"," - UA"," - RU"," - TR"," - BR"," - MX"," - PT"," - NL"," - BE"," - AT"," - CH"," - GR"," - DK"," - SE"," - NO"," - FI"," - LT"," - LV"," - EE"]
        vecchie_pulite=[]
        for v in vecchie:
            n=str(v.get("nome","")).upper()
            if any(s in n for s in suffissi):
                print(f"  RIMOSSO da archivio (straniero): {v.get('nome')}")
                continue
            vecchie_pulite.append(v)
        vecchie=vecchie_pulite
        # Mappa vecchie img per link: se nuova non ha img, tieni la vecchia GIUSTA!
        vecchie_per_link={ (v.get("link","") or ""): v.get("img","") for v in vecchie }
        for it in list(nuove)+list(vecchie):
            # Se questa e' nuova e non ha img, ma la vecchia con stesso link ce l'aveva, tienila!
            if not it.get("img") and vecchie_per_link.get(it.get("link","")):
                it=dict(it); it["img"]=vecchie_per_link[it.get("link","")]
            link=(it.get("link","") or "").strip()
            if not link or link=="#" or link in visti: continue
            visti.add(link)
            out.append({"nome":str(it.get("nome",""))[:80],"link":link,"img":it.get("img","")})
        return out[:200]  # max 200 per tipo, per non far diventare il sito pesante
    arch["apps"]=unisci(nuove_apps, arch.get("apps",[]))
    arch["giochi"]=unisci(nuovi_giochi, arch.get("giochi",[]))
    open(arch_path,"w",encoding="utf-8").write(_json.dumps(arch,ensure_ascii=False,indent=2))
    print(f"Archivio: {len(arch['apps'])} App totali, {len(arch['giochi'])} Giochi totali (vecchie + nuove)!")
    # Rigenera index.html con i dati dell'archivio
    t=open("index.html",encoding="utf-8").read()
    # Se index.html e' quello vecchio (senza /*APPS_JSON*/), usa il nuovo template gia' caricato
    # Sostituisci i segnaposto con i dati veri
    apps_json=_json.dumps(arch["apps"],ensure_ascii=False)
    giochi_json=_json.dumps(arch["giochi"],ensure_ascii=False)
    # Sostituisci sia i segnaposto vuoti sia eventuali dati vecchi gia' inseriti
    t=_re.sub(r"/\*APPS_JSON\*/\[.*?\]", f"/*APPS_JSON*/{apps_json}", t, flags=_re.DOTALL)
    t=_re.sub(r"/\*GIOCHI_JSON\*/\[.*?\]", f"/*GIOCHI_JSON*/{giochi_json}", t, flags=_re.DOTALL)
    # Fallback: se non c'erano segnaposto (vecchio template), sostituisci il primo [] dopo APPS
    if "/*APPS_JSON*/" not in t:
        print("ATTENZIONE: index.html vecchio! Carica il nuovo index.html con i tasti Successivo!")
    open("index.html","w",encoding="utf-8").write(t)
    print(f"Sito aggiornato! Pagina 1 = 10 nuove, Successivo = vecchie! Totale {len(arch['apps'])+len(arch['giochi'])}")

if __name__=="__main__":
    tok=login()
    if not tok: exit()
    apps, giochi=prendi_offerte(tok)
    if not apps and not giochi:
        print("Nessuna offerta - sito invariato")
        exit()
    aggiorna_html(apps, giochi)
