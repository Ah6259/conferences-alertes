# -*- coding: utf-8 -*-
"""
« Rapports du mois » (demande d'Ahmed du 18/10/2026, règle commune § 25) : des articles AUTOMATIQUES mais VRAIS,
écrits à partir des SEULES données gratuites du site (donnees/conferences.json, déjà nettoyées par construire_site.py).

  rapports/            liste des mois
  rapports/AAAA-MM/    le rapport du mois : événements qui COMMENCENT ce mois-là, par type, format, domaine, continent,
                       pays, spécialité ; dates limites de soumission du mois ; calendrier ; méthode ; « Citer ces chiffres ».

Historique : donnees/rapports.json (mois -> conférences vues + chiffres + premier jour + dernière date).
  - Mois en cours : recalculé à chaque passage du robot (« chiffres au <date> »).
    Une conférence terminée (absente des données parce que sa date de fin est passée) reste comptée ;
    une conférence retirée AVANT sa fin (annulée, déplacée, corrigée, doublon fusionné) n'est plus comptée.
  - Mois FINI : figé, plus jamais modifié (seule la mise en page commune peut changer, jamais un chiffre).
  - Pas de rapport pour un mois de moins de MIN_EVENEMENTS événements (pas de page presque vide).
Aucune estimation : chaque chiffre est un décompte de fiches du site.

    python robot/rapports.py --amorcer-git      (une seule fois : rejoue l'historique git de conferences.json)
"""
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys

MIN_EVENEMENTS = 10     # pas de rapport (ni de page) pour un mois avec moins d'événements
MIN_PAYS = 2            # un pays n'entre dans le classement qu'à partir de 2 événements
MIN_SPEC = 3            # une spécialité, à partir de 3 événements
THEMES_SITE = ("comptabilite", "finance", "finance-islamique")
CHAMPS = ("id", "acronyme", "titre", "annee", "type", "debut", "fin", "ville", "pays", "mode", "continent", "domaines", "specialites", "lien")


# ------------------------------------------------------------------ historique
def charger(chemin):
    try:
        with open(chemin, encoding="utf-8") as f:
            h = json.load(f)
        if isinstance(h, dict) and isinstance(h.get("mois"), dict):
            return h
    except (OSError, ValueError):
        pass
    return {"mois": {}}


def sauver(chemin, hist):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(hist, f, ensure_ascii=False, indent=0, sort_keys=True)
        f.write("\n")
    os.replace(tmp, chemin)


def limites_du_mois(c, mois):
    return [{"date": x["date"], "type": x["type"]} for x in c.get("dates_limites") or []
            if x.get("type") in ("article", "resume") and str(x.get("date", ""))[:7] == mois]


def pertinente(c, mois):
    """Une conférence compte pour un mois si elle y COMMENCE, ou si une de ses dates limites de soumission y tombe."""
    return c["debut"][:7] == mois or bool(limites_du_mois(c, mois))


def fiche(c, mois):
    f = {k: c.get(k) for k in CHAMPS}
    f["limites"] = limites_du_mois(c, mois)
    return f


def mettre_a_jour(hist, confs, jour):
    """Met à jour le mois de `jour` avec les conférences du site (déjà nettoyées). Fige les mois passés. Renvoie le mois traité."""
    mois = jour[:7]
    for cle, e in hist["mois"].items():
        if cle < mois and not e.get("fini"):
            e["fini"] = True                      # mois terminé : figé pour toujours
    e = hist["mois"].get(mois)
    if e and (e.get("fini") or jour < e.get("derniere_date", "")):
        return mois                               # jamais modifié une fois fini ; jamais de retour en arrière
    if not e:
        e = {"fini": False, "premier_jour": jour, "conferences": []}
    actuelles = {c["id"]: c for c in confs}
    vues = {}
    for c in e["conferences"]:
        if c["id"] not in actuelles and c["fin"] < jour:
            vues[c["id"]] = c                     # terminée : reste comptée
    for c in confs:
        if pertinente(c, mois):
            vues[c["id"]] = fiche(c, mois)
    e["conferences"] = sorted(vues.values(), key=lambda c: (c["debut"], c["id"]))
    e["derniere_date"] = jour
    e["chiffres"] = calculer(e["conferences"], mois)
    hist["mois"][mois] = e
    return mois


def compter(confs, cle):
    res = {}
    for c in confs:
        vals = c[cle] if isinstance(c[cle], list) else [c[cle]]
        for v in vals:
            res[v] = res.get(v, 0) + 1
    return res


def calculer(vues, mois):
    ev = [c for c in vues if c["debut"][:7] == mois]
    lim = sorted((x["date"], x["type"], c["id"]) for c in vues for x in c.get("limites", []))
    pays = compter([c for c in ev if c["pays"] and c["mode"] != "en-ligne"], "pays")
    return {
        "evenements": len(ev),
        "par_type": compter(ev, "type"),
        "par_mode": compter(ev, "mode"),
        "par_domaine": compter(ev, "domaines"),
        "par_continent": compter(ev, "continent"),
        "par_pays": pays,
        "par_specialite": compter(ev, "specialites"),
        "pays": len(pays),
        "themes_site": sum(1 for c in ev if set(c["domaines"]) & set(THEMES_SITE)),
        "tunisie": sum(1 for c in ev if c["pays"] == "TN" and c["mode"] != "en-ligne"),
        "afrique": sum(1 for c in ev if c["continent"] == "afrique"),
        "limites": len(lim),
        "limites_conferences": len({x[2] for x in lim}),
    }


