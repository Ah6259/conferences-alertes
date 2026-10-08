# -*- coding: utf-8 -*-
"""
Construit le site statique « Radar des conférences / Conference Radar » à partir de donnees/conferences.json
(rempli chaque jour par collecter.py). Trois langues : français, anglais, arabe (?lang=fr|en|ar).

Pages produites (racine du dépôt) :
  index.html                         accueil : toutes les conférences à venir, filtres, recherche
  domaine/<domaine>/                 une page par grand domaine (seulement s'il a des conférences)
  specialite/<spécialité>/           une page par spécialité
  continent/<continent>/, pays/<code>/   par continent, par pays (au moins 3 conférences)
  mois/<AAAA-MM>/                    par mois de l'événement
  conference/<id>/                   fiche de chaque conférence (JSON-LD Event)
  flux/ + flux/*.xml                 flux Atom gratuits par domaine et par spécialité
  a-propos/, publier/, abonnement/, abonnement/conditions/, sitemap.xml

Robustesse (comme le site Appels d'offres) : données illisibles -> sauvegarde ; chute > 50 % -> sauvegarde ;
sans sauvegarde -> site existant gardé ; bandeau daté si la dernière lecture réussie a 2 jours ou plus.

    python robot/construire_site.py [--aujourdhui AAAA-MM-JJ] [--donnees X.json] [--sortie dossier]
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import shutil
import sys
import urllib.parse

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import classement as K   # noqa: E402
import reglages          # noqa: E402
import sources as S      # noqa: E402

RACINE_SITE = os.path.dirname(ICI)
URL_SITE = "https://ah6259.github.io/conferences-alertes/"
CHEMIN_SITE = "/conferences-alertes/"
NOM = ("Radar des conférences", "Conference Radar", "رادار المؤتمرات")
OG_IMAGE = "assets/og-image-v1.jpg"
SEUIL_CHUTE = 0.5
AGE_AVERTISSEMENT = 2
MIN_PAYS = 3              # page par pays seulement à partir de 3 conférences
PAR_FLUX = 60             # entrées par flux Atom

E = lambda t: html.escape(str(t or ""), quote=True)
ISO = lambda t: "⁦" + str(t) + "⁩"     # isole un nombre ou un mot latin dans un texte arabe
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

MOIS_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
MOIS_FR_LONG = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
MOIS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MOIS_EN_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MOIS_AR = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"]


def L(fr, en, ar):
    """Texte en trois langues (le bon s'affiche selon la langue de la page)."""
    return f'<span data-l="fr">{fr}</span><span data-l="en">{en}</span><span data-l="ar">{ar}</span>'


def d3(d):
    """Une date -> (fr, en, ar) : « 16 févr. 2027 », « 16 Feb 2027 », « 16 فبراير 2027 »."""
    a, m, j = int(d[:4]), int(d[5:7]), int(d[8:10])
    return f"{j} {MOIS_FR[m - 1]} {a}", f"{j} {MOIS_EN[m - 1]} {a}", f"{ISO(j)} {MOIS_AR[m - 1]} {ISO(a)}"


def periode3(d1, d2):
    """Dates de l'événement, courtes : « 16–23 févr. 2027 », « 30 nov. – 4 déc. 2026 »."""
    if not d2 or d2 == d1:
        return d3(d1)
    a1, m1, j1 = int(d1[:4]), int(d1[5:7]), int(d1[8:10])
    a2, m2, j2 = int(d2[:4]), int(d2[5:7]), int(d2[8:10])
    if (a1, m1) == (a2, m2):
        return (f"{j1}–{j2} {MOIS_FR[m1 - 1]} {a1}", f"{j1}–{j2} {MOIS_EN[m1 - 1]} {a1}",
                f"{ISO(f'{j1}–{j2}')} {MOIS_AR[m1 - 1]} {ISO(a1)}")
    if a1 == a2:
        return (f"{j1} {MOIS_FR[m1 - 1]} – {j2} {MOIS_FR[m2 - 1]} {a2}", f"{j1} {MOIS_EN[m1 - 1]} – {j2} {MOIS_EN[m2 - 1]} {a2}",
                f"{ISO(j1)} {MOIS_AR[m1 - 1]} – {ISO(j2)} {MOIS_AR[m2 - 1]} {ISO(a2)}")
    f1, f2 = d3(d1), d3(d2)
    return tuple(f"{x} – {y}" for x, y in zip(f1, f2))


def mois3(cle):
    a, m = int(cle[:4]), int(cle[5:7])
    return f"{MOIS_FR_LONG[m - 1].capitalize()} {a}", f"{MOIS_EN_LONG[m - 1]} {a}", f"{MOIS_AR[m - 1]} {ISO(a)}"


def LL(t):
    return L(*t)


def nom_dom(slug):
    d = K.D_PAR_SLUG[slug]
    return d[1], d[2], d[3]


def nom_spec(slug):
    s = K.S_PAR_SLUG[slug]
    return s[2], s[3], s[4]


def nom_pays(code):
    p = K.PAYS.get(code)
    return (p[0], p[1], p[2]) if p else ("", "", "")


def nom_cont(slug):
    c = K.C_PAR_SLUG[slug]
    return c[1], c[2], c[3]


# ------------------------------------------------------------ images : un dessin COULEUR par grand domaine (aplats, fond pastel)
DESSINS = {
    # comptabilité : registre comptable + calculatrice
    "comptabilite": '<rect x="7" y="6" width="26" height="34" rx="3" fill="#1F7A6D"/><rect x="11" y="11" width="18" height="3" rx="1.5" fill="#CDEBE5"/><rect x="11" y="18" width="18" height="2.4" rx="1.2" fill="#9ED3C8"/><rect x="11" y="23" width="14" height="2.4" rx="1.2" fill="#9ED3C8"/><rect x="11" y="28" width="16" height="2.4" rx="1.2" fill="#9ED3C8"/><rect x="25" y="22" width="17" height="21" rx="3" fill="#F2B33D"/><rect x="28" y="25" width="11" height="4" rx="1" fill="#fff"/><g fill="#8A5A00"><circle cx="30" cy="33" r="1.4"/><circle cx="34" cy="33" r="1.4"/><circle cx="38" cy="33" r="1.4"/><circle cx="30" cy="38" r="1.4"/><circle cx="34" cy="38" r="1.4"/><circle cx="38" cy="38" r="1.4"/></g>',
    # finance : courbe qui monte + pièce
    "finance": '<rect x="6" y="8" width="36" height="30" rx="4" fill="#1E5AA8"/><path d="M11 31l8-8 6 5 11-12" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><path d="M31 16h5v5" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><circle cx="36" cy="37" r="7.5" fill="#F2B33D"/><circle cx="36" cy="37" r="4.6" fill="none" stroke="#B9830F" stroke-width="1.6"/>',
    # finance islamique : arc (architecture) + étoile à huit branches + pièce
    "finance-islamique": '<path d="M8 42V22a16 16 0 0 1 32 0v20z" fill="#0B7A3E"/><path d="M13.5 42V24a10.5 10.5 0 0 1 21 0v18z" fill="#DDF1E5"/><g transform="translate(24 28)" fill="#F2B33D"><rect x="-6.5" y="-6.5" width="13" height="13"/><rect x="-6.5" y="-6.5" width="13" height="13" transform="rotate(45)"/></g><circle cx="24" cy="28" r="3.2" fill="#0B7A3E"/>',
    "informatique": '<rect x="7" y="10" width="34" height="23" rx="3" fill="#3F51B5"/><rect x="10" y="13" width="28" height="17" rx="1.5" fill="#E8EAF9"/><path d="M4 36h40l-3 4H7z" fill="#2C3A8C"/><circle cx="17" cy="21.5" r="2.6" fill="#F2B33D"/><circle cx="31" cy="17" r="2.2" fill="#3F51B5"/><circle cx="31" cy="26" r="2.2" fill="#3F51B5"/><path d="M19 20.6l10-3M19 22.4l10 3.4" stroke="#3F51B5" stroke-width="1.6"/>',
    "ingenierie": '<rect x="8" y="36" width="20" height="5" rx="2" fill="#8A4A12"/><path d="M15 36l4-14 4 1.2-3 12.8z" fill="#C26A1B"/><circle cx="19" cy="21" r="4" fill="#F2B33D"/><path d="M21 19l13-7 2.2 3.4-12.6 7.6z" fill="#C26A1B"/><circle cx="35" cy="13.5" r="3" fill="#8A4A12"/><path d="M36 16l4 5-2.4 1.6-3.4-4.4z" fill="#F2B33D"/>',
    "physique": '<ellipse cx="24" cy="24" rx="18" ry="7" fill="none" stroke="#6B3FA0" stroke-width="2.6"/><ellipse cx="24" cy="24" rx="18" ry="7" fill="none" stroke="#9A73CC" stroke-width="2.6" transform="rotate(60 24 24)"/><ellipse cx="24" cy="24" rx="18" ry="7" fill="none" stroke="#6B3FA0" stroke-width="2.6" transform="rotate(-60 24 24)"/><circle cx="24" cy="24" r="4.6" fill="#F2B33D"/>',
    "vie-sante": '<path d="M24 41S7 30.5 7 18.5A8.5 8.5 0 0 1 24 13a8.5 8.5 0 0 1 17 5.5C41 30.5 24 41 24 41z" fill="#C2412F"/><path d="M10 24h8l3-6 4 11 3-5h10" fill="none" stroke="#fff" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round"/><circle cx="38" cy="24" r="2.4" fill="#F2B33D"/>',
    "mathematiques": '<rect x="7" y="7" width="34" height="34" rx="8" fill="#0E7C86"/><path d="M15 15h14l-8 9 8 9H15" fill="none" stroke="#fff" stroke-width="3" stroke-linejoin="round"/><circle cx="35" cy="34" r="3.4" fill="#F2B33D"/>',
    "shs": '<path d="M24 12c-5-3-11-3-17-1v26c6-2 12-2 17 1z" fill="#8A6A2F"/><path d="M24 12c5-3 11-3 17-1v26c-6-2-12-2-17 1z" fill="#B48B45"/><path d="M24 12v26" stroke="#F2B33D" stroke-width="2.4"/>',
    "economie": '<rect x="8" y="26" width="7" height="14" rx="1.5" fill="#2E8B57"/><rect x="19" y="18" width="7" height="22" rx="1.5" fill="#43A86F"/><rect x="30" y="10" width="7" height="30" rx="1.5" fill="#2E8B57"/><path d="M7 21l11-7 9 4 13-9" fill="none" stroke="#F2B33D" stroke-width="2.6" stroke-linecap="round"/>',
    "terre-environnement": '<circle cx="24" cy="24" r="17" fill="#3D7A3D"/><path d="M12 18c4 0 5 4 9 4s3 6 0 8-2 6-5 6c-2-3-6-6-6-11 0-3 1-5 2-7zM28 10c3 3 1 6 4 8s6 1 6 5c-3 1-6-2-9 0-2-3-4-8-1-13z" fill="#7DBE6E"/><circle cx="35" cy="34" r="3.6" fill="#F2B33D"/>',
}


def dessin(slug, cls="ic-d"):
    c = K.D_PAR_SLUG[slug][4]
    return f'<span class="{cls}" style="--c:{c}" aria-hidden="true"><svg viewBox="0 0 48 48">{DESSINS[slug]}</svg></span>'


ICONE_LIEU = '<svg viewBox="0 0 24 24"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>'
ICONE_LIEN = '<svg viewBox="0 0 24 24"><path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5"/></svg>'
ICONE_RSS = '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="5.5" cy="18.5" r="2.5"/><path d="M3 10a11 11 0 0 1 11 11h-3a8 8 0 0 0-8-8zM3 3a18 18 0 0 1 18 18h-3A15 15 0 0 0 3 6z"/></svg>'
ICONE_TELEGRAM = '<svg viewBox="0 0 24 24"><path d="M21 4.5 2.8 11.4c-.9.4-.9 1.6.1 1.9l4.5 1.4 1.7 5.3c.3.8 1.3 1 1.9.4l2.5-2.4 4.6 3.4c.7.5 1.7.1 1.9-.7L23 5.8c.2-1-.9-1.8-2-1.3z"/><path d="m8 14.6 9.5-6.6"/></svg>'
ICONE_CLOCHE = '<svg viewBox="0 0 24 24"><path d="M6 16.5V11a6 6 0 0 1 12 0v5.5l1.8 1.8H4.2z"/><path d="M10 20.5a2 2 0 0 0 4 0"/></svg>'
ICONE_WA = '<svg viewBox="0 0 24 24"><path d="M4 20l1.3-4A8 8 0 1 1 8.4 19z"/><path d="M9 8.6c0 3.4 2.9 6.4 6.4 6.4l1-1.4-2-1-1 .9c-1-.4-2.1-1.5-2.5-2.5l.9-1-1-2z"/></svg>'

# Vraies photos libres de droits (Wikimedia Commons) : crédit + licence sous le bandeau et dans « À propos »,
# preuve de la licence dans « preuves/2026-10-06/photos/ » (hors dépôt). Aucune marque lisible.
MOSAIQUE = "assets/photos/conferences-mosaique.jpg"
MOSAIQUE_MOBILE = "assets/photos/conferences-mosaique-carre.jpg"
PHOTOS = [{
    "sujet": ("Séance de questions-réponses d'un congrès scientifique (Boston, 2008)", "Panel session at an academic conference (Boston, 2008)", "جلسة نقاش في مؤتمر علمي (بوسطن، 2008)"),
    "auteur": "Piotrus", "licence": "CC BY-SA 3.0", "licence_url": "https://creativecommons.org/licenses/by-sa/3.0/deed.fr",
    "source_url": "https://commons.wikimedia.org/wiki/File:ASA_conference_2008_-_44.JPG",
}, {
    "sujet": ("Session de posters d'un congrès de médecine (Paris, 2011)", "Poster session at a medical congress (Paris, 2011)", "جلسة ملصقات علمية في مؤتمر طبي (باريس، 2011)"),
    "auteur": "Copyleft", "licence": "CC BY 3.0", "licence_url": "https://creativecommons.org/licenses/by/3.0/deed.fr",
    "source_url": "https://commons.wikimedia.org/wiki/File:2011_international_congress_intensive_care_medicine_paris_posters_science.jpg",
}]

COMPTEUR = "https://prix-eaux-tunisie.goatcounter.com"
FORMSPREE = "https://formspree.io"
CSP = ("default-src 'self'; script-src 'self' https://gc.zgo.at; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
       f"font-src 'self' https://fonts.gstatic.com; img-src 'self' data: {COMPTEUR}; connect-src 'self' {COMPTEUR} {FORMSPREE}; "
       f"form-action 'self' https://docs.google.com {FORMSPREE}; frame-src 'none'; object-src 'none'; base-uri 'self'")

# ------------------------------------------------------------ Alertes Pro (abonnement payant, comme le site Appels d'offres)
ABO = {
    "prix_mois": 9, "prix_an": 79, "essai_jours": 14, "rappel_jours": 3,
    "numero": "24 321 390", "whatsapp": "21624321390", "paiements": ["D17", "IZI"],
    "formspree": "https://formspree.io/f/mwlpakqj",
}
TEXTE_PREUVE = "Bonjour, voici la preuve de paiement de mon abonnement Alertes Pro (Radar des conférences). Nom : "
TEXTE_ETRANGER = "Bonjour, je souhaite m'abonner aux Alertes Pro (Radar des conférences) depuis l'étranger. Nom : "


def reglage(nom, motif):
    v = str(getattr(reglages, nom, "") or "").strip()
    if v and not re.fullmatch(motif, v):
        print(f"  ! échec : réglage {nom} mal écrit ({v[:60]}) -> ignoré")
        return ""
    return v


def adresses():
    canaux = {}
    brut = getattr(reglages, "TELEGRAM_CANAUX_URL", {}) or {}
    for d in K.D_PAR_SLUG:
        v = str(brut.get(d, "") or "").strip() if isinstance(brut, dict) else ""
        if v and not re.fullmatch(r"https://t\.me/[A-Za-z0-9_]{4,64}", v):
            print(f"  ! échec : canal Telegram du domaine {d} mal écrit -> ignoré")
            v = ""
        canaux[d] = v
    return {
        "canaux": canaux,
        "robot": reglage("TELEGRAM_ROBOT_ALERTES", r"@?[A-Za-z][A-Za-z0-9_]{1,28}[Bb][Oo][Tt]").lstrip("@"),
        "formulaire": reglage("FORMULAIRE_ORGANISATEURS_URL", r"https://(forms\.gle/[A-Za-z0-9_-]{4,64}|docs\.google\.com/forms/[A-Za-z0-9_/=?&.-]{8,200})"),
    }


# ------------------------------------------------------------ données
def charger(chemin):
    """Renvoie (dictionnaire, liste propre) ou (None, []) si le fichier est absent ou illisible."""
    try:
        with open(chemin, encoding="utf-8") as f:
            brut = json.load(f)
        confs = brut["conferences"]
    except (OSError, ValueError, KeyError, TypeError):
        return None, []
    if not isinstance(confs, list):
        return None, []
    return brut, nettoyer(confs)


LIEN_OK = re.compile(r"^https://[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:[/?#][^\s\"'<>]*)?$")


def nettoyer(confs):
    """Garde les fiches valides (dates, lien officiel https, domaine connu), fusionne les identifiants en double."""
    propres = {}
    for c in confs:
        if not isinstance(c, dict):
            continue
        ident = str(c.get("id") or "")
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", ident):
            continue
        if not DATE.match(str(c.get("debut") or "")) or not LIEN_OK.match(str(c.get("lien") or "")):
            continue
        f = dict(c)
        f["fin"] = f["fin"] if DATE.match(str(f.get("fin") or "")) and f["fin"] >= f["debut"] else f["debut"]
        f["specialites"] = [s for s in f.get("specialites") or [] if s in K.S_PAR_SLUG]
        if not f["specialites"]:
            continue
        f["domaines"] = K.domaines_de(f["specialites"])
        f["pays"] = f.get("pays") if f.get("pays") in K.PAYS else ""
        f["mode"] = f.get("mode") if f.get("mode") in K.MODES else "presentiel"
        f["continent"] = K.continent(f["pays"], f["mode"])
        f["type"] = f.get("type") if f.get("type") in K.TYPES else "conference"
        f["titre"] = re.sub(r"\s+", " ", str(f.get("titre") or "")).strip()[:220]
        f["acronyme"] = re.sub(r"\s+", " ", str(f.get("acronyme") or "")).strip()[:40]
        f["ville"] = re.sub(r"\s+", " ", str(f.get("ville") or "")).strip()[:60]
        f["rang"] = re.sub(r"\s+", " ", str(f.get("rang") or "")).strip()[:40]
        f["dates_limites"] = [x for x in f.get("dates_limites") or [] if isinstance(x, dict) and DATE.match(str(x.get("date") or ""))
                              and x.get("type") in ("article", "resume", "autre")]
        f["sources"] = [s for s in f.get("sources") or [] if s in S.SOURCES] or ["ccfddl"]
        f["ajoute_le"] = f["ajoute_le"] if DATE.match(str(f.get("ajoute_le") or "")) else f["debut"]
        propres[ident] = f
    return list(propres.values())


def a_venir(confs, jour):
    """Conférences pas encore terminées le jour donné, triées par date de début."""
    res = [c for c in confs if c["fin"] >= jour]
    res.sort(key=lambda c: (c["debut"], c["id"]))
    return res


def limites_soumission(c, jour=None):
    return [x for x in c["dates_limites"] if x["type"] in ("article", "resume") and (jour is None or x["date"] >= jour)]


# ------------------------------------------------------------ morceaux de page
def texte_lieu(c):
    if c["mode"] == "en-ligne":
        return L("En ligne", "Online", "عن بعد")
    pf, pe, pa = nom_pays(c["pays"])
    v = E(c["ville"])
    fr = ", ".join(x for x in (v, pf) if x) or "Lieu à confirmer"
    en = ", ".join(x for x in (v, pe) if x) or "Venue to be confirmed"
    ar = "، ".join(x for x in ((f"<bdi>{v}</bdi>" if v else ""), pa) if x) or "المكان سيُحدَّد"
    if c["mode"] == "hybride":
        fr, en, ar = fr + " · hybride", en + " · hybrid", ar + " · هجين"
    return L(fr, en, ar)


def nom_conf(c):
    """« AAAI 2027 — AAAI Conference on Artificial Intelligence »."""
    acr = c["acronyme"]
    if acr and str(c["annee"]) not in acr:
        acr = f"{acr} {c['annee']}"
    titre = c["titre"]
    if acr and titre and titre.lower() not in (c["acronyme"].lower(), acr.lower()):
        return acr, titre
    return (acr or titre), ""


# ------------------------------------------------------------ cartes légères (une seule langue dans le HTML, traduite par assets/textes.js)
TX = {}     # dictionnaire des textes courts répétés : clé -> (fr, en, ar), écrit dans assets/textes.js


def t(cle, fr, en, ar):
    """Petit texte répété sur chaque carte : écrit UNE fois (anglais), traduit par page.js grâce à assets/textes.js."""
    TX[cle] = (fr, en, ar)
    return f'<span data-t="{cle}">{E(en)}</span>'


def t_spec(s):
    return t("s:" + s, *nom_spec(s))


def t_pays(code):
    return t("p:" + code, *nom_pays(code)) if code in K.PAYS else ""


def lieu_court(c):
    if c["mode"] == "en-ligne":
        return t("m:en-ligne", *K.MODES["en-ligne"])
    morceaux = [f"<bdi>{E(c['ville'])}</bdi>" if c["ville"] else "", t_pays(c["pays"])]
    txt = ", ".join(x for x in morceaux if x) or t("lieu-inconnu", "Lieu à confirmer", "Venue to be confirmed", "المكان سيُحدَّد")
    if c["mode"] == "hybride":
        txt += " · " + t("m:hybride", *K.MODES["hybride"])
    return txt


def dates_en(d1, d2):
    return re.sub("[⁦⁩]", "", periode3(d1, d2)[1])


def bloc_limite(c, jour):
    """Dates limites de soumission à venir (le JavaScript montre la prochaine selon la date du visiteur, dans sa langue)."""
    morceaux, vues = [], set()
    for x in limites_soumission(c, jour):
        if x["date"] in vues:          # résumé et article le même jour : une seule ligne
            continue
        vues.add(x["date"])
        h = (x["heure"] + (" " + x["fuseau"] if x["fuseau"] else "")) if x["heure"] else ""
        quoi = t("q:resume", "résumé", "abstract", "ملخص") if x["type"] == "resume" else t("q:article", "article", "paper", "مقال")
        morceaux.append(f'<b class="dl" data-d="{x["date"]}">{d3(x["date"])[1]}</b>'
                        f'<small class="dl-quoi" data-d="{x["date"]}">{quoi}{(" · <bdi dir=" + chr(34) + "ltr" + chr(34) + ">" + E(h) + "</bdi>") if h else ""}</small>')
    if limites_soumission(c):
        ferme = t("ferme", "Soumissions closes", "Submissions closed", "انتهى أجل الإرسال")
    else:
        ferme = t("voir-site", "Voir le site officiel", "See official website", "انظر الموقع الرسمي")
    morceaux.append(f'<b class="dl-ferme"{" hidden" if limites_soumission(c, jour) else ""}>{ferme}</b>')
    return "".join(morceaux)


def carte(c, racine, jour):
    s0 = c["specialites"][0]
    d0 = K.S_PAR_SLUG[s0][1]
    coul = K.D_PAR_SLUG[d0][4]
    sigle, titre = nom_conf(c)
    lims = limites_soumission(c, jour)
    urgent = bool(lims) and (dt.date.fromisoformat(lims[0]["date"]) - dt.date.fromisoformat(jour)).days < 7
    rang = f'<span class="rang">{E(c["rang"].split(" · ")[0])}</span>' if c["rang"] else ""
    titre_html = f'<span class="sigle">{E(sigle)}</span>' + (f" — {E(titre)}" if titre else "")
    return f"""<article class="cf{' urgent' if urgent else ''}{'' if lims else ' ferme'}" id="{c['id']}" style="--c:{coul}" data-dom="{' '.join(c['domaines'])}" data-spec="{' '.join(c['specialites'])}" data-cont="{c['continent']}" data-mode="{c['mode']}" data-debut="{c['debut']}" data-fin="{c['fin']}" data-ajout="{c['ajoute_le'] if c['ajoute_le'] > PREMIERE[0] else ''}" data-limites="{' '.join(x['date'] for x in limites_soumission(c))}">
<div class="cf-haut"><span class="ic-m"><svg viewBox="0 0 48 48"><use href="#d-{d0}"/></svg></span><a class="pastille" href="{racine}specialite/{s0}/">{t_spec(s0)}</a><span class="pastille neutre">{t("ty:" + c["type"], *K.TYPES[c["type"]])}</span>{rang}<span class="nouveau" hidden>{t("nouveau", "Nouveau", "New", "جديد")}</span><span class="rappel" hidden></span></div>
<h3 lang="en" dir="ltr"><a href="{racine}conference/{c['id']}/">{titre_html}</a></h3>
<p class="lieu">{USE_LIEU}<span>{lieu_court(c)}</span></p>
<div class="cf-infos"><div><span>{t("dates", "Dates", "Dates", "التاريخ")}</span><b class="dt" data-d1="{c['debut']}" data-d2="{c['fin']}">{dates_en(c['debut'], c['fin'])}</b><small class="reste-ev"></small></div>
<div class="limite"><span>{t("limite", "Date limite", "Deadline", "آخر أجل")}</span>{bloc_limite(c, jour)}<small class="reste"></small></div></div>
<div class="cf-liens"><a class="fiche" href="{racine}conference/{c['id']}/">{t("fiche", "Fiche", "Details", "البطاقة")}</a><a class="officiel" href="{E(c['lien'])}" target="_blank" rel="noopener">{t("officiel", "Site officiel", "Official site", "الموقع الرسمي")}{USE_LIEN}</a></div>
</article>"""


SPRITE = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>'
          + "".join(f'<symbol id="d-{k}" viewBox="0 0 48 48">{v}</symbol>' for k, v in DESSINS.items())
          + ICONE_LIEU.replace('<svg viewBox="0 0 24 24">', '<symbol id="i-lieu" viewBox="0 0 24 24">').replace("</svg>", "</symbol>")
          + ICONE_LIEN.replace('<svg viewBox="0 0 24 24">', '<symbol id="i-lien" viewBox="0 0 24 24">').replace("</svg>", "</symbol>")
          + "</defs></svg>")
