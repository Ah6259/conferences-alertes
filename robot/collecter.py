# -*- coding: utf-8 -*-
"""
Collecte quotidienne des conférences À VENIR (12 à 18 mois) -> donnees/conferences.json

    python robot/collecter.py
    python robot/collecter.py --cache dossier     (PC : réutilise les archives déjà téléchargées)
    python robot/collecter.py --aujourdhui 2026-10-06 --sortie X.json   (tests)

Qualité :
  - dates normalisées (AAAA-MM-JJ) ; une date qu'on ne comprend pas n'est JAMAIS devinée (fiche écartée) ;
  - lien officiel obligatoire (https) ; doublons fusionnés (même sigle + même année + mêmes dates) ;
  - domaine + spécialités, pays + continent, sur place / en ligne / hybride ;
  - organisateurs connus pour leurs conférences « prédatrices » écartés (liste gardée sous forme d'empreintes) ;
  - fiches absurdes écartées (année impossible, plus de 60 jours, fin avant début).
Robustesse (comme le site Appels d'offres) :
  - une source en panne (injoignable, vide, format changé, < 30 % de ses fiches habituelles) : ses anciennes
    conférences sont GARDÉES (au plus 30 jours), « échec » au journal, état dans « sources » ;
  - collecte totale < 50 % de la précédente : on REFUSE de publier (ancien fichier gardé, statut « panne ») ;
  - statut_source / derniere_lecture_reussie lus par construire_site.py et par le robot GitHub (issue d'alerte).
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unicodedata

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import classement as K   # noqa: E402
import sources as S      # noqa: E402

RACINE = os.path.dirname(ICI)
DONNEES = os.path.join(RACINE, "donnees", "conferences.json")
FENETRE_JOURS = 548          # 18 mois
SEUIL_SOURCE = 0.3           # une source qui rend moins de 30 % de ses fiches habituelles = panne
SEUIL_TOTAL = 0.5            # collecte totale < 50 % de la précédente = refus de publier
GARDE_JOURS = 30             # anciennes fiches d'une source en panne gardées au plus 30 jours
ORDRE = ["officiel", "ccfddl", "hf", "hci", "robo", "neuro", "bio", "inspire", "organisateur"]   # priorité lors des fusions

# Organisateurs écartés (conférences « prédatrices » documentées : jugements, presse scientifique). Empreintes SHA-256
# (16 premiers caractères) du nom de domaine : la liste en clair est dans l'étude privée d'Ahmed.
ECARTES = {"c28b10b783903c0d", "c34530a1b1d5dae9", "3f7bd90c339cd351", "194ef596c8e06487", "8a6bd00d5ca5be51",
           "dae8c9f443451f07"}
MOTIF_ECARTE = re.compile(r"\b\d+(st|nd|rd|th) edition of\b", re.I)    # signature typique de ces organisateurs
LIEN_OK = re.compile(r"^https?://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:[/?#][^\s\"'<>]*)?$")


def maintenant():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def domaine_lien(lien):
    m = re.match(r"^https?://([^/:?#]+)", lien or "")
    h = (m.group(1) if m else "").lower()
    parties = h.split(".")
    return ".".join(parties[-2:]) if len(parties) >= 2 else h


def ecarte(f):
    d = domaine_lien(f["lien"])
    return hashlib.sha256(d.encode()).hexdigest()[:16] in ECARTES or bool(MOTIF_ECARTE.search(f["titre"] or ""))


def slug(t):
    t = "".join(c for c in unicodedata.normalize("NFKD", str(t or "")) if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


def propre(t, n=200):
    t = re.sub(r"<[^>]*>", "", str(t or ""))
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[:n - 1].rsplit(" ", 1)[0] + "…"


def normaliser(f, jour):
    """Fiche brute -> fiche propre, ou None si elle doit être écartée (raison dans f['_ecart'])."""
    lien = str(f.get("lien") or "").strip()
    if lien.startswith("http://"):
        lien = "https://" + lien[7:]
    if not LIEN_OK.match(lien):
        return None
    d1, d2 = f.get("debut") or "", f.get("fin") or ""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d1):
        return None                                   # jamais de date inventée
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d2) or d2 < d1:
        d2 = d1
    j = dt.date.fromisoformat(jour)
    if d2 < jour or d1 > (j + dt.timedelta(days=FENETRE_JOURS)).isoformat():
        return None                                   # passée ou trop lointaine
    if (dt.date.fromisoformat(d2) - dt.date.fromisoformat(d1)).days > 60:
        return None                                   # absurde
    titre = propre(f.get("titre"), 220)
    acr = propre(f.get("acronyme"), 40)
    if not titre and not acr:
        return None
    if f.get("code_pays") or f.get("mode"):
        ville, code, mode = f.get("ville") or "", f.get("code_pays") or "", f.get("mode") or "presentiel"
        if not ville and f.get("lieu"):
            ville = K.lire_lieu(f["lieu"])[0]
    else:
        ville, code, mode = K.lire_lieu(f.get("lieu"))
    specs = [s for s in f.get("specialites") or [] if s in K.S_PAR_SLUG]
    # précision par mots-clés du titre (vision, langage, robotique…) pour les listes générales d'informatique
    if f["source"] in ("ccfddl", "hf") and specs and specs[0] in ("ia-apprentissage", "info-interdisciplinaire"):
        fins = [s for s in K.specialites_par_mots(f.get("mots") or titre)
                if s in ("vision", "langage", "robotique", "signal", "bioinformatique", "neurosciences", "medecine", "donnees")]
        specs = list(dict.fromkeys(fins[:2] + specs))
    if not specs:
        specs = K.specialites_par_mots(f.get("mots") or titre)[:2]
    # thèmes mis en avant (comptabilité, finance, finance islamique) : ajoutés quand le titre en parle clairement
    elif f["source"] not in ("officiel", "organisateur"):
        for s in K.specialites_par_mots(f.get("mots") or titre):
            if (K.S_PAR_SLUG[s][1] in ("comptabilite", "finance-islamique") or s in ("fintech", "banque", "marches")) and s not in specs:
                specs.append(s)
    if not specs:
        return None
    lims = []
    vus = set()
    for x in sorted((x for x in f.get("dates_limites") or [] if x and x.get("date")), key=lambda x: (x["date"], x["type"])):
        cle = (x["date"], x["type"])
        if cle in vus or x["date"] > d2:
            continue
        vus.add(cle)
        lims.append(x)
    prochaine = next((x for x in lims if x["date"] >= jour and x["type"] in ("article", "resume")), None)
    annee = f.get("annee") or int(d1[:4])
    try:
        annee = int(annee)
    except (TypeError, ValueError):
        annee = int(d1[:4])
    res = {
        "id": "", "acronyme": acr, "titre": titre or acr, "annee": annee, "type": K.type_evenement(f"{acr} {titre}"),
        "debut": d1, "fin": d2, "ville": propre(ville, 60), "pays": code if code in K.PAYS else "", "mode": mode,
        "continent": "", "domaines": K.domaines_de(specs), "specialites": specs[:3],
        "date_limite": prochaine["date"] if prochaine else "", "type_limite": prochaine["type"] if prochaine else "",
        "heure_limite": prochaine["heure"] if prochaine else "", "fuseau_limite": prochaine["fuseau"] if prochaine else "",
        "dates_limites": lims[-8:], "lien": lien, "rang": propre(f.get("rang"), 40),
        "sources": [f["source"]], "identifiant_source": f.get("identifiant") or "",
        "verifie_le": f.get("verifie_le") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(f.get("verifie_le") or "")) else "",
        "page_verifiee": f.get("page_verifiee") if LIEN_OK.match(str(f.get("page_verifiee") or "")) else "",
    }
    res["continent"] = K.continent(res["pays"], mode)
    if ecarte(res):
        return None
    return res


def cle_doublon(c):
    a = slug(c["acronyme"])
    return (a, c["annee"]) if a else (slug(c["titre"])[:60], c["debut"])


def fusionner(liste, jour):
    """Fusionne les doublons (même sigle + même année, dates proches) ; la source la plus précise passe d'abord."""
    liste = sorted(liste, key=lambda c: (ORDRE.index(c["sources"][0]) if c["sources"][0] in ORDRE else 99))
    groupes = {}
    res = []
    for c in liste:
        k = cle_doublon(c)
        cible = None
        for autre in groupes.get(k, []):
            if abs((dt.date.fromisoformat(autre["debut"]) - dt.date.fromisoformat(c["debut"])).days) <= 10:
                cible = autre
                break
        if cible is None:
            groupes.setdefault(k, []).append(c)
            res.append(c)
            continue
        for champ in ("ville", "pays", "rang", "date_limite", "type_limite", "heure_limite", "fuseau_limite"):
            if not cible[champ] and c[champ]:
                cible[champ] = c[champ]
        if not cible["continent"]:
            cible["continent"] = K.continent(cible["pays"], cible["mode"])
        for s in c["specialites"]:
            if s not in cible["specialites"] and len(cible["specialites"]) < 4:
                cible["specialites"].append(s)
        cible["domaines"] = K.domaines_de(cible["specialites"])
        vus = {(x["date"], x["type"]) for x in cible["dates_limites"]}
        cible["dates_limites"] = sorted(cible["dates_limites"] + [x for x in c["dates_limites"] if (x["date"], x["type"]) not in vus],
                                        key=lambda x: x["date"])[-8:]
        recalculer_limite(cible, jour)
        for s in c["sources"]:
            if s not in cible["sources"]:
                cible["sources"].append(s)
    return res


