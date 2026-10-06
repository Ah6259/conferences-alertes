# -*- coding: utf-8 -*-
"""
Conférences signalées par leurs ORGANISATEURS (formulaire Google, réponses publiées en CSV) -> fiches brutes.

Ne fait rien tant que CSV_ORGANISATEURS_URL (robot/reglages.py) est vide.
Contrôles (une réponse refusée n'est jamais publiée) : nom, dates AAAA-MM-JJ à venir (≤ 18 mois, ≤ 60 jours),
lien officiel https, spécialité connue, case « j'accepte » cochée, pas de HTML, ≤ 3 conférences par lien officiel.
Le filtre des organisateurs douteux de collecter.py s'applique aussi (même chemin que les autres sources).

Colonnes reconnues (en-têtes du formulaire, mots-clés) : nom/name, sigle/acronym, début/start, fin/end, ville/city,
pays/country, format, spécialité/specialty, date limite/deadline, lien/link, accepte/accept.
"""
import csv
import io
import re

import classement as K
import reglages
import sources as S

COLONNES = {
    "titre": ("nom de la conf", "conference name", "nom", "name"),
    "acronyme": ("sigle", "acronym"),
    "debut": ("début", "debut", "start"),
    "fin": ("fin", "end"),
    "ville": ("ville", "city"),
    "pays": ("pays", "country"),
    "mode": ("format",),
    "specialite": ("spécialité", "specialite", "specialty"),
    "limite": ("date limite", "deadline"),
    "lien": ("lien", "link", "site"),
    "accepte": ("accepte", "accept", "certifie"),
}


def colonne(entetes, cle):
    for i, e in enumerate(entetes):
        el = e.lower()
        if any(m in el for m in COLONNES[cle]):
            return i
    return -1


def date_form(v):
    v = str(v or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", v) or None
    if m:
        return S.iso(*m.groups())
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", v)          # jj/mm/aaaa (feuille en paramètres France)
    return S.iso(m.group(3), m.group(2), m.group(1)) if m else ""


def analyser(texte):
    lignes = list(csv.reader(io.StringIO(texte)))
    if len(lignes) < 1:
        return []
    ent = lignes[0]
    idx = {k: colonne(ent, k) for k in COLONNES}
    if min(idx[k] for k in ("titre", "debut", "lien", "specialite")) < 0:
        raise ValueError("colonnes du formulaire introuvables")
    par_lien, res = {}, []
    specs_noms = {}
    for s in K.SPECIALITES:
        for n in s[2:5]:
            specs_noms[n.lower()] = s[0]
        specs_noms[s[0]] = s[0]
    for l in lignes[1:]:
        g = lambda k: (l[idx[k]].strip() if 0 <= idx[k] < len(l) else "")
        if idx["accepte"] >= 0 and not re.search(r"oui|yes|j'accepte|accept", g("accepte"), re.I):
            continue
        titre, lien = g("titre"), g("lien")
        if not titre or len(titre) > 200 or re.search(r"[<>]", titre + lien):
            continue
        if not re.fullmatch(r"https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/[^\s\"'<>]*)?", lien):
            continue
        spec = specs_noms.get(g("specialite").lower(), "")
        if not spec:
            continue
        par_lien[lien] = par_lien.get(lien, 0) + 1
        if par_lien[lien] > 3:
            continue
        mode = g("mode").lower()
        mode = "en-ligne" if re.search(r"ligne|online", mode) else "hybride" if re.search(r"hybrid", mode) else "presentiel"
        res.append(S.fiche("organisateur", acronyme=g("acronyme")[:40], titre=titre, lien=lien,
                           debut=date_form(g("debut")), fin=date_form(g("fin")), ville=g("ville")[:60],
                           code_pays=K.code_pays(g("pays")), mode=mode, specialites=[spec],
                           dates_limites=[x for x in [S.limite(date_form(g("limite")), "article", "Submission")] if x]))
    return res


def lire(jour=None):
    """Renvoie la liste des fiches, ou None si le formulaire n'est pas réglé."""
    url = str(getattr(reglages, "CSV_ORGANISATEURS_URL", "") or "").strip()
    if not url:
        return None
    if not re.fullmatch(r"https://docs\.google\.com/spreadsheets/d/e/[A-Za-z0-9_-]+/pub\?[A-Za-z0-9_=&.-]*output=csv[A-Za-z0-9_=&.-]*", url):
        raise ValueError("CSV_ORGANISATEURS_URL mal écrit")
    return analyser(S.telecharger(url, accepte="text/csv").decode("utf-8", errors="replace"))