def avec_page(hist):
    """Mois qui ont un rapport (assez d'événements), du plus récent au plus ancien."""
    return sorted((k for k, e in hist["mois"].items() if e.get("chiffres", {}).get("evenements", 0) >= MIN_EVENEMENTS), reverse=True)


def mois_precedent(cle):
    a, m = int(cle[:4]), int(cle[5:7])
    return f"{a - 1}-12" if m == 1 else f"{a}-{m - 1:02d}"


# ------------------------------------------------------------------ partage + signature (demande d'Ahmed du 18/10/2026)
DOMAINE = "conferences.clicvia.com"


def signature(C):
    """« Un rapport de Radar des conférences · conferences.clicvia.com », sous le titre."""
    fr, en, ar = C.NOM
    return (f'<p class="rp-signature">{C.L(f"Un rapport de <b>{fr}</b> · {DOMAINE}", f"A report by <b>{en}</b> · {DOMAINE}", f"تقرير من <b>{ar}</b> · {C.ISO(DOMAINE)}")}</p>')


def bloc_partage(C, url, titre3, haut):
    """UN SEUL bouton « Partager ce rapport » : menu de partage du téléphone (Facebook, WhatsApp, LinkedIn…), sinon lien copié.
    Le texte partagé dit de quel site vient l'article, SANS adresse (Facebook prendrait la 1re adresse du texte
    et montrerait l'aperçu de l'accueil) : l'adresse du rapport passe seulement dans le champ url. Le code est dans assets/page.js (CSP : pas de script en ligne)."""
    fr, en, ar = C.NOM
    tf, te, ta = (str(x).replace("\u2066", "").replace("\u2069", "") for x in titre3)
    textes = {"fr": f"{tf} — Rapport du mois de {fr} :",
              "en": f"{te} — Monthly report by {en}:",
              "ar": f"{ta} — تقرير الشهر من {ar}:"}
    attrs = "".join(f' data-titre-{k}="{C.E(t)}"' for k, t in zip(("fr", "en", "ar"), (tf, te, ta)))
    attrs += "".join(f' data-texte-{k}="{C.E(t)}"' for k, t in textes.items())
    ico = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/>'
           '<circle cx="18" cy="19" r="3"/><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"/></svg>')
    return (f'<section class="carte rp-partage{" rp-partage-haut" if haut else " rp-partage-bas"}">'
            f'<button type="button" class="rp-partager" data-partage-rapport data-url="{C.E(url)}"{attrs}>{ico}'
            f'<span>{C.L("Partager ce rapport", "Share this report", "شارك هذا التقرير")}</span></button>'
            f'<p class="rp-copie" role="status" hidden>{C.L("Lien copié ✓ — collez-le où vous voulez", "Link copied ✓ — paste it wherever you like", "تم نسخ الرابط ✓ — الصقه حيث تشاء")}</p>'
            f'</section>')


# ------------------------------------------------------------------ pages
def pages(C, hist, vis, jour, v, etat, images=False):
    """Renvoie [(chemin, html, lastmod, aperçu ou None)] : rapports/ + rapports/AAAA-MM/ pour chaque mois qui a assez d'événements.
    Aperçu = image propre au rapport à dessiner (voir apercu()) ; images=False : image générale du site."""
    res = []
    mois_ok = avec_page(hist)
    if not mois_ok:
        return res
    ids_fiches = {c["id"] for c in vis}
    for cle in mois_ok:
        res.append(page_mois(C, hist, cle, ids_fiches, jour, v, etat, images))
    res.insert(0, page_liste(C, hist, mois_ok, v, etat) + (None,))
    return res


def apercu(C, cle, e):
    """Image d'aperçu PROPRE au rapport (18/10/2026, Ahmed) : (fichier, titre, mois, chiffre clé, sous-titre), chiffres de la page.
    Le nom dépend du contenu : quand les chiffres changent, Facebook prend la nouvelle image."""
    ch = e["chiffres"]
    titre = "Conférences scientifiques · Academic conferences"
    chiffre = f"{pl(ch['evenements'], 'événement', 'événements')} · {ch['pays']} pays"
    sous = f"{pl(ch['limites'], 'date limite', 'dates limites')} de soumission · chiffres au {C.d3(e['derniere_date'])[0]}"
    h = hashlib.sha1(f"{titre}|{cle}|{chiffre}|{sous}".encode()).hexdigest()[:8]
    return (f"{chemin_mois(cle)}apercu-{h}.jpg", titre, C.mois3(cle)[0].lower(), chiffre, sous)


def chemin_mois(cle):
    return f"rapports/{cle}/"


def pct(n, tot):
    return round(100 * n / tot) if tot else 0


def jsonld(obj):
    return '<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "\n</script>\n"


def ligne_tab(C, nom3, n, tot):
    p = pct(n, tot)
    return (f'<tr><th scope="row">{C.LL(nom3)}</th><td class="n">{n}</td><td class="n">{C.L(f"{p} %", f"{p}%", C.ISO(f"{p} %"))}</td></tr>')