USE_LIEU = '<svg viewBox="0 0 24 24"><use href="#i-lieu"/></svg>'
USE_LIEN = '<svg viewBox="0 0 24 24"><use href="#i-lien"/></svg>'


def ecrire_textes(sortie):
    """assets/textes.js : traductions des petits textes des cartes (fichier externe : aucun script en ligne)."""
    js = ("/* Fichier FABRIQUÉ par robot/construire_site.py (ne pas modifier à la main) : textes courts des cartes en"
          + chr(10) + "   français, anglais et arabe, utilisés par page.js (attribut data-t). */" + chr(10)
          + "window.TEXTES = " + json.dumps({k: list(v) for k, v in sorted(TX.items())}, ensure_ascii=False, separators=(",", ":")) + ";" + chr(10))
    ecrire(sortie, "assets/textes.js", js)


def compter(confs, cle):
    res = {}
    for c in confs:
        vals = c[cle] if isinstance(c[cle], list) else [c[cle]]
        for v in vals:
            if v:
                res[v] = res.get(v, 0) + 1
    return res


def options(paires, tous, compte):
    o = [f'<option value="" data-fr="{E(tous[0])}" data-en="{E(tous[1])}" data-ar="{E(tous[2])}">{E(tous[1])} ({sum(compte.values()) if isinstance(compte, dict) else compte})</option>']
    for v, n3, n in paires:
        o.append(f'<option value="{v}" data-fr="{E(n3[0])}" data-en="{E(n3[1])}" data-ar="{E(re.sub("[⁦⁩]", "", n3[2]))}">{E(n3[1])} ({n})</option>')
    return "".join(o)


def filtres(confs, jour, sans=()):
    """Barre de recherche et filtres. Seules les valeurs présentes sur la page sont proposées, avec leur nombre."""
    n = len(confs)
    blocs = [f'<div class="f-q"><label for="f-q">{L("Rechercher", "Search", "بحث")}</label>'
             '<input id="f-q" type="search" enterkeyhint="search" autocomplete="off" placeholder="AAAI, quantum, Tokyo…" '
             'data-fr="Sigle, thème, ville, pays…" data-en="Acronym, topic, city, country…" data-ar="اسم المؤتمر، موضوع، مدينة…"></div>']
    if "domaine" not in sans:
        cd = compter(confs, "domaines")
        paires = [(d[0], nom_dom(d[0]), cd[d[0]]) for d in K.DOMAINES if cd.get(d[0])]
        if len(paires) > 1:
            blocs.append(f'<div><label for="f-dom">{L("Domaine", "Field", "المجال")}</label><select id="f-dom">'
                         f'{options(paires, ("Tous les domaines", "All fields", "كل المجالات"), n)}</select></div>')
    if "specialite" not in sans:
        cs = compter(confs, "specialites")
        paires = [(s[0], nom_spec(s[0]), cs[s[0]]) for s in K.SPECIALITES if cs.get(s[0])]
        if len(paires) > 1:
            blocs.append(f'<div><label for="f-spec">{L("Spécialité", "Specialty", "التخصص")}</label><select id="f-spec">'
                         f'{options(paires, ("Toutes les spécialités", "All specialties", "كل التخصصات"), n)}</select></div>')
    if "continent" not in sans:
        cc = compter(confs, "continent")
        paires = [(x[0], nom_cont(x[0]), cc[x[0]]) for x in K.CONTINENTS if cc.get(x[0])]
        if len(paires) > 1:
            blocs.append(f'<div><label for="f-cont">{L("Lieu", "Where", "المكان")}</label><select id="f-cont">'
                         f'{options(paires, ("Monde entier", "Worldwide", "كل العالم"), n)}</select></div>')
    cm = compter(confs, "mode")
    paires = [(m, K.MODES[m], cm[m]) for m in K.MODES if cm.get(m)]
    if len(paires) > 1:
        blocs.append(f'<div><label for="f-mode">{L("Format", "Format", "الصيغة")}</label><select id="f-mode">'
                     f'{options(paires, ("Tous les formats", "All formats", "كل الصيغ"), n)}</select></div>')
    blocs.append(f'<div><label for="f-limite">{L("Date limite", "Deadline", "آخر أجل")}</label><select id="f-limite">'
                 '<option value="" data-fr="Toutes" data-en="All" data-ar="الكل">All</option>'
                 '<option value="ouverte" data-fr="Encore ouverte" data-en="Still open" data-ar="ما زال مفتوحًا">Still open</option>'
                 '<option value="7" data-fr="Dans les 7 jours" data-en="Within 7 days" data-ar="خلال 7 أيام">Within 7 days</option>'
                 '<option value="30" data-fr="Dans les 30 jours" data-en="Within 30 days" data-ar="خلال 30 يومًا">Within 30 days</option>'
                 '<option value="90" data-fr="Dans les 3 mois" data-en="Within 3 months" data-ar="خلال 3 أشهر">Within 3 months</option></select></div>')
    if "mois" not in sans:
        mm = compter([dict(c, m=c["debut"][:7]) for c in confs], "m")
        paires = [(k, mois3(k), mm[k]) for k in sorted(mm)]
        if len(paires) > 1:
            blocs.append(f'<div><label for="f-mois">{L("Mois de l\'événement", "Event month", "شهر الحدث")}</label><select id="f-mois">'
                         f'{options(paires, ("Tous les mois", "Any month", "كل الأشهر"), n)}</select></div>')
    blocs.append(f'<div class="f-tri"><label for="f-tri">{L("Trier par", "Sort by", "الترتيب حسب")}</label><select id="f-tri">'
                 '<option value="limite" data-fr="Date limite la plus proche" data-en="Nearest deadline" data-ar="أقرب آخر أجل">Nearest deadline</option>'
                 '<option value="debut" data-fr="Date de l\'événement" data-en="Event date" data-ar="تاريخ الحدث">Event date</option>'
                 '<option value="ajout" data-fr="Ajoutées récemment" data-en="Recently added" data-ar="المضافة حديثًا">Recently added</option></select></div>')
    return f'<section class="carte filtres">{"".join(blocs)}</section>'


