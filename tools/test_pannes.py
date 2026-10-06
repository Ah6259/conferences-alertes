# -*- coding: utf-8 -*-
"""
Scénarios de panne et de qualité — à relancer après toute modification des robots :
    python tools/test_pannes.py

Rien n'est lu sur Internet : les sources sont simulées. Chaque scénario travaille dans un dossier TEMPORAIRE ;
le vrai site n'est jamais modifié.

A. Lecture des dates et des lieux (jamais de date inventée).
B. Collecte (collecter.py) : source injoignable, vide, format changé, chute brutale d'une source, chute totale
   (publication refusée), retour à la normale, doublons fusionnés, organisateurs douteux écartés, liens non officiels,
   conférences passées, trop lointaines ou absurdes, textes piégés.
C. Construction (construire_site.py) : JSON corrompu, chute, aucune donnée, panne d'un jour / de 3 jours, retour à la normale.
D. Formulaire des organisateurs (CSV) : réponses invalides refusées.
E. Telegram par domaine : sans secret rien ; jamais deux fois ; erreur -> renvoi au passage suivant.
"""
import datetime as dt
import io
import json
import os
import contextlib
import shutil
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.dirname(ICI)
sys.path.insert(0, os.path.join(SITE, "robot"))
import classement as K      # noqa: E402
import collecter as R       # noqa: E402
import construire_site as C  # noqa: E402
import organisateurs as O   # noqa: E402
import sources as S         # noqa: E402
import telegram as T        # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JOUR = "2026-10-06"
erreurs = total = 0


def check(desc, cond):
    global erreurs, total
    total += 1
    print(("OK   " if cond else "FAIL ") + desc)
    if not cond:
        erreurs += 1


def plus(d, n):
    return (dt.date.fromisoformat(d) + dt.timedelta(days=n)).isoformat()


def silence(f, *a, **k):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        r = f(*a, **k)
    return r, out.getvalue()


# ------------------------------------------------------------------ A. dates et lieux
check("dates : « February 16-23, 2027 »", S.dates_texte("February 16-23, 2027") == ("2027-02-16", "2027-02-23"))
check("dates : « April, 13-17, 2026 »", S.dates_texte("April, 13-17, 2026") == ("2026-04-13", "2026-04-17"))
check("dates : « November 30 - December 4, 2026 »", S.dates_texte("November 30 - December 4, 2026") == ("2026-11-30", "2026-12-04"))
check("dates : « December 28, 2026 - January 2, 2027 »", S.dates_texte("December 28, 2026 - January 2, 2027") == ("2026-12-28", "2027-01-02"))
check("dates : « 9-12 November 2026 »", S.dates_texte("9-12 November 2026") == ("2026-11-09", "2026-11-12"))
check("dates : « June 06-11 » avec l'année de l'édition", S.dates_texte("June 06-11", 2027) == ("2027-06-06", "2027-06-11"))
check("dates : « TBD » -> rien (jamais deviné)", S.dates_texte("TBD", 2027) == ("", ""))
check("dates : « May 2027 (exact dates TBD) » -> rien", S.dates_texte("May 2027 (exact dates TBD)") == ("", ""))
check("dates : « February 30, 2027 » (impossible) -> rien", S.dates_texte("February 30, 2027") == ("", ""))
check("lieu : « Montréal, Québec, Canada » -> CA", K.lire_lieu("Montréal, Québec, Canada")[:2] == ("Montréal", "CA"))
check("lieu : « San Diego, CA » = Californie (US), pas le Canada", K.lire_lieu("San Diego, CA")[1] == "US")
check("lieu : « Atlanta, Georgia » -> US", K.lire_lieu("Atlanta, Georgia")[1] == "US")
check("lieu : « Virtual » -> en ligne, sans pays", K.lire_lieu("Virtual") == ("", "", "en-ligne"))
check("lieu : « Vienna, Austria (hybrid) » -> hybride, AT", K.lire_lieu("Vienna, Austria (hybrid)")[1:] == ("AT", "hybride"))
check("lieu : pays inconnu -> vide (jamais deviné)", K.lire_lieu("Somewhere, Atlantis")[1] == "")
# classement par mots-clés en anglais, français et arabe (comptabilité, finance, finance islamique)
for texte, attendu in [("International Conference on Islamic Finance", "economie-islamique"), ("Islamic banking and sukuk", "banque-islamique"),
                       ("Global Sukuk Forum", "sukuk"), ("Takaful Summit", "takaful"), ("Zakat and Waqf conference", "zakat-waqf"),
                       ("AAOIFI Shari'ah Boards Conference", "aaoifi-charia"), ("مؤتمر المالية الإسلامية", "economie-islamique"),
                       ("الملتقى الدولي حول الصيرفة الإسلامية", "banque-islamique"), ("مؤتمر الصكوك", "sukuk"), ("ندوة الوقف والزكاة", "zakat-waqf"),
                       ("Colloque international de finance islamique", "economie-islamique"), ("Auditing Section Midyear Meeting", "audit"),
                       ("IFRS research conference", "compta-financiere"), ("Management Accounting Research Conference", "compta-gestion"),
                       ("Congrès de comptabilité", "compta-generale"), ("المؤتمر الدولي للمحاسبة", "compta-generale"), ("Tax symposium", "fiscalite"),
                       ("FinTech research conference", "fintech"), ("Banking conference", "banque"), ("Asset pricing workshop", "marches")]:
    r = K.specialites_par_mots(texte)
    check(f"mots-clés : « {texte} » -> {attendu}", attendu in r)