def tableau(C, titre3, entete3, lignes, note=""):
    if not lignes:
        return ""
    return (f'<section class="carte rp"><h2>{C.LL(titre3)}</h2><div class="rp-tab"><table>'
            f'<thead><tr><th scope="col">{C.LL(entete3)}</th><th scope="col" class="n">{C.L("Événements", "Events", "فعاليات")}</th>'
            f'<th scope="col" class="n">{C.L("Part", "Share", "النسبة")}</th></tr></thead><tbody>{"".join(lignes)}</tbody></table></div>'
            f'{note}</section>')


def pl(n, sing, plur):
    """« 1 école », « 6 écoles »."""
    return f"{n} {sing if n <= 1 else plur}"


def de(mot):
    """« de novembre », « d'octobre »."""
    return ("d'" if mot[:1].lower() in "aâàeéèêioôuy" else "de ") + mot


def premiers(compte):
    """Valeurs à égalité en tête (classement honnête : toutes les ex aequo)."""
    if not compte:
        return [], 0
    m = max(compte.values())
    return sorted(k for k, n in compte.items() if n == m), m


def page_mois(C, hist, cle, ids_fiches, jour, v, etat, images=False):
    L, LL, ISO, E = C.L, C.LL, C.ISO, C.E
    e = hist["mois"][cle]
    ch = e["chiffres"]
    racine = "../../"
    m3 = C.mois3(cle)
    mfr, men, mar = m3[0].lower(), m3[1], m3[2]
    fini = bool(e.get("fini"))
    der3 = C.d3(e["derniere_date"])
    prem3 = C.d3(e["premier_jour"])
    n, npays = ch["evenements"], ch["pays"]
    ev = [c for c in e["conferences"] if c["debut"][:7] == cle]
    tp = ch["par_type"]
    nc, na, ne = tp.get("conference", 0), tp.get("atelier", 0), tp.get("ecole", 0)
    md = ch["par_mode"]
    npr, nhy, nel = md.get("presentiel", 0), md.get("hybride", 0), md.get("en-ligne", 0)

    # ---- en bref (chaque phrase = un décompte)
    bref = [L(f"<b>{n} événements scientifiques</b> commencent en {mfr} : {pl(nc, "conférence", "conférences")}, {pl(na, "atelier", "ateliers")} et {pl(ne, "école scientifique", "écoles scientifiques")}.",
              f"<b>{n} academic events</b> start in {men}: {pl(nc, "conference", "conferences")}, {pl(na, "workshop", "workshops")} and {pl(ne, "school", "schools")}.",
              f"<b>{ISO(n)} فعالية علمية</b> تبدأ في {mar}: {ISO(nc)} مؤتمر و{ISO(na)} ورشة عمل و{ISO(ne)} مدرسة علمية.")]
    if not fini:
        fin_ = sum(1 for c in ev if c["fin"] < jour)
        avenir = n - fin_
        lien_m = (f' (<a href="{racine}mois/{cle}/">{L("liste des conférences " + de(mfr), "list of " + men + " conferences", "قائمة مؤتمرات " + mar)}</a>)'
                  if avenir else "")
        bref.append(L(f"Au {der3[0]} : {pl(fin_, "déjà terminé", "déjà terminés")}, <b>{pl(avenir, "pas encore terminé", "pas encore terminés")}</b>",
                      f"On {der3[1]}: {fin_} already over, <b>{avenir} not over yet</b>",
                      f"في {der3[2]}: {ISO(fin_)} انتهت و<b>{ISO(avenir)} لم تنته بعد</b>") + lien_m + ".")
    bref.append(L(f"Format : {npr} sur place, {pl(nhy, "hybride", "hybrides")}, {nel} en ligne ; les événements sur place ou hybrides ont lieu dans <b>{npays} pays</b>.",
                  f"Format: {npr} in person, {nhy} hybrid, {nel} online; in-person and hybrid events take place in <b>{npays} countries</b>.",
                  f"الصيغة: {ISO(npr)} حضوري، {ISO(nhy)} هجين، {ISO(nel)} عن بعد؛ الفعاليات الحضورية والهجينة تُقام في <b>{ISO(npays)} بلدًا</b>."))
    doms, nd = premiers(ch["par_domaine"])
    if doms:
        noms = [C.nom_dom(d) for d in doms]
        bref.append(L(f"Domaine le plus représenté : {', '.join(x[0] for x in noms)} ({nd} événements).",
                      f"Most represented field: {', '.join(x[1] for x in noms)} ({nd} events).",
                      f"المجال الأكثر حضورًا: {'، '.join(x[2] for x in noms)} ({ISO(nd)} فعالية)."))
    pays_cl = {k: x for k, x in ch["par_pays"].items() if x >= MIN_PAYS}
    tete, npt = premiers(pays_cl)
    if tete:
        noms = [C.nom_pays(p) for p in tete]
        bref.append(L(f"Pays qui en accueille le plus : {', '.join(x[0] for x in noms)} ({npt} événements).",
                      f"Country hosting the most: {', '.join(x[1] for x in noms)} ({npt} events).",
                      f"البلد الأكثر احتضانًا: {'، '.join(x[2] for x in noms)} ({ISO(npt)} فعالية)."))
    th = ch["themes_site"]
    bref.append(L(f"Comptabilité, finance et finance islamique : {th} événements.",
                  f"Accounting, finance and Islamic finance: {th} events.",
                  f"المحاسبة والمالية والتمويل الإسلامي: {ISO(th)} فعالية."))
    tn, af = ch["tunisie"], ch["afrique"]
    bref.append(L(f"En Afrique : {af} événements, dont {tn} en Tunisie.",
                  f"In Africa: {af} events, including {tn} in Tunisia.",
                  f"في إفريقيا: {ISO(af)} فعالية، منها {ISO(tn)} في تونس."))
    bref.append(L(f"<b>{ch['limites']} dates limites de soumission</b> (résumé ou article complet) tombent en {mfr}, pour {ch['limites_conferences']} conférences.",
                  f"<b>{ch['limites']} submission deadlines</b> (abstract or full paper) fall in {men}, for {ch['limites_conferences']} conferences.",
                  f"<b>{ISO(ch['limites'])} أجل إرسال</b> (ملخص أو مقال كامل) يحل في {mar}، لـ{ISO(ch['limites_conferences'])} مؤتمر."))
    prec = mois_precedent(cle)
    ep = hist["mois"].get(prec)
    if ep and ep.get("chiffres", {}).get("evenements", 0) >= MIN_EVENEMENTS:
        p3 = C.mois3(prec)
        np_ = ep["chiffres"]["evenements"]
        bref.append(L(f"Évolution : {np_} événements en {p3[0].lower()} (<a href=\"../{prec}/\">rapport</a>), {n} en {mfr}, comptés de la même façon.",
                      f"Change: {np_} events in {p3[1]} (<a href=\"../{prec}/\">report</a>), {n} in {men}, counted the same way.",
                      f"التطوّر: {ISO(np_)} فعالية في {p3[2]} (<a href=\"../{prec}/\">التقرير</a>)، و{ISO(n)} في {mar}، بنفس طريقة العدّ."))
    else:
        bref.append(L("Premier rapport mensuel du site : pas encore de comparaison avec le mois précédent.",
                      "The site's first monthly report: no comparison with the previous month yet.",
                      "أول تقرير شهري للموقع: لا مقارنة بعد مع الشهر السابق."))

    # ---- tableaux
    t_dom = tableau(C, ("Par domaine", "By field", "حسب المجال"), ("Domaine", "Field", "المجال"),
                    [ligne_tab(C, C.nom_dom(d[0]), ch["par_domaine"][d[0]], n) for d in sorted(C.K.DOMAINES, key=lambda d: -ch["par_domaine"].get(d[0], 0)) if ch["par_domaine"].get(d[0])],
                    f'<p class="petit">{L("Un événement peut appartenir à plusieurs domaines : la somme peut dépasser le total.", "An event can belong to several fields: the sum can exceed the total.", "قد تنتمي الفعالية إلى أكثر من مجال: قد يتجاوز المجموع العدد الكلي.")}</p>')
    cont_noms = {x[0]: C.nom_cont(x[0]) for x in C.K.CONTINENTS}
    cont_noms[""] = ("Lieu non précisé", "Venue not given", "المكان غير مذكور")
    t_cont = tableau(C, ("Par continent", "By continent", "حسب القارة"), ("Continent", "Continent", "القارة"),
                     [ligne_tab(C, cont_noms[k], x, n) for k, x in sorted(ch["par_continent"].items(), key=lambda kv: (-kv[1], kv[0])) if k in cont_noms])
    t_pays = tableau(C, ("Par pays", "By country", "حسب البلد"), ("Pays", "Country", "البلد"),
                     [ligne_tab(C, C.nom_pays(k), x, n) for k, x in sorted(pays_cl.items(), key=lambda kv: (-kv[1], kv[0]))],
                     f'<p class="petit">{L(f"Pays avec au moins {MIN_PAYS} événements sur place ou hybrides ({len(pays_cl)} pays sur {npays}).", f"Countries with at least {MIN_PAYS} in-person or hybrid events ({len(pays_cl)} of {npays} countries).", f"البلدان التي تحتضن {ISO(MIN_PAYS)} فعاليات حضورية أو هجينة على الأقل ({ISO(len(pays_cl))} من {ISO(npays)}).")}</p>')
    specs = {k: x for k, x in ch["par_specialite"].items() if x >= MIN_SPEC and k in C.K.S_PAR_SLUG}
    t_spec = tableau(C, ("Spécialités les plus présentes", "Most present specialties", "التخصصات الأكثر حضورًا"), ("Spécialité", "Specialty", "التخصص"),
                     [ligne_tab(C, C.nom_spec(k), x, n) for k, x in sorted(specs.items(), key=lambda kv: (-kv[1], kv[0]))],
                     f'<p class="petit">{L(f"Spécialités avec au moins {MIN_SPEC} événements ; un événement peut en avoir plusieurs.", f"Specialties with at least {MIN_SPEC} events; an event can have several.", f"التخصصات التي لها {ISO(MIN_SPEC)} فعاليات على الأقل؛ قد يكون للفعالية أكثر من تخصص.")}</p>')

    # ---- calendrier
    def lien_conf(c):
        sigle, titre = C.nom_conf(c)
        txt = E(sigle) + (f" <small>— {E(titre)}</small>" if titre else "")
        if c["id"] in ids_fiches and not fini:
            return f'<a href="{racine}conference/{c["id"]}/" lang="en" dir="ltr">{txt}</a>'
        return f'<a href="{E(c["lien"])}" target="_blank" rel="noopener" lang="en" dir="ltr">{txt}</a>'

    items = []
    for c in ev:
        p = C.periode3(c["debut"], c["fin"])
        doms_c = " · ".join(LL(C.nom_dom(d)) for d in c["domaines"] if d in C.K.D_PAR_SLUG)
        items.append(f'<li data-id="{E(c["id"])}"><span class="rp-date">{LL(p)}</span> {lien_conf(c)}'
                     f'<span class="rp-info">{C.texte_lieu(c)} · {doms_c}</span></li>')
    cal = (f'<section class="carte rp" id="calendrier"><h2>{L(f"Calendrier : les {n} événements {de(mfr)}", f"Calendar: the {n} events of {men}", f"الرزنامة: فعاليات {mar} ({ISO(n)})")}</h2>'
           f'<ol class="rp-cal">{"".join(items)}</ol></section>')
    lims = sorted(((x["date"], x["type"], c) for c in e["conferences"] for x in c.get("limites", [])), key=lambda t: (t[0], t[2]["id"]))
    quoi = {"resume": ("résumé", "abstract", "ملخص"), "article": ("article complet", "full paper", "مقال كامل")}
    li_l = "".join(f'<li data-d="{d}"><span class="rp-date">{LL(C.d3(d))}</span> {lien_conf(c)} <span class="rp-info">{LL(quoi[t])}</span></li>' for d, t, c in lims)
    sec_lim = (f'<section class="carte rp" id="dates-limites"><h2>{L(f"Les {len(lims)} dates limites de soumission {de(mfr)}", f"The {len(lims)} submission deadlines of {men}", f"آجال الإرسال في {mar} ({ISO(len(lims))})")}</h2>'
               f'<ol class="rp-cal">{li_l}</ol>'
               f'<p class="petit">{L("Les dates peuvent être prolongées : seul le site officiel de la conférence fait foi.", "Deadlines can be extended: only the conference official website is authoritative.", "قد تُمدَّد الآجال: الموقع الرسمي للمؤتمر هو المرجع الوحيد.")}</p></section>') if lims else ""

    # ---- FAQ (visible + JSON-LD, mêmes réponses)
    faq = [(f"Combien de conférences scientifiques commencent en {mfr} ?",
            f"{n} événements relevés par Conference Radar (chiffres au {der3[0]}) : {pl(nc, "conférence", "conférences")}, {pl(na, "atelier", "ateliers")} et {pl(ne, "école scientifique", "écoles scientifiques")} ; "
            f"les événements sur place ou hybrides ont lieu dans {npays} pays.",
            f"How many academic conferences start in {men}?",
            f"{n} events listed by Conference Radar (figures as of {der3[1]}): {pl(nc, "conference", "conferences")}, {pl(na, "workshop", "workshops")} and {pl(ne, "school", "schools")}; in-person and hybrid events take place in {npays} countries.",
            f"كم مؤتمرًا علميًا يبدأ في {mar}؟",
            f"{ISO(n)} فعالية رصدها رادار المؤتمرات (أرقام {der3[2]}): {ISO(nc)} مؤتمر و{ISO(na)} ورشة عمل و{ISO(ne)} مدرسة علمية، في {ISO(npays)} بلدًا.")]
    if tete:
        noms = [C.nom_pays(p) for p in tete]
        faq.append((f"Quel pays accueille le plus de conférences en {mfr} ?",
                    f"{', '.join(x[0] for x in noms)}, avec {npt} événements sur {n}.",
                    f"Which country hosts the most conferences in {men}?",
                    f"{', '.join(x[1] for x in noms)}, with {npt} of the {n} events.",
                    f"أي بلد يحتضن أكثر المؤتمرات في {mar}؟",
                    f"{'، '.join(x[2] for x in noms)}، بـ{ISO(npt)} فعالية من {ISO(n)}."))
    faq.append((f"Combien de dates limites de soumission tombent en {mfr} ?",
                f"{ch['limites']} dates limites (résumé ou article complet), pour {ch['limites_conferences']} conférences.",
                f"How many submission deadlines fall in {men}?",
                f"{ch['limites']} deadlines (abstract or full paper), for {ch['limites_conferences']} conferences.",
                f"كم أجل إرسال يحل في {mar}؟",
                f"{ISO(ch['limites'])} أجل (ملخص أو مقال كامل) لـ{ISO(ch['limites_conferences'])} مؤتمر."))
    faq.append((f"Y a-t-il des conférences en Tunisie en {mfr} ?",
                (f"Oui : {tn} événement{'s' if tn > 1 else ''} en Tunisie, sur {af} en Afrique." if tn else
                 f"Aucun des {n} événements relevés n'a lieu en Tunisie ; {af} ont lieu en Afrique."),
                f"Are there conferences in Tunisia in {men}?",
                (f"Yes: {tn} event{'s' if tn > 1 else ''} in Tunisia, out of {af} in Africa." if tn else
                 f"None of the {n} listed events takes place in Tunisia; {af} take place in Africa."),
                f"هل توجد مؤتمرات في تونس في {mar}؟",
                (f"نعم: {ISO(tn)} في تونس من أصل {ISO(af)} في إفريقيا." if tn else
                 f"لا تُقام أي من الفعاليات الـ{ISO(n)} في تونس؛ {ISO(af)} في إفريقيا.")))
    faq_html = "".join(f'<details><summary>{L(E(q), E(qe), E(qa))}</summary><p>{L(E(r), E(re_), E(ra))}</p></details>'
                       for q, r, qe, re_, qa, ra in faq)

    # ---- méthode, citer
    partiel = e["premier_jour"] > cle + "-01"
    meth = [L("Sources : les listes ouvertes de conférences (licence MIT), la base INSPIRE-HEP (CC0) et la sélection officielle du site (comptabilité, finance, finance islamique), lues chaque jour par le robot du site.",
              "Sources: open conference lists (MIT licence), the INSPIRE-HEP database (CC0) and the site's official selection (accounting, finance, Islamic finance), read every day by the site's robot.",
              "المصادر: قوائم المؤتمرات المفتوحة (رخصة ⁨MIT⁩) وقاعدة ⁨INSPIRE-HEP⁩ (⁨CC0⁩) والاختيار الرسمي للموقع (المحاسبة، المالية، التمويل الإسلامي)، يقرؤها البرنامج الآلي للموقع كل يوم."),
            L("Un événement compte pour le mois où il commence ; il reste compté après sa fin. Un événement retiré des sources avant sa fin (annulé, déplacé, corrigé) n'est plus compté.",
              "An event counts for the month in which it starts; it stays counted after it ends. An event removed from the sources before its end (cancelled, moved, corrected) is no longer counted.",
              "تُحسب الفعالية في الشهر الذي تبدأ فيه وتبقى محسوبة بعد نهايتها. الفعالية التي تُحذف من المصادر قبل نهايتها (إلغاء، نقل، تصحيح) لا تُحسب."),
            L("Aucune estimation : chaque chiffre est un simple décompte des fiches du site. Les frais d'inscription ne figurent pas dans nos sources : ce rapport n'en parle pas.",
              "No estimate: every figure is a plain count of the site's entries. Registration fees are not in our sources: this report does not cover them.",
              "لا تقدير: كل رقم هو عدّ بسيط لبطاقات الموقع. رسوم التسجيل غير موجودة في مصادرنا ولا يتناولها هذا التقرير."),
            L(f"Classements : un pays à partir de {MIN_PAYS} événements, une spécialité à partir de {MIN_SPEC} ; en cas d'égalité, tous les ex aequo sont cités.",
              f"Rankings: a country from {MIN_PAYS} events, a specialty from {MIN_SPEC}; ties are all listed.",
              f"الترتيب: البلد ابتداءً من {ISO(MIN_PAYS)} فعاليات، والتخصص ابتداءً من {ISO(MIN_SPEC)}؛ وعند التساوي تُذكر كلها.")]
    if partiel:
        meth.append(L(f"Le site relève ce mois depuis le {prem3[0]} : les événements déjà terminés avant cette date ne sont pas comptés.",
                      f"The site has recorded this month since {prem3[1]}: events already over before that date are not counted.",
                      f"يرصد الموقع هذا الشهر منذ {prem3[2]}: الفعاليات التي انتهت قبل هذا التاريخ غير محسوبة."))
    meth.append(L(f"Mois terminé : chiffres arrêtés au {der3[0]}, ils ne seront plus modifiés." if fini else
                  f"Mois en cours : chiffres au {der3[0]}, recalculés chaque jour jusqu'à la fin du mois, puis figés.",
                  f"Month over: figures frozen on {der3[1]}, they will not change any more." if fini else
                  f"Current month: figures as of {der3[1]}, recalculated every day until the end of the month, then frozen.",
                  f"شهر منتهٍ: أرقام موقوفة في {der3[2]} ولن تتغير بعد الآن." if fini else
                  f"الشهر الجاري: أرقام {der3[2]}، تُعاد كل يوم حتى نهاية الشهر ثم تُثبَّت."))
    url = C.URL_SITE + chemin_mois(cle)
    titre_art_fr = f"Conférences scientifiques, {mfr} : le rapport du mois"
    citer = (f'<section class="carte rp" id="citer"><h2>{L("Citer ces chiffres", "Cite these figures", "الاستشهاد بهذه الأرقام")}</h2>'
             f'<p>{L("Journalistes, blogs, universités : vous pouvez reprendre ces chiffres en citant la source avec ce lien.", "Journalists, blogs, universities: you may reuse these figures, citing the source with this link.", "صحفيون، مدونات، جامعات: يمكنكم نقل هذه الأرقام مع ذكر المصدر بهذا الرابط.")}</p>'
             f'<p class="rp-citer" lang="fr" dir="ltr">Source : Conference Radar (Radar des conférences), « {E(titre_art_fr)} », {url} '
             f'({L("chiffres au", "figures as of", "أرقام")} {LL(der3)}).</p></section>')

    # ---- en-tête de page
    etat_txt = (L(f"Mois terminé : chiffres arrêtés au {der3[0]}.", f"Month over: figures frozen on {der3[1]}.", f"شهر منتهٍ: أرقام موقوفة في {der3[2]}.") if fini else
                L(f"Chiffres au {der3[0]}, mis à jour chaque jour jusqu'à la fin du mois.", f"Figures as of {der3[1]}, updated every day until the end of the month.",
                  f"أرقام {der3[2]}، تُحدَّث كل يوم حتى آخر الشهر."))
    hero = f"""{C.fil(racine, f'<a href="../">{L("Rapports du mois", "Monthly reports", "تقارير الشهر")}</a>', LL(m3))}
    <h1>{L(f"Conférences scientifiques : {mfr}", f"Academic conferences: {men}", f"المؤتمرات العلمية: {mar}")}</h1>
    {signature(C)}
    <p class="intro">{L("Le rapport du mois, calculé sur les conférences, ateliers et écoles scientifiques relevés par le site.", "The monthly report, computed from the conferences, workshops and schools listed on the site.", "تقرير الشهر، محسوب من المؤتمرات وورشات العمل والمدارس العلمية التي يرصدها الموقع.")} {etat_txt}</p>"""
    titre3 = (f"Conférences scientifiques : {mfr}", f"Academic conferences: {men}", f"المؤتمرات العلمية: {mar}")
    contenu = f"""{bloc_partage(C, url, titre3, True)}
<section class="carte resume" aria-label="Summary">
  <div class="r-avenir" id="rp-n"><b>{n}</b><span>{L(f"événements commencent en {mfr}", f"events start in {men}", f"فعالية تبدأ في {mar}")}</span></div>
  <div class="r-limites" id="rp-limites"><b>{ch['limites']}</b><span>{L("dates limites de soumission ce mois", "submission deadlines this month", "أجل إرسال هذا الشهر")}</span></div>
  <div class="r-domaines" id="rp-pays"><b>{npays}</b><span>{L("pays (sur place ou hybride)", "countries (in person or hybrid)", "بلدًا (حضوري أو هجين)")}</span></div>
</section>
<section class="carte rp" id="en-bref"><h2>{L("En bref", "In brief", "باختصار")}</h2><ul class="rp-bref">{"".join(f"<li>{b}</li>" for b in bref)}</ul></section>
{t_dom}
{t_cont}
{t_pays}
{t_spec}
{cal}
{sec_lim}
<section class="carte rp" id="faq"><h2>{L("Questions fréquentes", "Frequently asked questions", "أسئلة شائعة")}</h2>{faq_html}</section>
<section class="carte rp" id="methode"><h2>{L("Comment ces chiffres sont calculés", "How these figures are computed", "كيف تُحسب هذه الأرقام")}</h2><ul class="rp-bref">{"".join(f"<li>{x}</li>" for x in meth)}</ul>
<p class="petit"><a href="{racine}a-propos/">{L("Méthode et sources du site", "Site method and sources", "منهجية الموقع ومصادره")}</a></p></section>
{citer}
<section class="carte rp"><h2>{L("Aller plus loin", "Go further", "للمزيد")}</h2><ul class="rp-bref">
<li><a href="{racine}">{L("Toutes les conférences à venir", "All upcoming conferences", "كل المؤتمرات القادمة")}</a></li>
<li><a href="{racine}flux/">{L("Alertes gratuites par flux RSS", "Free RSS alerts", "تنبيهات مجانية عبر RSS")}</a></li>
<li><a href="../">{L("Tous les rapports du mois", "All monthly reports", "كل تقارير الشهر")}</a></li></ul></section>
{bloc_partage(C, url, titre3, False)}"""
    titre = f"Conférences scientifiques {mfr} : {n} événements, {npays} pays — rapport du mois · Academic conferences {men} | Conference Radar"
    desc = (f"{C.NOM[0]} — rapport du mois. Chiffres au {der3[0]} : {n} conférences, ateliers et écoles scientifiques commencent en {mfr} ({npays} pays) ; "
            f"{ch['limites']} dates limites de soumission. Par domaine, continent et pays, calendrier et méthode. Monthly report, {men}.")
    ap = apercu(C, cle, e) if images else None
    img = ap[0] if ap else C.OG_IMAGE
    art = {"@context": "https://schema.org", "@type": "Article", "headline": f"Conférences scientifiques {mfr} : {n} événements, {npays} pays"[:110],
           "inLanguage": ["en", "fr", "ar"], "datePublished": e["premier_jour"], "dateModified": e["derniere_date"], "url": url,
           "author": {"@type": "Organization", "name": "Conference Radar", "url": C.URL_SITE},
           "publisher": {"@type": "Organization", "name": "Conference Radar", "url": C.URL_SITE},
           "image": C.URL_SITE + img}
    fil_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Conference Radar", "item": C.URL_SITE},
        {"@type": "ListItem", "position": 2, "name": "Rapports du mois", "item": C.URL_SITE + "rapports/"},
        {"@type": "ListItem", "position": 3, "name": m3[0], "item": url}]}
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": r}} for q, r, *_ in faq]}
    ld = jsonld(fil_ld) + jsonld(art) + jsonld(faq_ld)
    return (chemin_mois(cle), C.page(chemin_mois(cle), racine, titre, desc, hero, contenu, v, etat, ld, og_image=img, og_type="article"),
            e["derniere_date"], ap)