def liste_html(confs, racine, jour, vide):
    cartes = "\n".join(carte(c, racine, jour) for c in confs)
    n = len(confs)
    return f"""<p class="compte" id="compte" aria-live="polite"><span>{L(f"{n} conférence{'s' if n > 1 else ''} à venir", f"{n} upcoming conference{'s' if n > 1 else ''}", f"{ISO(n)} مؤتمر قادم")}</span></p>
<div class="liste" id="liste">
{cartes}
</div>
<button type="button" class="plus" id="plus" hidden>Show more</button>
<p class="carte vide" id="vide"{' hidden' if confs else ''}>{LL(vide)}</p>"""


def tuiles_domaines(confs, racine, actuel=None):
    cd = compter(confs, "domaines")
    t = []
    for d in K.DOMAINES:
        n = cd.get(d[0], 0)
        if not n:
            continue
        t.append(f'<a href="{racine}domaine/{d[0]}/" style="--c:{d[4]}"{" class=" + chr(34) + "ici" + chr(34) if d[0] == actuel else ""}>'
                 f'{dessin(d[0])}<span class="d-txt"><b>{LL(nom_dom(d[0]))}</b><small>{L(f"{n} à venir", f"{n} upcoming", f"{ISO(n)} قادم")}</small></span></a>')
    return f'<div class="domaines" id="grille-domaines">{"".join(t)}</div>'


def grille(paires, racine, dossier, ident, actuel=None, classe=""):
    liens = "".join(f'<a href="{racine}{dossier}/{slug}/"{" class=" + chr(34) + "ici" + chr(34) if slug == actuel else ""}>'
                    f'<span>{LL(n3)}</span><span class="n">{n}</span></a>' for slug, n3, n in paires if n)
    return f'<div class="grille{(" " + classe) if classe else ""}" id="{ident}">{liens}</div>'


def paires_specs(confs, domaine=None):
    cs = compter(confs, "specialites")
    return [(s[0], nom_spec(s[0]), cs.get(s[0], 0)) for s in K.SPECIALITES if cs.get(s[0]) and (domaine is None or s[1] == domaine)]


def paires_conts(confs):
    cc = compter(confs, "continent")
    return [(x[0], nom_cont(x[0]), cc.get(x[0], 0)) for x in K.CONTINENTS if cc.get(x[0])]


def paires_pays(confs):
    cp = compter(confs, "pays")
    return sorted([(code.lower(), nom_pays(code), n) for code, n in cp.items() if n >= MIN_PAYS], key=lambda x: -x[2])


def paires_mois(confs):
    mm = compter([dict(c, m=c["debut"][:7]) for c in confs], "m")
    return [(k, mois3(k), mm[k]) for k in sorted(mm)]


def boutons_alertes(adr, domaines=None, racine=""):
    """Alertes GRATUITES sans données personnelles : flux RSS (toujours) + canaux Telegram (s'ils existent)."""
    b = []
    for d in domaines or []:
        url = adr["canaux"].get(d)
        if url:
            b.append(f'<a class="btn-alerte" href="{E(url)}" target="_blank" rel="noopener">{ICONE_TELEGRAM}'
                     f'{L("Alertes gratuites sur Telegram : ", "Free Telegram alerts: ", "تنبيهات مجانية على تيليغرام: ")}{LL(nom_dom(d))}</a>')
    flux = f"{racine}flux/{domaines[0]}.xml" if domaines and len(domaines) == 1 else f"{racine}flux/"
    b.append(f'<a class="btn-alerte btn-rss" href="{flux}">{ICONE_RSS}'
             f'{L("Alertes gratuites par flux RSS (sans inscription)", "Free RSS alerts (no sign-up)", "تنبيهات مجانية عبر ⁨RSS⁩ (دون تسجيل)")}</a>')
    return f'<div class="alertes-btn">{"".join(b)}</div>'


def bouton_pro_accueil(racine=""):
    n = ABO["essai_jours"]
    titre = L("Alertes Pro : les conférences de VOTRE spécialité sur Telegram", "Pro Alerts: conferences in YOUR specialty on Telegram",
              "تنبيهات Pro: مؤتمرات تخصصك على تيليغرام")
    sous = L(f"{n} jours d'essai gratuit · nouvelles conférences et rappels de dates limites",
             f"{n}-day free trial · new conferences and deadline reminders",
             f"تجربة مجانية {ISO(n)} يومًا · مؤتمرات جديدة وتذكير بآجال الإرسال")
    return (f'    <a class="btn-pro-grand" id="btn-pro-accueil" href="{racine}abonnement/">{ICONE_CLOCHE}'
            f'<span>{titre}<small>{sous}</small></span></a>')


AVIS = """<section class="carte avis" id="avis" aria-labelledby="avis-titre">
  <h2 id="avis-titre"><span data-l="fr">Votre avis</span><span data-l="en">Your feedback</span><span data-l="ar">رأيك يهمّنا</span></h2>
  <p class="avis-intro"><span data-l="fr">Une remarque, une conférence manquante, une erreur ? Écrivez-nous : chaque message est lu.</span><span data-l="en">A comment, a missing conference, a mistake? Write to us: every message is read.</span><span data-l="ar">ملاحظة، مؤتمر ناقص، خطأ؟ اكتب لنا: كل رسالة تُقرأ.</span></p>
  <form id="avis-form" action="https://formspree.io/f/mwlpakqj" method="POST">
    <fieldset>
      <legend><span data-l="fr">Votre note (facultatif)</span><span data-l="en">Your rating (optional)</span><span data-l="ar">تقييمك (اختياري)</span></legend>
      <div class="avis-notes">
        <label><input type="radio" name="note" value="😀 Très bien"><span class="emoji" aria-hidden="true">😀</span><span class="avis-cache"><span data-l="fr">Très bien</span><span data-l="en">Very good</span><span data-l="ar">ممتاز</span></span></label>
        <label><input type="radio" name="note" value="🙂 Bien"><span class="emoji" aria-hidden="true">🙂</span><span class="avis-cache"><span data-l="fr">Bien</span><span data-l="en">Good</span><span data-l="ar">جيد</span></span></label>
        <label><input type="radio" name="note" value="😐 Moyen"><span class="emoji" aria-hidden="true">😐</span><span class="avis-cache"><span data-l="fr">Moyen</span><span data-l="en">Average</span><span data-l="ar">متوسط</span></span></label>
        <label><input type="radio" name="note" value="🙁 Pas bien"><span class="emoji" aria-hidden="true">🙁</span><span class="avis-cache"><span data-l="fr">Pas bien</span><span data-l="en">Poor</span><span data-l="ar">سيئ</span></span></label>
      </div>
    </fieldset>
    <label class="avis-etiquette" for="avis-message"><span data-l="fr">Votre message</span><span data-l="en">Your message</span><span data-l="ar">رسالتك</span></label>
    <textarea id="avis-message" name="message" required maxlength="1000" rows="4" data-ph-fr="Ce qui vous plaît, ce qui manque, une conférence à ajouter…" data-ph-en="What you like, what is missing, a conference to add…" data-ph-ar="ما يعجبك، ما ينقص، مؤتمر يجب إضافته…"></textarea>
    <span class="avis-compte" id="avis-compte" aria-live="off">0 / 1000</span>
    <label class="avis-etiquette" for="avis-email"><span data-l="fr">Votre e-mail (facultatif, pour vous répondre)</span><span data-l="en">Your e-mail (optional, so we can reply)</span><span data-l="ar">بريدك الإلكتروني (اختياري، للرد عليك)</span></label>
    <input type="email" id="avis-email" name="email" autocomplete="email" maxlength="200" data-ph-fr="nom@example.com" data-ph-en="name@example.com" data-ph-ar="nom@example.com">
    <input type="hidden" name="site" value="Radar des conférences">
    <input type="hidden" name="page" value="">
    <input type="hidden" name="_subject" value="Avis — Radar des conférences">
    <input type="text" name="_gotcha" class="avis-piege" tabindex="-1" autocomplete="off" aria-hidden="true">
    <div class="avis-actions">
      <button type="submit" class="avis-envoyer"><span data-l="fr">Envoyer</span><span data-l="en">Send</span><span data-l="ar">إرسال</span></button>
      <span id="avis-status" role="status" aria-live="polite"></span>
    </div>
    <p class="avis-mention"><span data-l="fr">Votre avis est envoyé au créateur du site (service Formspree). Rien n&#39;est envoyé sans clic sur « Envoyer ».</span><span data-l="en">Your feedback is sent to the site owner (Formspree service). Nothing is sent until you press “Send”.</span><span data-l="ar">يُرسل رأيك إلى صاحب الموقع (خدمة ⁨Formspree⁩). لا يُرسل أي شيء دون الضغط على «إرسال».</span></p>
  </form>
</section>"""


def page(chemin, racine, titre, description, hero, contenu, v, etat, jsonld="", classe_hero="", scripts=(), alternates=True):
    canon = URL_SITE + chemin
    alt = ""
    if alternates:
        alt = "".join(f'<link rel="alternate" hreflang="{l}" href="{canon}?lang={l}">' for l in ("fr", "en", "ar")) + \
              f'<link rel="alternate" hreflang="x-default" href="{canon}">\n'
    return f"""<!doctype html>
<html lang="en" dir="ltr" translate="no" data-racine="{racine}">
<head>
<meta charset="utf-8">
<meta name="google" content="notranslate">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="robots" content="noai, noimageai">
<title>{E(titre)}</title>
<meta name="description" content="{E(description)}">
<link rel="canonical" href="{canon}">
{alt}<link rel="icon" href="{racine}assets/logo.svg" type="image/svg+xml">
<link rel="icon" href="{racine}favicon.ico" sizes="32x32">
<link rel="apple-touch-icon" href="{racine}assets/apple-touch-icon.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Conferences">
<link rel="manifest" href="{racine}manifest.webmanifest">
<link rel="alternate" type="application/atom+xml" title="Conference Radar — all" href="{racine}flux/tout.xml">
<meta name="theme-color" content="#3B2F96">
<meta property="og:title" content="{E(titre.split(' | ')[0])}">
<meta property="og:description" content="{E(description)}">
<meta property="og:url" content="{canon}">
<meta property="og:image" content="{URL_SITE}{OG_IMAGE}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta property="og:type" content="website">
<meta property="og:locale" content="en_US"><meta property="og:locale:alternate" content="fr_FR"><meta property="og:locale:alternate" content="ar_TN">
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;700;800&family=Noto+Kufi+Arabic:wght@400;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{racine}assets/style.css?v={v}">
{jsonld}<script src="{racine}assets/textes.js?v={v}"></script>
<script src="{racine}assets/page.js?v={v}"></script>
<script src="{racine}assets/app.js?v={v}"></script>
<script src="{racine}assets/avis.js?v={v}"></script>
{"".join(f'<script src="{racine}assets/{s}?v={v}"></script>{chr(10)}' for s in scripts)}</head>
<body data-maj="{etat['maj']}" data-maj-texte="{etat['maj_texte']}" data-panne="{'1' if etat['panne'] else '0'}">
{SPRITE}
<header class="entete" id="entete"></header>
<section class="hero{classe_hero}">
  <div class="wrap">
{hero}
    <span class="maj">{L("Mis à jour le", "Updated", "تحيين")}&nbsp;{ISO(etat['maj_texte']) if etat['maj_texte'] else '—'}</span>
  </div>
</section>
<main class="wrap chevauche">
<div class="alerte-panne{' on' if etat['panne'] else ''}" id="alerte-panne" role="status">{E(etat['message'])}</div>
{contenu}
</main>
<footer id="pied"><div class="wrap"><p>Sources : CCF Deadlines, AI Deadlines, HCI Deadlines, Neuro Deadlines, Bioinformatics Conferences, RoboDDL (MIT) · INSPIRE-HEP (CC0) · official organiser pages · © 2026 Radar des conférences / Conference Radar — tous droits réservés.</p></div></footer>
<script data-goatcounter="{COMPTEUR}/count" async src="https://gc.zgo.at/count.js"></script>
</body>
</html>
"""


def fil(racine, *etapes):
    morceaux = [f'<a href="{racine}">{L("Accueil", "Home", "الرئيسية")}</a>']
    for e in etapes:
        morceaux.append(e if e.startswith("<a ") else e)
    return '    <p class="fil">' + " › ".join(morceaux) + "</p>"


def credit_photos():
    morceaux = " · ".join(
        f'<a href="{E(ph["source_url"])}" target="_blank" rel="noopener">{E(ph["auteur"])}</a> '
        f'<a href="{E(ph["licence_url"])}" target="_blank" rel="noopener license">{E(ph["licence"])}</a>' for ph in PHOTOS)
    return (f'    <p class="credit-photo" data-photo="{E(MOSAIQUE)} {E(MOSAIQUE_MOBILE)}">{L("Photos", "Photos", "صور")} '
            f'<bdi dir="ltr">(Wikimedia Commons) : {morceaux}</bdi></p>')


# ------------------------------------------------------------ pages de liste
def page_liste(chemin, racine, titre, desc, hero, confs, jour, v, etat, sans=(), apres="", avant="", jsonld="", classe_hero=""):
    vide = ("Aucune conférence à venir pour ce choix. Essayez un autre filtre.", "No upcoming conference for this choice. Try another filter.",
            "لا يوجد مؤتمر قادم لهذا الاختيار. جرّب تصفية أخرى.")
    contenu = f"""{avant}{filtres(confs, jour, sans)}
{liste_html(confs, racine, jour, vide)}
{apres}"""
    return chemin, page(chemin, racine, titre, desc, hero, contenu, v, etat, jsonld, classe_hero)


