# -*- coding: utf-8 -*-
"""
Alertes GRATUITES sur les canaux Telegram publics, UN canal par grand domaine (même mécanique que le site Appels d'offres).
Chaque jour, pour chaque canal : les nouvelles conférences du domaine + « ⏰ Date limite dans 7 jours ».

Ne fait RIEN (et ne sonne pas en échec) tant que les secrets n'existent pas :
  TELEGRAM_BOT_TOKEN   jeton du robot (donné par @BotFather)
  TELEGRAM_CANAUX      liste « domaine=@canal » séparés par des points-virgules,
                       ex. « informatique=@radarconf_info;physique=@radarconf_physique »
Jamais deux fois la même annonce : mémoire dans donnees/telegram-envoyes.json (seuls les messages vraiment partis
sont notés ; en cas d'erreur, ils repartent au passage suivant). Les conférences de la toute première collecte sont
notées sans envoi (sinon des centaines de messages le premier jour).

    python robot/telegram.py --essai          (affiche les messages sans rien envoyer)
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
import classement as K          # noqa: E402
import construire_site as C     # noqa: E402

DONNEES = os.path.join(os.path.dirname(ICI), "donnees")
MARGE = 3900           # limite de Telegram : 4096 caractères par message
FRAIS_JOURS = 3        # une conférence ajoutée il y a plus de 3 jours n'est plus « nouvelle »
OUBLI_JOURS = 400
RAPPEL_JOURS = 7
H = lambda t: html.escape(str(t or ""), quote=False)


def canaux_secret(texte):
    """« informatique=@x;physique=@y » -> {"informatique": "@x", …} (domaines inconnus ou canaux mal écrits ignorés)."""
    res = {}
    for morceau in re.split(r"[;\n,]", texte or ""):
        if "=" not in morceau:
            continue
        d, c = (x.strip() for x in morceau.split("=", 1))
        if d in K.D_PAR_SLUG and re.fullmatch(r"@[A-Za-z0-9_]{4,64}|-100\d{6,15}", c):
            res[d] = c
    return res


def charger_memoire(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            m = json.load(f)
        if isinstance(m.get("envoyes"), dict) and isinstance(m.get("rappels"), dict):
            return m
    except (OSError, ValueError, AttributeError):
        pass
    return {"envoyes": {}, "rappels": {}}


def sauver_memoire(chemin, m, jour):
    oubli = (dt.date.fromisoformat(jour) - dt.timedelta(days=OUBLI_JOURS)).isoformat()
    for k in ("envoyes", "rappels"):
        m[k] = {t: d for t, d in m[k].items() if d >= oubli}
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(m, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, chemin)


def ligne(c):
    sigle, titre = C.nom_conf(c)
    p = C.periode3(c["debut"], c["fin"])[1]
    lieu = ", ".join(x for x in (c["ville"], C.nom_pays(c["pays"])[1]) if x) or ("Online" if c["mode"] == "en-ligne" else "")
    lims = C.limites_soumission(c)
    lim = next((x["date"] for x in lims if x["date"] >= JOUR[0]), "")
    t = f"• <b>{H(sigle)}</b>" + (f" — {H(titre[:90])}" if titre else "")
    t += f"\n  📅 {H(p)}" + (f" · 📍 {H(lieu)}" if lieu else "")
    if lim:
        t += f" · ⏳ {H(C.d3(lim)[1])}"
    t += f'\n  <a href="{H(C.URL_SITE)}conference/{c["id"]}/">Details</a> · <a href="{H(c["lien"])}">Official site</a>'
    return t


JOUR = [""]


def preparer(confs, domaine, memoire, jour, premiere):
    """Blocs [(texte, [clés nouvelles], [clés rappels])] pour un domaine, et les clés notées sans envoi."""
    JOUR[0] = jour
    frais = (dt.date.fromisoformat(jour) - dt.timedelta(days=FRAIS_JOURS)).isoformat()
    cible = (dt.date.fromisoformat(jour) + dt.timedelta(days=RAPPEL_JOURS)).isoformat()
    a_voir = [c for c in C.a_venir(confs, jour) if domaine in c["domaines"]]
    nouvelles, anciennes = [], []
    for c in a_voir:
        k = f"{domaine}|{c['id']}"
        if k in memoire["envoyes"]:
            continue
        (nouvelles if c["ajoute_le"] >= frais and c["ajoute_le"] > premiere else anciennes).append(c)
    rappels = [c for c in a_voir if any(x["date"] == cible for x in C.limites_soumission(c))
               and f"{domaine}|{c['id']}|{cible}" not in memoire["rappels"]]
    nom = C.nom_dom(domaine)
    blocs = []
    if nouvelles:
        blocs.append((f"🆕 <b>{H(nom[1])} — new conferences</b> ({len(nouvelles)})\n<i>{H(nom[0])} : nouvelles conférences</i>", [], []))
        for c in sorted(nouvelles, key=lambda c: c["debut"]):
            blocs.append((ligne(c), [f"{domaine}|{c['id']}"], []))
    if rappels:
        blocs.append((f"\n⏰ <b>Deadline in 7 days</b> · <i>date limite dans 7 jours</i> ({len(rappels)})", [], []))
        for c in sorted(rappels, key=lambda c: c["id"]):
            blocs.append((ligne(c), [], [f"{domaine}|{c['id']}|{cible}"]))
    if blocs:
        blocs.append((f"\nSources: open lists (MIT) & INSPIRE-HEP (CC0). Always check the official website. {C.URL_SITE}", [], []))
    return blocs, [f"{domaine}|{c['id']}" for c in anciennes]


def decouper(blocs, marge=MARGE):
    messages, texte, ids, rap = [], "", [], []
    for t, n, r in blocs:
        if len(t) > marge:
            t = t[:marge - 1] + "…"
        if texte and len(texte) + 1 + len(t) > marge:
            messages.append((texte, ids, rap))
            texte, ids, rap = "", [], []
        texte = (texte + "\n" + t) if texte else t.lstrip("\n")
        ids, rap = ids + n, rap + r
    if texte:
        messages.append((texte, ids, rap))
    return messages


def envoyer(jeton, canal, texte):
    """Envoie un message ; renvoie (True, "") ou (False, raison). Remplacée par une fausse fonction dans les tests."""
    donnees = urllib.parse.urlencode({"chat_id": canal, "text": texte, "parse_mode": "HTML",
                                      "disable_web_page_preview": "true"}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{jeton}/sendMessage", data=donnees)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            rep = json.loads(r.read().decode("utf-8", errors="replace"))
            return (True, "") if rep.get("ok") else (False, str(rep.get("description"))[:200])
    except urllib.error.HTTPError as e:
        try:
            return False, f"code {e.code} : " + str(json.loads(e.read().decode()).get("description"))[:200]
        except Exception:
            return False, f"code {e.code}"
    except Exception as e:   # réseau coupé, délai…
        return False, str(e)[:200]


def main(argv=None):
    p = argparse.ArgumentParser(description="Alertes gratuites sur les canaux Telegram par domaine.")
    p.add_argument("--donnees", default=os.path.join(DONNEES, "conferences.json"))
    p.add_argument("--memoire", default=os.path.join(DONNEES, "telegram-envoyes.json"))
    p.add_argument("--aujourdhui", default=dt.date.today().isoformat())
    p.add_argument("--essai", action="store_true", help="affiche les messages sans les envoyer")
    a = p.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    jeton = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    canaux = canaux_secret(os.environ.get("TELEGRAM_CANAUX", ""))
    print("Alertes Telegram par domaine…")
    if not a.essai and not (jeton and canaux):
        print("  Telegram pas encore configuré (secrets TELEGRAM_BOT_TOKEN / TELEGRAM_CANAUX absents) : rien envoyé")
        return 0
    brut, confs = C.charger(a.donnees)
    if not confs:
        print("  ! échec : données illisibles : rien envoyé")
        return 0
    premiere = str((brut or {}).get("premiere_collecte") or "")
    memoire = charger_memoire(a.memoire)
    domaines = list(canaux) if canaux else [d[0] for d in K.DOMAINES]
    for d in domaines:
        blocs, anciennes = preparer(confs, d, memoire, a.aujourdhui, premiere)
        messages = decouper(blocs)
        if a.essai:
            for t, _, _ in messages:
                print(f"[{d}]\n{t}\n" + "-" * 40)
            continue
        for k in anciennes:
            memoire["envoyes"][k] = a.aujourdhui
        envoyes = 0
        for texte, ids, rap in messages:
            ok, raison = envoyer(jeton, canaux[d], texte)
            if not ok:
                print(f"  ! échec : Telegram a refusé le message du domaine {d} ({raison}) — il repartira au prochain passage")
                break
            envoyes += 1
            for k in ids:
                memoire["envoyes"][k] = a.aujourdhui
            for k in rap:
                memoire["rappels"][k] = a.aujourdhui
        print(f"  {d} : {envoyes}/{len(messages)} message(s) envoyé(s)")
    if not a.essai:
        sauver_memoire(a.memoire, memoire, a.aujourdhui)
    return 0


if __name__ == "__main__":
    sys.exit(main())