def page_liste(C, hist, mois_ok, v, etat):
    L, LL, ISO = C.L, C.LL, C.ISO
    racine = "../"
    lignes = []
    for cle in mois_ok:
        e = hist["mois"][cle]
        ch = e["chiffres"]
        d = C.d3(e["derniere_date"])
        etat_m = (L(f"chiffres arrêtés au {d[0]}", f"figures frozen on {d[1]}", f"أرقام موقوفة في {d[2]}") if e.get("fini") else
                  L(f"mois en cours, chiffres au {d[0]}", f"current month, figures as of {d[1]}", f"الشهر الجاري، أرقام {d[2]}"))
        ne, npy, nl = ch["evenements"], ch["pays"], ch["limites"]
        txt = L(f"{ne} événements, {npy} pays, {nl} dates limites", f"{ne} events, {npy} countries, {nl} deadlines",
                f"{ISO(ne)} فعالية، {ISO(npy)} بلدًا، {ISO(nl)} أجل")
        lignes.append(f'<li><a href="{cle}/"><b>{LL(C.mois3(cle))}</b></a> — {txt}'
                      f' <small>({etat_m})</small></li>')
    hero = f"""{C.fil(racine, L("Rapports du mois", "Monthly reports", "تقارير الشهر"))}
    <h1>{L("Rapports du mois", "Monthly reports", "تقارير الشهر")}</h1>
    {signature(C)}
    <p class="intro">{L("Chaque mois, les conférences scientifiques relevées par le site, en chiffres : par domaine, continent et pays, avec les dates limites de soumission. Des décomptes, jamais des estimations.",
                        "Every month, the academic conferences listed on the site, in figures: by field, continent and country, with submission deadlines. Counts, never estimates.",
                        "كل شهر، المؤتمرات العلمية التي يرصدها الموقع بالأرقام: حسب المجال والقارة والبلد، مع آجال الإرسال. عدّ فقط، دون تقديرات.")}</p>"""
    titre3 = ("Rapports du mois : les conférences scientifiques en chiffres", "Monthly reports: academic conferences in figures", "تقارير الشهر: المؤتمرات العلمية بالأرقام")
    url = C.URL_SITE + "rapports/"
    contenu = (bloc_partage(C, url, titre3, True) +
               f'<section class="carte rp"><h2>{L("Les rapports", "The reports", "التقارير")}</h2><ul class="rp-bref" id="rp-liste">{"".join(lignes)}</ul>'
               f'<p class="petit">{L(f"Un mois n\'a un rapport qu\'à partir de {MIN_EVENEMENTS} événements. Le mois en cours est mis à jour chaque jour ; un mois terminé n\'est plus jamais modifié.", f"A month gets a report only from {MIN_EVENEMENTS} events. The current month is updated every day; a finished month is never changed again.", f"لا يكون للشهر تقرير إلا ابتداءً من {ISO(MIN_EVENEMENTS)} فعاليات. يُحدَّث الشهر الجاري كل يوم، والشهر المنتهي لا يتغير أبدًا.")}</p></section>'
               + bloc_partage(C, url, titre3, False))
    titre = "Rapports du mois : les conférences scientifiques en chiffres · Monthly reports | Conference Radar"
    desc = f"{C.NOM[0]} — rapport du mois. Chaque mois, les conférences scientifiques relevées par le site en chiffres : par domaine, continent et pays, dates limites de soumission. Monthly reports."
    return "rapports/", C.page("rapports/", racine, titre, desc, hero, contenu, v, etat), max(hist["mois"][k]["derniere_date"] for k in mois_ok)


