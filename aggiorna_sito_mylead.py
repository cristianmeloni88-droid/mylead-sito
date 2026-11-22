"""
SHARDAN - MyLead -> Sito: 10 App + 10 Giochi OGNI ORA, i piu pagati in alto!
FIX TOKEN: cerca il token in TUTTI i campi possibili!
"""
import os, re, requests, json
BASE="https://api.mylead.global/api/external/v1"  # CORRETTO 22 NOV SERA: SENZA _ ! Quello con _ non esiste, DNS fallisce!

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
                if tok and tok.lower().startswith("bearer "):
                    tok=tok[7:].strip()
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
    headers={"Authorization": f"Bearer {tok}", "Accept": "application/json", "User-Agent": "ShardanBot/1.0"}
    apps=[]; giochi=[]; visti=set()
    apps_backup=[]; giochi_backup=[]
    # Cerca in 10 pagine (1000 offerte). Prima IT, poi resto mondo per riempire!
    # CORRETTO: endpoint vero = /campaigns (quello che dava 200 nel log!)
    # Proviamo prima /campagna, se da 404 proviamo /campaigns
    endpoint_campagna = "/campaigns"  # Quello che funziona! /campagna dava 404!
    for page in range(1, 31):  # 30 pagine = 3000 offerte! Cerca piu' Giochi IT!
        if len(apps)>=10 and len(giochi)>=10:
            break
        try:
            r=requests.get(f"{BASE}{endpoint_campagna}?page={page}&limit=100", headers=headers, timeout=20)
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
    import json as _json, os as _os
    arch_path="archivio.json"
    arch={"apps":[],"giochi":[]}
    if _os.path.exists(arch_path):
        try:
            arch=_json.load(open(arch_path,encoding="utf-8"))
        except:
            arch={"apps":[],"giochi":[]}
    def unisci(nuove, vecchie):
        out=[]; visti=set()
        suffissi=[" - DE"," - PL"," - FR"," - ES"," - VN"," - CZ"," - SK"," - RO"," - HU"," - BG"," - HR"," - RS"," - UA"," - RU"," - TR"," - BR"," - MX"," - PT"," - NL"," - BE"," - AT"," - CH"," - GR"," - DK"," - SE"," - NO"," - FI"," - LT"," - LV"," - EE"]
        vecchie_pulite=[]
        for v in vecchie:
            n=str(v.get("nome","")).upper()
            if any(s in n for s in suffissi):
                continue
            vecchie_pulite.append(v)
        vecchie=vecchie_pulite
        vecchie_per_link={ (v.get("link","") or ""): v.get("img","") for v in vecchie }
        for it in list(nuove)+list(vecchie):
            if not it.get("img") and vecchie_per_link.get(it.get("link","")):
                it=dict(it); it["img"]=vecchie_per_link[it.get("link","")]
            link=(it.get("link","") or "").strip()
            if not link or link=="#" or link in visti: continue
            visti.add(link)
            out.append({"nome":str(it.get("nome",""))[:80],"link":link,"img":it.get("img","")})
        return out[:200]
    arch["apps"]=unisci(nuove_apps, arch.get("apps",[]))
    arch["giochi"]=unisci(nuovi_giochi, arch.get("giochi",[]))
    open(arch_path,"w",encoding="utf-8").write(_json.dumps(arch,ensure_ascii=False,indent=2))
    print(f"Archivio salvato: {len(arch['apps'])} App, {len(arch['giochi'])} Giochi!")
    apps_json=_json.dumps(arch["apps"],ensure_ascii=False)
    giochi_json=_json.dumps(arch["giochi"],ensure_ascii=False)
    # === TEMPLATE COMPLETO - riscrive index.html da zero, non dipende dal vecchio! ===
    html = """<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CACCIATORE DI GIOCHI E APPLICAZIONI</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(160deg,#000000,#0a0a2e,#0d3b2e,#2b0a4a);background-attachment:fixed;color:#fff;font-family:Arial,sans-serif;text-align:center;padding:14px;min-height:100vh}
.top{font-size:13px;color:#00ff66;letter-spacing:2px;margin:6px 0 10px;font-weight:bold}
.principale{background:linear-gradient(135deg,#111827,#1e1b4b,#065f46);border:3px solid #00ff66;border-radius:22px;padding:22px 16px;margin:10px auto;max-width:560px;box-shadow:0 0 30px rgba(0,255,102,.45)}
.logo{width:100%;max-width:340px;height:auto;border-radius:16px;border:3px solid #00ff66;object-fit:contain;box-shadow:0 0 20px #00ff66;background:#000}
h1{font-size:32px;margin:12px 0 4px;background:linear-gradient(90deg,#00ff66,#00e5ff,#ffcc00);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sotto{color:#d1d5db;font-size:15px;margin-bottom:10px}
.badge{display:inline-block;background:#00ff66;color:#000;font-weight:bold;padding:6px 14px;border-radius:20px;font-size:13px;margin:4px}
.badge-blu{background:#00e5ff}
.badge-giallo{background:#ffcc00}
.desc{background:rgba(255,255,255,.08);border-radius:14px;padding:12px;margin:14px 0;font-size:14px;line-height:1.6}
.btn{display:inline-block;padding:13px 24px;border-radius:25px;text-decoration:none;font-weight:bold;margin:6px;font-size:15px}
.btn-tg{background:#0088cc;color:#fff;box-shadow:0 4px 0 #005580}
.btn-tt{background:#fff;color:#000;box-shadow:0 4px 0 #aaa}
.mini{font-size:12px;color:#9ca3af;margin-top:10px}
.secondaria{border-radius:22px;padding:18px 14px;margin:16px auto;max-width:560px}
.app-box{background:linear-gradient(135deg,#0ea5e9,#2563eb,#7c3aed);border:3px solid #38bdf8;box-shadow:0 0 22px rgba(56,189,248,.45)}
.giochi-box{background:linear-gradient(135deg,#f97316,#ef4444,#a21caf);border:3px solid #fb923c;box-shadow:0 0 22px rgba(251,146,60,.45)}
.secondaria h2{font-size:26px;margin-bottom:4px}
.secondaria .sottotitolo{font-size:13px;opacity:.9;margin-bottom:12px}
.card{background:rgba(255,255,255,.95);color:#111;border-radius:14px;padding:12px;margin:10px 0;text-align:left;display:flex;gap:12px;align-items:center}
.card-info{flex:1;min-width:0}
.card b{font-size:18px}
.locandina{width:84px;height:84px;min-width:84px;object-fit:cover;border-radius:12px;background:#eee;display:block;border:2px solid #eee}
.locandina-fallback{width:84px;height:84px;min-width:84px;border-radius:12px;background:linear-gradient(135deg,#111827,#065f46);display:flex;align-items:center;justify-content:center;font-size:38px;flex-shrink:0}
.card .tag{display:inline-block;background:#111;color:#fff;font-size:11px;padding:4px 8px;border-radius:10px;margin-bottom:6px}
.card p{color:#555;font-size:13px;margin:6px 0 10px}
.btn-verde{background:linear-gradient(90deg,#00ff66,#00ccff);color:#000;padding:10px 18px;border-radius:20px;text-decoration:none;font-weight:bold;display:inline-block;font-size:14px}
.btn-arancio{background:linear-gradient(90deg,#ffcc00,#ff6b00);color:#000;padding:10px 18px;border-radius:20px;text-decoration:none;font-weight:bold;display:inline-block;font-size:14px}
.nav{display:flex;justify-content:space-between;align-items:center;gap:8px;margin:16px 0 4px}
.nav-btn{background:#fff;color:#111;border:none;padding:12px 18px;border-radius:22px;font-weight:bold;font-size:15px;cursor:pointer;box-shadow:0 3px 0 #aaa}
.nav-btn:disabled{opacity:.35;cursor:default;box-shadow:none}
.nav-info{font-size:13px;font-weight:bold;background:rgba(0,0,0,.35);padding:8px 12px;border-radius:16px}
.footer{color:#aaa;font-size:12px;margin:20px 0;line-height:1.7}
</style>
</head>
<body>
<div class="top">✦ SHARDANFIGHTER AFFILIATES ✦</div>
<div class="principale">
<img class="logo" src="Meta_AI_916953475_1358533226248945_6687323588161160706_n_20261120_165054.webp" alt="CacciatoreDiOfferte">
<h1>CACCIATORE DI GIOCHI E APPLICAZIONI</h1>
<div class="sotto">App e Giochi - di Shardan 🏹</div>
<span class="badge">🔥 <span id="totale">20</span> SCELTE - APP + GIOCHI</span>
<span class="badge badge-blu">✦ NUOVO OGNI ORA</span>
<span class="badge badge-giallo">⭐ ARCHIVIO SEMPRE QUI</span>
<div class="desc">Benvenuto nella tana del Cacciatore! 🏹<br>Qui trovi le <b>App</b> e i <b>Giochi</b> che ho scelto per te.<br>Le nuove vanno in alto, le vecchie restano! Usa <b>Successivo ➡️</b> per vedere quelle di prima!<br><b>Io caccio, tu scopri!</b> 💚</div>
<a class="btn btn-tg" href="https://t.me/+J6anDQ24gC41MDM8">📱 Telegram - Offerte</a>
<a class="btn btn-tt" href="https://www.tiktok.com/@shardanfighter1237">🎵 TikTok - @shardanfighter1237</a>
<div class="mini">👇 Scorri giù per App e Giochi 👇</div>
</div>
<div class="secondaria app-box">
<h2>📱 APP</h2>
<div class="sottotitolo">App scelte da Shardan • Le nuove in alto • Aggiornate ogni ora • Le vecchie restano!</div>
<div id="app-list"></div>
<div class="nav"><button class="nav-btn" id="app-prev" onclick="cambiaPagina('app',-1)">⬅️ Precedente</button><span class="nav-info" id="app-info">Pagina 1</span><button class="nav-btn" id="app-next" onclick="cambiaPagina('app',1)">Successivo ➡️</button></div>
</div>
<div class="secondaria giochi-box">
<h2>🎮 GIOCHI</h2>
<div class="sottotitolo">Giochi scelti da Shardan • I nuovi in alto • Aggiornati ogni ora • Le vecchie restano!</div>
<div id="giochi-list"></div>
<div class="nav"><button class="nav-btn" id="giochi-prev" onclick="cambiaPagina('giochi',-1)">⬅️ Precedente</button><span class="nav-info" id="giochi-info">Pagina 1</span><button class="nav-btn" id="giochi-next" onclick="cambiaPagina('giochi',1)">Successivo ➡️</button></div>
</div>
<div class="footer">CacciatoreDiOfferte di Shardan - App e Giochi<br>Le App e i Giochi ti portano sul sito ufficiale del partner.<br>🏹 Buona caccia!</div>
<script>
const APPS = /*APPS_JSON*/__APPS__;
const GIOCHI = /*GIOCHI_JSON*/__GIOCHI__;
let pagApp=0, pagGiochi=0; const PER=10;
function disegna(tipo){
  const lista = tipo==='app'?APPS:GIOCHI;
  const pag = tipo==='app'?pagApp:pagGiochi;
  const box = document.getElementById(tipo==='app'?'app-list':'giochi-list');
  const start=pag*PER; const pezzi=lista.slice(start,start+PER);
  box.innerHTML='';
  pezzi.forEach((it,i)=>{
    const n=start+i+1;
    const div=document.createElement('div'); div.className='card';
    const img = it.img ? `<img class="locandina" src="${it.img}" alt="" loading="lazy" onerror="this.remove()">` : ``;
    const fallback = `<div class="locandina-fallback" style="${it.img?'display:none':''}">${tipo==='app'?'📱':'🎮'}</div>`;
    div.innerHTML = tipo==='app'
      ? `${img}${fallback}<div class="card-info"><span class="tag">APP • #${n}</span><br><b>${it.nome}</b><p>Scopri l'app scelta da Shardan!</p><a class="btn-verde" href="${it.link}" target="_blank" rel="noopener">👉 Scopri l'App</a></div>`
      : `${img}${fallback}<div class="card-info"><span class="tag">GIOCO • #${n}</span><br><b>${it.nome}</b><p>Prova il gioco scelto da Shardan!</p><a class="btn-arancio" href="${it.link}" target="_blank" rel="noopener">🎮 Prova il Gioco</a></div>`;
    box.appendChild(div);
  });
  const totale=Math.max(1,Math.ceil(lista.length/PER));
  document.getElementById(tipo==='app'?'app-info':'giochi-info').textContent=`Pagina ${pag+1} di ${totale} • ${lista.length} totali`;
  document.getElementById(tipo==='app'?'app-prev':'giochi-prev').disabled = pag===0;
  document.getElementById(tipo==='app'?'app-next':'giochi-next').disabled = pag>=totale-1;
  document.getElementById('totale').textContent = APPS.length+GIOCHI.length;
}
function cambiaPagina(tipo,dir){
  if(tipo==='app'){ pagApp=Math.max(0,pagApp+dir); disegna('app'); }
  else{ pagGiochi=Math.max(0,pagGiochi+dir); disegna('giochi'); }
}
disegna('app'); disegna('giochi');
</script>
</body>
</html>
"""
    html = html.replace("__APPS__", apps_json).replace("__GIOCHI__", giochi_json)
    open("index.html","w",encoding="utf-8").write(html)
    print(f"SITO RIGENERATO DA ZERO! App: {len(arch['apps'])}, Giochi: {len(arch['giochi'])}")
    print(f"index.html ora è di {len(html)} caratteri - contiene {html.count('https://')} link!")

if __name__=="__main__":
    tok=login()
    if not tok: exit()
    apps, giochi=prendi_offerte(tok)
    if not apps and not giochi:
        print("Nessuna offerta - sito invariato")
        exit()
    aggiorna_html(apps, giochi)