def jsonld_event(c):
    sigle, titre = nom_conf(c)
    mode = {"presentiel": "OfflineEventAttendanceMode", "en-ligne": "OnlineEventAttendanceMode", "hybride": "MixedEventAttendanceMode"}[c["mode"]]
    ev = {"@context": "https://schema.org", "@type": "Event", "name": f"{sigle}" + (f" — {titre}" if titre else ""),
          "startDate": c["debut"], "endDate": c["fin"], "eventStatus": "https://schema.org/EventScheduled",
          "eventAttendanceMode": "https://schema.org/" + mode, "url": c["lien"],
          "description": f"{K.TYPES[c['type']][1]} — {', '.join(nom_spec(s)[1] for s in c['specialites'])}."}
    if c["mode"] == "en-ligne":
        ev["location"] = {"@type": "VirtualLocation", "url": c["lien"]}
    else:
        adr = {"@type": "PostalAddress"}
        if c["ville"]:
            adr["addressLocality"] = c["ville"]
        if c["pays"]:
            adr["addressCountry"] = c["pays"]
        ev["location"] = {"@type": "Place", "name": c["ville"] or nom_pays(c["pays"])[1] or "TBA", "address": adr}
    return '<script type="application/ld+json">\n' + json.dumps(ev, ensure_ascii=False).replace("</", "<\\/") + "\n</script>\n"


def page_fiche(c, jour, v, etat, adr):
    racine = "../../"
    sigle, titre = nom_conf(c)
    s0 = c["specialites"][0]
    d0 = K.S_PAR_SLUG[s0][1]
    p = periode3(c["debut"], c["fin"])
    lims = c["dates_limites"]
    lignes = []
    for x in lims:
        f, e, a = d3(x["date"])
        h = " · " + E(x["heure"]) + (" " + E(x["fuseau"]) if x["fuseau"] else "") if x["heure"] else ""
        quoi = {"resume": ("Résumé", "Abstract", "الملخص"), "article": ("Article complet", "Full paper", "المقال الكامل"),
                "autre": ("Autre étape", "Other step", "مرحلة أخرى")}[x["type"]]
        lib = f' <small>({E(x["libelle"])})</small>' if x.get("libelle") and x["libelle"].lower() not in ("paper", "abstract") else ""
        lignes.append(f'<li class="{"passe" if x["date"] < jour else ""}" data-d="{x["date"]}"><span>{LL(quoi)}{lib}</span><b>{L(f + h, e + h, a + h)}</b></li>')
    srcs = ", ".join(f'<a href="{E(S.SOURCES[s]["url"])}" target="_blank" rel="noopener">{E(S.SOURCES[s]["nom"])}</a> ({E(S.SOURCES[s]["licence"])})'
                     if S.SOURCES[s]["url"] else f'{E(S.SOURCES[s]["nom"])}' for s in c["sources"])
    specs = " · ".join(f'<a href="{racine}specialite/{s}/">{LL(nom_spec(s))}</a>' for s in c["specialites"])
    doms = " · ".join(f'<a href="{racine}domaine/{d}/">{LL(nom_dom(d))}</a>' for d in c["domaines"])
    lieu = texte_lieu(c)
    verif = ""
    if c.get("verifie_le"):
        vf = d3(c["verifie_le"])
        lien_v = (f' (<a href="{E(c["page_verifiee"])}" target="_blank" rel="noopener">{L("page vérifiée", "checked page", "الصفحة المراجعة")}</a>)'
                  if c.get("page_verifiee") else "")
        verif = "<br>" + L(f"Vérifié sur la page officielle le {vf[0]}", f"Checked on the official page on {vf[1]}", f"رُوجع على الصفحة الرسمية في {vf[2]}") + lien_v
    hero = f"""{fil(racine, f'<a href="{racine}domaine/{d0}/">{LL(nom_dom(d0))}</a>', f'<a href="{racine}specialite/{s0}/">{LL(nom_spec(s0))}</a>')}
    {dessin(d0, "hero-ic")}
    <h1><span data-l="fr">{E(sigle)}</span><span data-l="en">{E(sigle)}</span><span data-l="ar"><bdi>{E(sigle)}</bdi></span></h1>
    <p class="intro" lang="en" dir="ltr">{E(titre) if titre else ""}</p>"""
    contenu = f"""<section class="carte cf-fiche" id="{c['id']}" data-limites="{' '.join(x['date'] for x in limites_soumission(c))}" data-fin="{c['fin']}">
  <dl class="fiche-dl">
    <dt>{L("Type", "Type", "النوع")}</dt><dd>{LL(K.TYPES[c['type']])}{(' · ' + E(c['rang'])) if c['rang'] else ''}</dd>
    <dt>{L("Dates", "Dates", "التاريخ")}</dt><dd>{LL(p)}</dd>
    <dt>{L("Lieu", "Venue", "المكان")}</dt><dd>{lieu}</dd>
    <dt>{L("Domaine", "Field", "المجال")}</dt><dd>{doms}</dd>
    <dt>{L("Spécialités", "Specialties", "التخصصات")}</dt><dd>{specs}</dd>
    <dt>{L("Site officiel", "Official website", "الموقع الرسمي")}</dt><dd><a href="{E(c['lien'])}" target="_blank" rel="noopener">{E(re.sub(r'^https?://', '', c['lien'])[:70])}</a></dd>
    <dt>{L("Source", "Source", "المصدر")}</dt><dd>{srcs}{verif}</dd>
  </dl>
  <a class="gros-lien" href="{E(c['lien'])}" target="_blank" rel="noopener">{L("Ouvrir le site officiel de la conférence", "Open the official conference website", "افتح الموقع الرسمي للمؤتمر")}{ICONE_LIEN}</a>
</section>
<section class="carte">
  <h2>{L("Dates limites", "Deadlines", "آجال الإرسال")}</h2>
  {('<ul class="limites">' + "".join(lignes) + "</ul>") if lignes else "<p>" + L("Pas de date limite publiée dans nos sources : consultez le site officiel.", "No deadline published in our sources: check the official website.", "لا يوجد أجل منشور في مصادرنا: راجع الموقع الرسمي.") + "</p>"}
  <p class="avert">{L("Les dates peuvent changer (prolongation, report) : seul le site officiel de la conférence fait foi. Ce site n'est lié à aucun organisateur.",
                      "Dates may change (extensions, postponements): only the official conference website is authoritative. This site is not affiliated with any organiser.",
                      "قد تتغير التواريخ (تمديد، تأجيل): الموقع الرسمي للمؤتمر هو المرجع الوحيد. هذا الموقع لا علاقة له بأي جهة منظمة.")}</p>
</section>
{boutons_alertes(adr, [d0], racine)}
<a class="btn-pro" href="{racine}abonnement/">{L("Recevoir les rappels de cette spécialité sur Telegram (Alertes Pro)", "Get reminders for this specialty on Telegram (Pro Alerts)", "تلقَّ تذكيرات هذا التخصص على تيليغرام (تنبيهات Pro)")}</a>"""
    titre_page = f"{sigle}{(' — ' + titre) if titre else ''}"[:90] + f" · {p[1]} | Conference Radar"
    lieu_txt = ", ".join(x for x in (c["ville"], nom_pays(c["pays"])[1]) if x) or ("online" if c["mode"] == "en-ligne" else "")
    desc = (f"{sigle}: {p[1]}{', ' + lieu_txt if lieu_txt else ''}. "
            + (f"Submission deadline {d3(limites_soumission(c, jour)[0]['date'])[1]}. " if limites_soumission(c, jour) else "")
            + f"Dates, deadlines, official link. Dates limites et lien officiel ({nom_spec(s0)[0]}).")
    return f"conference/{c['id']}/", page(f"conference/{c['id']}/", racine, titre_page, desc, hero, contenu, v, etat, jsonld_event(c))


# ------------------------------------------------------------ flux Atom (alertes gratuites sans données personnelles)
def atom(titre, chemin, confs, maj):
    X = lambda t: html.escape(str(t or ""), quote=False)
    entrees = []
    for c in sorted(confs, key=lambda c: (c["ajoute_le"], c["debut"]), reverse=True)[:PAR_FLUX]:
        sigle, t = nom_conf(c)
        p = periode3(c["debut"], c["fin"])
        lieu = ", ".join(x for x in (c["ville"], nom_pays(c["pays"])[1]) if x) or ("Online" if c["mode"] == "en-ligne" else "")
        lims = limites_soumission(c)
        dl = ("Deadline: " + ", ".join(d3(x["date"])[1] for x in lims[:3])) if lims else "Deadline: see official website"
        resume = f"{p[1]} · {lieu} · {dl} · Official: {c['lien']}"
        entrees.append(f"""<entry>
<id>{URL_SITE}conference/{c['id']}/</id>
<title>{X(sigle + (' — ' + t if t else ''))}</title>
<link href="{URL_SITE}conference/{c['id']}/"/>
<updated>{c['ajoute_le']}T06:00:00Z</updated>
<summary>{X(resume)}</summary>
</entry>""")
    return f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<title>{X(titre)}</title>
<id>{URL_SITE}{chemin}</id>
<link rel="self" href="{URL_SITE}{chemin}"/>
<link href="{URL_SITE}"/>
<updated>{maj}T06:00:00Z</updated>
<author><name>Conference Radar / Radar des conférences</name></author>
<rights>© 2026 Conference Radar. Sources: open lists (MIT) and INSPIRE-HEP (CC0).</rights>
{chr(10).join(entrees)}
</feed>
"""


# ------------------------------------------------------------ Alertes Pro
def prix_abo():
    m, a = ABO["prix_mois"], ABO["prix_an"]
    return L(f"{m} DT / mois <small>ou {a} DT / an</small>", f"{m} TND / month <small>or {a} TND / year</small>",
             f"{ISO(m)} دينار / شهر <small>أو {ISO(a)} دينار / سنة</small>")


def lien_wa(texte, ident, libelle):
    url = f"https://wa.me/{ABO['whatsapp']}?text={urllib.parse.quote(texte)}"
    return f'<a class="btn-wa" id="{ident}" href="{E(url)}" data-texte="{E(texte)}" target="_blank" rel="noopener">{ICONE_WA}{libelle}</a>'


def lien_preuve(ident="abo-preuve"):
    return lien_wa(TEXTE_PREUVE, ident, L("Envoyer la preuve de paiement par WhatsApp", "Send the payment proof on WhatsApp", "أرسل إثبات الدفع عبر واتساب"))


APPLIS = {  # liens officiels (Google Play, App Store), demande d'Ahmed du 08/10/2026 ; Wafacash retiré (pas de compte)
    "D17": ("https://play.google.com/store/apps/details?id=tn.mobipost", "https://apps.apple.com/tn/app/digipostbank-d17/id1475640303"),
    "IZI": ("https://play.google.com/store/apps/details?id=tn.izi.consumer", "https://apps.apple.com/tn/app/izi/id1603653941"),
}


def lien_appli(m, t):
    return f'<a class="appli" href="{APPLIS[m][t == "iPhone"]}" target="_blank" rel="noopener noreferrer">{t}</a>'


def liste_paiements(ident="abo-etranger"):
    # paiement en 3 étapes numérotées + phrase de confiance (demande d'Ahmed, 08/10/2026 : simple, rassurant)
    applis = "".join(f'<a class="appli-btn" href="{APPLIS[m][0]}" target="_blank" rel="noopener noreferrer">{m}</a>' for m in ABO["paiements"])
    ios = " · ".join(f'<a class="appli" href="{APPLIS[m][1]}" target="_blank" rel="noopener noreferrer">{m}</a>' for m in ABO["paiements"])
    e1, e1b = L("Ouvrez l'application :", 'Open the app:', 'افتح التطبيق:'), L('Sur iPhone :', 'On iPhone:', 'على آيفون:')
    e2 = L('Choisissez « Transfert rapide » (dans IZI : « Transfert ») et tapez le numéro', 'Choose “Transfert rapide” (in IZI: “Transfert”) and enter the number', 'اختر « التحويل السريع » (في IZI: « تحويل ») وأدخل الرقم')
    e2b, e3 = L('Montant :', 'Amount:', 'المبلغ:'), L('Motif :', 'Reference:', 'سبب الدفع:')
    e3b = L('Puis envoyez la capture du paiement par WhatsApp (bouton vert).', 'Then send the payment screenshot on WhatsApp (green button).', 'ثم أرسل لقطة الدفع عبر واتساب (الزر الأخضر).')
    conf = L("Vous payez directement dans l'application officielle de La Poste Tunisienne (D17) ou de Zitouna Paiement (IZI) : nous ne voyons jamais vos codes.", 'You pay directly in the official app of La Poste Tunisienne (D17) or Zitouna Paiement (IZI): we never see your codes.', 'تدفع مباشرة في التطبيق الرسمي للبريد التونسي (D17) أو لزيتونة للدفع (IZI): لا نطّلع أبدًا على رموزك.')
    motif = L('votre nom', 'your name', 'اسمك')
    paie = (f'<div class="paie"><ol class="paie-etapes"><li>{e1} <span class="applis">{applis}</span><br><span class="petit">{e1b} {ios}</span></li>'
            f'<li>{e2} <strong><bdi dir="ltr">{ABO["numero"]}</bdi></strong>.<br>{e2b} <strong>{prix_abo()}</strong></li>'
            f'<li>{e3} <strong>{motif}</strong>. {e3b}</li></ol><p class="paie-confiance">{conf}</p></div>')
    etranger = (f'<p class="carte-etranger">{L("Paiement par carte pour l\'étranger : bientôt ; écrivez-nous sur WhatsApp.", "Card payment from abroad: coming soon; write to us on WhatsApp.", "الدفع بالبطاقة من الخارج: قريبًا؛ راسلنا عبر واتساب.")}</p>'
                + lien_wa(TEXTE_ETRANGER, ident, L("Je suis à l'étranger : écrire sur WhatsApp", "I am abroad: write on WhatsApp", "أنا خارج تونس: راسلنا عبر واتساب")))
    return paie + etranger


def texte_telegram(robot):
    if robot:
        lien = f'<a href="https://t.me/{E(robot)}" target="_blank" rel="noopener"><bdi dir="ltr">@{E(robot)}</bdi></a>'
        return L(f"Ouvrez notre robot {lien} dans Telegram et envoyez <b>/start</b> suivi de votre code (exemple : <code>/start AB12CD</code>). Le code vous est donné à l'activation.",
                 f"Open our bot {lien} in Telegram and send <b>/start</b> followed by your code (example: <code>/start AB12CD</code>). The code is given to you at activation.",
                 f"افتح برنامجنا {lien} في تيليغرام وأرسل <b><bdi dir=\"ltr\">/start</bdi></b> متبوعًا برمزك (مثال: <code dir=\"ltr\">/start AB12CD</code>). يُعطى لك الرمز عند التفعيل.")
    return L("Le lien Telegram vous est envoyé à l'activation, avec votre code personnel : il suffira d'ouvrir notre robot et d'envoyer <b>/start</b> suivi de votre code.",
             "The Telegram link is sent to you at activation, with your personal code: just open our bot and send <b>/start</b> followed by your code.",
             "يُرسل إليك رابط تيليغرام عند التفعيل مع رمزك الشخصي: يكفي أن تفتح برنامجنا وترسل <b><bdi dir=\"ltr\">/start</bdi></b> متبوعًا برمزك.")


def pages_abonnement(confs, adr, v, etat):
    essai, pm, pa, rj = ABO["essai_jours"], ABO["prix_mois"], ABO["prix_an"], ABO["rappel_jours"]
    cs = compter(confs, "specialites")
    groupes = []
    for d in K.DOMAINES:
        specs = [s for s in K.SPECIALITES if s[1] == d[0] and cs.get(s[0])]
        if not specs:
            continue
        groupes.append(f'<p class="groupe">{LL(nom_dom(d[0]))}</p>' + "".join(
            f'<label class="case"><input type="checkbox" name="specialites" value="{s[0]}"> <span>{LL(nom_spec(s[0]))}</span></label>' for s in specs))
    cases = "".join(groupes)
    accepte = L('J\'accepte les <a href="conditions/">conditions de l\'abonnement</a>.', 'I accept the <a href="conditions/">subscription terms</a>.',
                'أوافق على <a href="conditions/">شروط الاشتراك</a>.')
    hero = f"""{fil("../", L("Alertes Pro", "Pro Alerts", "تنبيهات Pro"))}
    <h1>{L("Alertes Pro sur Telegram", "Pro Alerts on Telegram", "تنبيهات Pro على تيليغرام")}</h1>
    <p class="intro">{L("Chaque matin, seulement les nouvelles conférences de VOS spécialités et les rappels de leurs dates limites, directement sur votre téléphone. La consultation du site et les flux RSS restent gratuits.",
                        "Every morning, only the new conferences in YOUR specialties and reminders of their deadlines, straight to your phone. Browsing the site and the RSS feeds stay free.",
                        "كل صباح، المؤتمرات الجديدة في تخصصاتك فقط وتذكير بآجال الإرسال، مباشرة على هاتفك. تصفح الموقع وخلاصات ⁨RSS⁩ يبقيان مجانيين.")}</p>"""
    contenu = f"""<section class="offre-pro" id="offre">
  <p class="ruban">{L(f"{essai} jours d'essai gratuit", f"{essai}-day free trial", f"تجربة مجانية {ISO(essai)} يومًا")}</p>
  <h2>{L("Abonnement Alertes Pro", "Pro Alerts subscription", "اشتراك تنبيهات Pro")}</h2>
  <p class="prix" id="abo-prix">{prix_abo()}</p>
  <ul class="avantages masque-si-paiement">
    <li>{L("Un message chaque matin sur <b>Telegram</b> : seulement les nouvelles conférences de vos spécialités", "One message every morning on <b>Telegram</b>: only new conferences in your specialties", "رسالة كل صباح على <b>تيليغرام</b>: المؤتمرات الجديدة في تخصصاتك فقط")}</li>
    <li>{L("Rappels des dates limites de soumission à J-7 et J-1", "Submission deadline reminders 7 days and 1 day before", "تذكير بآجال الإرسال قبل 7 أيام وقبل يوم")}</li>
    <li>{L("Plusieurs spécialités au choix, dans tous les domaines", "Several specialties of your choice, in every field", "عدة تخصصات حسب اختيارك في كل المجالات")}</li>
    <li>{L("Sources vérifiées, organisateurs douteux écartés, lien officiel de chaque conférence", "Checked sources, dubious organisers filtered out, official link for every conference", "مصادر موثوقة، استبعاد المنظمين المشبوهين، الرابط الرسمي لكل مؤتمر")}</li>
    <li>{L(f"Pas de renouvellement automatique : rappel {rj} jours avant la fin, puis l'alerte s'arrête simplement", f"No automatic renewal: reminder {rj} days before the end, then alerts simply stop", f"لا تجديد آلي: تذكير قبل النهاية بـ{ISO(rj)} أيام، ثم يتوقف التنبيه ببساطة")}</li>
    <li><strong>{L("Sans engagement au-delà d'un an", "No commitment beyond one year", "دون التزام بعد السنة")}</strong></li>
  </ul>
  <p class="petit masque-si-paiement">{L(f"{essai} jours d'essai gratuit, sans paiement. Ensuite, paiement par D17 ou IZI (bouton « Paiement »). Une facture vous est adressée.",
                      f"{essai}-day free trial, no payment. Then payment by D17 or IZI (“Payment” button). An invoice is sent to you.",
                      f"تجربة مجانية لمدة {ISO(essai)} يومًا دون دفع. بعدها، الدفع عبر ⁨D17⁩ أو ⁨IZI⁩ (زر «الدفع»). تُرسل إليك فاتورة.")}</p>
  <details class="paiement" id="paiement"><summary class="btn-clair">{L("Paiement", "Payment", "الدفع")}</summary>
    {liste_paiements()}
    {lien_preuve()}
    <p class="petit">{L("Payez après l'essai gratuit (ou tout de suite si vous préférez), avec pour motif votre nom, puis envoyez la preuve par WhatsApp. Une facture vous est adressée.",
                        "Pay after the free trial (or right away if you prefer), with your name as reference, then send the proof on WhatsApp. An invoice is sent to you.",
                        "ادفع بعد التجربة المجانية (أو فورًا إن أردت) مع ذكر اسمك كسبب للدفع، ثم أرسل الإثبات عبر واتساب. تُرسل إليك فاتورة.")}</p>
  </details>
  <a class="btn-pro" href="#inscription">{L(f"Je m'inscris : {essai} jours gratuits", f"Sign up: {essai} days free", f"أسجّل: {ISO(essai)} يومًا مجانًا")}</a>