# ------------------------------------------------------------------ amorçage (une fois) depuis l'historique git
def amorcer_git(racine_site):
    """Rejoue, dans l'ordre, chaque version de donnees/conferences.json enregistrée dans git (vraies données du robot)."""
    sys.path.insert(0, os.path.join(racine_site, "robot"))
    import construire_site as C
    chemin = os.path.join(racine_site, "donnees", "rapports.json")
    hist = charger(chemin)
    lignes = subprocess.check_output(["git", "log", "--reverse", "--format=%H", "--", "donnees/conferences.json"], cwd=racine_site, text=True).split()
    for h in lignes:
        try:
            brut = json.loads(subprocess.check_output(["git", "show", f"{h}:donnees/conferences.json"], cwd=racine_site))
        except (subprocess.CalledProcessError, ValueError):
            continue
        jour = str(brut.get("mis_a_jour") or "")[:10]
        if len(jour) != 10:
            continue
        mettre_a_jour(hist, C.nettoyer(brut.get("conferences") or []), jour)
        print(jour, {k: e["chiffres"]["evenements"] for k, e in hist["mois"].items()})
    sauver(chemin, hist)


if __name__ == "__main__":
    if "--amorcer-git" in sys.argv:
        amorcer_git(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    else:
        print(__doc__)