check("mots-clés : « Islamic finance » n'est pas rangé en finance générale", "finance-generale" not in K.specialites_par_mots("Islamic finance conference"))


# ------------------------------------------------------------------ B. collecte
def brute(acr, annee=2027, debut="2027-03-10", fin="2027-03-12", lien=None, lieu="Paris, France", lims=("2026-11-01",), spec="vision", source="ccfddl", titre=None):
    return S.fiche(source, acronyme=acr, annee=annee, titre=titre or f"International Conference {acr}", lien=lien or f"https://{acr.lower()}.org/{annee}/",
                   debut=debut, fin=fin, lieu=lieu, specialites=[spec],
                   dates_limites=[S.limite(d, "article", "Paper") for d in lims])


def jeu(n, prefixe="C", source="ccfddl"):
    return [brute(f"{prefixe}{k}", debut=plus("2026-11-01", k), fin=plus("2026-11-03", k), source=source) for k in range(n)]


def faux_lire(table):
    def lire(ident, cache, tmp):
        v = table.get(ident, [])
        if isinstance(v, Exception):
            raise v
        return v() if callable(v) else v
    return lire


tmp = tempfile.mkdtemp(prefix="test-conf-")
try:
    sortie = os.path.join(tmp, "donnees", "conferences.json")
    normal = {"ccfddl": jeu(40), "hf": jeu(12, "H", "hf"), "hci": jeu(10, "I", "hci"), "neuro": jeu(10, "N", "neuro"),
              "bio": jeu(10, "B", "bio"), "robo": jeu(10, "R", "robo"), "inspire": jeu(30, "P", "inspire"),
              "officiel": jeu(10, "O", "officiel")}
    code, _ = silence(R.collecter, sortie, JOUR, lire=faux_lire(normal))
    d = json.load(open(sortie, encoding="utf-8"))
    check(f"collecte normale : {d['nombre']} conférences, statut ok, toutes les sources ok", code == 0 and d["nombre"] == 132 and d["statut_source"]["etat"] == "ok"
          and all(v["etat"] == "ok" for v in d["sources"].values()))
    check("collecte : première collecte notée (rien de « nouveau » ce jour-là)", d["premiere_collecte"] == JOUR)

    # source injoignable
    t = dict(normal, inspire=OSError("réseau coupé"))
    code, out = silence(R.collecter, sortie, plus(JOUR, 1), lire=faux_lire(t))
    d = json.load(open(sortie, encoding="utf-8"))
    check("source injoignable : panne notée, anciennes conférences de la source GARDÉES, « échec » au journal",
          d["sources"]["inspire"]["etat"] == "panne" and sum(1 for c in d["conferences"] if c["sources"][0] == "inspire") == 30
          and "échec" in out and d["statut_source"]["etat"] == "panne")
    depuis = d["statut_source"]["depuis"]
    code, out = silence(R.collecter, sortie, plus(JOUR, 2), lire=faux_lire(t))
    d = json.load(open(sortie, encoding="utf-8"))
    check("panne qui dure : date « depuis » gardée", d["statut_source"]["depuis"] == depuis)
    # source vide
    code, out = silence(R.collecter, sortie, plus(JOUR, 2), lire=faux_lire(dict(normal, hf=[])))
    d = json.load(open(sortie, encoding="utf-8"))
    check("source vide : c'est une panne (jamais « aucune conférence »), anciennes gardées",
          d["sources"]["hf"]["etat"] == "panne" and sum(1 for c in d["conferences"] if c["sources"][0] == "hf") == 12)
    # format changé
    code, out = silence(R.collecter, sortie, plus(JOUR, 2), lire=faux_lire(dict(normal, hci=[{"titre": "x"}, {"rien": 1}])))
    d = json.load(open(sortie, encoding="utf-8"))
    check("format changé (fiches illisibles) : panne, anciennes gardées", d["sources"]["hci"]["etat"] == "panne" and "format changé" in d["sources"]["hci"]["raison"])
    # chute d'une source
    code, out = silence(R.collecter, sortie, plus(JOUR, 2), lire=faux_lire(dict(normal, ccfddl=jeu(5))))
    d = json.load(open(sortie, encoding="utf-8"))
    check("chute d'une source (5 au lieu de 40) : panne, les 40 gardées", d["sources"]["ccfddl"]["etat"] == "panne" and
          sum(1 for c in d["conferences"] if c["sources"][0] == "ccfddl") == 40)
    # retour à la normale
    code, out = silence(R.collecter, sortie, plus(JOUR, 3), lire=faux_lire(normal))
    d = json.load(open(sortie, encoding="utf-8"))
    check("retour à la normale : statut ok, plus de panne", d["statut_source"]["etat"] == "ok" and all(v["etat"] == "ok" for v in d["sources"].values()))
    # chute totale : publication refusée
    avant = json.load(open(sortie, encoding="utf-8"))
    tout_casse = {k: (jeu(2, "Z" + k) if k == "ccfddl" else OSError("x")) for k in normal}
    t2 = {k: OSError("x") for k in normal}
    shutil.copy(sortie, sortie + ".copie")
    # toutes les sources en panne depuis plus de 30 jours : rien n'est gardé -> collecte vide -> refus
    code, out = silence(R.collecter, sortie, plus(JOUR, 60), lire=faux_lire(t2))
    d = json.load(open(sortie, encoding="utf-8"))
    check("tout en panne depuis longtemps : publication REFUSÉE, ancienne liste gardée, statut panne", code == 1 and
          len(d["conferences"]) == len(avant["conferences"]) and d["statut_source"]["etat"] == "panne" and "REFUSÉE" in out)
    shutil.copy(sortie + ".copie", sortie)
    del tout_casse

    # qualité : doublons, prédateurs, liens, dates
    q = [brute("AAAI", source="ccfddl", spec="ia-apprentissage"),
         brute("AAAI", source="hf", spec="vision", lims=("2026-11-01", "2026-10-20")),               # doublon (autre source)
         brute("FAKE1", lien="https://www.conferenceseries.com/2027/x"),                              # organisateur écarté
         brute("FAKE2", titre="5th Edition of World Congress on Everything"),                         # signature typique écartée
         brute("BADLINK", lien="javascript:alert(1)"),
         brute("NOHTTPS", lien="ftp://example.org"),
         brute("PASSE", debut="2026-09-01", fin="2026-09-03"),
         brute("LOIN", debut="2028-12-01", fin="2028-12-03"),
         brute("ABSURDE", debut="2027-01-01", fin="2027-06-01"),
         brute("SANSDATE", debut="", fin=""),
         brute("PIEGE", titre='<script>alert("x")</script> Conference'),
         brute("ENLIGNE", lieu="Virtual")]
    code, _ = silence(R.collecter, os.path.join(tmp, "q", "c.json"), JOUR, lire=faux_lire({"ccfddl": q}))
    dq = json.load(open(os.path.join(tmp, "q", "c.json"), encoding="utf-8"))
    ids = {c["acronyme"]: c for c in dq["conferences"]}
    check("doublons fusionnés (même sigle, même année, mêmes dates) : une seule AAAI, deux sources, dates limites réunies",
          sum(1 for c in dq["conferences"] if c["acronyme"] == "AAAI") == 1 and ids["AAAI"]["sources"] == ["ccfddl", "hf"]
          and len(ids["AAAI"]["dates_limites"]) == 2 and set(ids["AAAI"]["specialites"]) == {"ia-apprentissage", "vision"})
    check("organisateurs douteux écartés (domaine connu et « Nth Edition of »)", "FAKE1" not in ids and "FAKE2" not in ids)
    check("liens non officiels (javascript:, ftp:) écartés", "BADLINK" not in ids and "NOHTTPS" not in ids)
    check("conférences passées, trop lointaines (> 18 mois), absurdes (> 60 jours) ou sans date écartées",
          not any(x in ids for x in ("PASSE", "LOIN", "ABSURDE", "SANSDATE")))
    check("texte piégé : balises retirées du titre", "PIEGE" in ids and "<" not in ids["PIEGE"]["titre"])
    check("« Virtual » -> en ligne, continent « en-ligne »", ids["ENLIGNE"]["mode"] == "en-ligne" and ids["ENLIGNE"]["continent"] == "en-ligne")
    check("prochaine date limite = la plus proche à venir", ids["AAAI"]["date_limite"] == "2026-10-20")

    # ------------------------------------------------------------------ C. construction
    copie = os.path.join(tmp, "site")
    for f in ("assets", "robot"):
        shutil.copytree(os.path.join(SITE, f), os.path.join(copie, f), ignore=shutil.ignore_patterns("__pycache__", "photos", "icons"))
    os.makedirs(os.path.join(copie, "donnees"))
    donnees = os.path.join(copie, "donnees", "conferences.json")
    shutil.copy(sortie, donnees)
    code, out = silence(C.construire, donnees, copie, plus(JOUR, 3))
    e = json.load(open(os.path.join(copie, "donnees", "etat-source.json"), encoding="utf-8"))
    n_pages = len(open(os.path.join(copie, "sitemap.xml"), encoding="utf-8").read().split("<url>")) - 1
    check(f"construction normale : {n_pages} pages, pas d'avertissement, sauvegarde faite", code == 0 and not e["bandeau_visible"]
          and os.path.exists(donnees.replace(".json", ".sauvegarde.json")) and n_pages > 100)
    html = open(os.path.join(copie, "index.html"), encoding="utf-8").read()
    check("construction : les textes sont échappés (aucune balise <script> venue des données)", "<script>alert" not in html)
    # JSON corrompu -> sauvegarde
    open(donnees, "w", encoding="utf-8").write("{corrompu")
    code, out = silence(C.construire, donnees, copie, plus(JOUR, 3))
    check("JSON corrompu : dernière sauvegarde utilisée, avertissement, « échec » au journal",
          code == 0 and "sauvegarde utilisée" in out and json.load(open(os.path.join(copie, "donnees", "etat-source.json"), encoding="utf-8"))["source_en_panne"])
    # chute -> sauvegarde
    d = json.load(open(donnees.replace(".json", ".sauvegarde.json"), encoding="utf-8"))
    d2 = dict(d, conferences=d["conferences"][:10])
    json.dump(d2, open(donnees, "w", encoding="utf-8"))
    code, out = silence(C.construire, donnees, copie, plus(JOUR, 3))
    check("chute brutale (10 au lieu de 132) : sauvegarde utilisée", "données suspectes" in out)
    # aucune donnée, aucune sauvegarde, site existant -> rien n'est touché
    os.remove(donnees.replace(".json", ".sauvegarde.json"))
    open(donnees, "w", encoding="utf-8").write("")
    avant = open(os.path.join(copie, "index.html"), encoding="utf-8").read()
    code, out = silence(C.construire, donnees, copie, plus(JOUR, 3))
    check("données illisibles sans sauvegarde : le site existant est gardé tel quel (code 1)",
          code == 1 and open(os.path.join(copie, "index.html"), encoding="utf-8").read() == avant)
    # panne d'un jour / de 3 jours
    d["derniere_lecture_reussie"] = plus(JOUR, 3) + " 05:20"
    json.dump(d, open(donnees, "w", encoding="utf-8"))
    silence(C.construire, donnees, copie, plus(JOUR, 4))
    e = json.load(open(os.path.join(copie, "donnees", "etat-source.json"), encoding="utf-8"))
    check("dernière lecture d'hier : pas encore de bandeau", not e["bandeau_visible"])
    silence(C.construire, donnees, copie, plus(JOUR, 6))
    e = json.load(open(os.path.join(copie, "donnees", "etat-source.json"), encoding="utf-8"))
    check("3 jours sans lecture : bandeau daté", e["bandeau_visible"] and 'class="alerte-panne on"' in open(os.path.join(copie, "index.html"), encoding="utf-8").read())

    # ------------------------------------------------------------------ D. formulaire des organisateurs
    csv = ("Horodateur,Nom de la conférence,Sigle,Date de début,Date de fin,Ville,Pays,Format,Spécialité,Date limite,Lien officiel,J'accepte\n"
           "x,Good Conf,GC,2027-03-01,2027-03-03,Tunis,Tunisie,Sur place,Vision par ordinateur,2026-12-01,https://good.org/,Oui\n"
           "x,Sans accord,SA,2027-03-01,2027-03-03,Tunis,Tunisie,Sur place,Vision par ordinateur,,https://sa.org/,\n"
           "x,<b>HTML</b>,H,2027-03-01,2027-03-03,Tunis,Tunisie,,Vision par ordinateur,,https://h.org/,Oui\n"
           "x,Lien http,LH,2027-03-01,2027-03-03,Tunis,Tunisie,,Vision par ordinateur,,http://lh.org/,Oui\n"
           "x,Spécialité inconnue,SI,2027-03-01,2027-03-03,Tunis,Tunisie,,Cuisine,,https://si.org/,Oui\n"
           "x,En ligne,EL,01/04/2027,02/04/2027,,,En ligne,Neurosciences,,https://el.org/,Oui\n")
    f = O.analyser(csv)
    check("organisateurs : seules les réponses valides gardées (accord, pas de HTML, lien https, spécialité connue)", [x["acronyme"] for x in f] == ["GC", "EL"])
    check("organisateurs : dates jj/mm/aaaa comprises, pays reconnu, format en ligne", f[1]["debut"] == "2027-04-01" and f[0]["code_pays"] == "TN" and f[1]["mode"] == "en-ligne")
    try:
        O.analyser("a,b,c\n1,2,3\n")
        check("organisateurs : colonnes changées -> erreur (anciennes gardées)", False)
    except ValueError:
        check("organisateurs : colonnes changées -> erreur (anciennes gardées)", True)

    # ------------------------------------------------------------------ E. Telegram par domaine
    mem = os.path.join(tmp, "tg.json")
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    os.environ.pop("TELEGRAM_CANAUX", None)
    code, out = silence(T.main, ["--donnees", sortie, "--memoire", mem, "--aujourdhui", plus(JOUR, 3)])
    check("Telegram sans secrets : rien envoyé, pas d'échec", code == 0 and "pas encore configuré" in out and not os.path.exists(mem))
    check("Telegram : secret des canaux lu (domaines inconnus ignorés)", T.canaux_secret("informatique=@radar_info;inconnu=@x;physique=@radar_phys")
          == {"informatique": "@radar_info", "physique": "@radar_phys"})
    # une nouvelle conférence arrive après la première collecte
    d = json.load(open(sortie, encoding="utf-8"))
    nouv = dict(d["conferences"][0], id="nouvelle-2027", acronyme="NOUV", ajoute_le=plus(JOUR, 3))
    d["conferences"].append(nouv)
    json.dump(d, open(sortie, "w", encoding="utf-8"))
    envois = []
    T.envoyer = lambda j, c, t: (envois.append((c, t)), (True, ""))[1]
    os.environ["TELEGRAM_BOT_TOKEN"] = "123:abc"
    os.environ["TELEGRAM_CANAUX"] = "informatique=@radar_info"
    silence(T.main, ["--donnees", sortie, "--memoire", mem, "--aujourdhui", plus(JOUR, 3)])
    check("Telegram : la nouvelle conférence est annoncée, les anciennes (première collecte) non",
          len(envois) == 1 and "NOUV" in envois[0][1] and envois[0][0] == "@radar_info" and "C0 " not in envois[0][1])
    envois.clear()
    silence(T.main, ["--donnees", sortie, "--memoire", mem, "--aujourdhui", plus(JOUR, 3)])
    check("Telegram : jamais deux fois la même annonce", not envois)
    nouv2 = dict(nouv, id="autre-2027", acronyme="AUTRE")
    d["conferences"].append(nouv2)
    json.dump(d, open(sortie, "w", encoding="utf-8"))
    T.envoyer = lambda j, c, t: (False, "code 429 : trop de messages")
    code, out = silence(T.main, ["--donnees", sortie, "--memoire", mem, "--aujourdhui", plus(JOUR, 3)])
    check("Telegram en erreur : « échec » au journal, le robot continue", code == 0 and "échec" in out)
    T.envoyer = lambda j, c, t: (envois.append((c, t)), (True, ""))[1]
    silence(T.main, ["--donnees", sortie, "--memoire", mem, "--aujourdhui", plus(JOUR, 3)])
    check("Telegram : l'annonce refusée repart au passage suivant", len(envois) == 1 and "AUTRE" in envois[0][1])
finally:
    os.environ.pop("TELEGRAM_BOT_TOKEN", None)
    os.environ.pop("TELEGRAM_CANAUX", None)
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{total - erreurs}/{total} scénarios réussis" + (f" — {erreurs} ÉCHEC(S) : ne pas publier." if erreurs else " — tout est bon."))
sys.exit(1 if erreurs else 0)