</section>
<section class="carte">
  <h2>{L("Comment ça marche ?", "How does it work?", "كيف يعمل؟")}</h2>
  <ol class="etapes" data-l="fr">
    <li>Vous choisissez vos <b>spécialités</b> dans le formulaire ci-dessous.</li>
    <li>Nous activons votre abonnement (en général sous 24 heures) et vous envoyons votre <b>code personnel</b>.</li>
    <li>Dans Telegram, vous ouvrez notre robot et envoyez <b>/start</b> suivi de votre code.</li>
    <li>Chaque matin : les nouvelles conférences de vos spécialités, et un rappel 7 jours puis 1 jour avant chaque date limite.</li>
  </ol>
  <ol class="etapes" data-l="en">
    <li>Choose your <b>specialties</b> in the form below.</li>
    <li>We activate your subscription (usually within 24 hours) and send you your <b>personal code</b>.</li>
    <li>In Telegram, open our bot and send <b>/start</b> followed by your code.</li>
    <li>Every morning: new conferences in your specialties, plus a reminder 7 days and 1 day before each deadline.</li>
  </ol>
  <ol class="etapes" data-l="ar">
    <li>تختار <b>تخصصاتك</b> في الاستمارة أسفله.</li>
    <li>نفعّل اشتراكك (عادة في غضون ⁦24⁩ ساعة) ونرسل إليك <b>رمزك الشخصي</b>.</li>
    <li>في تيليغرام، تفتح برنامجنا وترسل <b><bdi dir="ltr">/start</bdi></b> متبوعًا برمزك.</li>
    <li>كل صباح: المؤتمرات الجديدة في تخصصاتك، وتذكير قبل كل أجل بـ⁦7⁩ أيام ثم بيوم.</li>
  </ol>
</section>
<section class="carte abo" id="inscription" aria-labelledby="abo-titre">
  <h2 id="abo-titre">{L("Inscription", "Sign-up", "التسجيل")}</h2>
  <form id="abo-form" action="{ABO['formspree']}" method="POST" novalidate>
    <label class="abo-etiquette" for="abo-nom">{L("Votre nom", "Your name", "اسمك")}</label>
    <input id="abo-nom" name="nom" required maxlength="100" autocomplete="name">
    <label class="abo-etiquette" for="abo-etab">{L("Université ou institution", "University or institution", "الجامعة أو المؤسسة")}</label>
    <input id="abo-etab" name="etablissement" required maxlength="140" autocomplete="organization">
    <label class="abo-etiquette" for="abo-pays">{L("Pays", "Country", "البلد")}</label>
    <input id="abo-pays" name="pays" required maxlength="60" autocomplete="country-name">
    <label class="abo-etiquette" for="abo-tel">{L("Téléphone (WhatsApp ou Telegram, avec l'indicatif)", "Phone (WhatsApp or Telegram, with country code)", "الهاتف (واتساب أو تيليغرام، مع رمز البلد)")}</label>
    <input id="abo-tel" name="telephone" required inputmode="tel" maxlength="20" autocomplete="tel" placeholder="+216 24 321 390">
    <label class="abo-etiquette" for="abo-email">{L("E-mail (pour la confirmation et la facture)", "E-mail (for confirmation and invoice)", "البريد الإلكتروني (للتأكيد والفاتورة)")}</label>
    <input id="abo-email" type="email" name="email" required maxlength="200" autocomplete="email">
    <fieldset class="abo-choix" id="abo-specs">
      <legend>{L("Vos spécialités (une ou plusieurs)", "Your specialties (one or more)", "تخصصاتك (واحد أو أكثر)")}</legend>
      <div class="cases">{cases}</div>
    </fieldset>
    <fieldset class="abo-choix" id="abo-formule">
      <legend>{L("Votre formule", "Your plan", "صيغتك")}</legend>
      <label class="case"><input type="radio" name="formule" value="essai {essai} jours" checked> <span>{L(f"<b>{essai} jours d'essai gratuit</b>, je paierai ensuite si je suis satisfait", f"<b>{essai}-day free trial</b>, I will pay afterwards if satisfied", f"<b>تجربة مجانية {ISO(essai)} يومًا</b>، وأدفع بعدها إن كنت راضيًا")}</span></label>
      <label class="case"><input type="radio" name="formule" value="je paie directement"> <span>{L(f"Je paie directement ({pm} DT / mois ou {pa} DT / an)", f"I pay right away ({pm} TND / month or {pa} TND / year)", f"أدفع مباشرة ({ISO(pm)} دينار / شهر أو {ISO(pa)} دينار / سنة)")}</span></label>
    </fieldset>
    <label class="case"><input type="checkbox" name="conditions" value="oui" required id="abo-conditions"> <span>{accepte}</span></label>
    <input type="hidden" name="site" value="Radar des conférences">
    <input type="hidden" name="page" value="">
    <input type="hidden" name="_subject" value="Abonnement Alertes Pro — Radar des conférences">
    <input type="text" name="_gotcha" class="abo-piege" tabindex="-1" autocomplete="off" aria-hidden="true">
    <button type="submit" class="btn-pro">{L("Envoyer mon inscription", "Send my sign-up", "أرسل تسجيلي")}</button>
    <p id="abo-status" role="status" aria-live="polite"></p>
    <p class="petit">{L("Vos coordonnées servent seulement à l'abonnement et à la facture : elles ne sont jamais publiées ni vendues (envoi par le service Formspree). Rien n'est envoyé sans clic sur « Envoyer ».",
                        "Your details are only used for the subscription and the invoice: they are never published or sold (sent through the Formspree service). Nothing is sent until you press “Send”.",
                        "تُستعمل بياناتك للاشتراك والفاتورة فقط: لا تُنشر ولا تُباع أبدًا (إرسال عبر خدمة ⁨Formspree⁩). لا يُرسل أي شيء دون الضغط على «أرسل».")}</p>
  </form>
  <div class="apres-abo" id="apres-abo" hidden>
    <h3>{L("Merci, votre inscription est bien reçue", "Thank you, your sign-up has been received", "شكرًا، وصلنا تسجيلك")}</h3>
    <p>{L(f"Nous activons votre abonnement, en général sous 24 heures. Vos {essai} jours d'essai gratuit commencent à l'activation.", f"We activate your subscription, usually within 24 hours. Your {essai} free days start at activation.", f"نفعّل اشتراكك عادة في غضون ⁦24⁩ ساعة. تبدأ أيامك المجانية الـ{ISO(essai)} عند التفعيل.")}</p>
    <h3>{L("Recevoir les alertes sur Telegram", "Receive alerts on Telegram", "تلقي التنبيهات على تيليغرام")}</h3>
    <p id="abo-telegram">{texte_telegram(adr["robot"])}</p>
    <p class="petit">{L("Installez Telegram (gratuit) sur votre téléphone si ce n'est pas déjà fait.", "Install Telegram (free) on your phone if not already done.", "ثبّت تيليغرام (مجاني) على هاتفك إن لم يكن مثبتًا.")}</p>
    <h3>{L("Paiement", "Payment", "الدفع")}</h3>
    <p>{L("Après l'essai (ou tout de suite si vous avez choisi de payer directement), payez par D17 ou IZI, avec pour motif votre nom :", "After the trial (or right away if you chose to pay now), pay by D17 or IZI, with your name as reference:", "بعد التجربة (أو فورًا إن اخترت الدفع مباشرة)، ادفع عبر ⁨D17⁩ أو ⁨IZI⁩ مع ذكر اسمك:")}</p>
    {liste_paiements("abo-etranger-apres")}
    {lien_preuve("abo-preuve-apres")}
    <p class="petit">{L(f"Une facture vous est adressée. Pas de renouvellement automatique : nous vous prévenons {rj} jours avant la fin.", f"An invoice is sent to you. No automatic renewal: we warn you {rj} days before the end.", f"تُرسل إليك فاتورة. لا تجديد آلي: نعلمك قبل النهاية بـ{ISO(rj)} أيام.")}</p>
  </div>