def donner_ids(liste):
    vus = set()
    for c in sorted(liste, key=lambda c: (c["debut"], c["titre"])):
        base = slug(c["acronyme"])[:40] or slug(c["titre"])[:50].rsplit("-", 1)[0]
        if not base:
            base = "conference"
        if str(c["annee"]) not in base:
            base = f"{base}-{c['annee']}"
        i, ident = 2, base
        while ident in vus:
            ident = f"{base}-{i}"
            i += 1
        vus.add(ident)
        c["id"] = ident
    return liste


def recalculer_limite(c, jour):
    p = next((x for x in c["dates_limites"] if x["date"] >= jour and x["type"] in ("article", "resume")), None)
    c["date_limite"] = p["date"] if p else ""
    c["type_limite"] = p["type"] if p else ""
    c["heure_limite"] = p["heure"] if p else ""
    c["fuseau_limite"] = p["fuseau"] if p else ""


def charger(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("conferences"), list):
            return d
    except (OSError, ValueError):
        pass
    return None


def ecrire_json(chemin, d):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, chemin)


def lire_source(ident, cache, dossier_tmp):
    """Renvoie la liste brute d'une source (lève une exception si elle est injoignable ou illisible)."""
    if ident == "inspire":
        return S.lire_inspire()
    if ident == "officiel":
        return S.lire_officiel(os.path.join(RACINE, "donnees", "selection-officielle.json"))
    depot = next(l[1] for l in S.LISTES_GITHUB if l[0] == ident)
    chemin = os.path.join(cache, depot.replace("/", "_")) if cache else ""
    if not (chemin and os.path.isdir(chemin)):
        chemin = S.archive_github(depot, cache or dossier_tmp)
    return S.LECTEURS[ident](chemin)


