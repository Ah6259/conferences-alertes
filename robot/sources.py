# -*- coding: utf-8 -*-
"""
Sources LÉGALES des conférences (preuves des licences et conditions : dossier « preuves/ » sur le PC, jamais publié).

1. Listes ouvertes de dates limites publiées sur GitHub sous licence MIT (on cite chaque liste et sa licence) :
   - ccfddl/ccf-deadlines             informatique (toutes spécialités)
   - huggingface/ai-deadlines         intelligence artificielle
   - hci-deadlines/conf-database      interaction humain-machine
   - hyejuryu/neuro-deadlines         neurosciences
   - hlnicholls/bioinformatics-conferences   bioinformatique, génomique, cardiologie
   - RoboDDL/RoboDDL                  robotique
   Lues par l'API officielle de GitHub (archive du dépôt), comme tout programme autorisé par les conditions de GitHub.
2. INSPIRE-HEP (physique, astronomie) : métadonnées sous CC0, API publique /api/conferences (autorisée par robots.txt).
   Conditions INSPIRE respectées : aucun e-mail ni contact repris, aucune description reprise.
3. Sélection officielle (donnees/selection-officielle.json) : comptabilité, finance et finance islamique. Chaque conférence a été
   vérifiée sur la page officielle de son organisateur (faits seulement : nom, dates, lieu, date limite, lien). Aucun site
   concurrent ni agrégateur n'est recopié. Le robot mensuel verifier_officiels.py vérifie que chaque lien répond encore.

PAS de Wikidata : ses adresses de lecture automatique (query.wikidata.org/sparql, /w/api.php) sont interdites aux robots
par leur robots.txt (règle d'Ahmed : jamais contourner un robots.txt).

Chaque lecteur renvoie une liste de fiches « brutes » (voir fiche()) ; collecter.py nettoie, classe et fusionne.
"""
import datetime as dt
import glob
import io
import json
import os
import re
import tarfile
import time
import urllib.request

import classement as K

UA = "ConferenceRadarBot/1.0 (site gratuit d'alertes de conferences; https://github.com/Ah6259/conferences-alertes)"

LISTES_GITHUB = [
    # (identifiant, dépôt, nom affiché, licence)
    ("ccfddl", "ccfddl/ccf-deadlines", "CCF Deadlines (ccfddl)", "MIT"),
    ("hf", "huggingface/ai-deadlines", "AI Deadlines (Hugging Face)", "MIT"),
    ("hci", "hci-deadlines/conf-database", "HCI Deadlines", "MIT"),
    ("neuro", "hyejuryu/neuro-deadlines", "Neuro Deadlines", "MIT"),
    ("bio", "hlnicholls/bioinformatics-conferences", "Bioinformatics Conferences", "MIT"),
    ("robo", "RoboDDL/RoboDDL", "RoboDDL", "MIT"),
]
INSPIRE = ("inspire", "https://inspirehep.net/api/conferences", "INSPIRE-HEP", "CC0")
SOURCES = {s[0]: {"nom": s[2], "licence": s[3], "url": f"https://github.com/{s[1]}"} for s in LISTES_GITHUB}
SOURCES["inspire"] = {"nom": "INSPIRE-HEP", "licence": "CC0", "url": "https://inspirehep.net/conferences"}
SOURCES["officiel"] = {"nom": "Official organiser pages (checked) / pages officielles vérifiées",
                       "licence": "facts published by the organiser / faits publiés par l'organisateur", "url": ""}
SOURCES["organisateur"] = {"nom": "Organisateur (formulaire)", "licence": "publication demandée par l'organisateur", "url": ""}


# ------------------------------------------------------------------ téléchargement
def telecharger(url, accepte="application/json", delai=60):
    """Téléchargement honnête (User-Agent du site). Remplacé par une fausse fonction dans les tests."""
    entetes = {"User-Agent": UA, "Accept": accepte}
    jeton = os.environ.get("GITHUB_TOKEN", "").strip()
    if jeton and url.startswith("https://api.github.com/"):
        entetes["Authorization"] = "Bearer " + jeton
    req = urllib.request.Request(url, headers=entetes)
    with urllib.request.urlopen(req, timeout=delai) as r:
        return r.read()