</section>
<p class="avert">{L("La consultation du site reste <b>gratuite, sans inscription</b>, et les flux RSS par domaine restent gratuits. L'abonnement ajoute seulement l'alerte personnalisée sur Telegram.",
                    "Browsing the site stays <b>free, without sign-up</b>, and the RSS feeds by field stay free. The subscription only adds the personalised Telegram alert.",
                    "تصفح الموقع يبقى <b>مجانيًا ودون تسجيل</b>، وخلاصات ⁨RSS⁩ حسب المجال تبقى مجانية. الاشتراك يضيف فقط التنبيه الشخصي على تيليغرام.")}</p>"""
    titre = f"Pro Alerts: conferences of your specialty on Telegram — {essai} days free · Alertes Pro | Conference Radar"
    desc = (f"Receive every morning on Telegram the new academic conferences of your specialties and deadline reminders. "
            f"{pm} TND / month or {pa} TND / year, {essai}-day free trial, no automatic renewal. Alertes de conférences sur Telegram.")
    res = [("abonnement/", page("abonnement/", "../", titre, desc, hero, contenu, v, etat, scripts=("abonnement.js",)))]

    hero = f"""    <p class="fil"><a href="../../">{L("Accueil", "Home", "الرئيسية")}</a> › <a href="../">{L("Alertes Pro", "Pro Alerts", "تنبيهات Pro")}</a> › {L("Conditions", "Terms", "الشروط")}</p>
    <h1>{L("Conditions de l'abonnement", "Subscription terms", "شروط الاشتراك")}</h1>
    <p class="intro">{L("Alertes Pro : prix, essai gratuit, paiement, données personnelles, arrêt.", "Pro Alerts: price, free trial, payment, personal data, cancellation.", "تنبيهات Pro: السعر، التجربة المجانية، الدفع، المعطيات الشخصية، الإيقاف.")}</p>"""
    num = ABO["numero"]
    sections = [
        (("1. Le service et le vendeur", "1. The service and the seller", "1. الخدمة والبائع"),
         ("Alertes Pro est vendu par l'éditeur du site « Radar des conférences ». Le service envoie chaque matin sur Telegram les nouvelles conférences correspondant aux spécialités choisies par l'abonné, et des rappels avant leurs dates limites de soumission. La consultation du site et les flux RSS restent gratuits et sans inscription.",
          "Pro Alerts is sold by the publisher of the “Conference Radar” website. The service sends every morning on Telegram the new conferences matching the specialties chosen by the subscriber, and reminders before their submission deadlines. Browsing the site and the RSS feeds remain free and without sign-up.",
          "يبيع ناشرُ موقع «رادار المؤتمرات» خدمةَ تنبيهات Pro. ترسل الخدمة كل صباح على تيليغرام المؤتمرات الجديدة المطابقة للتخصصات التي اختارها المشترك، وتذكيرات قبل آجال الإرسال. تصفح الموقع وخلاصات ⁨RSS⁩ يبقيان مجانيين ودون تسجيل.")),
        (("2. Prix", "2. Price", "2. السعر"),
         (f"{pm} DT par mois ou {pa} DT par an, en dinars tunisiens. Le prix affiché au moment de l'inscription s'applique à toute la période payée.",
          f"{pm} TND per month or {pa} TND per year (Tunisian dinars). The price shown at sign-up applies to the whole paid period.",
          f"{ISO(pm)} دينار في الشهر أو {ISO(pa)} دينار في السنة. السعر المعروض عند التسجيل يُطبَّق على كامل المدة المدفوعة.")),
        (("3. Essai gratuit", "3. Free trial", "3. التجربة المجانية"),
         (f"Les {essai} premiers jours sont gratuits, sans paiement et sans engagement. Sans paiement à la fin de l'essai, l'alerte s'arrête simplement.",
          f"The first {essai} days are free, without payment or commitment. Without payment at the end of the trial, alerts simply stop.",
          f"الأيام الـ{ISO(essai)} الأولى مجانية، دون دفع ودون التزام. إذا لم يتم الدفع في نهاية التجربة، يتوقف التنبيه ببساطة.")),
        (("4. Paiement et facture", "4. Payment and invoice", "4. الدفع والفاتورة"),
         (f"Paiement par D17 ou IZI au {num}, avec pour motif le nom de l'abonné, puis preuve envoyée par WhatsApp au même numéro. Paiement par carte depuis l'étranger : bientôt (nous écrire sur WhatsApp). La période payée commence après l'essai gratuit ou après la période déjà payée. Une facture est adressée à l'abonné.",
          f"Payment by D17 or IZI to {num}, with the subscriber's name as reference, then proof sent on WhatsApp to the same number. Card payment from abroad: coming soon (write to us on WhatsApp). The paid period starts after the free trial or after the period already paid. An invoice is sent to the subscriber.",
          f"الدفع عبر ⁨D17⁩ أو ⁨IZI⁩ على الرقم {ISO(num)} مع ذكر اسم المشترك، ثم إرسال الإثبات عبر واتساب على نفس الرقم. الدفع بالبطاقة من الخارج: قريبًا (راسلنا عبر واتساب). تبدأ المدة المدفوعة بعد التجربة المجانية أو بعد المدة المدفوعة سابقًا. تُرسل فاتورة إلى المشترك.")),
        (("5. Pas de renouvellement automatique", "5. No automatic renewal", "5. لا تجديد آلي"),
         (f"Sans engagement au-delà d'un an. Il n'y a aucun renouvellement automatique : un rappel est envoyé {rj} jours avant la fin ; sans nouveau paiement, l'alerte s'arrête simplement à la date de fin.",
          f"No commitment beyond one year. There is no automatic renewal: a reminder is sent {rj} days before the end; without a new payment, alerts simply stop on the end date.",
          f"دون التزام بعد السنة. لا يوجد أي تجديد آلي: يُرسل تذكير قبل النهاية بـ{ISO(rj)} أيام، ودون دفع جديد يتوقف التنبيه ببساطة في تاريخ النهاية.")),
        (("6. Arrêt (résiliation) et remboursement", "6. Cancellation and refunds", "6. الإيقاف (الفسخ) والاسترجاع"),
         ("L'abonné peut arrêter les alertes à tout moment, en envoyant /stop au robot Telegram ou en nous écrivant sur WhatsApp. Pendant l'essai gratuit, rien n'est dû. Aucune période déjà payée n'est remboursée ; elle n'est simplement pas renouvelée.",
          "The subscriber can stop the alerts at any time by sending /stop to the Telegram bot or by writing to us on WhatsApp. Nothing is due during the free trial. No period already paid is refunded; it is simply not renewed.",
          "يمكن للمشترك إيقاف التنبيهات في أي وقت بإرسال ⁨/stop⁩ إلى برنامج تيليغرام أو بمراسلتنا عبر واتساب. خلال التجربة المجانية لا يُستحق أي مبلغ. لا تُسترجع أي مدة مدفوعة؛ فقط لا تُجدَّد.")),
        (("7. Limites", "7. Limits", "7. الحدود"),
         ("Les conférences viennent de listes ouvertes et de bases publiques (voir « À propos »). Le classement par spécialité est automatique et peut se tromper ; une conférence peut manquer si une source est en panne. Seul le site officiel de chaque conférence fait foi : vérifiez-le toujours avant de soumettre.",
          "Conferences come from open lists and public databases (see “About”). Classification by specialty is automatic and may be wrong; a conference may be missing if a source is down. Only each conference's official website is authoritative: always check it before submitting.",
          "المؤتمرات مصدرها قوائم مفتوحة وقواعد عمومية (انظر «من نحن»). الترتيب حسب التخصص آلي وقد يخطئ، وقد يغيب مؤتمر إذا تعطل مصدر. الموقع الرسمي لكل مؤتمر هو المرجع الوحيد: تثبّت منه دائمًا قبل الإرسال.")),
        (("8. Données personnelles", "8. Personal data", "8. المعطيات الشخصية"),
         ("Nous gardons seulement : nom, institution, pays, téléphone, e-mail, spécialités choisies, dates de l'abonnement et identifiant Telegram. Elles servent uniquement à envoyer les alertes et la facture, sont conservées dans un espace privé, ne sont jamais publiées ni vendues, et sont supprimées sur simple demande (WhatsApp). Le formulaire passe par le service Formspree et les alertes par Telegram. Traitement déclaré auprès de l'INPDP (Tunisie).",
          "We only keep: name, institution, country, phone, e-mail, chosen specialties, subscription dates and Telegram identifier. They are only used to send alerts and the invoice, are kept in a private space, are never published or sold, and are deleted on simple request (WhatsApp). The form goes through the Formspree service and the alerts through Telegram. Processing declared to the INPDP (Tunisia).",
          "نحتفظ فقط بـ: الاسم، المؤسسة، البلد، الهاتف، البريد الإلكتروني، التخصصات المختارة، تواريخ الاشتراك ومعرّف تيليغرام. تُستعمل فقط لإرسال التنبيهات والفاتورة، وتُحفظ في فضاء خاص، ولا تُنشر ولا تُباع أبدًا، وتُحذف بمجرد الطلب (واتساب). تمر الاستمارة عبر خدمة ⁨Formspree⁩ والتنبيهات عبر تيليغرام. معالجة مصرّح بها لدى الهيئة الوطنية لحماية المعطيات الشخصية.")),
        (("9. Contact", "9. Contact", "9. الاتصال"), (f"WhatsApp : {num}.", f"WhatsApp: {num}.", f"واتساب: {ISO(num)}.")),
    ]
    corps = "\n".join(f"  <h2>{LL(t)}</h2>\n  <p>{LL(p)}</p>" for t, p in sections)
    contenu = f"""<section class="carte conditions">
{corps}
  <p class="avert">{L("Ce site n'est pas officiel et n'est lié à aucun organisateur de conférence.", "This site is not official and is not affiliated with any conference organiser.", "هذا الموقع ليس رسميًا ولا علاقة له بأي جهة منظمة للمؤتمرات.")}</p>
  <p><a class="btn-pro" href="../#inscription">{L("Retour à l'inscription", "Back to sign-up", "العودة إلى التسجيل")}</a></p>
</section>"""
    titre = "Pro Alerts terms (Telegram reminders for conferences) · Conditions de l'abonnement | Conference Radar"
    desc = (f"Pro Alerts terms: {pm} TND / month or {pa} TND / year, {essai}-day free trial, no automatic renewal, payment D17 or IZI, "
            "personal data and cancellation. Conditions de l'abonnement Alertes Pro.")
    res.append(("abonnement/conditions/", page("abonnement/conditions/", "../../", titre, desc, hero, contenu, v, etat)))
    return res


# ------------------------------------------------------------ construction
def version_assets(sortie):
    h = hashlib.sha1()
    for f in ("style.css", "textes.js", "page.js", "app.js", "avis.js", "abonnement.js"):
        p = os.path.join(sortie, "assets", f)
        if os.path.exists(p):
            with open(p, "rb") as fh:
                h.update(fh.read().replace(b"\r\n", b"\n"))
    return h.hexdigest()[:8]


def ecrire(sortie, chemin, contenu):
    p = os.path.join(sortie, chemin)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(contenu)
    os.replace(tmp, p)


PREMIERE = [""]     # date de la toute première collecte : rien n'est « Nouveau » ce jour-là


DOSSIERS_GENERES = ("domaine", "specialite", "continent", "pays", "mois", "conference", "flux")


def construire(donnees, sortie, jour):
    sauvegarde = donnees.replace(".json", ".sauvegarde.json")
    brut, confs = charger(donnees)
    brut_s, confs_s = charger(sauvegarde)
    panne, raison, repli = False, "", False
    if not confs:
        if confs_s:
            print(f"  ! échec : {os.path.basename(donnees)} illisible ou vide -> dernière sauvegarde utilisée")
            brut, confs, panne, raison, repli = brut_s, confs_s, True, "données illisibles", True
        elif os.path.exists(os.path.join(sortie, "index.html")):
            print("  ! échec : données illisibles et aucune sauvegarde -> le site existant est gardé tel quel")
            return 1
        else:
            print("  ! échec : aucune donnée -> site construit vide, avec avertissement")
            brut, panne, raison, repli = {}, True, "aucune donnée", True
    elif confs_s and len(a_venir(confs, jour)) < SEUIL_CHUTE * len(a_venir(confs_s, jour)):
        print(f"  ! échec : seulement {len(confs)} conférences contre {len(confs_s)} avant -> données suspectes, sauvegarde utilisée")
        brut, confs, panne, raison, repli = brut_s, confs_s, True, "données suspectes", True
    else:
        tmp = sauvegarde + ".tmp"
        shutil.copyfile(donnees, tmp)
        os.replace(tmp, sauvegarde)

    PREMIERE[0] = str((brut or {}).get("premiere_collecte") or "")
    statut = (brut or {}).get("statut_source") or {}
    passage = (brut or {}).get("dernier_passage") or {}
    source_en_panne = statut.get("etat") == "panne" or passage.get("reussi") is False
    if source_en_panne:
        print(f"  ! échec : {statut.get('raison') or 'lecture ratée'} (depuis {statut.get('depuis') or passage.get('date')})")
    maj = str((brut or {}).get("derniere_lecture_reussie") or (brut or {}).get("mis_a_jour") or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}", maj):
        maj = ""
    age = (dt.date.fromisoformat(jour) - dt.date.fromisoformat(maj[:10])).days if maj else None
    panne = panne or age is None or age >= AGE_AVERTISSEMENT
    if panne and not raison:
        raison = "lecture ancienne"
    maj_texte = (f"{maj[8:10]}/{maj[5:7]}/{maj[0:4]}" + (" " + maj[11:16] if len(maj) >= 16 else "")) if maj else ""
    message = (f"⚠️ The sources could not be read since {maj_texte[:10]}: the list may be incomplete. Always check the official website."
               if maj else "⚠️ Data unavailable for now.") if panne else ""
    ecrire(sortie, "donnees/etat-source.json", json.dumps({
        "source_en_panne": bool(source_en_panne or repli),
        "depuis": statut.get("depuis") or passage.get("date") or "",
        "raison": statut.get("raison") or raison or "",
        "derniere_lecture_reussie": maj, "jours_sans_lecture": age,
        "bandeau_visible": panne, "construit_le": jour}, ensure_ascii=False, indent=1) + "\n")
    etat = {"maj": maj, "maj_texte": maj_texte, "panne": panne, "message": message}

    vis = a_venir(confs, jour)
    v = "__V__"               # remplacé à l'écriture par l'empreinte des fichiers (textes.js est fabriqué pendant la construction)
    adr = adresses()
    pages = []
    for d in DOSSIERS_GENERES:       # les pages générées sont refaites à chaque passage (fini les pages périmées)
        shutil.rmtree(os.path.join(sortie, d), ignore_errors=True)

    cd = compter(vis, "domaines")
    domaines_presents = [d[0] for d in K.DOMAINES if cd.get(d[0])]
    n_lim30 = sum(1 for c in vis if any(jour <= x["date"] <= (dt.date.fromisoformat(jour) + dt.timedelta(days=30)).isoformat()
                                        for x in limites_soumission(c)))

    # ---- accueil
    hero = f"""{credit_photos()}
    <h1>{L("Conférences scientifiques à venir : dates limites et alertes", "Upcoming academic conferences: deadlines &amp; alerts", "المؤتمرات العلمية القادمة: آجال الإرسال والتنبيهات")}</h1>
    <p class="intro">{L("Pour les enseignants-chercheurs du monde entier : les conférences des 18 prochains mois, par domaine et spécialité — dont la comptabilité, la finance et la finance islamique — avec la date limite de soumission et le lien officiel. Sources vérifiées, organisateurs douteux écartés. Gratuit, sans inscription.",
                        "For professors and researchers worldwide: conferences of the next 18 months, by field and specialty — including accounting, finance and Islamic finance — with the submission deadline and the official link. Checked sources, dubious organisers filtered out. Free, no sign-up.",
                        "للأساتذة والباحثين في كل العالم: مؤتمرات الأشهر الـ⁦18⁩ القادمة حسب المجال والتخصص، ومنها المحاسبة والمالية والتمويل الإسلامي، مع آخر أجل للإرسال والرابط الرسمي. مصادر موثوقة واستبعاد المنظمين المشبوهين. مجاني ودون تسجيل.")}</p>
{bouton_pro_accueil()}"""
    faq = [
        ("How do I find upcoming conferences in my field?",
         "Choose your field and specialty: the site lists academic conferences of the next 18 months with dates, venue, submission deadline and the official link. The list is updated every day from open sources."),
        ("Is it free?", "Yes. Browsing the site and the RSS alerts by field are free, without sign-up. Only the personalised Telegram alerts (Pro Alerts) are paid: "
         f"{ABO['prix_mois']} TND per month or {ABO['prix_an']} TND per year, with a {ABO['essai_jours']}-day free trial."),
        ("How are predatory conferences avoided?",
         "Conferences come only from curated open lists (MIT licence) and the INSPIRE-HEP database (CC0). Organisers known for predatory conferences are filtered out, and every entry links to the official website."),
        ("Les dates sont-elles fiables ?",
         "Les dates viennent de listes ouvertes tenues par des chercheurs et de bases publiques ; elles peuvent changer (prolongation). Seul le site officiel de la conférence fait foi."),
    ]
    jsonld = ('<script type="application/ld+json">\n' + json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r in faq]},
        ensure_ascii=False) + "\n</script>\n")
    avant = f"""<section class="carte resume" aria-label="Summary">
  <div class="r-avenir" id="r-avenir"><b>{len(vis)}</b><span>{L("conférences à venir", "upcoming conferences", "مؤتمر قادم")}</span></div>
  <div class="r-limites" id="r-limites"><b>{n_lim30}</b><span>{L("dates limites sous 30 jours", "deadlines within 30 days", "آجال خلال 30 يومًا")}</span></div>
  <div class="r-domaines" id="r-domaines"><b>{len(domaines_presents)}</b><span>{L("grands domaines", "fields", "مجالات")}</span></div>