def collecter(sortie, jour, cache="", lire=None, organisateurs=None):
    global maintenant
    maintenant = lambda: f"{jour} {dt.datetime.now():%H:%M}"      # horodatage = jour de la collecte (tests : --aujourdhui)
    lire = lire or lire_source
    ancien = charger(sortie)
    anciennes = (ancien or {}).get("conferences") or []
    etats_avant = (ancien or {}).get("sources") or {}
    etats, toutes = {}, []
    dossier_tmp = tempfile.mkdtemp(prefix="conf-")
    try:
        for ident in [l[0] for l in S.LISTES_GITHUB] + ["inspire", "officiel"]:
            avant = etats_avant.get(ident) or {}
            habituel = int(avant.get("nombre") or 0)
            try:
                brutes = lire(ident, cache, dossier_tmp)
                propres = [c for c in (normaliser(f, jour) for f in brutes if isinstance(f, dict)) if c]
                if not brutes:
                    raise ValueError("réponse vide")
                if not propres:
                    raise ValueError("format changé : aucune conférence lisible")
                if habituel >= 10 and len(propres) < SEUIL_SOURCE * habituel:
                    raise ValueError(f"seulement {len(propres)} conférences contre {habituel} d'habitude")
                etats[ident] = {"etat": "ok", "nombre": len(propres), "brutes": len(brutes),
                                "derniere_reussite": maintenant(), "raison": "", "depuis": ""}
                toutes += propres
                print(f"  {ident} : {len(propres)} conférences à venir (sur {len(brutes)} fiches)")
            except Exception as e:   # noqa: BLE001  (toute panne d'une source est rattrapée)
                raison = str(e)[:160] or e.__class__.__name__
                reussite = avant.get("derniere_reussite") or ""
                depuis = avant.get("depuis") or maintenant()[:10]
                gardees = []
                if reussite and (dt.date.fromisoformat(jour) - dt.date.fromisoformat(reussite[:10])).days <= GARDE_JOURS:
                    gardees = [dict(c) for c in anciennes if c.get("sources", [""])[0] == ident and c.get("fin", "") >= jour]
                    for c in gardees:
                        recalculer_limite(c, jour)
                etats[ident] = {"etat": "panne", "nombre": habituel, "brutes": 0, "derniere_reussite": reussite,
                                "raison": raison, "depuis": depuis}
                toutes += gardees
                print(f"  ! échec : source {ident} en panne ({raison}) — {len(gardees)} anciennes conférences gardées")
        if organisateurs is not None:
            orga = [c for c in (normaliser(f, jour) for f in organisateurs) if c]
            toutes += orga
            etats["organisateur"] = {"etat": "ok", "nombre": len(orga), "brutes": len(organisateurs),
                                     "derniere_reussite": maintenant(), "raison": "", "depuis": ""}
    finally:
        shutil.rmtree(dossier_tmp, ignore_errors=True)

    confs = donner_ids(fusionner(toutes, jour))
    confs.sort(key=lambda c: (c["debut"], c["id"]))
    # date d'arrivée sur le site (gardée d'un passage à l'autre) : « Nouveau », flux RSS, Telegram
    vues = {}
    for c in anciennes:
        if isinstance(c, dict) and c.get("ajoute_le") and c.get("debut"):
            vues[cle_doublon(c)] = c["ajoute_le"]
            vues[c.get("id")] = c["ajoute_le"]
    for c in confs:
        c["ajoute_le"] = vues.get(cle_doublon(c)) or vues.get(c["id"]) or jour
    pannes = [k for k, v in etats.items() if v["etat"] == "panne"]
    n_avant = len([c for c in anciennes if c.get("fin", "") >= jour])
    if not confs or (n_avant >= 20 and len(confs) < SEUIL_TOTAL * n_avant):
        raison = f"collecte anormale : {len(confs)} conférences contre {n_avant} avant"
        print(f"  ! échec : {raison} — publication REFUSÉE, ancien fichier gardé")
        if ancien:
            st = ancien.get("statut_source") or {}
            ancien["statut_source"] = {"etat": "panne", "raison": raison,
                                       "depuis": st.get("depuis") if st.get("etat") == "panne" else maintenant()[:10]}
            ancien["dernier_passage"] = {"date": maintenant(), "reussi": False}
            ecrire_json(sortie, ancien)
        return 1
    total_ok = len(pannes) < len(etats)
    st_avant = (ancien or {}).get("statut_source") or {}
    statut = {"etat": "ok", "raison": "", "depuis": ""}
    if pannes:
        statut = {"etat": "panne", "raison": "source(s) en panne : " + ", ".join(
            f"{S.SOURCES.get(p, {}).get('nom', p)} ({etats[p]['raison']})" for p in pannes),
            "depuis": st_avant.get("depuis") if st_avant.get("etat") == "panne" and st_avant.get("depuis") else maintenant()[:10]}
    d = {
        "site": "Conference Radar",
        "premiere_collecte": (ancien or {}).get("premiere_collecte") or jour,
        "mis_a_jour": maintenant(),
        "derniere_lecture_reussie": maintenant() if total_ok else (ancien or {}).get("derniere_lecture_reussie", ""),
        "dernier_passage": {"date": maintenant(), "reussi": total_ok},
        "statut_source": statut,
        "sources": etats,
        "nombre": len(confs),
        "conferences": confs,
    }
    ecrire_json(sortie, d)
    par = {}
    for c in confs:
        for dm in c["domaines"]:
            par[dm] = par.get(dm, 0) + 1
    print(f"  {len(confs)} conférences à venir enregistrées ; par domaine : "
          + ", ".join(f"{k} {v}" for k, v in sorted(par.items(), key=lambda x: -x[1])))
    return 0 if not pannes else 2


def main():
    p = argparse.ArgumentParser(description="Collecte des conférences à venir.")
    p.add_argument("--sortie", default=DONNEES)
    p.add_argument("--aujourdhui", default=dt.date.today().isoformat())
    p.add_argument("--cache", default="", help="dossier des archives déjà téléchargées (PC)")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("Collecte des conférences…")
    orga = None
    try:
        import organisateurs
        orga = organisateurs.lire(a.aujourdhui)
    except Exception as e:   # noqa: BLE001
        print(f"  ! échec : formulaire des organisateurs non lu ({str(e)[:120]})")
    code = collecter(a.sortie, a.aujourdhui, a.cache, organisateurs=orga)
    return 1 if code == 1 else 0     # une source en panne n'arrête pas le robot (code 2 -> 0)


if __name__ == "__main__":
    sys.exit(main())
