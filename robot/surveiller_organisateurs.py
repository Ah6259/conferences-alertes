# -*- coding: utf-8 -*-
"""
Surveillance MENSUELLE des organisateurs SÉRIEUX de finance islamique (22/11/2026, « fais 2 » d'Ahmed).

Pourquoi : la sélection officielle (donnees/selection-officielle.json) est faite à la main, conférence par conférence, sur la page
officielle de l'organisateur (les organisateurs en série sont écartés). Ce robot lit chaque mois la page « événements » des
organisateurs sérieux listés dans donnees/organisateurs-suivis.json et repère les LIGNES NOUVELLES qui annoncent une conférence
(un mot comme conference / forum / symposium / summit / مؤتمر + une année à venir) et qui ne sont pas déjà dans la sélection.

Il n'ajoute JAMAIS rien au site tout seul : il écrit les nouveautés dans donnees/surveillance-organisateurs.json ; le robot GitHub
(verif-officiels.yml) ouvre alors l'issue « Finance islamique : nouvelles éditions à vérifier », que Claude traite (GUIDE § 4 : page
officielle lue, dates jamais devinées). Lecture polie : robots.txt respecté, une page toutes les 3 secondes, User-Agent honnête,
jamais de contournement (page protégée = notée « à vérifier à la main »).

    python robot/surveiller_organisateurs.py
"""
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, ICI)
import sources as S   # noqa: E402
import verifier_officiels as V   # noqa: E402

SUIVIS = os.path.join(RACINE, "donnees", "organisateurs-suivis.json")
SELECTION = os.path.join(RACINE, "donnees", "selection-officielle.json")
MEMOIRE = os.path.join(RACINE, "donnees", "surveillance-organisateurs.json")

# Sur une page qui annonce AUSSI d'autres sujets (plateforme d'universités, forum économique général : « filtrer » dans
# organisateurs-suivis.json), seules les lignes qui parlent de finance islamique comptent.
MOTS_FINANCE_ISLAMIQUE = re.compile(r"islam|shari'?a|syariah|halal|sukuk|takaful|zakat|zakah|waqf|wakaf|muamalat|إسلام|الصكوك|التكافل|الزكاة|الوقف", re.I)
MOTS_EVENEMENT = re.compile(r"\b(conference|conférence|forum|symposium|summit|congress|congrès|colloque|colloquium|workshop|dialogues?|"
                            r"roundtable|seminar|séminaire)\b|مؤتمر|ملتقى|ندوة|منتدى", re.I)


PIED = re.compile(r"©|copyright|all rights reserved|tous droits", re.I)   # ligne de bas de page (« © 2026 … Forum »), jamais une annonce


def texte_de(page_html):
    """Texte visible d'une page, une ligne par bloc (titres, paragraphes, éléments de liste, cellules)."""
    t = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", page_html)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|td|th|a|span|section|article)>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return [re.sub(r"\s+", " ", l).strip() for l in t.split("\n") if l.strip()]


def lignes_evenements(lignes, annee):
    """Lignes qui annoncent un événement de l'année en cours ou des suivantes (une ligne courte, sans doublon)."""
    annees = {str(annee + i) for i in range(3)}
    vues, res = set(), []
    for l in lignes:
        if not (10 <= len(l) <= 220) or not MOTS_EVENEMENT.search(l) or not any(a in l for a in annees) or PIED.search(l):
            continue
        cle = re.sub(r"\W+", " ", l.lower()).strip()
        if cle not in vues:
            vues.add(cle)
            res.append(l)
    return res


def deja_dans_selection(ligne, selection):
    """Vrai si la ligne parle d'une conférence déjà dans la sélection (sigle ou début du titre reconnu)."""
    bas = re.sub(r"\W+", " ", ligne.lower())
    for c in selection.get("conferences") or []:
        sigle = re.sub(r"\W+", " ", str(c.get("acronyme") or "").lower()).strip()
        titre = re.sub(r"\W+", " ", str(c.get("titre") or "").lower()).strip()
        if sigle and len(sigle) >= 4 and sigle in bas:
            return True
        if titre and len(titre) >= 20 and titre[:40] in bas:
            return True
    return False


def lire(url):
    """(etat, texte) : ok / protege / injoignable."""
    req = urllib.request.Request(url, headers={"User-Agent": S.UA, "Accept": "text/html,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            brut = r.read(3_000_000).decode("utf-8", errors="replace")
        if "challenge-platform" in brut or "Just a moment" in brut:
            return "protege", ""
        return "ok", brut
    except urllib.error.HTTPError as e:
        return ("protege" if e.code in (401, 403, 429) else "injoignable"), ""
    except Exception:   # noqa: BLE001  (délai dépassé, certificat, réseau : on réessaiera le mois prochain)
        return "injoignable", ""


def main(jour=None, lire_url=lire, pause=3):
    jour = jour or dt.date.today().isoformat()
    annee = int(jour[:4])
    with open(SUIVIS, encoding="utf-8") as f:
        suivis = json.load(f).get("organisateurs") or []
    with open(SELECTION, encoding="utf-8") as f:
        sel = json.load(f)
    try:
        with open(MEMOIRE, encoding="utf-8") as f:
            memoire = json.load(f).get("pages") or {}
    except (OSError, ValueError):
        memoire = {}
    cache, nouveautes, etats = {}, [], []
    for o in suivis:
        url = o.get("page_evenements") or ""
        if not url.startswith("https://"):
            continue
        if not V.autorise(url, cache):
            etats.append({"nom": o.get("nom"), "url": url, "etat": "protege", "detail": "robots.txt interdit la lecture automatique"})
            continue
        etat, page = lire_url(url)
        time.sleep(max(pause, o.get("pause") or 0) if pause else 0)
        if etat != "ok":
            etats.append({"nom": o.get("nom"), "url": url, "etat": etat, "detail": "à vérifier à la main" if etat == "protege" else "ne répond pas"})
            continue
        lignes = lignes_evenements(texte_de(page), annee)
        if o.get("filtrer"):
            lignes = [l for l in lignes if MOTS_FINANCE_ISLAMIQUE.search(l)]
        avant = (memoire.get(url) or {}).get("lignes")
        connues = set(avant or [])
        nouvelles = [l for l in lignes if l not in connues and not deja_dans_selection(l, sel)]
        for l in nouvelles:
            nouveautes.append({"nom": o.get("nom"), "url": url, "ligne": l})
        memoire[url] = {"nom": o.get("nom"), "lu_le": jour, "lignes": lignes,
                        "empreinte": hashlib.sha256("\n".join(lignes).encode()).hexdigest()[:16]}
        etats.append({"nom": o.get("nom"), "url": url, "etat": "ok", "detail": f"{len(lignes)} annonce(s), {len(nouvelles)} nouvelle(s)"})
        print(f"  ok           {o.get('nom')} — {len(lignes)} annonce(s), {len(nouvelles)} nouvelle(s)")
    for e in etats:
        if e["etat"] != "ok":
            print(f"  {e['etat']:12} {e['nom']} — {e['detail']}")
    d = {"lu_le": jour, "nouveautes": nouveautes, "etats": etats, "pages": memoire}
    tmp = MEMOIRE + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, MEMOIRE)
    print(f"  {len(suivis)} organisateurs suivis, {len(nouveautes)} nouveauté(s) à vérifier")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