</section>
<section class="carte bientot" id="bientot" hidden aria-labelledby="bientot-titre">
  <h2 id="bientot-titre">{L("⏰ Dates limites cette semaine", "⏰ Deadlines this week", "⏰ آجال هذا الأسبوع")}</h2>
  <ol class="bientot-liste" id="bientot-liste"></ol>
</section>
<h2 class="titre-section" id="domaines">{L("Par grand domaine", "By field", "حسب المجال")}</h2>
{tuiles_domaines(vis, "")}
{boutons_alertes(adr, domaines_presents, "")}
"""
    apres = f"""<h2 class="titre-section" id="specialites">{L("Par spécialité", "By specialty", "حسب التخصص")}</h2>
{grille(paires_specs(vis), "", "specialite", "grille-specs")}
<h2 class="titre-section" id="lieux">{L("Par continent et par pays", "By continent and country", "حسب القارة والبلد")}</h2>
{grille(paires_conts(vis), "", "continent", "grille-continents")}
<div style="height:8px"></div>
{grille(paires_pays(vis), "", "pays", "grille-pays")}
<h2 class="titre-section" id="mois">{L("Par mois", "By month", "حسب الشهر")}</h2>
{grille(paires_mois(vis), "", "mois", "grille-mois", classe="mois")}
<section class="carte" style="margin-top:18px">
  <h2>{L("Comment ça marche ?", "How does it work?", "كيف يعمل الموقع؟")}</h2>
  <ol class="etapes" data-l="fr">
    <li>Chaque jour, un robot lit des <b>listes ouvertes</b> de conférences tenues par des chercheurs (licence MIT) et la base publique <b>INSPIRE-HEP</b> (CC0).</li>
    <li>Les dates sont mises au même format, les doublons fusionnés, chaque conférence rangée par <b>domaine</b>, <b>spécialité</b> et <b>pays</b>. Les organisateurs connus pour leurs conférences « prédatrices » sont écartés.</li>
    <li>Vous ouvrez le <b>site officiel</b> de la conférence pour soumettre. Alertes gratuites : flux RSS par domaine ; alertes personnalisées : <a href="abonnement/">Alertes Pro</a>.</li>
  </ol>
  <ol class="etapes" data-l="en">
    <li>Every day, a robot reads <b>open conference lists</b> maintained by researchers (MIT licence) and the public <b>INSPIRE-HEP</b> database (CC0).</li>
    <li>Dates are normalised, duplicates merged, each conference sorted by <b>field</b>, <b>specialty</b> and <b>country</b>. Organisers known for predatory conferences are filtered out.</li>
    <li>You open the conference's <b>official website</b> to submit. Free alerts: RSS feeds by field; personalised alerts: <a href="abonnement/">Pro Alerts</a>.</li>
  </ol>
  <ol class="etapes" data-l="ar">
    <li>كل يوم، يقرأ برنامج آلي <b>قوائم مفتوحة</b> للمؤتمرات يحررها باحثون (رخصة ⁨MIT⁩) وقاعدة <b>⁨INSPIRE-HEP⁩</b> العمومية (⁨CC0⁩).</li>
    <li>تُوحَّد صيغة التواريخ وتُدمج المكررات ويُرتَّب كل مؤتمر حسب <b>المجال</b> و<b>التخصص</b> و<b>البلد</b>، مع استبعاد المنظمين المعروفين بالمؤتمرات «المفترسة».</li>
    <li>تفتح <b>الموقع الرسمي</b> للمؤتمر للإرسال. تنبيهات مجانية: خلاصات ⁨RSS⁩ حسب المجال؛ تنبيهات شخصية: <a href="abonnement/">تنبيهات Pro</a>.</li>
  </ol>
  <p class="avert">{L("Ce site n'est pas officiel et n'est lié à aucun organisateur. Vérifiez toujours le site officiel de la conférence : seul lui fait foi.", "This site is not official and is not affiliated with any organiser. Always check the conference's official website: it alone is authoritative.", "هذا الموقع ليس رسميًا ولا علاقة له بأي جهة منظمة. تثبّت دائمًا من الموقع الرسمي للمؤتمر: هو وحده المرجع.")} <a href="a-propos/">{L("Méthode et sources", "Method and sources", "المنهجية والمصادر")}</a></p>
</section>
{AVIS}"""
    titre = f"Academic conferences 2026–2027: {len(vis)} upcoming, deadlines & free alerts · Conférences scientifiques | Conference Radar"
    desc = ("Upcoming academic conferences worldwide by field and specialty, with submission deadlines and official links. Free, no sign-up. "
            "Conférences scientifiques à venir, dates limites, alertes gratuites. المؤتمرات العلمية القادمة.")
    pages.append(page_liste("", "", titre, desc, hero, vis, jour, v, etat, avant=avant, apres=apres, jsonld=jsonld, classe_hero=" hero-photo"))

    # ---- grands domaines
    for d in domaines_presents:
        sel = [c for c in vis if d in c["domaines"]]
        n3 = nom_dom(d)
        hero = f"""{fil("../../", L("Domaines", "Fields", "المجالات"))}
    {dessin(d, "hero-ic")}
    <h1>{LL(n3)}</h1>
    <p class="intro">{L(f"{len(sel)} conférences à venir, avec leur date limite de soumission et leur lien officiel.", f"{len(sel)} upcoming conferences, with their submission deadline and official link.", f"{ISO(len(sel))} مؤتمر قادم مع آخر أجل للإرسال والرابط الرسمي.")}</p>"""
        avant = (f'<section class="carte"><h2>{L("Spécialités", "Specialties", "التخصصات")}</h2>{grille(paires_specs(sel, d), "../../", "specialite", "grille-specs")}</section>'
                 f'{boutons_alertes(adr, [d], "../../")}')
        apres = f'<h2 class="titre-section">{L("Autres domaines", "Other fields", "مجالات أخرى")}</h2>{tuiles_domaines(vis, "../../", d)}'
        titre = f"{n3[1]} conferences 2026–2027: {len(sel)} upcoming, deadlines · Conférences {n3[0]} | Conference Radar"
        desc = f"Upcoming {n3[1].lower()} conferences with submission deadlines and official links. Free. Conférences à venir : {n3[0].lower()}. {n3[2]}."
        pages.append(page_liste(f"domaine/{d}/", "../../", titre, desc, hero, sel, jour, v, etat, sans=("domaine",), avant=avant, apres=apres))

    # ---- spécialités
    for s in K.SPECIALITES:
        sel = [c for c in vis if s[0] in c["specialites"]]
        if not sel:
            continue
        n3 = nom_spec(s[0])
        hero = f"""{fil("../../", f'<a href="../../domaine/{s[1]}/">{LL(nom_dom(s[1]))}</a>')}
    {dessin(s[1], "hero-ic")}
    <h1>{LL(n3)}</h1>
    <p class="intro">{L(f"{len(sel)} conférences à venir dans cette spécialité, avec leur date limite de soumission.", f"{len(sel)} upcoming conferences in this specialty, with their submission deadline.", f"{ISO(len(sel))} مؤتمر قادم في هذا التخصص مع آخر أجل للإرسال.")}</p>"""
        apres = f'<h2 class="titre-section">{L("Autres spécialités du domaine", "Other specialties in this field", "تخصصات أخرى في المجال")}</h2>{grille(paires_specs(vis, s[1]), "../../", "specialite", "grille-specs", s[0])}'
        avant = f'<p class="alertes-btn"><a class="btn-alerte btn-rss" href="../../flux/specialite-{s[0]}.xml">{ICONE_RSS}{L("Flux RSS gratuit de cette spécialité", "Free RSS feed for this specialty", "خلاصة ⁨RSS⁩ مجانية لهذا التخصص")}</a></p>'
        titre = f"{n3[1]} conferences 2026–2027: {len(sel)} upcoming, CFP deadlines · {n3[0]} | Conference Radar"
        desc = f"Upcoming {n3[1]} conferences and calls for papers with deadlines and official links. Conférences {n3[0].lower()} à venir. {n3[2]}."
        pages.append(page_liste(f"specialite/{s[0]}/", "../../", titre, desc, hero, sel, jour, v, etat, sans=("domaine", "specialite"), avant=avant, apres=apres))

    # ---- continents et pays
    for x in K.CONTINENTS:
        sel = [c for c in vis if c["continent"] == x[0]]
        if not sel:
            continue
        n3 = nom_cont(x[0])
        hero = f"""{fil("../../", L("Lieux", "Places", "الأماكن"))}
    <h1>{L(f"Conférences : {n3[0]}", f"Conferences: {n3[1]}", f"مؤتمرات: {n3[2]}")}</h1>
    <p class="intro">{L(f"{len(sel)} conférences à venir.", f"{len(sel)} upcoming conferences.", f"{ISO(len(sel))} مؤتمر قادم.")}</p>"""
        pays_ici = [p for p in paires_pays(vis) if K.PAYS[p[0].upper()][3] == x[0]]
        apres = (f'<h2 class="titre-section">{L("Pays", "Countries", "البلدان")}</h2>{grille(pays_ici, "../../", "pays", "grille-pays")}' if pays_ici else "") + \
                f'<h2 class="titre-section">{L("Autres continents", "Other continents", "قارات أخرى")}</h2>{grille(paires_conts(vis), "../../", "continent", "grille-continents", x[0])}'
        titre = f"Academic conferences in {n3[1]} 2026–2027: {len(sel)} upcoming · Conférences {n3[0]} | Conference Radar"
        desc = f"Upcoming academic conferences in {n3[1]} with submission deadlines and official links. Conférences scientifiques : {n3[0]}. {n3[2]}."
        pages.append(page_liste(f"continent/{x[0]}/", "../../", titre, desc, hero, sel, jour, v, etat, sans=("continent",), apres=apres))
    for code_bas, n3, n in paires_pays(vis):
        code = code_bas.upper()
        sel = [c for c in vis if c["pays"] == code and c["mode"] != "en-ligne"]
        cont = K.PAYS[code][3]
        hero = f"""{fil("../../", f'<a href="../../continent/{cont}/">{LL(nom_cont(cont))}</a>')}
    <h1>{L(f"Conférences : {n3[0]}", f"Conferences in {n3[1]}", f"مؤتمرات في {n3[2]}")}</h1>
    <p class="intro">{L(f"{len(sel)} conférences à venir.", f"{len(sel)} upcoming conferences.", f"{ISO(len(sel))} مؤتمر قادم.")}</p>"""
        apres = f'<h2 class="titre-section">{L("Autres pays", "Other countries", "بلدان أخرى")}</h2>{grille(paires_pays(vis), "../../", "pays", "grille-pays", code_bas)}'
        titre = f"Academic conferences in {n3[1]} 2026–2027: {len(sel)} upcoming · Conférences {n3[0]} | Conference Radar"
        desc = f"Upcoming academic conferences in {n3[1]} with submission deadlines and official links. Conférences scientifiques : {n3[0]}. {n3[2]}."
        pages.append(page_liste(f"pays/{code_bas}/", "../../", titre, desc, hero, sel, jour, v, etat, sans=("continent",), apres=apres))

    # ---- mois
    for cle, n3, n in paires_mois(vis):
        sel = [c for c in vis if c["debut"][:7] == cle]
        hero = f"""{fil("../../", L("Mois", "Months", "الأشهر"))}
    <h1>{L(f"Conférences de {n3[0].lower()}", f"Conferences in {n3[1]}", f"مؤتمرات {n3[2]}")}</h1>
    <p class="intro">{L(f"{len(sel)} conférences commencent ce mois-là.", f"{len(sel)} conferences start that month.", f"{ISO(len(sel))} مؤتمر يبدأ في هذا الشهر.")}</p>"""
        apres = f'<h2 class="titre-section">{L("Autres mois", "Other months", "أشهر أخرى")}</h2>{grille(paires_mois(vis), "../../", "mois", "grille-mois", cle, "mois")}'
        titre = f"Academic conferences {n3[1]}: {len(sel)} conferences · Conférences {n3[0].lower()} | Conference Radar"
        desc = f"Academic conferences starting in {n3[1]}, with submission deadlines and official links. Conférences scientifiques de {n3[0].lower()}."
        pages.append(page_liste(f"mois/{cle}/", "../../", titre, desc, hero, sel, jour, v, etat, sans=("mois",), apres=apres))

    # ---- fiches
    for c in vis:
        pages.append(page_fiche(c, jour, v, etat, adr))

    # ---- flux Atom (alertes gratuites)
    maj_flux = (maj or jour)[:10]
    ecrire(sortie, "flux/tout.xml", atom("Conference Radar — all upcoming conferences", "flux/tout.xml", vis, maj_flux))
    liens_flux = [f'<li><a href="tout.xml">{ICONE_RSS}{L("Toutes les conférences", "All conferences", "كل المؤتمرات")}</a></li>']
    for d in domaines_presents:
        sel = [c for c in vis if d in c["domaines"]]
        ecrire(sortie, f"flux/{d}.xml", atom(f"Conference Radar — {nom_dom(d)[1]}", f"flux/{d}.xml", sel, maj_flux))
        liens_flux.append(f'<li><a href="{d}.xml">{ICONE_RSS}{LL(nom_dom(d))}</a></li>')
    for s in K.SPECIALITES:
        sel = [c for c in vis if s[0] in c["specialites"]]
        if sel:
            ecrire(sortie, f"flux/specialite-{s[0]}.xml", atom(f"Conference Radar — {nom_spec(s[0])[1]}", f"flux/specialite-{s[0]}.xml", sel, maj_flux))
            liens_flux.append(f'<li><a href="specialite-{s[0]}.xml">{ICONE_RSS}{LL(nom_spec(s[0]))}</a></li>')
    canaux = "".join(f'<li><a href="{E(adr["canaux"][d])}" target="_blank" rel="noopener">{ICONE_TELEGRAM}{LL(nom_dom(d))}</a></li>'
                     for d in domaines_presents if adr["canaux"].get(d))
    hero = f"""{fil("../", L("Alertes gratuites", "Free alerts", "تنبيهات مجانية"))}
    <h1>{L("Alertes gratuites par flux RSS", "Free alerts by RSS feed", "تنبيهات مجانية عبر ⁨RSS⁩")}</h1>
    <p class="intro">{L("Sans inscription et sans donnée personnelle : ajoutez le flux de votre domaine ou de votre spécialité dans votre lecteur de flux (Feedly, Thunderbird, Outlook…) : chaque nouvelle conférence y apparaît.",
                        "No sign-up, no personal data: add the feed of your field or specialty to your feed reader (Feedly, Thunderbird, Outlook…): every new conference shows up there.",
                        "دون تسجيل ودون معطيات شخصية: أضف خلاصة مجالك أو تخصصك إلى قارئ الخلاصات (⁨Feedly⁩، ⁨Thunderbird⁩، ⁨Outlook⁩…): يظهر فيه كل مؤتمر جديد.")}</p>"""
    contenu = f"""<section class="carte"><h2>{L("Flux RSS (Atom)", "RSS (Atom) feeds", "خلاصات ⁨RSS⁩")}</h2><ul class="flux">{"".join(liens_flux)}</ul></section>
{f'<section class="carte"><h2>{L("Canaux Telegram gratuits", "Free Telegram channels", "قنوات تيليغرام مجانية")}</h2><ul class="flux">{canaux}</ul></section>' if canaux else ''}
<section class="carte"><h2>{L("Alertes personnalisées", "Personalised alerts", "تنبيهات شخصية")}</h2>
<p>{L("Pour recevoir seulement VOS spécialités sur Telegram, avec les rappels J-7 et J-1 des dates limites :", "To receive only YOUR specialties on Telegram, with 7-day and 1-day deadline reminders:", "لتلقي تخصصاتك فقط على تيليغرام مع تذكير قبل الآجال بـ⁦7⁩ أيام وبيوم:")}</p>
<a class="btn-pro" href="../abonnement/">{L("Alertes Pro (14 jours d'essai gratuit)", "Pro Alerts (14-day free trial)", "تنبيهات Pro (تجربة مجانية ⁦14⁩ يومًا)")}</a></section>"""
    pages.append(("flux/", page("flux/", "../", "Free RSS alerts for upcoming conferences, by field and specialty · Alertes gratuites | Conference Radar",
                                "Free RSS (Atom) feeds of upcoming academic conferences by field and specialty, no sign-up, no personal data. Flux RSS gratuits par domaine.",
                                hero, contenu, v, etat)))

    # ---- à propos et sources
    hero = f"""{fil("../", L("À propos", "About", "من نحن"))}
    <h1>{L("À propos, méthode et sources", "About, method and sources", "من نحن، المنهجية والمصادر")}</h1>
    <p class="intro">{L("D'où viennent les conférences, comment elles sont vérifiées et classées, et leurs limites.", "Where the conferences come from, how they are checked and classified, and their limits.", "من أين تأتي المؤتمرات، كيف تُراجَع وتُرتَّب، وحدودها.")}</p>"""
    par_dom = " · ".join(f"{nom_dom(d)[0]} : {cd[d]}" for d in domaines_presents)
    lignes_src = "".join(f'<li><b>{E(S.SOURCES[s]["nom"])}</b> — <a href="{E(S.SOURCES[s]["url"])}" rel="noopener">{E(S.SOURCES[s]["url"].replace("https://", ""))}</a> — '
                         f'{L("licence", "licence", "رخصة")} {E(S.SOURCES[s]["licence"])}</li>' for s in ("ccfddl", "hf", "hci", "neuro", "bio", "robo", "inspire"))
    lignes_src += ("<li>" + L("<b>Sélection officielle (comptabilité, finance, finance islamique)</b> — chaque conférence vérifiée une à une sur la page officielle de son organisateur (associations savantes, universités, AAOIFI, banques centrales…) ; on n'en reprend que les faits (nom, dates, lieu, date limite, lien). La date de vérification est indiquée sur chaque fiche ; un robot vérifie chaque mois que les liens répondent encore.",
                              "<b>Official selection (accounting, finance, Islamic finance)</b> — each conference checked one by one on its organiser's official page (learned societies, universities, AAOIFI, central banks…); only facts are used (name, dates, venue, deadline, link). The check date is shown on each page; a robot checks every month that the links still work.",
                              "<b>اختيار رسمي (المحاسبة، المالية، التمويل الإسلامي)</b> — كل مؤتمر رُوجع على الصفحة الرسمية للجهة المنظمة (جمعيات علمية، جامعات، أيوفي، بنوك مركزية…)؛ نأخذ الوقائع فقط (الاسم، التواريخ، المكان، الأجل، الرابط). تاريخ المراجعة مذكور في كل بطاقة، ويتحقق برنامج آلي كل شهر من أن الروابط ما زالت تعمل.") + "</li>")
    contenu = f"""<section class="carte">
  <h2>{L("Ce que fait ce site", "What this site does", "ماذا يقدّم هذا الموقع")}</h2>
  <p data-l="fr">Un service <b>gratuit, sans inscription</b>, pour les enseignants-chercheurs : chaque jour, les conférences scientifiques des 18 prochains mois, rangées par <b>domaine</b>, <b>spécialité</b>, <b>pays</b> et <b>mois</b>, avec la <b>date limite de soumission</b> et le <b>lien officiel</b>. Alertes gratuites par flux RSS ; seules les alertes personnalisées sur Telegram (<a href="../abonnement/">Alertes Pro</a>) sont payantes. Aujourd'hui : {E(par_dom)}.</p>
  <p data-l="en">A <b>free service, without sign-up</b>, for professors and researchers: every day, the academic conferences of the next 18 months, sorted by <b>field</b>, <b>specialty</b>, <b>country</b> and <b>month</b>, with the <b>submission deadline</b> and the <b>official link</b>. Free alerts by RSS feed; only personalised Telegram alerts (<a href="../abonnement/">Pro Alerts</a>) are paid.</p>
  <p data-l="ar">خدمة <b>مجانية ودون تسجيل</b> للأساتذة والباحثين: كل يوم، المؤتمرات العلمية للأشهر الـ⁦18⁩ القادمة مرتبة حسب <b>المجال</b> و<b>التخصص</b> و<b>البلد</b> و<b>الشهر</b>، مع <b>آخر أجل للإرسال</b> و<b>الرابط الرسمي</b>. تنبيهات مجانية عبر ⁨RSS⁩؛ التنبيهات الشخصية على تيليغرام (<a href="../abonnement/">تنبيهات Pro</a>) وحدها بمقابل.</p>
