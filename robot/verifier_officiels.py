# -*- coding: utf-8 -*-
"""
Vérification MENSUELLE de la sélection officielle (donnees/selection-officielle.json : comptabilité, finance, finance islamique).

Pour chaque conférence encore à venir : le lien officiel répond-il encore ? (lecture lente, une page toutes les 3 secondes,
User-Agent honnête, robots.txt respecté : une page interdite aux robots n'est PAS lue, elle est notée « à vérifier à la main »).
Jamais de contournement d'une protection (Cloudflare, connexion…) : une page protégée est notée « à vérifier à la main ».

Résultat : donnees/verification-officielle.json (lu par le robot GitHub, qui ouvre une issue « Sélection officielle : liens à
revérifier » quand des liens ne répondent plus, puis la referme quand tout va bien).
Le site n'est JAMAIS modifié par ce robot : une conférence n'est retirée qu'après sa date de fin (ou à la main).

    python robot/verifier_officiels.py
"""
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
sys.path.insert(0, ICI)
import sources as S   # noqa: E402

SELECTION = os.path.join(RACINE, "donnees", "selection-officielle.json")
SORTIE = os.path.join(RACINE, "donnees", "verification-officielle.json")


def autorise(url, cache):
    p = urllib.parse.urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(base + "/robots.txt")
        try:
            rp.read()
        except Exception:     # robots.txt illisible : on reste prudent mais on peut lire la page publique
            rp = None
        cache[base] = rp
    rp = cache[base]
    return True if rp is None else rp.can_fetch(S.UA, url)


def tester(url):
    """Renvoie (etat, detail) : ok / injoignable / protege."""
    req = urllib.request.Request(url, headers={"User-Agent": S.UA, "Accept": "text/html,application/pdf,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            debut = r.read(4000).decode("utf-8", errors="replace")
            if "challenge-platform" in debut or "Just a moment" in debut:
                return "protege", "page protégée (vérification humaine) : à vérifier à la main"
            return "ok", f"code {r.status}"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403, 429):
            return "protege", f"code {e.code} : à vérifier à la main"
        return "injoignable", f"code {e.code}"
    except Exception as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):      # certificat du site incomplet : la page marche dans un navigateur
            return "protege", "certificat du site incomplet : à vérifier à la main"
        return "injoignable", str(e)[:120]


def main(jour=None, tester_url=tester, pause=3):
    jour = jour or dt.date.today().isoformat()
    with open(SELECTION, encoding="utf-8") as f:
        sel = json.load(f)
    cache, res = {}, []
    for c in sel.get("conferences") or []:
        if str(c.get("fin") or "") < jour:
            continue
        url = str(c.get("lien") or "")
        if not autorise(url, cache):
            etat, detail = "protege", "robots.txt interdit la lecture automatique : à vérifier à la main"
        else:
            etat, detail = tester_url(url)
            time.sleep(pause)
        res.append({"acronyme": c.get("acronyme"), "lien": url, "etat": etat, "detail": detail})
        print(f"  {etat:12} {c.get('acronyme')} — {detail}")
    casses = [r for r in res if r["etat"] == "injoignable"]
    d = {"verifie_le": jour, "nombre": len(res), "injoignables": len(casses),
         "a_verifier_a_la_main": sum(1 for r in res if r["etat"] == "protege"), "resultats": res}
    tmp = SORTIE + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    os.replace(tmp, SORTIE)
    print(f"  {len(res)} liens vérifiés, {len(casses)} injoignable(s)" + (" — « échec » : voir l'issue GitHub" if casses else ""))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