def archive_github(depot, dossier):
    """Télécharge l'archive (tar.gz) du dépôt par l'API officielle et l'extrait dans `dossier`. Renvoie le chemin."""
    brut = telecharger(f"https://api.github.com/repos/{depot}/tarball", accepte="application/vnd.github+json", delai=120)
    cible = os.path.join(dossier, depot.replace("/", "_"))
    os.makedirs(cible, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(brut), mode="r:gz") as t:
        for m in t.getmembers():
            if not m.isfile() or not re.search(r"\.(ya?ml|json)$", m.name) or m.size > 5_000_000:
                continue
            nom = m.name.split("/", 1)[1] if "/" in m.name else m.name
            if ".." in nom or nom.startswith("/"):
                continue
            chemin = os.path.join(cible, nom)
            os.makedirs(os.path.dirname(chemin), exist_ok=True)
            with open(chemin, "wb") as f:
                f.write(t.extractfile(m).read())
    return cible


# ------------------------------------------------------------------ dates
MOIS = {m: i + 1 for i, ms in enumerate([
    "january jan janvier", "february feb fevrier février", "march mar mars", "april apr avril", "may mai",
    "june jun juin", "july jul juillet", "august aug aout août", "september sep sept septembre",
    "october oct octobre", "november nov novembre", "december dec décembre decembre"]) for m in ms.split()}
_M = r"(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)\.?"


def iso(a, m, j):
    try:
        return dt.date(int(a), int(m), int(j)).isoformat()
    except (ValueError, TypeError):
        return ""


def date_iso(v):
    """« 2026-07-28 23:59:59 » ou date YAML -> « 2026-07-28 » ; "" si absent ou TBD."""
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    m = re.match(r"^\s*'?(\d{4})-(\d{1,2})-(\d{1,2})", str(v or ""))
    return iso(*m.groups()) if m else ""


def heure_de(v):
    m = re.search(r"\b(\d{1,2}):(\d{2})", str(v or ""))
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""


def dates_texte(texte, annee=None):
    """« February 16-23, 2027 », « April, 13-17, 2026 », « November 30 - December 4, 2026 », « 9-12 November 2026 »
    -> (début, fin) ISO. Rien n'est inventé : ("", "") si le texte n'est pas compris."""
    t = str(texte or "").lower()
    t = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", t)
    t = re.sub(_M + r",", r"\1", t)
    t = t.replace("–", "-").replace("—", "-").replace(" to ", " - ")
    t = re.sub(r"\s+", " ", t).strip()
    ans = [int(x) for x in re.findall(r"\b(20\d\d)\b", t)]
    a1 = ans[0] if ans else (int(annee) if annee else None)
    a2 = ans[-1] if ans else a1
    if not a1:
        return "", ""
    m = re.search(_M + r" (\d{1,2})(?:,? (20\d\d))? ?- ?" + _M + r" (\d{1,2})", t)        # Nov 30 - Dec 4
    if m:
        m1, m2 = MOIS[m.group(1)], MOIS[m.group(4)]
        y1 = int(m.group(3)) if m.group(3) else (a2 if m1 <= m2 else a2 - 1)
        return iso(y1, m1, m.group(2)), iso(a2, m2, m.group(5))
    m = re.search(_M + r" (\d{1,2}) ?- ?(\d{1,2})\b", t)                                     # February 16-23
    if m:
        return iso(a1, MOIS[m.group(1)], m.group(2)), iso(a1, MOIS[m.group(1)], m.group(3))
    m = re.search(r"\b(\d{1,2}) " + _M + r" ?- ?(\d{1,2}) " + _M, t)                          # 30 Nov - 4 Dec
    if m:
        m1, m2 = MOIS[m.group(2)], MOIS[m.group(4)]
        return iso(a2 if m1 <= m2 else a2 - 1, m1, m.group(1)), iso(a2, m2, m.group(3))
    m = re.search(r"\b(\d{1,2}) ?- ?(\d{1,2}) " + _M, t)                                     # 9-12 November
    if m:
        return iso(a1, MOIS[m.group(3)], m.group(1)), iso(a1, MOIS[m.group(3)], m.group(2))
    m = re.search(_M + r" (\d{1,2})\b", t)                                                    # June 5, 2026 (un jour)
    if m:
        d = iso(a1, MOIS[m.group(1)], m.group(2))
        return d, d
    m = re.search(r"\b(\d{1,2}) " + _M, t)
    if m:
        d = iso(a1, MOIS[m.group(2)], m.group(1))
        return d, d
    return "", ""