</section>
<section class="carte">
  <h2>{L("Sources (licences ouvertes)", "Sources (open licences)", "المصادر (رخص مفتوحة)")}</h2>
  <ul class="sources">{lignes_src}</ul>
  <p class="petit">{L("Les listes ouvertes sont tenues par des communautés de chercheurs et publiées sous licence MIT, qui permet leur réutilisation en citant la source. Les métadonnées d'INSPIRE-HEP sont publiées sous CC0 ; nous n'en reprenons ni contact ni description. Chaque conférence renvoie à son site officiel. Les noms des conférences et organisateurs appartiennent à leurs propriétaires.",
                        "The open lists are maintained by research communities and published under the MIT licence, which allows reuse with attribution. INSPIRE-HEP metadata are published under CC0; we take no contacts or descriptions from it. Every conference links to its official website. Conference and organiser names belong to their owners.",
                        "القوائم المفتوحة يحررها باحثون وتُنشر برخصة ⁨MIT⁩ التي تسمح بإعادة الاستعمال مع ذكر المصدر. بيانات ⁨INSPIRE-HEP⁩ منشورة برخصة ⁨CC0⁩، ولا نأخذ منها أي معطيات اتصال أو وصف. كل مؤتمر مرفق برابط موقعه الرسمي. أسماء المؤتمرات والمنظمين ملك لأصحابها.")}</p>
</section>
<section class="carte">
  <h2>{L("Méthode et qualité", "Method and quality", "المنهجية والجودة")}</h2>
  <ol class="etapes" data-l="fr">
    <li>Lecture quotidienne des sources par leurs accès officiels (API de GitHub, API publique d'INSPIRE), en respectant leurs conditions et leur fichier robots.txt.</li>
    <li>Dates mises au même format ; une date qu'on ne comprend pas n'est <b>jamais devinée</b> : la conférence est alors écartée.</li>
    <li>Doublons fusionnés (même sigle, même année, mêmes dates) ; lien officiel obligatoire.</li>
    <li>Organisateurs connus pour leurs conférences « prédatrices » (frais élevés sans vraie relecture) <b>écartés</b>.</li>
    <li>Classement automatique par domaine et spécialité : quelques erreurs sont possibles.</li>
    <li>Si une source tombe en panne, ses conférences déjà connues restent affichées (30 jours au plus) et un <b>avertissement daté</b> apparaît.</li>
  </ol>
  <ol class="etapes" data-l="en">
    <li>Daily reading of the sources through their official access points (GitHub API, INSPIRE public API), respecting their terms and robots.txt.</li>
    <li>Dates normalised; a date we cannot understand is <b>never guessed</b>: the conference is then left out.</li>
    <li>Duplicates merged (same acronym, year and dates); an official link is mandatory.</li>
    <li>Organisers known for predatory conferences (high fees without real peer review) are <b>filtered out</b>.</li>
    <li>Automatic classification by field and specialty: a few mistakes are possible.</li>
    <li>If a source goes down, its known conferences stay listed (30 days at most) with a <b>dated warning</b>.</li>
  </ol>
  <ol class="etapes" data-l="ar">
    <li>قراءة يومية للمصادر عبر منافذها الرسمية (واجهة ⁨GitHub⁩، الواجهة العمومية لـ⁨INSPIRE⁩) مع احترام شروطها وملف ⁨robots.txt⁩.</li>
    <li>توحيد صيغة التواريخ؛ التاريخ غير المفهوم <b>لا يُخمَّن أبدًا</b> ويُستبعد المؤتمر.</li>
    <li>دمج المكررات (نفس الاسم والسنة والتواريخ)؛ الرابط الرسمي إجباري.</li>
    <li><b>استبعاد</b> المنظمين المعروفين بالمؤتمرات «المفترسة» (رسوم مرتفعة دون تحكيم حقيقي).</li>
    <li>ترتيب آلي حسب المجال والتخصص: أخطاء قليلة ممكنة.</li>
    <li>إذا تعطل مصدر، تبقى مؤتمراته المعروفة ظاهرة (⁦30⁩ يومًا على الأكثر) مع <b>تنبيه مؤرَّخ</b>.</li>
  </ol>
  <p class="avert">{L("<b>Avertissement :</b> ce site n'est pas officiel et n'est lié à aucun organisateur. Vérifiez toujours le site officiel de la conférence (dates, frais, éditeur des actes) avant de soumettre.",
                      "<b>Disclaimer:</b> this site is not official and not affiliated with any organiser. Always check the conference's official website (dates, fees, proceedings publisher) before submitting.",
                      "<b>تنبيه:</b> هذا الموقع ليس رسميًا ولا علاقة له بأي جهة منظمة. تثبّت دائمًا من الموقع الرسمي للمؤتمر (التواريخ، الرسوم، ناشر الأعمال) قبل الإرسال.")}</p>
</section>
<section class="carte" id="credits-photos">
  <h2>{L("Crédits des photos", "Photo credits", "حقوق الصور")}</h2>
  <ul class="sources">{"".join(f'<li data-photo="{E(MOSAIQUE)} {E(MOSAIQUE_MOBILE)}">{LL(ph["sujet"])} — {L("photo", "photo", "صورة")} : <b>{E(ph["auteur"])}</b>, {L("licence", "licence", "رخصة")} <a href="{E(ph["licence_url"])}" rel="noopener license">{E(ph["licence"])}</a>, <a href="{E(ph["source_url"])}" rel="noopener">Wikimedia Commons</a> ({L("recadrée", "cropped", "مقصوصة")}).</li>' for ph in PHOTOS)}</ul>
</section>"""
    titre = "About, method and open sources · À propos et sources | Conference Radar"
    desc = "Free service. Where the upcoming conferences come from (open lists under MIT licence, INSPIRE-HEP under CC0), how they are checked and classified."
    pages.append(("a-propos/", page("a-propos/", "../", titre, desc, hero, contenu, v, etat)))

    # ---- organisateurs : signaler une conférence (gratuit)
    hero = f"""{fil("../", L("Signaler une conférence", "Submit a conference", "أضف مؤتمرًا"))}
    <h1>{L("Organisateurs : signalez votre conférence", "Organisers: submit your conference", "المنظمون: أضيفوا مؤتمركم")}</h1>
    <p class="intro">{L("Gratuit. Votre conférence apparaît sur le site après un contrôle automatique, avec la mention « signalée par l'organisateur ».", "Free. Your conference appears on the site after an automatic check, marked “submitted by the organiser”.", "مجانًا. يظهر مؤتمركم في الموقع بعد مراقبة آلية مع عبارة «أضافه المنظم».")}</p>"""
    if adr["formulaire"]:
        action = (f'<a class="btn-publier" id="btn-publier" href="{E(adr["formulaire"])}" target="_blank" rel="noopener">'
                  f'{L("Remplir le formulaire", "Fill in the form", "املأ الاستمارة")}</a>')
    else:
        action = f'<p class="bientot-pub" id="btn-publier">{L("Bientôt : le formulaire sera ouvert ici.", "Coming soon: the form will open here.", "قريبًا: ستُفتح الاستمارة هنا.")}</p>'
    contenu = f"""<section class="carte">
  <h2>{L("Comment ça marche ?", "How does it work?", "كيف يعمل؟")}</h2>
  <ol class="etapes" data-l="fr"><li>Vous indiquez le nom, les dates, le lieu, la spécialité, la date limite et le <b>lien officiel</b> (https).</li><li>Un robot contrôle (dates à venir, lien officiel, pas de doublon, organisateurs douteux refusés).</li><li>La conférence apparaît dans la journée et disparaît après sa date de fin.</li></ol>
  <ol class="etapes" data-l="en"><li>You give the name, dates, venue, specialty, deadline and the <b>official link</b> (https).</li><li>A robot checks it (future dates, official link, no duplicate, dubious organisers refused).</li><li>The conference appears within the day and disappears after its end date.</li></ol>
  <ol class="etapes" data-l="ar"><li>تذكرون الاسم والتواريخ والمكان والتخصص وآخر أجل و<b>الرابط الرسمي</b> (⁨https⁩).</li><li>يراقب برنامج آلي الطلب (تواريخ قادمة، رابط رسمي، دون تكرار، رفض المنظمين المشبوهين).</li><li>يظهر المؤتمر في اليوم نفسه ويُحذف بعد تاريخ نهايته.</li></ol>
  {action}
</section>"""
    pages.append(("publier/", page("publier/", "../", "Submit your conference for free · Signaler une conférence | Conference Radar",
                                   "Conference organisers: submit your academic conference for free. Automatic check, official link required. Signaler gratuitement une conférence.",
                                   hero, contenu, v, etat)))

    # ---- Alertes Pro
    pages += pages_abonnement(vis, adr, v, etat)

    # ---- écriture + plan du site
    ecrire_textes(sortie)
    v = version_assets(sortie)
    for chemin, contenu in pages:
        ecrire(sortie, chemin + "index.html", contenu.replace("__V__", v))
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for chemin, _ in pages:
        sitemap.append(f"  <url><loc>{URL_SITE}{chemin}</loc><lastmod>{jour}</lastmod></url>")
    sitemap.append("</urlset>")
    ecrire(sortie, "sitemap.xml", "\n".join(sitemap) + "\n")
    # pages vidéo (video/) tirées de la page À propos : mêmes en-tête, pied, CSP et ?v= (tools/page_video.py)
    sys.path.insert(0, os.path.join(RACINE_SITE, "tools"))
    from page_video import pages_video
    with open(os.path.join(RACINE_SITE, "tools", "page_video.json"), encoding="utf-8") as fv:
        pages_video(sortie, json.load(fv))
    print(f"  {len(pages)} pages, {len(vis)} conférences à venir (sur {len(confs)} en mémoire), version {v}"
          f"{', AVERTISSEMENT : ' + raison if panne else ''}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Construit le site statique des conférences.")
    p.add_argument("--donnees", default=os.path.join(RACINE_SITE, "donnees", "conferences.json"))
    p.add_argument("--sortie", default=RACINE_SITE)
    p.add_argument("--aujourdhui", default=dt.date.today().isoformat(), help="date du jour AAAA-MM-JJ (tests)")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not DATE.match(a.aujourdhui):
        print("date invalide")
        return 2
    print("Construction du site…")
    return construire(a.donnees, a.sortie, a.aujourdhui)


if __name__ == "__main__":
    sys.exit(main())