def fiche(source, **k):
    f = {"source": source, "acronyme": "", "annee": None, "titre": "", "lien": "", "debut": "", "fin": "",
         "lieu": "", "ville": "", "code_pays": "", "mode": "", "dates_limites": [], "specialites": [], "rang": "", "mots": ""}
    f.update(k)
    return f


def limite(date, type_="article", libelle="", heure="", fuseau=""):
    d = date_iso(date)
    return {"date": d, "type": type_, "libelle": str(libelle or "")[:80], "heure": heure or heure_de(date),
            "fuseau": str(fuseau or "")[:12]} if d else None


def _yaml(chemin):
    import yaml
    with open(chemin, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ------------------------------------------------------------------ lecteurs des listes GitHub
def lire_ccfddl(dossier):
    res = []
    for f in sorted(glob.glob(os.path.join(dossier, "conference", "*", "*.yml"))):
        for c in _yaml(f) or []:
            if not isinstance(c, dict):
                continue
            rang = c.get("rank") or {}
            r = []
            if str(rang.get("core") or "").strip() not in ("", "N", "None"):
                r.append(f"CORE {rang['core']}")
            if str(rang.get("ccf") or "").strip() not in ("", "N", "None"):
                r.append(f"CCF {rang['ccf']}")
            sous = K.SOUS_CCF.get(str(c.get("sub") or ""), "info-interdisciplinaire")
            for e in c.get("confs") or []:
                if not isinstance(e, dict):
                    continue
                d1, d2 = dates_texte(e.get("date"), e.get("year"))
                lims = []
                for tl in e.get("timeline") or []:
                    if not isinstance(tl, dict):
                        continue
                    com = str(tl.get("comment") or "")
                    lims.append(limite(tl.get("abstract_deadline"), "resume", ("Abstract · " + com) if com else "Abstract", fuseau=e.get("timezone")))
                    lims.append(limite(tl.get("deadline"), "article", com or "Paper", fuseau=e.get("timezone")))
                res.append(fiche("ccfddl", acronyme=str(c.get("title") or ""), annee=e.get("year"),
                                 titre=str(c.get("description") or c.get("title") or ""), lien=str(e.get("link") or ""),
                                 debut=d1, fin=d2, lieu=str(e.get("place") or ""), dates_limites=[x for x in lims if x],
                                 specialites=[sous], rang=" · ".join(r), mots=f"{c.get('title')} {c.get('description')}"))
    return res


def lire_hf(dossier):
    res = []
    for f in sorted(glob.glob(os.path.join(dossier, "src", "data", "conferences", "*.yml"))):
        for e in _yaml(f) or []:
            if not isinstance(e, dict):
                continue
            d1, d2 = date_iso(e.get("start")), date_iso(e.get("end"))
            if not d1:
                d1, d2 = dates_texte(e.get("date"), e.get("year"))
            lims = []
            for x in e.get("deadlines") or []:
                if isinstance(x, dict):
                    ty = {"paper": "article", "abstract": "resume"}.get(str(x.get("type")), "autre")
                    lims.append(limite(x.get("date"), ty, x.get("label"), fuseau=x.get("timezone")))
            if e.get("deadline"):
                lims.append(limite(e.get("deadline"), "article", "Paper", fuseau=e.get("timezone")))
            if e.get("abstract_deadline"):
                lims.append(limite(e.get("abstract_deadline"), "resume", "Abstract", fuseau=e.get("timezone")))
            specs = [K.ETIQUETTES_HF[t] for t in (e.get("tags") or []) if t in K.ETIQUETTES_HF]
            lieu = str(e.get("venue") or "")
            if not lieu or not re.search(r",", lieu):
                lieu = ", ".join(x for x in (str(e.get("city") or ""), str(e.get("country") or "")) if x)
            res.append(fiche("hf", acronyme=str(e.get("title") or ""), annee=e.get("year"),
                             titre=str(e.get("full_name") or e.get("title") or ""), lien=str(e.get("link") or ""),
                             debut=d1, fin=d2, lieu=lieu, dates_limites=[x for x in lims if x],
                             specialites=list(dict.fromkeys(specs)) or ["ia-apprentissage"],
                             rang=str(e.get("rankings") or "").replace("CCF: ", "CCF ").replace("CORE: ", "CORE ").replace(", ", " · ")[:60],
                             mots=f"{e.get('title')} {e.get('full_name')}"))
    return res


def lire_hci(dossier):
    res = []
    for f in sorted(glob.glob(os.path.join(dossier, "conferences", "*.yml"))):
        for e in _yaml(f) or []:
            if not isinstance(e, dict):
                continue
            d1, d2 = date_iso(e.get("start")), date_iso(e.get("end"))
            if not d1:
                d1, d2 = dates_texte(e.get("date"), e.get("year"))
            lims = [limite(e.get("abstract_deadline"), "resume", "Abstract", fuseau=e.get("timezone")),
                    limite(e.get("deadline"), "article", "Paper", fuseau=e.get("timezone"))]
            res.append(fiche("hci", acronyme=str(e.get("title") or ""), annee=e.get("year"),
                             titre=str(e.get("full_name") or e.get("title") or ""), lien=str(e.get("link") or ""),
                             debut=d1, fin=d2, lieu=str(e.get("place") or ""), dates_limites=[x for x in lims if x],
                             specialites=["ihm"], mots=f"{e.get('title')} {e.get('full_name')}"))
    return res


def lire_neuro(dossier):
    with open(os.path.join(dossier, "data", "conferences.json"), encoding="utf-8") as f:
        d = json.load(f)
    res = []
    for e in d.get("conferences") or []:
        if not isinstance(e, dict):
            continue
        ev = e.get("event") or {}
        lims = []
        for x in e.get("deadlines") or []:
            if isinstance(x, dict):
                ty = str(x.get("type") or "")
                lims.append(limite(x.get("date"), "resume" if ty in ("abstract", "poster") else "article" if ty == "paper" else "autre",
                                   x.get("label")))
        res.append(fiche("neuro", acronyme=str(e.get("name") or ""), annee=e.get("year"),
                         titre=str(e.get("full_name") or e.get("name") or ""), lien=str(e.get("website") or ""),
                         debut=date_iso(ev.get("start")), fin=date_iso(ev.get("end")), lieu=str(ev.get("location") or ""),
                         dates_limites=[x for x in lims if x], specialites=["neurosciences"],
                         mots=f"{e.get('name')} {e.get('full_name')}"))
    return res


def lire_bio(dossier):
    res = []
    for e in _yaml(os.path.join(dossier, "_data", "conferences.yml")) or []:
        if not isinstance(e, dict):
            continue
        sous = e.get("sub")
        sous = sous if isinstance(sous, list) else [sous]
        specs = list(dict.fromkeys(K.SOUS_BIO[s] for s in sous if s in K.SOUS_BIO)) or ["bioinformatique"]
        d1, d2 = date_iso(e.get("start")), date_iso(e.get("end"))
        if not d1:
            d1, d2 = dates_texte(e.get("date"), e.get("year"))
        lims = [limite(e.get("abstract_deadline"), "resume", "Abstract", fuseau=e.get("timezone")),
                limite(e.get("deadline"), "article", "Submission", fuseau=e.get("timezone"))]
        res.append(fiche("bio", acronyme=str(e.get("title") or ""), annee=e.get("year"),
                         titre=str(e.get("full_name") or e.get("title") or ""), lien=str(e.get("link") or ""),
                         debut=d1, fin=d2, lieu=str(e.get("place") or ""), dates_limites=[x for x in lims if x],
                         specialites=specs, mots=f"{e.get('title')} {e.get('full_name')}"))
    return res


def lire_robo(dossier):
    res = []
    for f in sorted(glob.glob(os.path.join(dossier, "src", "data", "conference", "*.yaml"))):
        c = _yaml(f) or {}
        if not isinstance(c, dict):
            continue
        for e in c.get("knownEditions") or []:
            if not isinstance(e, dict):
                continue
            d1, d2 = dates_texte(e.get("conferenceDates"), e.get("year"))
            lims = [limite(e.get("abstractDeadline"), "resume", "Abstract", fuseau=e.get("timezone")),
                    limite(e.get("paperDeadline"), "article", "Paper", fuseau=e.get("timezone"))]
            rang = " · ".join(x for x in (f"CCF {c.get('ccfRank')}" if c.get("ccfRank") not in (None, "", "N/A") else "",) if x)
            res.append(fiche("robo", acronyme=str(c.get("title") or ""), annee=e.get("year"),
                             titre=str(c.get("fullTitle") or c.get("title") or ""), lien=str(e.get("link") or c.get("homepage") or ""),
                             debut=d1, fin=d2, lieu=str(e.get("location") or ""), dates_limites=[x for x in lims if x],
                             specialites=["robotique"], rang=rang, mots=f"{c.get('title')} {c.get('fullTitle')} robotics"))
    return res


def lire_officiel(chemin):
    """Sélection officielle (fichier du dépôt, aucune lecture sur Internet)."""
    with open(chemin, encoding="utf-8") as f:
        d = json.load(f)
    res = []
    for e in d.get("conferences") or []:
        if not isinstance(e, dict):
            continue
        res.append(fiche("officiel", acronyme=str(e.get("acronyme") or ""), annee=e.get("annee"), titre=str(e.get("titre") or ""),
                         lien=str(e.get("lien") or ""), debut=date_iso(e.get("debut")), fin=date_iso(e.get("fin")),
                         ville=str(e.get("ville") or ""), code_pays=str(e.get("code_pays") or ""), mode=str(e.get("mode") or "presentiel"),
                         specialites=[s for s in e.get("specialites") or [] if s in K.S_PAR_SLUG],
                         dates_limites=[x for x in (limite(l.get("date"), l.get("type") or "article", l.get("libelle"))
                                                    for l in e.get("dates_limites") or [] if isinstance(l, dict)) if x],
                         page_verifiee=str(e.get("page_verifiee") or ""), verifie_le=str(e.get("verifie_le") or ""),
                         mots=f"{e.get('acronyme')} {e.get('titre')}"))
    return res


LECTEURS = {"ccfddl": lire_ccfddl, "hf": lire_hf, "hci": lire_hci, "neuro": lire_neuro, "bio": lire_bio, "robo": lire_robo}


# ------------------------------------------------------------------ INSPIRE-HEP (CC0)
def lire_inspire_json(pages):
    """pages = liste de réponses JSON de l'API. On ne garde ni contact, ni e-mail, ni description (conditions INSPIRE)."""
    res = []
    for p in pages:
        for h in ((p or {}).get("hits") or {}).get("hits") or []:
            m = h.get("metadata") or {}
            titre = ((m.get("titles") or [{}])[0] or {}).get("title") or ""
            sous = ((m.get("titles") or [{}])[0] or {}).get("subtitle") or ""
            urls = [u.get("value") for u in m.get("urls") or [] if isinstance(u, dict)]
            adr = (m.get("addresses") or [{}])[0] or {}
            villes = adr.get("cities") or []
            ville = str(villes[0]) if villes else ""
            mode = "presentiel"
            if re.search(r"online|virtual", ville, re.I):
                mode, ville = "en-ligne", ""
            code = str(adr.get("country_code") or "")
            code = {"FX": "FR"}.get(code, code)
            specs = list(dict.fromkeys(K.CATEGORIES_INSPIRE[c["term"]] for c in m.get("inspire_categories") or []
                                       if isinstance(c, dict) and c.get("term") in K.CATEGORIES_INSPIRE)) or ["physique-generale"]
            acr = (m.get("acronyms") or [""])[0]
            res.append(fiche("inspire", acronyme=str(acr or ""), annee=int(str(m.get("opening_date"))[:4]) if m.get("opening_date") else None,
                             titre=str(titre) + (f" — {sous}" if sous else ""), lien=str(urls[0]) if urls else "",
                             debut=date_iso(m.get("opening_date")), fin=date_iso(m.get("closing_date")),
                             lieu=", ".join(x for x in (ville, str(adr.get("country") or "")) if x),
                             ville=ville, code_pays=code if code in K.PAYS else "", mode=mode,
                             specialites=specs[:3], identifiant=f"inspire-{m.get('control_number')}",
                             mots=f"{titre} {sous}"))
    return res


def lire_inspire():
    pages, page = [], 1
    while page <= 6:
        brut = telecharger(f"{INSPIRE[1]}?start_date=upcoming&sort=dateasc&size=250&page={page}"
                           "&fields=titles,acronyms,addresses,urls,opening_date,closing_date,inspire_categories,control_number")
        p = json.loads(brut.decode("utf-8"))
        pages.append(p)
        total = (p.get("hits") or {}).get("total") or 0
        if page * 250 >= total:
            break
        page += 1
        time.sleep(3)          # lecture lente
    return lire_inspire_json(pages)
