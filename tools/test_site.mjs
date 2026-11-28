// Test automatique de « Radar des conférences / Conference Radar » — à lancer après chaque modification :
//   node tools/test_site.mjs                 (teste le site de ce dossier)
//   node tools/test_site.mjs --racine X      (teste une copie, ex. pour le sabotage volontaire)
// jsdom s'installe une fois par PC (dans ce dossier) :  npm install --no-save --no-package-lock jsdom
import { JSDOM } from "jsdom";
import { readFileSync, existsSync, readdirSync, statSync, mkdtempSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { fileURLToPath, pathToFileURL } from "url";
import { dirname, join, resolve } from "path";
import { createHash } from "crypto";

const i = process.argv.indexOf("--racine");
const root = i > 0 ? process.argv[i + 1] : join(dirname(fileURLToPath(import.meta.url)), "..");
const URL_SITE = "https://conferences.clicvia.com/";
const lire = f => readFileSync(join(root, f), "utf8");
let erreurs = 0, total = 0;
const check = (desc, cond) => { total++; if (!cond) { console.log("FAIL " + desc); erreurs++; } else console.log("OK   " + desc); };
const plus = (d, n) => new Date(Date.parse(d + "T00:00:00Z") + n * 86400000).toISOString().slice(0, 10);
const ecart = (a, b) => Math.round((Date.parse(a) - Date.parse(b)) / 86400000);

// ---- Données de référence ----------------------------------------------------------------
const etat = JSON.parse(lire("donnees/etat-source.json"));
const JOUR = etat.construit_le;
const brut = JSON.parse(lire("donnees/conferences.json"));
const avenir = brut.conferences.filter(c => c.fin >= JOUR);
const PAR_ID = Object.fromEntries(avenir.map(c => [c.id, c]));
check(`données : ${avenir.length} conférences à venir le ${JOUR} (objectif : plusieurs centaines, au moins 200)`, avenir.length >= 200);
check("données : chaque conférence a un lien officiel https, une date de début, un domaine et une spécialité",
  avenir.every(c => /^https:\/\//.test(c.lien) && /^\d{4}-\d{2}-\d{2}$/.test(c.debut) && c.domaines.length && c.specialites.length));
check("données : aucune date inventée (dates limites au format AAAA-MM-JJ, fin ≥ début, durée ≤ 60 jours)",
  avenir.every(c => c.fin >= c.debut && ecart(c.fin, c.debut) <= 60 && c.dates_limites.every(x => /^\d{4}-\d{2}-\d{2}$/.test(x.date))));
check("données : fenêtre de 18 mois respectée", avenir.every(c => ecart(c.debut, JOUR) <= 548));
check("données : identifiants uniques", new Set(avenir.map(c => c.id)).size === avenir.length);
const vides = avenir.filter(c => !c.pays && c.mode !== "en-ligne").length;
check(`données : lieu connu pour presque toutes (${vides} sans pays, au plus 5 %)`, vides <= avenir.length * 0.05);
check("données : chaque conférence cite sa source (liste ouverte MIT, INSPIRE CC0 ou page officielle vérifiée)", avenir.every(c => c.sources.length));
// Thèmes demandés par Ahmed (06/10/2026) : comptabilité, finance et SURTOUT finance islamique.
// Minimums comptés sur la SÉLECTION OFFICIELLE (fichier qui ne fait que grandir) et jamais sur les conférences à venir
// (qui diminuent seules avec le temps) : le robot quotidien n'est jamais bloqué (règle commune § 13).
const SEL = JSON.parse(lire("donnees/selection-officielle.json")).conferences;
const domSpec = s => ({ "compta-generale": "comptabilite", "compta-financiere": "comptabilite", "compta-gestion": "comptabilite", audit: "comptabilite",
  fiscalite: "comptabilite", gouvernance: "comptabilite", "finance-generale": "finance", "finance-entreprise": "finance", marches: "finance", banque: "finance",
  fintech: "finance", "economie-islamique": "finance-islamique", "banque-islamique": "finance-islamique", sukuk: "finance-islamique", takaful: "finance-islamique",
  "zakat-waqf": "finance-islamique", "aaoifi-charia": "finance-islamique" })[s];
const MINI = { "comptabilite": 20, "finance": 10, "finance-islamique": 10 };
for (const [dm, n] of Object.entries(MINI)) {
  const k = SEL.filter(c => c.specialites.some(s => domSpec(s) === dm)).length;
  check(`sélection officielle : thème « ${dm} » : ${k} conférences vérifiées (au moins ${n})`, k >= n);
  const av = avenir.filter(c => c.domaines.includes(dm)).length;
  if (av < n) console.log(`   (info, ne bloque pas) thème « ${dm} » : seulement ${av} conférences encore à venir — enrichir la sélection (GUIDE §4)`);
}
check("sélection officielle : chaque entrée a un lien https, des dates AAAA-MM-JJ et une page vérifiée",
  SEL.every(c => /^https:\/\//.test(c.lien) && /^\d{4}-\d{2}-\d{2}$/.test(c.debut) && c.fin >= c.debut && /^https:\/\//.test(c.page_verifiee) && c.specialites.length));
check("sélection officielle : chaque conférence a sa date de vérification et sa page vérifiée",
  avenir.filter(c => c.sources[0] === "officiel").every(c => /^\d{4}-\d{2}-\d{2}$/.test(c.verifie_le) && /^https:\/\//.test(c.page_verifiee)));
check("finance islamique : des spécialités dédiées dans la sélection (banque islamique, sukuk, zakat/waqf, AAOIFI/charia…)",
  ["banque-islamique", "sukuk", "zakat-waqf", "aaoifi-charia", "economie-islamique"].every(s => SEL.some(c => c.specialites.includes(s))));

// ---- Chargement d'une page comme un navigateur ---------------------------------------------
// 19/11/2026 (accueil léger, CV.3) : une longue liste n'a que ses 30 premières conférences dans la page, le reste dans liste.json
// chargé au 1er geste. Le faux navigateur lit ce fichier (fetch) ; page() charge la liste complète sauf avec { leger: true }.
async function page(chemin, params = "", { leger = false } = {}) {
  const dossier = dirname(join(root, chemin));
  const html = lire(chemin).replace(/<script([^>]*) src="(?!https?:)([^"?]+)(\?[^"]*)?"([^>]*)><\/script>/g,
    (_, a, src) => `<script>${readFileSync(join(dossier, src), "utf8").replace(/<\/script/gi, "<\\/script")}</script>`);   // « </script> » écrit dans un commentaire ne coupe pas la balise
  const dom = new JSDOM(html, { url: URL_SITE + chemin.replace("index.html", "") + "?" + params, runScripts: "dangerously", pretendToBeVisual: true });
  dom.window.fetch = async u => { const f = join(dossier, String(u).split("?")[0]); return existsSync(f) ? { ok: true, json: async () => JSON.parse(readFileSync(f, "utf8")) } : { ok: false, status: 404 }; };
  await new Promise(ok => dom.window.addEventListener("load", ok));
  const l = dom.window.document.getElementById("liste"), q = dom.window.document.getElementById("f-q");
  if (!leger && l && l.dataset.reste && q) { q.dispatchEvent(new dom.window.Event("focus")); await new Promise(r => setTimeout(r, 80)); }
  return dom.window;
}
const texte = el => (el ? el.textContent : "").replace(/[⁦-⁩ ]/g, " ").replace(/\s+/g, " ").trim();
const visibles = d => [...d.querySelectorAll("#liste .cf")].filter(c => c.dataset.ok === "1");
const affichees = d => [...d.querySelectorAll("#liste .cf")].filter(c => !c.hidden);
const changer = (w, id, v) => { const s = w.document.getElementById(id); s.value = v; s.dispatchEvent(new w.Event("change")); };
const prochaine = (c, jour) => (c.dates_limites || []).filter(x => (x.type === "article" || x.type === "resume") && x.date >= jour).map(x => x.date).sort()[0] || "";

// ---- 1. Accueil ----------------------------------------------------------------------------
{ const wl = await page("index.html", `lang=fr&jour=${JOUR}`, { leger: true }), dl = wl.document, l = dl.getElementById("liste");
  check(`accueil léger : 30 conférences au plus dans la page, le reste dans liste.json, vrai total affiché (${avenir.length})`,
    !!l.dataset.reste && dl.querySelectorAll("#liste .cf").length <= 30 && texte(dl.getElementById("compte")).startsWith(String(avenir.length))
    && JSON.parse(lire("liste.json")).total === avenir.length && !dl.getElementById("plus").hidden);
  changer(wl, "f-mode", [...dl.getElementById("f-mode").options].map(o => o.value).find(Boolean) || "");
  await new Promise(r => setTimeout(r, 80));
  check("accueil léger : un filtre charge toute la liste", dl.querySelectorAll("#liste .cf").length === avenir.length); }
let w = await page("index.html", `lang=fr&jour=${JOUR}`);
let d = w.document;
let cartes = visibles(d);
check(`accueil : ${avenir.length} cartes retenues`, cartes.length === avenir.length);
check("accueil : 15 cartes affichées d'abord", affichees(d).length === 15);
check("bouton « Afficher plus » avec le nombre restant", !d.getElementById("plus").hidden && texte(d.getElementById("plus")).includes(String(avenir.length - 15)));
d.getElementById("plus").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
check("« Afficher plus » montre 15 cartes de plus", affichees(d).length === 30);
check("tri par défaut : date limite la plus proche d'abord (sans date limite ouverte à la fin)", (() => {
  const l = cartes.map(c => c.dataset.prochaine || "9999"); return l.every((x, k) => !k || l[k - 1] <= x); })());
check("chaque carte : lien officiel https (nouvel onglet, noopener) = lien des données, et fiche existante",
  cartes.every(c => { const a = c.querySelector("a.officiel"), f = c.querySelector("a.fiche");
    return a && PAR_ID[c.id] && a.href === new URL(PAR_ID[c.id].lien).href && a.target === "_blank" && a.rel.includes("noopener") &&
      f && existsSync(join(root, f.getAttribute("href"), "index.html")); }));
check("chaque carte : sigle/titre, lieu, dates, bloc date limite, image du domaine",
  cartes.every(c => texte(c.querySelector("h3")) && texte(c.querySelector(".lieu")) && texte(c.querySelector(".dt")) &&
    c.querySelector(".limite") && c.querySelector(".ic-m use") && d.getElementById(c.querySelector(".ic-m use").getAttribute("href").slice(1))));
check("dates limites : la PROCHAINE date limite (date du visiteur) est montrée, les autres cachées",
  cartes.every(c => { const p = prochaine(PAR_ID[c.id], JOUR); const vis = [...c.querySelectorAll(".dl")].filter(b => !b.hidden);
    return p ? vis.length === 1 && vis[0].dataset.d === p && c.querySelector(".dl-ferme").hidden : vis.length === 0 && !c.querySelector(".dl-ferme").hidden; }));
check("étiquettes J-7 … J-1 / Dernier jour : présentes seulement à 7 jours ou moins",
  cartes.every(c => { const p = prochaine(PAR_ID[c.id], JOUR); const r = c.querySelector(".rappel"); const n = p ? ecart(p, JOUR) : null;
    return n !== null && n <= 7 ? !r.hidden && (n === 0 ? /Dernier jour/.test(r.textContent) : r.textContent === `J-${n}`) : r.hidden; }));
check("date limite à moins de 7 jours en rouge (classe urgent), et seulement alors",
  cartes.every(c => { const p = prochaine(PAR_ID[c.id], JOUR); return c.classList.contains("urgent") === (!!p && ecart(p, JOUR) < 7); }));
check("« Nouveau » jamais affiché le jour de la toute première collecte", brut.premiere_collecte !== JOUR || cartes.every(c => c.querySelector(".nouveau").hidden));
const nSemaine = avenir.filter(c => { const p = prochaine(c, JOUR); return p && ecart(p, JOUR) <= 7; }).length;
check(`« Dates limites cette semaine » : ${Math.min(6, nSemaine)} lignes, chacune vers une carte`, d.getElementById("bientot").hidden === (nSemaine === 0) &&
  d.querySelectorAll("#bientot-liste a").length === Math.min(6, nSemaine) && [...d.querySelectorAll("#bientot-liste a")].every(a => d.getElementById(a.getAttribute("href").slice(1))));
check("résumé : nombre de conférences à venir", +texte(d.querySelector("#r-avenir b")) === avenir.length);
check("résumé : dates limites sous 30 jours", +texte(d.querySelector("#r-limites b")) === avenir.filter(c => { const p = prochaine(c, JOUR); return p && ecart(p, JOUR) <= 30; }).length);
check("accueil : gros bouton doré Alertes Pro en haut, vers abonnement/", d.querySelector(".hero #btn-pro-accueil")?.getAttribute("href") === "abonnement/");
check("en-tête : bouton doré « Alertes Pro » sur la page", d.querySelector("#entete .entete-pro")?.getAttribute("href") === "abonnement/");
// Bouton Partager (demande d'Ahmed pour tous les sites)
{
  const b = d.querySelector("#entete button.partager");
  check("en-tête : bouton rond « Partager » (icône SVG, aria-label)", !!b && !!b.querySelector("svg circle") && /Partager/.test(b.getAttribute("aria-label")));
  const ouverts = [], comptes = [];
  w.open = (u) => ouverts.push(u);
  w.goatcounter = { count: o => comptes.push(o) };
  b.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await new Promise(r => setTimeout(r, 10));
  // partage par lien (demande d'Ahmed) : page vidéo du site (dans la langue de la page) + adresse du site
  const lg = w.document.documentElement.lang, q = lg === "en" ? "" : "?lang=" + lg;
  check("Partager sans menu du téléphone : WhatsApp avec titre, adresse du site et page vidéo (langue de la page), clic compté (partage/…)",
    ouverts.length === 1 && /^https:\/\/wa\.me\/\?text=/.test(ouverts[0]) && decodeURIComponent(ouverts[0]).endsWith(" " + URL_SITE + "video/" + q) && decodeURIComponent(ouverts[0]).includes(URL_SITE + q) &&
    comptes.length === 1 && comptes[0].path.startsWith("partage/") && comptes[0].event === true);
  const partages = [];
  Object.defineProperty(w.navigator, "share", { value: async o => { partages.push(o); }, configurable: true });
  b.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await new Promise(r => setTimeout(r, 10));
  check("Partager avec navigator.share : menu du téléphone (page vidéo + adresse du site, aucun fichier)", partages.length === 1 && partages[0].url === URL_SITE + "video/" + q && partages[0].text.includes(URL_SITE) && !partages[0].files && ouverts.length === 1);
}
check("accueil : « Gratuit, sans inscription » dit dès le premier écran (FR, EN, AR)",
  /Gratuit, sans inscription/.test(texte(d.querySelector('.intro [data-l="fr"]'))) && /Free, no sign-up/.test(texte(d.querySelector('.intro [data-l="en"]'))) && /مجاني/.test(texte(d.querySelector('.intro [data-l="ar"]'))));
check("accueil : alertes gratuites RSS (bouton) sans données personnelles", !!d.querySelector('.btn-rss[href^="flux/"]'));
check("pastille « Mis à jour le … »", /\d\d\/\d\d\/\d{4}/.test(texte(d.querySelector(".maj"))));
check("pas d'avertissement quand les données sont du jour", !d.getElementById("alerte-panne").classList.contains("on"));
const domsPresents = [...new Set(avenir.flatMap(c => c.domaines))];
check(`tuiles des domaines : ${domsPresents.length} domaines, image couleur, nombre, lien vers la page`,
  d.querySelectorAll("#grille-domaines a").length === domsPresents.length && [...d.querySelectorAll("#grille-domaines a")].every(a =>
    a.querySelector(".ic-d svg") && /\d+/.test(texte(a.querySelector("small"))) && existsSync(join(root, a.getAttribute("href"), "index.html"))));
const themes = ["comptabilite", "finance", "finance-islamique"].filter(x => avenir.some(c => c.domaines.includes(x)));
check(`accueil : les thèmes ${themes.join(", ")} sont les premières tuiles, avec leur image en couleur`,
  [...d.querySelectorAll("#grille-domaines a")].slice(0, themes.length).map(a => a.getAttribute("href")).join() === themes.map(x => `domaine/${x}/`).join() &&
  [...d.querySelectorAll("#grille-domaines a")].slice(0, themes.length).every(a => a.querySelector(".ic-d svg rect, .ic-d svg path")));
check("accueil : la comptabilité, la finance et la finance islamique sont citées dès le texte d'introduction (EN, FR, AR)",
  /accounting, finance and Islamic finance/.test(texte(d.querySelector('.intro [data-l="en"]'))) && /finance islamique/.test(texte(d.querySelector('.intro [data-l="fr"]'))) &&
  /التمويل الإسلامي/.test(texte(d.querySelector('.intro [data-l="ar"]'))));
check("aucun lien vide ou javascript:", [...d.querySelectorAll("a")].every(a => a.getAttribute("href") && !/^javascript:/i.test(a.getAttribute("href"))));

// ---- 2. Filtres (jamais un choix qui donne 0) ------------------------------------------------
const options0 = [...d.querySelectorAll(".filtres select option")].filter(o => o.value && o.closest("select").id !== "f-tri" && o.closest("select").id !== "f-limite" && /\(0\)$/.test(o.textContent));
check("filtres : aucun choix à 0 résultat au départ", options0.length === 0);
const dom = domsPresents.sort((a, b) => avenir.filter(c => c.domaines.includes(b)).length - avenir.filter(c => c.domaines.includes(a)).length)[1];
changer(w, "f-dom", dom);
cartes = visibles(d);
check(`filtre domaine « ${dom} » : ${avenir.filter(c => c.domaines.includes(dom)).length} cartes, toutes du domaine`,
  cartes.length === avenir.filter(c => c.domaines.includes(dom)).length && cartes.every(c => c.dataset.dom.split(" ").includes(dom)));
check("filtre domaine : compteur mis à jour", texte(d.getElementById("compte")).startsWith(String(cartes.length)));
const optSpec = [...d.querySelectorAll("#f-spec option")].find(o => o.value && cartes.some(c => c.dataset.spec.split(" ").includes(o.value)));
changer(w, "f-spec", optSpec.value);
const nSpec = avenir.filter(c => c.domaines.includes(dom) && c.specialites.includes(optSpec.value)).length;
check(`filtres domaine + spécialité combinés (${nSpec})`, visibles(d).length === nSpec && nSpec > 0);
check("option de spécialité : son nombre = résultats", optSpec.textContent.includes(`(${nSpec})`));
d.getElementById("effacer").dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
check("bouton « Tout afficher » remet tout", visibles(d).length === avenir.length);
changer(w, "f-cont", "europe");
check("filtre continent (Europe)", visibles(d).length === avenir.filter(c => c.continent === "europe").length && visibles(d).every(c => c.dataset.cont === "europe"));
changer(w, "f-cont", "");
if (d.getElementById("f-mode")) {
  changer(w, "f-mode", "hybride");
  check("filtre format (hybride)", visibles(d).length === avenir.filter(c => c.mode === "hybride").length);
  changer(w, "f-mode", "");
}
changer(w, "f-limite", "30");
check("filtre « date limite dans les 30 jours »", visibles(d).length === avenir.filter(c => { const p = prochaine(c, JOUR); return p && ecart(p, JOUR) <= 30; }).length &&
  visibles(d).every(c => c.dataset.prochaine && +c.dataset.reste <= 30));
changer(w, "f-limite", "ouverte");
check("filtre « date limite encore ouverte »", visibles(d).length === avenir.filter(c => prochaine(c, JOUR)).length);
changer(w, "f-limite", "");
const mois = avenir[0].debut.slice(0, 7);
changer(w, "f-mois", mois);
check(`filtre mois de l'événement (${mois})`, visibles(d).length === avenir.filter(c => c.debut.slice(0, 7) === mois).length);
changer(w, "f-mois", "");
changer(w, "f-tri", "debut");
const debs = visibles(d).map(c => c.dataset.debut);
check("tri par date de l'événement", debs.every((x, k) => !k || debs[k - 1] <= x));
changer(w, "f-tri", "limite");
const fq = d.getElementById("f-q");
const cible = avenir.find(c => c.ville && c.pays === "JP") || avenir.find(c => c.ville);
fq.value = cible.ville.toLowerCase(); fq.dispatchEvent(new w.Event("input"));
check(`recherche par ville (« ${cible.ville} »), sans souci de majuscules`, visibles(d).length >= 1 && visibles(d).some(c => c.id === cible.id));
fq.value = "Japon"; fq.dispatchEvent(new w.Event("input"));
const nJp = visibles(d).length;
fq.value = "japan"; fq.dispatchEvent(new w.Event("input"));
check("recherche du pays dans les trois langues (Japon = Japan)", nJp === visibles(d).length && nJp === avenir.filter(c => c.pays === "JP").length);
fq.value = ""; fq.dispatchEvent(new w.Event("input"));
w = await page("index.html", `lang=fr&jour=${JOUR}&domaine=${dom}&limite=90`);
check("filtres dans l'adresse (?domaine=…&limite=90)", visibles(w.document).length === avenir.filter(c => { const p = prochaine(c, JOUR); return c.domaines.includes(dom) && p && ecart(p, JOUR) <= 90; }).length);

// ---- Recherche « au son » (règle commune § 27, 18/10/2026, demande d'Ahmed) : deux écritures d'un même nom = même résultat
{ const w2 = await page("index.html", `lang=fr&jour=${JOUR}`), d2 = w2.document, fq = d2.getElementById("f-q"), S = w2.sonRecherche;
  const chercher = t => { fq.value = t; fq.dispatchEvent(new w2.Event("input")); return visibles(d2).map(c => c.id); };
  const commun = join(root, "..", "projets-ahmed", "outils communs", "recherche-au-son", "son.js");
  check("recherche au son : assets/son.js chargé avant app.js (copie identique de l'outil commun quand il est présent)", !!S &&
    (!existsSync(commun) || readFileSync(commun, "utf8") === lire("assets/son.js")));
  const paires = [["Djerba", "Jerba"], ["Kairouan", "Qairouan"], ["Hammamet", "Hamamet"], ["Houmt Souk", "Houmet Essouk"]];
  check("recherche au son : Djerba = Jerba, Kairouan = Qairouan, Hammamet = Hamamet, Houmt Souk = Houmet Essouk (même résultat)",
    paires.every(([a, b]) => chercher(a).join() === chercher(b).join()) &&
    paires.every(([a, b]) => S.trouve(S.cle("Commune de " + a), b) && S.trouve(S.cle("Commune de " + b), a)));
  // une paire tirée des VRAIES cartes : un mot d'un titre écrit avec une consonne doublée (« travaux » -> « travvaux »)
  const mots = [...d2.querySelectorAll("#liste .cf")].flatMap(c => ((c._q || c.textContent.toLowerCase()).match(/\b[a-z]{6,}\b/g) || []).map(m => [m, c.id]));
  const [mot, id] = mots.find(([m]) => /(?<=[a-z])[aeiou][bcdfglmnprstv][aeiou]/.test(m)) || ["", ""];
  const double = mot.replace(/(?<=[a-z])([aeiou])([bcdfglmnprstv])(?=[aeiou])/, "$1$2$2");
  const triple = mot.replace(/(?<=[a-z])([aeiou])([bcdfglmnprstv])(?=[aeiou])/, "$1$2$2$2");   // lettre triplée (« demisssion ») ; jamais au début du mot : « ettudes » y serait lu comme l'article (« Ettadhamen » = « Tadhamen »)
  const r1 = chercher(mot), r2 = chercher(double);
  check(`recherche au son : « ${mot} » écrit « ${double} » ou « ${triple} » trouve les mêmes cartes ; « demisssion » = « Démission »`, !!mot && r2.includes(id) && r2.length > 0 && r2.every(x => r1.includes(x))
    && chercher(triple).join() === r2.join() && S.trouve(S.cle("Démission"), "demisssion"));
  check("recherche au son : une recherche absurde (« zzzzqqq ») ne trouve toujours rien", chercher("zzzzqqq").length === 0);
  chercher(""); }

// ---- 3. Date du VISITEUR : fin, date limite passée, avertissement ---------------------------
const premiere = avenir.slice().sort((a, b) => a.fin.localeCompare(b.fin))[0];
w = await page("index.html", `lang=fr&jour=${plus(premiere.fin, 1)}`);
d = w.document;
check("une conférence terminée (date du visiteur) disparaît", d.getElementById(premiere.id).hidden && d.getElementById(premiere.id).dataset.ok === "");
// l'avertissement se compte depuis la DERNIÈRE LECTURE RÉUSSIE (data-maj), pas depuis la fin d'une conférence
// (07/10/2026 : une conférence finissait le jour même → jour simulé à 1 jour des données → faux échec qui bloquait le robot)
const MAJ = String(etat.derniere_lecture_reussie || JOUR).slice(0, 10);
w = await page("index.html", `lang=fr&jour=${plus(MAJ, 2)}`);
check("données de plus de 2 jours : avertissement daté visible", w.document.getElementById("alerte-panne").classList.contains("on") && /depuis le \d\d\/\d\d\/\d{4}/.test(texte(w.document.getElementById("alerte-panne"))));
const avecDeux = avenir.find(c => c.dates_limites.filter(x => (x.type === "article" || x.type === "resume") && x.date >= JOUR).length >= 2);
if (avecDeux) {
  const ds = avecDeux.dates_limites.filter(x => (x.type === "article" || x.type === "resume") && x.date >= JOUR).map(x => x.date).sort();
  w = await page("index.html", `lang=fr&jour=${plus(ds[0], 1)}`);
  const c = w.document.getElementById(avecDeux.id);
  check(`date limite passée (${ds[0]}) : la suivante (${ds[1]}) est montrée`, c.dataset.prochaine === ds[1] && [...c.querySelectorAll(".dl")].filter(b => !b.hidden).map(b => b.dataset.d).join() === ds[1]);
}
w = await page("index.html", `lang=fr&jour=${plus(MAJ, 1)}`);
check("données d'hier : pas encore d'avertissement", etat.bandeau_visible || !w.document.getElementById("alerte-panne").classList.contains("on"));
const derniere = avenir.map(c => c.fin).sort().pop();
w = await page("index.html", `lang=fr&jour=${plus(derniere, 1)}`);
check("tout terminé : aucune carte, message « aucune conférence », site non vide (domaines, sources)",
  visibles(w.document).length === 0 && !w.document.getElementById("vide").hidden && w.document.querySelectorAll("#grille-domaines a").length > 0);

// ---- 4. Trois langues -------------------------------------------------------------------------
const TEXTES = (() => { const ctx = {}; new Function("window", lire("assets/textes.js"))(ctx); return ctx.TEXTES; })();
for (const [lang, idx, dir, entete] of [["fr", 0, "ltr", /Radar des conférences/], ["en", 1, "ltr", /Conference Radar/], ["ar", 2, "rtl", /رادار المؤتمرات/]]) {
  w = await page("index.html", `lang=${lang}&jour=${JOUR}`);
  d = w.document;
  check(`${lang} : lang=${lang}, dir=${dir}, en-tête et pied traduits`, d.documentElement.lang === lang && d.documentElement.dir === dir &&
    entete.test(texte(d.getElementById("entete"))) && /©/.test(texte(d.getElementById("pied"))));
  const pts = [...d.querySelectorAll("[data-t]")];
  check(`${lang} : tous les petits textes des cartes traduits (${pts.length})`, pts.length > 0 && pts.every(el => TEXTES[el.dataset.t] && el.textContent === TEXTES[el.dataset.t][idx]));
  check(`${lang} : options des filtres traduites`, [...d.querySelectorAll("#f-limite option")].every(o => o.textContent === o.dataset[lang]));
  const dt0 = d.querySelector("#liste .cf .dt");
  const moisAttendu = { fr: /janv\.|févr\.|mars|avr\.|mai|juin|juil\.|août|sept\.|oct\.|nov\.|déc\./, en: /Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec/, ar: /يناير|فبراير|مارس|أبريل|مايو|يونيو|يوليو|أغسطس|سبتمبر|أكتوبر|نوفمبر|ديسمبر/ }[lang];
  check(`${lang} : dates écrites dans la langue (${texte(dt0)})`, moisAttendu.test(dt0.textContent) && (lang !== "ar" || /⁦\d/.test(dt0.textContent)));
}
check("textes.js : chaque clé a ses trois langues (arabe en écriture arabe)", Object.values(TEXTES).every(v => v.length === 3 && v.every(Boolean) && /[؀-ۿ]/.test(v[2])));

// ---- 5. Toutes les pages : SEO, sources, ©, cache, sécurité --------------------------------------
const sitemap = lire("sitemap.xml");
const urls = [...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1]);
const nFiches = urls.filter(u => /\/conference\//.test(u)).length;
const maigre = c => !((c.dates_limites || []).length || c.date_limite || c.rang || c.verifie_le);   // plan Google B.1 (25/11/2026)
// VIS.3 (27/11/2026) : plan RÉDUIT — aucune fiche de conférence (elles restent en ligne, ouvertes à Google, sans noindex), pages
// principales + catégories + DERNIER rapport du mois, au plus 160 adresses
const fichesEnLigne = avenir.filter(c => !maigre(c)).length;
const rapportsMois = urls.filter(u => /\/rapports\/\d{4}-\d{2}\/$/.test(u));
check(`sitemap RÉDUIT (VIS.3) : ${urls.length} adresses, aucune fiche de conférence (${fichesEnLigne} fiches en ligne hors du plan), un seul rapport du mois, accueil et catégories présents`,
  nFiches === 0 && fichesEnLigne > 0 && urls.length >= 40 && urls.length <= 160 && rapportsMois.length === 1 && urls.includes(URL_SITE) && urls.includes(URL_SITE + "abonnement/")
  && ["domaine/", "specialite/", "continent/", "pays/", "mois/"].every(k => urls.some(u => u.includes("/" + k))));
// 25/11/2026 (PASS.1, module commun du parcours d'achat) : assets/pass-commun.js = COPIE EXACTE du module de projets-ahmed
// (« outils communs/pass-commun/pass-commun.js », recopié par synchroniser.py) ; assets/pass-reglages.js = ce qui est propre au site.
const PASS_JS = lire("assets/pass-commun.js") + "\n" + lire("assets/pass-reglages.js");
check("abonnement : module commun du Pass (pass-commun.js) puis réglage du site (pass-reglages.js), seulement sur cette page, ancien abonnement.js retiré",
  /<script src="\.\.\/assets\/pass-commun\.js\?v=[^"]+"><\/script>\s*<script src="\.\.\/assets\/pass-reglages\.js\?v=/.test(lire("abonnement/index.html"))
  && !/pass-commun\.js|pass-reglages\.js|abonnement\.js/.test(lire("index.html")) && !existsSync(join(root, "assets/abonnement.js")) && !/abonnement\.js/.test(lire("abonnement/index.html")));
{ // la copie du module n'est jamais modifiée dans le site : empreinte écrite par synchroniser.py ; projets-ahmed à côté (PC, cloud) = copie identique au module ; absent (GitHub) = contrôle sauté
  const copie = readFileSync(join(root, "assets/pass-commun.js")), emp = createHash("sha256").update(copie).digest("hex");
  const attendue = existsSync(join(root, "assets/pass-commun.empreinte")) ? lire("assets/pass-commun.empreinte").trim() : "";
  check("module commun du Pass : assets/pass-commun.js NON modifié dans le site (empreinte écrite par synchroniser.py)", emp === attendue);
  const original = [process.env.PROJETS_AHMED, join(root, "..", "projets-ahmed"), join(root, "..", "..", "projets-ahmed"), join(root, "..", "..")]   // dépôts VOISINS seulement (un vieux clone ailleurs ne compte pas)
    .filter(Boolean).map(x => join(x, "outils communs", "pass-commun", "pass-commun.js")).find(x => existsSync(x));
  if (original) check("module commun du Pass : copie identique au module de projets-ahmed (sinon : python3 synchroniser.py)", readFileSync(original).equals(copie));
  else console.log("SAUTÉ copie du module commun : projets-ahmed absent (normal sur GitHub)"); }
const v = createHash("sha1").update(Buffer.concat(["style.css", "textes.js", "page.js", "son.js", "app.js", "avis.js", "pass-commun.js", "pass-reglages.js"].map(f =>
  Buffer.from(readFileSync(join(root, "assets", f), "latin1").replace(/\r\n/g, "\n"), "latin1")))).digest("hex").slice(0, 8);
let ok = { en: true, seo: true, v: true, h1: true, fichiers: true, copy: true, trad: true, src: true, meta: true, gc: true, ios: true, ext: true };
for (const u of urls) {
  const chemin = u.replace(URL_SITE, "") + "index.html";
  if (!existsSync(join(root, chemin))) { ok.fichiers = false; console.log("   page manquante : " + chemin); continue; }
  const h = lire(chemin);
  if (!(/<title>[^<]{20,}<\/title>/.test(h) && /<meta name="description" content="[^"]{50,}"/.test(h) && h.includes(`<link rel="canonical" href="${u}">`) &&
      (/^rapports\/\d{4}-\d{2}\//.test(chemin) ? h.includes(`property="og:image" content="${u}apercu-`) : h.includes(`property="og:image" content="${URL_SITE}${chemin === "video/index.html" ? "assets/video/apercu-video.jpg" : "assets/og-image-v1.jpg"}"`)) && h.includes('<meta property="og:image:type" content="image/jpeg">') && /name="viewport"/.test(h))) {
    ok.seo = false; console.log("   SEO incomplet : " + chemin); }
  if (!(h.match(/\?v=([0-9a-f]+)/g) || []).every(x => x === "?v=" + v) || !/\?v=/.test(h)) { ok.v = false; console.log("   ?v= périmé : " + chemin); }
  if (!/<h1>(<span data-l="fr">[^<]+<\/span><span data-l="en">[^<]+<\/span><span data-l="ar">.+?<\/span>)<\/h1>/.test(h) && !(chemin === "video/index.html" && /<h1 data-ven="[^"]+" data-vfr="[^"]+" data-var="[^"]+">/.test(h))) { ok.h1 = false; console.log("   h1 FR+EN+AR : " + chemin); }
  if (!/INSPIRE-HEP/.test(h) || !/MIT/.test(h)) ok.src = false;
  // page vidéo : textes traduits par attributs data-vfr / data-ven / data-var (tools/page_video.mjs)
  const nFr = (h.match(/data-l="fr"|data-vfr=/g) || []).length, nEn = (h.match(/data-l="en"|data-ven=/g) || []).length, nAr = (h.match(/data-l="ar"|data-var=/g) || []).length;
  if (!nFr || nFr !== nEn || nEn !== nAr) { ok.en = false; console.log(`   langues incomplètes (${nFr} fr / ${nEn} en / ${nAr} ar) : ${chemin}`); }
  if (!/©/.test(h)) ok.copy = false;
  if (!/<html [^>]*translate="no"/.test(h) || !h.includes('<meta name="google" content="notranslate">')) ok.trad = false;
  const csp = (h.match(/http-equiv="Content-Security-Policy" content="([^"]+)"/) || [])[1] || "";
  if (!/<meta name="robots" content="noai, noimageai">/.test(h) || !/<meta name="referrer" content="strict-origin-when-cross-origin">/.test(h) ||
      !/script-src 'self' https:\/\/gc\.zgo\.at;/.test(csp) || !/object-src 'none'/.test(csp) || !/frame-src 'none'/.test(csp) || /unsafe-eval/.test(csp) || /script-src[^;]*unsafe-inline/.test(csp)) {
    ok.meta = false; console.log("   sécurité (noai, referrer, CSP) : " + chemin); }
  if (!h.includes('<script data-goatcounter="https://prix-eaux-tunisie.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>') ||
      !/connect-src[^;]*https:\/\/prix-eaux-tunisie\.goatcounter\.com/.test(csp)) ok.gc = false;
  if (!/<meta name="apple-mobile-web-app-capable" content="yes">/.test(h) || !/<link rel="manifest"/.test(h)) ok.ios = false;
  if ([...h.matchAll(/<a [^>]*href="https?:\/\/[^"]+"[^>]*>/g)].some(m => !/rel="[^"]*noopener/.test(m[0]))) { ok.ext = false; console.log("   lien externe sans noopener : " + chemin); }
}
check("toutes les pages du sitemap existent", ok.fichiers);
check("toutes les pages : titre, description, canonical, og:image JPEG, viewport", ok.seo);
check(`toutes les pages : ?v=${v} (empreinte des fichiers, change à chaque modification)`, ok.v);
check("toutes les pages : titre h1 en français, anglais ET arabe", ok.h1);
check("version ANGLAISE complète : sur chaque page, chaque texte français a son texte anglais (et arabe)", ok.en);
check("toutes les pages : sources citées (listes MIT + INSPIRE-HEP CC0) et © même sans JavaScript", ok.src && ok.copy);
check("toutes les pages : pas de traduction automatique (translate=no + notranslate)", ok.trad);
check("toutes les pages : meta noai, referrer, CSP stricte (aucun script en ligne permis, aucun cadre)", ok.meta);
check("toutes les pages : statistiques GoatCounter (compteur prix-eaux-tunisie, sans cookies) + CSP compatible", ok.gc);
check("toutes les pages : installation téléphone (meta iPhone + manifeste)", ok.ios);
check("toutes les pages : liens externes avec rel=noopener", ok.ext);
try {
  const ld = JSON.parse(lire("index.html").match(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/)[1]);
  check("accueil : FAQ JSON-LD valide (4 questions)", ld["@type"] === "FAQPage" && ld.mainEntity.length >= 4);
} catch (e) { check("accueil : FAQ JSON-LD valide", false); }

// ---- 6. Fiches : JSON-LD Event, source + licence, lien officiel ------------------------------
let okFiche = true, okLd = true;
for (const c of avenir) {
  const h = lire(`conference/${c.id}/index.html`);
  let ld = null;
  try { ld = JSON.parse(h.match(/<script type="application\/ld\+json">\n([\s\S]*?)\n<\/script>/)[1]); } catch (e) { ld = null; }
  if (!ld || ld["@type"] !== "Event" || ld.startDate !== c.debut || ld.endDate !== c.fin || ld.url !== c.lien || !ld.name || !ld.location || !ld.eventAttendanceMode) { okLd = false; console.log("   JSON-LD : " + c.id); }
  if (!h.includes(`href="${c.lien.replace(/&/g, "&amp;")}"`) || !/(MIT|CC0|organisateur)/.test(h.split("<main")[1] || "")) { okFiche = false; console.log("   fiche : " + c.id); }
}
check(`fiches : JSON-LD Event valide (nom, dates, lieu, format, lien officiel) pour les ${avenir.length} conférences`, okLd);
check("fiches : lien officiel + source et licence affichés", okFiche);
const exF = avenir.find(c => c.dates_limites.length >= 2) || avenir[0];
w = await page(`conference/${exF.id}/index.html`, `lang=en&jour=${JOUR}`);
check(`fiche ${exF.id} : liste des dates limites, passées barrées (date du visiteur)`,
  w.document.querySelectorAll(".limites li").length === exF.dates_limites.length &&
  [...w.document.querySelectorAll(".limites li")].every(li => li.classList.contains("passe") === (li.dataset.d < JOUR)));
const exO = avenir.find(c => c.sources[0] === "officiel" && c.domaines.includes("finance-islamique")) || avenir.find(c => c.sources[0] === "officiel");
if (exO) {
  w = await page(`conference/${exO.id}/index.html`, `lang=en&jour=${JOUR}`);
  check(`fiche ${exO.id} (sélection officielle) : « Checked on the official page on … » + lien de la page vérifiée`,
    /Checked on the official page on \d/.test(texte(w.document.querySelector(".fiche-dl"))) && [...w.document.querySelectorAll(".fiche-dl a")].some(a => a.href === new URL(exO.page_verifiee).href));
}
w = await page(`conference/${exF.id}/index.html`, `lang=en&jour=${JOUR}`);
check("fiche : bouton Alertes Pro (spécialité de la fiche déjà cochée, clic compté « abonnement-fiche ») et alerte RSS gratuite du domaine",
  !!w.document.querySelector('a.btn-pro[href^="../../abonnement/?specialite="][href$="#inscription"][data-clic="abonnement-fiche"]') && !!w.document.querySelector(".btn-rss"));

// ---- 7. Pages de domaine, spécialité, continent, pays, mois ------------------------------------
let okListes = true;
for (const u of urls.filter(x => /\/(domaine|specialite|continent|pays|mois)\//.test(x))) {
  const chemin = u.replace(URL_SITE, "") + "index.html";
  const [, type, slug] = chemin.match(/^(domaine|specialite|continent|pays|mois)\/([^/]+)\//);
  const attendu = avenir.filter(c => type === "domaine" ? c.domaines.includes(slug) : type === "specialite" ? c.specialites.includes(slug) :
    type === "continent" ? c.continent === slug : type === "pays" ? c.pays === slug.toUpperCase() && c.mode !== "en-ligne" : c.debut.slice(0, 7) === slug).length;
  const reste = chemin.replace("index.html", "liste.json");          // accueil léger (19/11/2026) : page + reste de la liste
  const h = lire(chemin) + (existsSync(join(root, reste)) ? JSON.parse(lire(reste)).html : "");
  const n = (h.match(/<article class="cf/g) || []).length;
  if (n !== attendu || n === 0) { okListes = false; console.log(`   ${chemin} : ${n} cartes au lieu de ${attendu}`); }
}
check("pages domaine / spécialité / continent / pays / mois : les bonnes conférences, jamais une page vide", okListes);
if (existsSync(join(root, "domaine/finance-islamique/index.html"))) {
  w = await page("domaine/finance-islamique/index.html", `lang=en&jour=${JOUR}`);
  check("page Islamic finance : titre anglais, spécialités dédiées listées", /Islamic finance/.test(texte(w.document.querySelector("h1"))) && w.document.querySelectorAll("#grille-specs a").length >= 1);
}
w = await page("domaine/physique/index.html", `lang=fr&jour=${JOUR}`);
check("page domaine : pas de filtre domaine, spécialités du domaine seulement, filtre spécialité qui marche", !w.document.getElementById("f-dom") &&
  [...w.document.querySelectorAll("#grille-specs a")].every(a => /specialite\//.test(a.getAttribute("href"))) && (() => {
    const o = [...w.document.querySelectorAll("#f-spec option")].find(x => x.value); changer(w, "f-spec", o.value);
    return visibles(w.document).every(c => c.dataset.spec.split(" ").includes(o.value)) && visibles(w.document).length > 0; })());

// ---- 7 bis. Encadrés vers les Alertes Pro + clics comptés (28/11/2026, règle commune § 71) ------------------------------------
// Chaque page spécialité / domaine / continent / pays / mois a un encadré lié à son contenu (FR, EN, AR) : nombre = celui de la liste de la page,
// bouton vers abonnement/ avec la spécialité ou le domaine déjà coché, offre VRAIE (selon ABO["gratuit"]), jamais une nouvelle gratuité.
{ const GRAT = /"gratuit": True/.test(readFileSync(join(root, "robot/construire_site.py"), "utf8"));
  const OFFRE = GRAT ? ["Alertes Pro sur Telegram : gratuites pour le moment.", "Pro Alerts on Telegram: free for now.", "تنبيهات Pro على تيليغرام: مجانية حاليًا."]
    : [/^Alertes Pro sur Telegram : \d+ DT \/ mois ou \d+ DT \/ an\.$/, /^Pro Alerts on Telegram: \d+ TND \/ month or \d+ TND \/ year\.$/, /^تنبيهات Pro على تيليغرام: \d+ دينار \/ شهر أو \d+ دينار \/ سنة\.$/];
  const sorte = { domaine: 0, specialite: 0, continent: 0, pays: 0, mois: 0 }, fautes = [];
  for (const type of Object.keys(sorte)) for (const slug of readdirSync(join(root, type))) {
    const chemin = `${type}/${slug}/index.html`;
    if (!existsSync(join(root, chemin))) continue;
    const doc = new JSDOM(lire(chemin)).window.document, enc = doc.getElementById("encadre-pro"), faute = m => fautes.push(`${chemin} : ${m}`);
    if (!enc) { faute("pas d'encadré"); continue; }
    sorte[type]++;
    const attendu = avenir.filter(c => type === "domaine" ? c.domaines.includes(slug) : type === "specialite" ? c.specialites.includes(slug) :
      type === "continent" ? c.continent === slug : type === "pays" ? c.pays === slug.toUpperCase() && c.mode !== "en-ligne" : c.debut.slice(0, 7) === slug).length;
    const reste = chemin.replace("index.html", "liste.json");
    const cartesPage = ((lire(chemin) + (existsSync(join(root, reste)) ? JSON.parse(lire(reste)).html : "")).match(/<article class="cf/g) || []).length;
    const tx = ["fr", "en", "ar"].map(l => texte(enc.querySelector(`.encadre-texte [data-l="${l}"]`))), px = ["fr", "en", "ar"].map(l => texte(enc.querySelector(`.encadre-prix [data-l="${l}"]`)));
    if (+enc.dataset.n !== attendu || +enc.dataset.n !== cartesPage) faute(`nombre ${enc.dataset.n} au lieu de ${cartesPage} (liste de la page)`);
    if (!tx[0].startsWith(`${attendu} conférence`) || !tx[1].startsWith(`${attendu} upcoming conference`) || !tx[2].startsWith(`${attendu} مؤتمر`)) faute(`nombre du texte ≠ ${attendu} : ${tx[0].slice(0, 40)}`);
    if (!/Telegram/.test(tx[0] + tx[1]) || !/تيليغرام/.test(tx[2])) faute("texte sans Telegram");
    if (/gratuit|free|مجان/i.test(tx.join(" "))) faute("le texte de l'encadré promet une gratuité");
    if (!px.every((x, k) => typeof OFFRE[k] === "string" ? x === OFFRE[k] : OFFRE[k].test(x))) faute("offre fausse : " + px[0]);
    const a = enc.querySelector("a#encadre-btn"), href = a && a.getAttribute("href");
    const voulu = type === "specialite" ? `../../abonnement/?specialite=${slug}#inscription` : type === "domaine" ? `../../abonnement/?domaine=${slug}#inscription` : "../../abonnement/#inscription";
    if (!a || href !== voulu || a.getAttribute("data-clic") !== "abonnement-" + type || !/btn-pro/.test(a.className)) faute(`bouton faux (${href}, ${a && a.getAttribute("data-clic")})`);
    if (["fr", "en", "ar"].some(l => !texte(a && a.querySelector(`[data-l="${l}"]`)))) faute("bouton sans texte dans une langue");
  }
  if (fautes.length) console.log("   " + fautes.slice(0, 8).join("\n   "));
  check(`encadrés Alertes Pro (§ 71) sur CHAQUE page spécialité (${sorte.specialite}), domaine (${sorte.domaine}), continent (${sorte.continent}), pays (${sorte.pays}), mois (${sorte.mois}) en FR, EN, AR : nombre = liste de la page, bouton vers abonnement/ avec le choix déjà coché, offre vraie, aucune gratuité ajoutée`,
    fautes.length === 0 && Object.values(sorte).every(n => n > 0));
  // chaque lien vers abonnement/ (hors des pages abonnement/) est compté : data-clic="abonnement-…" (pages construites + en-tête / pied de page.js)
  const NOMS = /^abonnement-(specialite|domaine|pays|continent|mois|accueil|entete|pied|fiche|flux|apropos)$/, sansClic = [];
  const fouillerAbo = dd => { for (const n of readdirSync(join(root, dd), { withFileTypes: true })) {
    const f = join(dd, n.name);
    if (n.isDirectory() && !/^(node_modules|\.git|assets|donnees|captures|abonnement|tools|robot)$/.test(n.name)) fouillerAbo(f);
    else if (n.name === "index.html") for (const m of lire(f).matchAll(/<a\b[^>]*href="(?:\.\.\/)*abonnement\/[^"]*"[^>]*>/g)) {
      const c = (m[0].match(/data-clic="([^"]*)"/) || [])[1]; if (!c || !NOMS.test(c)) sansClic.push(f + " : " + m[0].slice(0, 90)); } } };
  fouillerAbo(".");
  const pj = lire("assets/page.js"), liensJs = [...pj.matchAll(/<a\b[^>]*href="\$\{racine\}abonnement\/"[^>]*>/g)].map(m => m[0]);
  if (sansClic.length) console.log("   " + sansClic.slice(0, 6).join("\n   "));
  check("chaque lien vers abonnement/ a son data-clic (pages construites, bouton doré de l'en-tête « abonnement-entete », pied de page « abonnement-pied »)",
    sansClic.length === 0 && liensJs.length === 2 && liensJs.some(x => /class="entete-pro"[^>]*data-clic="abonnement-entete"/.test(x)) && liensJs.some(x => /data-clic="abonnement-pied"/.test(x)));
  // clic compté avec un FAUX goatcounter (jamais le vrai compteur), rien sans goatcounter
  const wc = await page("specialite/banque-islamique/index.html", `lang=fr&jour=${JOUR}`, { leger: true }), dc = wc.document, vus = [];
  wc.addEventListener("click", e => e.preventDefault());           // jsdom ne navigue pas
  wc.goatcounter.count = o => vus.push(o);
  dc.getElementById("encadre-btn").dispatchEvent(new wc.MouseEvent("click", { bubbles: true, cancelable: true }));
  dc.querySelector("#entete a.entete-pro").dispatchEvent(new wc.MouseEvent("click", { bubbles: true, cancelable: true }));
  dc.querySelector('#pied a[data-clic="abonnement-pied"]').dispatchEvent(new wc.MouseEvent("click", { bubbles: true, cancelable: true }));
  dc.querySelector("h1").dispatchEvent(new wc.MouseEvent("click", { bubbles: true, cancelable: true }));      // clic ailleurs : rien
  check("clic compté (faux goatcounter) : événements /conferences-alertes/clic/abonnement-specialite, …-entete, …-pied (event: true) ; un clic ailleurs ne compte rien",
    vus.map(o => o.path).join() === "/conferences-alertes/clic/abonnement-specialite,/conferences-alertes/clic/abonnement-entete,/conferences-alertes/clic/abonnement-pied" && vus.every(o => o.event === true && o.title));
  let erreurJs = null; wc.addEventListener("error", e => { erreurJs = e; });
  delete wc.goatcounter.count; dc.getElementById("encadre-btn").dispatchEvent(new wc.MouseEvent("click", { bubbles: true, cancelable: true }));
  delete wc.goatcounter; dc.getElementById("encadre-btn").dispatchEvent(new wc.MouseEvent("click", { bubbles: true, cancelable: true }));
  check("sans GoatCounter (absent ou bloqué) : aucun comptage, aucune erreur, le lien reste un vrai lien", vus.length === 3 && !erreurJs && /^\.\.\/\.\.\/abonnement\//.test(dc.getElementById("encadre-btn").getAttribute("href")));
  // abonnement/ : les choix de la page précédente sont DÉJÀ COCHÉS (assets/pass-reglages.js, crochet brancher du module commun) ; valeur inconnue ignorée
  const coches = ww => [...ww.document.querySelectorAll('#abo-form input[name="specialites"]')].filter(x => x.checked).map(x => x.value);
  const repris = ww => !ww.document.getElementById("abo-repris").hidden;
  const toutes = [...new JSDOM(lire("abonnement/index.html")).window.document.querySelectorAll('input[name="specialites"]')];
  const spec1 = toutes[0].value, dom1 = "finance-islamique", deDom = toutes.filter(x => x.getAttribute("data-domaine") === dom1).map(x => x.value);
  let wa = await page("abonnement/index.html", `lang=fr&specialite=${spec1}`);
  check(`abonnement/?specialite=${spec1} : seule cette spécialité est cochée, phrase « Vos choix de la page précédente sont déjà cochés » affichée`,
    coches(wa).join() === spec1 && repris(wa) && /Vos choix de la page précédente sont déjà cochés/.test(texte(wa.document.getElementById("abo-repris"))));
  wa = await page("abonnement/index.html", `lang=en&domaine=${dom1}`);
  check(`abonnement/?domaine=${dom1} : toutes ses spécialités (${deDom.length}) cochées, aucune autre (EN : « already ticked »)`,
    deDom.length > 0 && coches(wa).sort().join() === deDom.sort().join() && repris(wa) && /already ticked/.test(wa.document.getElementById("abo-repris").textContent));
  wa = await page("abonnement/index.html", `lang=fr&specialite=zzz-inconnue,${spec1}`);
  const wb = await page("abonnement/index.html", "lang=fr&specialite=zzz-inconnue&domaine=pas-un-domaine"), wn = await page("abonnement/index.html", "lang=fr");
  check("valeur inconnue ignorée (rien coché, pas de phrase, pas d'erreur) ; mélange connu + inconnu : seule la connue est cochée ; sans paramètre : rien coché",
    coches(wa).join() === spec1 && coches(wb).length === 0 && !repris(wb) && coches(wn).length === 0 && !repris(wn));
}

// ---- 8. Flux RSS (Atom) gratuits ------------------------------------------------------------------
const flux = readdirSync(join(root, "flux")).filter(f => f.endsWith(".xml"));
let okFlux = true;
for (const f of flux) {
  const x = new JSDOM(lire("flux/" + f), { contentType: "application/xml" }).window.document;
  const entrees = [...x.querySelectorAll("entry")];
  if (x.querySelector("parsererror") || !entrees.length || !entrees.every(e => { const id = e.querySelector("id").textContent.replace(URL_SITE + "conference/", "").replace("/", ""); return PAR_ID[id]; })) {
    okFlux = false; console.log("   flux : " + f); }
}
check(`flux Atom : ${flux.length} flux XML valides (tout + domaines + spécialités), chaque entrée = une conférence à venir`, okFlux && flux.includes("tout.xml") && domsPresents.every(dm => flux.includes(dm + ".xml")));
check("page flux/ : un lien par flux", lire("flux/index.html").match(/href="[^"]+\.xml"/g).length >= flux.length);

// ---- 9. Images, icônes, aperçu ---------------------------------------------------------------------
const photos = readdirSync(join(root, "assets/photos")).filter(f => /\.(jpe?g|webp|png)$/i.test(f));
check("vraies photos : 2 fichiers ≤ 150 Ko", photos.length === 2 && photos.every(f => statSync(join(root, "assets/photos", f)).size <= 150000));
w = await page("index.html", `lang=fr&jour=${JOUR}`);
const credit = w.document.querySelector(".hero .credit-photo");
check("photo du bandeau : crédit de CHAQUE photo (auteur, licence CC, page Wikimedia)", !!credit && /Piotrus/.test(texte(credit)) && /Copyleft/.test(texte(credit)) &&
  (texte(credit).match(/CC BY/g) || []).length === 2 && [...credit.querySelectorAll("a")].filter(a => /commons\.wikimedia\.org\/wiki\/File:/.test(a.href)).length === 2);
check("À propos : crédits des photos", (lire("a-propos/index.html").match(/commons\.wikimedia\.org\/wiki\/File:/g) || []).length >= 2);
const css = lire("assets/style.css").replace(/\s+/g, "");
check("bandeau : photo sous un dégradé (téléphone : carrée, ordinateur : large)", /hero-photo\{background:linear-gradient\([^;]*url\(photos\/conferences-mosaique-carre\.jpg\)/.test(css) &&
  /url\(photos\/conferences-mosaique\.jpg\)/.test(css));
const og = readFileSync(join(root, "assets/og-image-v1.jpg"));
const tailleJpeg = b => { for (let k = 2; k < b.length;) { if (b[k] !== 0xFF) return null; const m = b[k + 1], n = b.readUInt16BE(k + 2);
  if (m >= 0xC0 && m <= 0xC3) return [b.readUInt16BE(k + 7), b.readUInt16BE(k + 5)]; k += 2 + n; } return null; };
check("image d'aperçu : JPEG 1200 × 630 de moins de 250 Ko", og[0] === 0xFF && og[1] === 0xD8 && og.length < 250000 && String(tailleJpeg(og)) === "1200,630");
const mani = JSON.parse(lire("manifest.webmanifest"));
check("manifeste : id unique /conferences-alertes/, icônes 192/512/maskable présentes", mani.id === "/" && mani.start_url === "./" &&
  mani.icons.length === 3 && mani.icons.every(ic => existsSync(join(root, ic.src))) && mani.icons.some(ic => ic.purpose === "maskable"));
check("icône de la famille (logo SVG avec accent doré #F2B33D, sans texte)", /#F2B33D/i.test(lire("assets/logo.svg")) && !/<text/.test(lire("assets/logo.svg")));

// ---- 10. Sécurité, robots d'IA, anti-copie, secrets, données personnelles, concurrents ----------------
const robots = lire("robots.txt");
const blocs = robots.split(/\n\s*\n/).map(b => b.trim());
const interdit = ua => blocs.some(b => b.split("\n").some(l => l.trim().toLowerCase() === "user-agent: " + ua.toLowerCase()) && /^Disallow: \/\s*$/m.test(b));
const IA = ["GPTBot", "ClaudeBot", "Claude-Web", "anthropic-ai", "CCBot", "Google-Extended", "Applebot-Extended",
  "Bytespider", "Amazonbot", "Meta-ExternalAgent", "FacebookBot", "Diffbot", "Omgilibot", "cohere-ai", "ImagesiftBot",
  "HTTrack", "WebCopier", "WebZIP", "Offline Explorer", "wget", "SiteSnagger"];
check(`robots.txt : les ${IA.length} robots d'IA et aspirateurs sont interdits`, IA.every(interdit));
check("robots.txt : Googlebot, Bingbot et les autres restent autorisés ; sitemap indiqué", ["Googlebot", "Bingbot", "*"].every(u => !interdit(u)) &&
  /Sitemap: https:\/\/conferences\.clicvia\.com\/sitemap\.xml/.test(robots));
const pj = lire("assets/page.js");
check("anti-copie : clic droit/glisser sur images bloqués, source ajoutée au texte copié, anti-iframe",
  /contextmenu/.test(pj) && /dragstart/.test(pj) && /clipboardData\.setData/.test(pj) && /window\.top !== window\.self/.test(pj));
check("anti-copie : cartes non sélectionnables, mais liens, dates et champs le restent",
  /\.cf,\.hero-photo,img\{-webkit-user-select:none;user-select:none/.test(css) && /\.cfa,\.cf-infosb,input,textarea,select,\.fiche-dldd\{-webkit-user-select:text;user-select:text/.test(css));
w = await page("index.html", `lang=fr&jour=${JOUR}`);
let copie = "";
const h3 = w.document.querySelector("#liste .cf h3");
const sel = w.getSelection(); const rg = w.document.createRange(); rg.selectNodeContents(h3); sel.removeAllRanges(); sel.addRange(rg);
const ev = new w.Event("copy", { bubbles: true, cancelable: true }); ev.clipboardData = { setData: (t, x) => { copie = x; } };
h3.dispatchEvent(ev);
check("anti-copie : le texte copié reçoit « Source : … — © … tous droits réservés »", /Source : https:\/\/conferences\.clicvia\.com\//.test(copie) && /tous droits réservés/.test(copie));
const fichiers = [];
const parcourir = dossier => { for (const f of readdirSync(join(root, dossier))) {
  if (["node_modules", ".git", "captures", "__pycache__"].includes(f)) continue;
  const c = join(dossier, f);
  if (statSync(join(root, c)).isDirectory()) parcourir(c); else if (/\.(py|js|mjs|json|md|yml|yaml|txt|html|css|xml|csv|sh|webmanifest)$/.test(f)) fichiers.push(c); } };
parcourir(".");
const secrets = fichiers.filter(f => { const t = lire(f);
  return /\b\d{8,10}:AA[A-Za-z0-9_-]{30,}/.test(t) || /AIza[0-9A-Za-z_-]{35}/.test(t) || /-----BEGIN [A-Z ]*PRIVATE KEY-----/.test(t) ||
    /gh[pousr]_[A-Za-z0-9]{30,}/.test(t) || /[A-Za-z0-9._%+-]+@(yahoo|gmail|hotmail|outlook)\.[a-z]{2,}/i.test(t); });
check(`aucun secret dans le dépôt (${fichiers.length} fichiers : jetons, clés, e-mails privés)`, secrets.length === 0);
if (secrets.length) console.log("   à vérifier : " + secrets.join(", "));
const fichiersAbo = fichiers.filter(f => /abonn[ée]s?[^/\\]*\.json$/i.test(f) || /memoire[^/\\]*\.json$/i.test(f));
const avecPerso = fichiers.filter(f => /"chat_?id"\s*:\s*-?\d/.test(lire(f)) || /"fin_essai"\s*:\s*"\d{4}/.test(lire(f)) || /"(contact|email|e-mail|telephone)"\s*:\s*"[^"]/.test(lire(f)));
check("aucune donnée personnelle dans le dépôt public (abonnés, chat_id, e-mails, téléphones, contacts)", !fichiersAbo.length && !avecPerso.length);
if (fichiersAbo.length || avecPerso.length) console.log("   à retirer : " + [...fichiersAbo, ...avecPerso].join(", "));
{ // 20/10/2026 (décision d'Ahmed : « Enlève tous les essais gratuits ») : aucune page (FR / EN / AR), aucun script, ni le manifeste ne parle d'essai gratuit
  const ESSAI = /essais? gratuits?|jours? d(?:'|&#x27;|&#39;|’)essai|(?:votre|pendant l(?:'|&#x27;|&#39;|’)|après l(?:'|&#x27;|&#39;|’)|fin de l(?:'|&#x27;|&#39;|’))essai\b|free[ -]trial|your trial|trial until|\d+-day trial|تجربة مجانية|التجربة المجانية|تجربتك|بعد التجربة|نهاية التجربة/i;
  const publics = fichiers.filter(f => /\.(html|js|json|txt|xml|webmanifest)$/.test(f) && !/^(\.\/)?(tools|robot)[\/\\]/.test(f));
  const fautifs = publics.filter(f => ESSAI.test(lire(f)));
  check(`aucune page ne parle d'essai gratuit / free trial / تجربة مجانية (${publics.length} fichiers lus)` + (fautifs.length ? " : " + fautifs.slice(0, 5).join(", ") : ""),
    publics.length > 50 && !fautifs.length);
}
// Concurrents : leurs noms ne doivent JAMAIS apparaître (liste gardée sous forme d'empreintes ; noms en clair dans l'étude privée)
const EMPREINTES = lire("tools/concurrents.sha256").split(/\s+/).filter(Boolean);
const trouves = [];
for (const f of fichiers) {
  if (/concurrents\.sha256$/.test(f)) continue;
  const mots = lire(f).toLowerCase().normalize("NFKD").replace(/[̀-ͯ]/g, "").match(/[a-z0-9]+/g) || [];
  for (let k = 0; k < mots.length; k++) for (const g of [mots[k], mots[k] + " " + mots[k + 1], mots[k] + mots[k + 1]])
    if (EMPREINTES.includes(createHash("sha256").update(g).digest("hex").slice(0, 16))) trouves.push(f + " (" + g + ")");
}
check(`aucun nom de concurrent dans le dépôt public (${EMPREINTES.length} noms vérifiés par empreinte)`, EMPREINTES.length >= 10 && trouves.length === 0);
if (trouves.length) console.log("   à retirer : " + [...new Set(trouves)].slice(0, 10).join(", "));

// ---- 11. Alertes Pro (payant) ----------------------------------------------------------------------------
w = await page("abonnement/index.html", "lang=fr");
d = w.document;
const ta = texte(d.querySelector("main"));
// 21/10/2026 (décision d'Ahmed, site international) : Alertes Pro GRATUITES pour commencer — interrupteur ABO["gratuit"] de construire_site.py
const GRATUIT = /"gratuit": True/.test(readFileSync(join(root, "robot/construire_site.py"), "utf8"));
if (GRATUIT) {
  check("abonnement GRATUIT : « Gratuit pour le moment », aucun prix, aucun paiement (D17, IZI, preuve, facture) sur la page",
    /Gratuit pour le moment/.test(texte(d.getElementById("abo-prix"))) && !/\bDT\b|TND|D17|IZI|preuve de paiement|facture|réception du paiement/.test(ta) && !d.getElementById("paiement") && !d.getElementById("abo-preuve"));
  check("abonnement GRATUIT : accueil et données Google sans prix", !/\d+ DT \/ mois|TND/.test(lire("index.html")) && /gratuit/.test(lire("index.html")));
} else {
  check("abonnement : prix tout de suite (9 DT / mois ou 79 DT / an), alertes dès réception du paiement, sans engagement au-delà d'un an, pas de renouvellement automatique",
    /9 DT \/ mois ou 79 DT \/ an/.test(texte(d.getElementById("abo-prix"))) && /dès réception du paiement/.test(ta) && /Sans engagement au-delà d'un an/.test(ta) && /Pas de renouvellement automatique/.test(ta));
  const pay = d.getElementById("paiement");
  check("bouton « Paiement » qui déplie D17 et IZI (liens vers les applications officielles, mode d'emploi, plus de Wafacash) au 24 321 390 + montant + motif", pay && pay.tagName === "DETAILS" && !pay.open &&
    ["D17", "IZI", "Transfert rapide"].every(m => texte(pay).includes(m)) && (texte(pay).match(/24 321 390/g) || []).length >= 1 && /Motif/.test(texte(pay)) && !/Wafacash/i.test(pay.outerHTML) && ["tn.mobipost", "tn.izi.consumer", "id1475640303", "id1603653941"].every(u => pay.querySelector(`a[href*="${u}"]`)));
  check("paiement : logos D17 / IZI dans les boutons, étape 2 pour les deux applications, bouton « ? » avec les deux écrans d'exemple", ["d17.png", "izi.png", "transfert-d17.svg", "transfert-izi.svg"].every(f => existsSync(join(root, "assets/paiement", f))) && /class="appli-btn"[^>]*><img src="\.\.\/assets\/paiement\/d17\.png"/.test(lire("abonnement/index.html")) && /class="aide-transfert"/.test(lire("abonnement/index.html")) && /Transfert d’argent/.test(lire("abonnement/index.html")));
  { // 18/10/2026 : le motif du paiement est le CODE PERSONNEL donné à l'inscription (#abo-code) — jamais « votre nom » / « nom de l'entreprise » ailleurs sur la page ou dans les conditions
    const sansBalises = f => lire(f).replace(/<[^>]*>/g, " ");
    const contradictions = [/pour motif (votre nom|le nom)/, /name as reference/, /motif du paiement et facture/];
    check("paiement : motif = code personnel partout (page d'abonnement + conditions), aucune phrase « motif = nom »",
      /id="abo-code"/.test(lire("abonnement/index.html")) && /motif[^.]{0,40}code personnel/.test(sansBalises("abonnement/index.html")) && /code personnel/.test(sansBalises("abonnement/conditions/index.html")) &&
      ["abonnement/index.html", "abonnement/conditions/index.html"].every(f => contradictions.every(r => !r.test(sansBalises(f)))));
  }
  check("paiement simple et rassurant (règle commune du 08/10/2026) : 3 étapes numérotées, phrase de confiance, description de l'offre cachée quand « Paiement » est ouvert", /<ol class="paie-etapes">/.test(lire("abonnement/index.html")) && /class="paie-confiance"/.test(lire("abonnement/index.html")) && /class="avantages[^"]*masque-si-paiement/.test(lire("abonnement/index.html")) && lire("assets/style.css").includes(":has(> details.paiement[open]) > .masque-si-paiement{display:none}"));
  check("paiement : ligne honnête pour l'étranger (carte : bientôt ; WhatsApp)", /Paiement par carte pour l'étranger : bientôt ; écrivez-nous sur WhatsApp/.test(texte(pay)));
  const wa = d.getElementById("abo-preuve");
  check("bouton vert « preuve de paiement » vers wa.me/21624321390 avec texte prérempli", wa && /^https:\/\/wa\.me\/21624321390\?text=/.test(wa.href) && /preuve de paiement/.test(decodeURIComponent(wa.href)));
}
const fa = d.getElementById("abo-form");
check(GRATUIT ? "formulaire GRATUIT : pas de choix de formule" : "formulaire : formule 1 mois (cochée) ou 1 an, plus de formule « essai »", [...fa.querySelectorAll('[name="formule"]')].map(x => x.value + (x.checked ? "*" : "")).join(",") === (GRATUIT ? "" : "1 mois*,1 an"));
check("formulaire : Formspree mwlpakqj, nom, institution, pays, téléphone, e-mail, spécialités, formule, conditions",
  fa.getAttribute("action") === "https://formspree.io/f/mwlpakqj" && ["nom", "etablissement", "pays", "telephone", "email", "conditions", ...(GRATUIT ? [] : ["formule"])].every(n => fa.querySelector(`[name="${n}"]`)) &&
  fa.querySelectorAll('input[name="specialites"]').length === new Set(avenir.flatMap(c => c.specialites)).size);
// envoi simulé
const envois = [], emails = [];   // emails = demandes au service d'e-mail automatique (A.17, 25/11/2026), gardées à part de Formspree
w.fetch = (u, o) => { if (/api-email\.clicvia\.com/.test(u)) emails.push({ u, o }); else envois.push({ u, o }); return Promise.resolve({ ok: true, status: 200 }); };
fa.querySelector('[name="nom"]').value = "Pr Test"; fa.querySelector('[name="etablissement"]').value = "Université X"; fa.querySelector('[name="pays"]').value = "Tunisie";
fa.querySelector('[name="telephone"]').value = "+216 24 000 000";
fa.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
await new Promise(r => setTimeout(r, 30));
check("inscription sans e-mail : message long « Indiquez une adresse e-mail valide : vous y recevez votre code et le lien Telegram. », rien n'est envoyé (ni Formspree ni e-mail automatique)",
  envois.length === 0 && emails.length === 0 && d.getElementById("abo-status").textContent === "Indiquez une adresse e-mail valide : vous y recevez votre code et le lien Telegram.");
fa.querySelector('[name="email"]').value = "prof@example.org";
fa.querySelector('input[name="specialites"]').checked = true; fa.querySelector('#abo-conditions').checked = true;
fa.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
await new Promise(r => setTimeout(r, 30));
const corps = envois[0] ? Object.fromEntries([...envois[0].o.body.entries()]) : {};
check("inscription simulée : envoi Formspree avec spécialités en une ligne et ligne « pour_activer »",
  envois.length === 1 && envois[0].u === "https://formspree.io/f/mwlpakqj" && corps.specialites && /specialites: /.test(corps.pour_activer || "") && corps.telephone === "+21624000000");
check("après l'envoi : confirmation, paiement et Telegram affichés", d.getElementById("abo-form").hidden && !d.getElementById("apres-abo").hidden);
// 14/10/2026 (règle commune § 15 : inscription immédiate ; plus d'essai depuis le 20/10/2026) : code créé sur place, lien Telegram avec les spécialités, gestes expliqués avant
if (!fa.getAttribute("data-robot")) {      // robot Telegram pas encore créé : pas de promesse d'inscription immédiate
  check("robot Telegram pas encore réglé : pas de bouton « Ouvrir Telegram », texte honnête « envoyé à l'activation »",
    !d.getElementById("abo-ouvrir-tg") && !d.getElementById("abo-code") && /activation/.test(texte(d.getElementById("apres-abo"))));
} else { const ap = d.getElementById("apres-abo"), codeC = d.getElementById("abo-code").textContent, lienC = d.getElementById("abo-ouvrir-tg").getAttribute("href");
  const spec1 = fa.querySelector('input[name="specialites"]').value;
  check("inscription IMMÉDIATE : code de 6 caractères, « Ouvrir Telegram » avec les spécialités (start=e<CODE>_<spécialités>), code envoyé et dans WhatsApp",
    /^[A-HJ-NP-Z2-9]{6}$/.test(codeC) && lienC === `https://t.me/${fa.getAttribute("data-robot")}?start=e${codeC}_${w.ESSAI_ALERTES.encoder([spec1], fa.getAttribute("data-specs").split(","))}`
    && lienC.split("start=")[1].length <= 64 && corps.code === codeC && (GRATUIT || decodeURIComponent(d.getElementById("abo-preuve-apres").href).includes("code " + codeC)));
  check("inscription IMMÉDIATE : 3 gestes avant Telegram (DÉMARRER, réponse le matin suivant), plus d'« activation sous 24 heures »",
    ap.querySelectorAll(".etapes-tg li").length === 3 && /DÉMARRER/.test(texte(ap)) && /le matin suivant/.test(texte(ap)));
  // 25/11/2026 (parcours commun des Pass, règle commune § 70) : code en gros + « reçu aussi par e-mail » + mémoire « pass-commande » (FR, EN, AR)
  check("après l'envoi (FR) : code en GROS ; « Vous le recevez aussi par e-mail » AFFICHÉ (e-mail automatique en service, EMAIL_AUTO = true) ; code dans « pour_activer »" + (GRATUIT ? " ; gratuit : aucune phrase « motif »" : ""),
    ap.querySelector(".code-commande #abo-code").textContent === codeC && ap.querySelectorAll("[data-email-auto]").length === 1 && !ap.querySelector("[data-email-auto]").hidden && /var EMAIL_AUTO = true;/.test(lire("assets/pass-reglages.js"))
    && corps.pour_activer.endsWith("code: " + codeC) && (!GRATUIT || !/motif|D17|IZI/.test(texte(ap)) && !ap.querySelector(".paie-etapes")));
  const memo = w.localStorage.getItem("pass-commande"), m = JSON.parse(memo || "{}");
  check("mémoire pass-commande : code, formule, date, lien Telegram — rien de personnel (ni nom, ni institution, ni pays, ni téléphone, ni e-mail)",
    m.code === codeC && m.formule === (GRATUIT ? "" : "1 mois") && /^\d{4}-\d{2}-\d{2}$/.test(m.date) && m.tg === lienC && Object.keys(m).sort().join() === "code,date,formule,tg"
    && !/Pr Test|Université X|Tunisie|24 000 000|24000000|prof@example/.test(JSON.stringify(Object.assign({}, w.localStorage))));
  const abo = lire("abonnement/index.html");
  // e-mail automatique (A.17, 25/11/2026) : UNE demande JSON au service, avec les champs attendus par verifier() du Worker (sites.json « conferences »)
  const jFr = emails[0] ? JSON.parse(emails[0].o.body) : {};
  check("e-mail automatique (FR) : UNE demande à https://api-email.clicvia.com/inscription (POST JSON) avec site conferences, langue fr, nom, e-mail, CE code, spécialités, établissement, pays, lien Telegram",
    emails.length === 1 && emails[0].u === "https://api-email.clicvia.com/inscription" && emails[0].o.method === "POST" && /application\/json/.test(emails[0].o.headers["Content-Type"])
    && jFr.site === "conferences" && jFr.langue === "fr" && jFr.nom === "Pr Test" && jFr.email === "prof@example.org" && jFr.code === codeC
    && Array.isArray(jFr.specialites) && jFr.specialites.join() === spec1 && jFr.etablissement === "Université X" && jFr.pays === "Tunisie" && jFr.lien_telegram === lienC && !("piege" in jFr));
  check("CSP de la page abonnement/ : connect-src autorise https://api-email.clicvia.com (sinon le navigateur bloque l'e-mail automatique)",
    /connect-src[^;"]*https:\/\/api-email\.clicvia\.com/.test(abo));
  // inscription dans chaque langue de la page : la langue envoyée = celle choisie par le visiteur
  const inscrire = async (lang, valeurs) => { const dd = new JSDOM(abo, { runScripts: "outside-only", url: URL_SITE + "abonnement/?lang=" + lang, pretendToBeVisual: true }), ww = dd.window, em = [], fs2 = [];
    ww.fetch = (u, o) => { if (/api-email\.clicvia\.com/.test(u)) em.push(JSON.parse(o.body)); else fs2.push(u); return Promise.resolve({ ok: true, status: 200 }); };
    ww.eval(lire("assets/page.js")); ww.eval(PASS_JS); ww.document.dispatchEvent(new ww.Event("DOMContentLoaded"));
    const f2 = ww.document.getElementById("abo-form");
    for (const [k, v] of Object.entries(valeurs)) f2.querySelector(`[name="${k}"]`).value = v;
    [...f2.querySelectorAll('input[name="specialites"]')].slice(0, 2).forEach(c => { c.checked = true; }); ww.document.getElementById("abo-conditions").checked = true;
    f2.dispatchEvent(new ww.Event("submit", { bubbles: true, cancelable: true })); await new Promise(r => setTimeout(r, 30));
    return { em, fs2, code: ww.document.getElementById("abo-code").textContent, lang: ww.document.documentElement.lang }; };
  const jsons = { fr: jFr };
  for (const [lang, nom] of [["en", "Dr Smith"], ["ar", "د. سامي"]]) {
    const r = await inscrire(lang, { nom, etablissement: "Univ Y", pays: "Maroc", telephone: "+212 600 000 000", email: "x@example.org" });
    jsons[lang] = r.em[0] || {};
    check(`e-mail automatique (${lang.toUpperCase()}) : une demande au service en langue ${lang} (langue de la page), avec CE code, le nom, 2 spécialités`,
      r.lang === lang && r.em.length === 1 && r.fs2.length === 1 && jsons[lang].langue === lang && jsons[lang].code === r.code && jsons[lang].nom === nom && jsons[lang].specialites.length === 2 && jsons[lang].site === "conferences");
  }
  { // le JSON envoyé est ACCEPTÉ par le vrai verifier() du Worker (dépôt projets-ahmed voisin ; absent sur GitHub : test sauté, jamais en échec)
    const dossier = [process.env.PROJETS_AHMED, "../projets-ahmed", "../../projets-ahmed"].filter(Boolean).map(x => resolve(root, x)).find(x => existsSync(join(x, "outils communs/email-clients/test_worker.mjs")));
    if (dossier) {   // même paquet que deployer.py / test_worker.mjs : sites.json inséré dans worker.js à la place de SITES_ICI
      const ec = join(dossier, "outils communs/email-clients"), wk = readFileSync(join(ec, "worker.js"), "utf8");
      const tmp = join(mkdtempSync(join(tmpdir(), "email-")), "worker.mjs");
      writeFileSync(tmp, wk.replace("/*SITES_ICI*/ {}", readFileSync(join(ec, "sites.json"), "utf8").trim()));
      const W = await import(pathToFileURL(tmp).href), ORI = "https://conferences.clicvia.com";
      for (const lang of ["fr", "en", "ar"]) { const v = W.verifier(jsons[lang], ORI);
        check(`e-mail automatique (${lang.toUpperCase()}) : le JSON envoyé est ACCEPTÉ par le vrai verifier() du service (langue ${lang}, lien Telegram du robot avec CE code gardé)` + (v.erreur ? " — refus : " + v.erreur : ""),
          !!v.d && v.d.langue === lang && v.d.lienTg === jsons[lang].lien_telegram && v.d.valeurs.specialites.length === jsons[lang].specialites.length && v.d.valeurs.pays && v.d.valeurs.etablissement); }
    } else console.log("SAUTÉ e-mail automatique : verifier() du service (dépôt projets-ahmed absent, normal sur GitHub)");
  }
  const revenir = (lang, valeur) => { const dd = new JSDOM(abo, { runScripts: "outside-only", url: URL_SITE + "abonnement/?lang=" + lang, pretendToBeVisual: true });
    if (valeur) dd.window.localStorage.setItem("pass-commande", valeur); dd.window.fetch = () => Promise.resolve({ ok: true });
    dd.window.eval(lire("assets/page.js")); dd.window.eval(PASS_JS); dd.window.document.dispatchEvent(new dd.window.Event("DOMContentLoaded")); return dd.window; };
  const visible = (el, lang) => texte(el).length && [...el.querySelectorAll(`[data-l="${lang}"]`)].map(texte).join(" ");
  for (const [lang, titre, ouvrir, nouv] of [["fr", "Votre commande en attente :", "Ouvrir Telegram", "Nouvelle commande"], ["en", "Your pending order:", "Open Telegram", "New order"], ["ar", "طلبك في الانتظار:", "افتح تيليغرام", "طلب جديد"]]) {
    const w2 = revenir(lang, memo), d2 = w2.document, at = d2.getElementById("abo-attente"), vu = visible(at, lang);
    check(`retour sur la page (${lang.toUpperCase()}) : bandeau « ${titre} code … » + « ${ouvrir} » (même lien) + « ${nouv} », formulaire caché`,
      w2.document.documentElement.lang === lang && !at.hidden && d2.getElementById("abo-form").hidden && vu.includes(titre) && vu.includes(ouvrir) && vu.includes(nouv)
      && at.querySelector("[data-code]").textContent === codeC && d2.getElementById("abo-attente-tg").getAttribute("href") === lienC
      && (!GRATUIT || !at.querySelector(".paie-etapes") && !at.querySelector(".btn-wa")));
    if (lang === "fr") { d2.getElementById("abo-nouvelle").dispatchEvent(new w2.Event("click"));
      check("« Nouvelle commande » : mémoire effacée, bandeau caché, formulaire de nouveau visible", w2.localStorage.getItem("pass-commande") === null && at.hidden && !d2.getElementById("abo-form").hidden); } }
  check("« reçu aussi par e-mail » (FR, EN, AR) : seulement dans les éléments [data-email-auto] (affichés par le module commun quand EMAIL_AUTO = true)", [...abo.matchAll(/<p class="petit" data-email-auto hidden>/g)].length >= 1
    && /You also receive it by e-mail\./.test(abo) && abo.includes("يصلك أيضًا عبر البريد الإلكتروني.") && !/<p[^>]*>(?:(?!<\/p>)[\s\S])*receive it by e-mail/.test(abo.replace(/<p class="petit" data-email-auto hidden>[\s\S]*?<\/p>/g, "")));
  { const vieux = JSON.stringify(Object.assign({}, m, { date: new Date(Date.now() - 61 * 864e5).toISOString().slice(0, 10) }));
    const w3 = revenir("fr", vieux), w4 = revenir("fr", JSON.stringify(Object.assign({}, m, { code: "abc" })));
    check("mémoire pass-commande : gardée 60 jours (au-delà : effacée, pas de bandeau) ; code au mauvais format ignoré",
      w3.document.getElementById("abo-attente").hidden && w3.localStorage.getItem("pass-commande") === null && !w3.document.getElementById("abo-form").hidden
      && w4.document.getElementById("abo-attente").hidden && w4.localStorage.getItem("pass-commande") === null); } }
w = await page("abonnement/conditions/index.html", "lang=fr");
const tc = texte(w.document.querySelector("main"));
if (GRATUIT) check("conditions GRATUITES : gratuit pour le moment, prévenu avant tout passage au payant, rien prélevé, arrêt /stop, données personnelles, INPDP, ni prix ni paiement ni facture",
  /Gratuit pour le moment/.test(tc) && /prévenus à l'avance/.test(tc) && /rien n'est jamais prélevé/.test(tc) && /\/stop/.test(tc) && /Données personnelles/.test(tc) && /INPDP/.test(tc) && !/\bDT\b|D17|IZI|facture|remboursée/.test(tc));
else check("conditions : vendeur = l'éditeur du site, prix, paiement (période payée dès l'activation), pas de renouvellement, aucun remboursement, données personnelles, INPDP",
  /vendu par l'éditeur du site/.test(tc) && /9 DT par mois ou 79 DT par an/.test(tc) && /commence le jour de l'activation/.test(tc) && !/gratuits, sans paiement/.test(tc) && /D17 ou IZI/.test(tc) &&
  /aucun renouvellement automatique/.test(tc) && /Aucune période déjà payée n'est remboursée/.test(tc) && /Données personnelles/.test(tc) && /INPDP/.test(tc));

// 14/10/2026 (contrôle de visibilité, règle commune § 8) : jamais de hreflang vers « ?lang= » (même page renvoyée par le serveur)
{ const toutes = []; const fouiller = d => { for (const n of readdirSync(join(root, d), { withFileTypes: true })) {
    if (n.isDirectory() && !/^(node_modules|\.git|assets|donnees|captures)$/.test(n.name)) fouiller(join(d, n.name));
    else if (n.name === "index.html") toutes.push(join(d, n.name)); } };
  fouiller("");
  check(`langues : aucune page (${toutes.length}) ne déclare un hreflang vers « ?lang= »`, toutes.length > 100 && toutes.every(f => !/hreflang="[a-z-]+" href="[^"]*[?]lang=/.test(lire(f)))); }

// ---- Rapports du mois (18/10/2026, règle commune § 25) : chaque chiffre = un décompte des fiches, cohérent avec les autres pages
{
  const H = JSON.parse(lire("donnees/rapports.json")).mois;
  const MIN = 10, cleJ = JOUR.slice(0, 7);
  const avecPage = Object.keys(H).filter(k => (H[k].conferences || []).filter(c => c.debut.slice(0, 7) === k).length >= MIN).sort();
  const lm = Object.fromEntries([...sitemap.matchAll(/<loc>([^<]+)<\/loc><lastmod>([^<]+)<\/lastmod>/g)].map(m => [m[1], m[2]]));
  check(`rapports : ${avecPage.length} mois avec rapport (au moins ${MIN} événements)`, avecPage.length >= 1);
  check("rapports : liste rapports/ et le DERNIER mois dans le plan du site (réduit, VIS.3), les autres en ligne, date = date des chiffres, adresse « rapports/AAAA-MM/ »",
    urls.includes(URL_SITE + "rapports/") && lm[URL_SITE + `rapports/${avecPage[avecPage.length - 1]}/`] === H[avecPage[avecPage.length - 1]].derniere_date   // VIS.3 : DERNIER mois seul dans le plan réduit
    && avecPage.every(k => existsSync(join(root, `rapports/${k}/index.html`))) &&
    urls.filter(u => u.includes("/rapports/") && u !== URL_SITE + "rapports/").every(u => /^\/rapports\/\d{4}-\d{2}\/$/.test(new URL(u).pathname) && avecPage.includes(new URL(u).pathname.slice(10, 17))));
  check("rapports : aucun mois sous le minimum n'a de page", Object.keys(H).filter(k => !avecPage.includes(k)).every(k => !existsSync(join(root, `rapports/${k}/index.html`))));
  check("rapports : un mois fini a toujours sa date des chiffres dans ce mois-là, et seul le mois en cours n'est pas figé",
    Object.entries(H).every(([k, e]) => e.derniere_date.slice(0, 7) === k && (k < cleJ ? e.fini === true : !e.fini)));
  for (const k of avecPage) {
    const e = H[k], ev = e.conferences.filter(c => c.debut.slice(0, 7) === k);
    const lims = e.conferences.flatMap(c => (c.limites || []).map(x => ({ ...x, id: c.id })));
    const w = await page(`rapports/${k}/index.html`, "lang=fr");
    const D = w.document;
    const n = +texte(D.querySelector("#rp-n b"));
    check(`rapport ${k} : ${n} événements = fiches qui commencent ce mois (${ev.length}) = chiffres enregistrés`, n === ev.length && n === e.chiffres.evenements);
    check(`rapport ${k} : calendrier = ces ${ev.length} événements, une ligne chacun`, D.querySelectorAll("#calendrier li").length === ev.length &&
      [...D.querySelectorAll("#calendrier li")].every(li => ev.some(c => c.id === li.dataset.id)));
    check(`rapport ${k} : ${lims.length} dates limites de soumission, toutes dans ce mois, = chiffre affiché`,
      +texte(D.querySelector("#rp-limites b")) === lims.length && D.querySelectorAll("#dates-limites li").length === lims.length &&
      [...D.querySelectorAll("#dates-limites li")].every(li => li.dataset.d.slice(0, 7) === k));
    const pays = new Set(ev.filter(c => c.pays && c.mode !== "en-ligne").map(c => c.pays));
    check(`rapport ${k} : ${pays.size} pays (sur place ou hybride) = chiffre affiché`, +texte(D.querySelector("#rp-pays b")) === pays.size);
    const lignesDom = [...D.querySelectorAll("section.rp")].find(s => /Par domaine/.test(texte(s.querySelector("h2"))));
    check(`rapport ${k} : tableau par domaine = décompte des fiches`, !!lignesDom && [...lignesDom.querySelectorAll("tbody tr")].every(tr => {
      const nb = +texte(tr.querySelector("td.n")); const nom = texte(tr.querySelector("th"));
      return nb > 0 && ev.filter(c => c.domaines.some(dm => nom.includes(({ comptabilite: "Comptabilité", finance: "Finance", "finance-islamique": "Finance islamique", informatique: "Informatique", physique: "Physique", "vie-sante": "vie", ingenierie: "Ingénierie" })[dm] || "§"))).length >= nb; }));
    let ld = [];
    try { ld = [...lire(`rapports/${k}/index.html`).matchAll(/<script type="application\/ld\+json">\n([\s\S]*?)\n<\/script>/g)].map(m => JSON.parse(m[1])); } catch (x) { ld = []; }
    const art = ld.find(x => x["@type"] === "Article"), fq = ld.find(x => x["@type"] === "FAQPage");
    check(`rapport ${k} : JSON-LD fil d'Ariane + Article (date des chiffres) + FAQ dont la 1re réponse donne le même nombre`,
      ld.some(x => x["@type"] === "BreadcrumbList") && art && art.dateModified === e.derniere_date && art.url === URL_SITE + `rapports/${k}/` &&
      fq && fq.mainEntity.length >= 3 && fq.mainEntity[0].acceptedAnswer.text.startsWith(`${ev.length} événements`));
    const main = texte(D.querySelector("main"));
    check(`rapport ${k} : « Citer ces chiffres » avec l'adresse, méthode, date des chiffres`,
      main.includes("Citer ces chiffres") && main.includes(URL_SITE + `rapports/${k}/`) && /Comment ces chiffres sont calculés/.test(main) && /Aucune estimation/.test(main));
    check(`rapport ${k} : évolution seulement si le mois précédent a un rapport`,
      (() => { const a = +k.slice(0, 4), m = +k.slice(5, 7); const prec = m === 1 ? `${a - 1}-12` : `${a}-${String(m - 1).padStart(2, "0")}`;
        return avecPage.includes(prec) ? main.includes("Évolution") && !!D.querySelector(`a[href="../${prec}/"]`) : main.includes("pas encore de comparaison"); })());
    if (k === cleJ) {
      const duMois = avenir.filter(c => c.debut.slice(0, 7) === k);
      const cartesMois = existsSync(join(root, `mois/${k}/index.html`)) ? (lire(`mois/${k}/index.html`).match(/<article class="cf/g) || []).length : 0;
      check(`rapport ${k} : « pas encore terminés » = ${duMois.length} = cartes de la page mois/${k}/ (${cartesMois})`,
        new RegExp(`${duMois.length} pas encore terminé`).test(main) && cartesMois === duMois.length);
      check(`rapport ${k} : chaque conférence encore à venir du mois est dans le calendrier, avec sa fiche`,
        duMois.every(c => { const a = D.querySelector(`#calendrier li[data-id="${c.id}"] a`); return a && a.getAttribute("href") === `../../conference/${c.id}/` && existsSync(join(root, `conference/${c.id}/index.html`)); }));
      const limAVenir = avenir.flatMap(c => c.dates_limites.filter(x => (x.type === "article" || x.type === "resume") && x.date.slice(0, 7) === k).map(x => c.id + x.date));
      check(`rapport ${k} : toutes les dates limites du mois des fiches actuelles (${limAVenir.length}) sont dans le rapport`,
        limAVenir.every(x => lims.some(l => l.id + l.date === x)));
      check(`page mois/${k}/ : lien vers le rapport du mois (si la page existe encore), et le rapport n'y renvoie que si elle existe`,
        existsSync(join(root, `mois/${k}/index.html`)) ? lire(`mois/${k}/index.html`).includes(`href="../../rapports/${k}/"`) && !!D.querySelector(`a[href="../../mois/${k}/"]`)
          : !D.querySelector(`a[href="../../mois/${k}/"]`));
    }
  }
  // « Partager ce rapport » (demande d'Ahmed du 18/10/2026) : UN SEUL bouton en haut + un en bas, texte qui nomme le site, signature, aperçu
  const css = lire("assets/style.css"), pjs = lire("assets/page.js");
  check("rapports : code du bouton « Partager ce rapport » dans page.js (menu du téléphone, sinon lien copié, compté) et style ≥ 44 px, sans la classe .partager de l'en-tête",
    /button\[data-partage-rapport\]/.test(pjs) && /navigator\.share\(\{ title: titre, text: texte, url: url \}\)/.test(pjs) && /clipboard\.writeText/.test(pjs) &&
    /window\.prompt/.test(pjs) && /path: "partage" \+ location\.pathname/.test(pjs) &&
    (() => { const m = css.match(/\.rp-partager\{[^}]*min-height:(\d+)px/); return m && +m[1] >= 44; })());
  async function testerPartage(chemin, adresse) {
    const brut = lire(chemin);
    const w = await page(chemin, "lang=fr"), D = w.document;
    const bs = [...D.querySelectorAll("button[data-partage-rapport]")];
    const main = D.querySelector("main");
    check(`${chemin} : UN bouton « Partager ce rapport » en haut et UN en bas, avec la bonne adresse`,
      bs.length === 2 && bs.every(b => b.dataset.url === adresse && main.contains(b) && !b.classList.contains("partager") && /Partager ce rapport/.test(texte(b))) &&
      main.firstElementChild.nextElementSibling === bs[0].closest("section") && bs[1].closest("section") === main.lastElementChild);
    check(`${chemin} : aucun bouton Facebook / WhatsApp / LinkedIn séparé`, !/sharer|wa\.me|linkedin\.com\/share|facebook\.com\/share/i.test(brut));
    check(`${chemin} : plus de phrase d'aide sous le bouton (demande d'Ahmed)`, !/rp-partage-aide|LinkedIn… :/.test(brut));
    check(`${chemin} : le texte partagé nomme le site (sans adresse), dans les 3 langues`,
      bs.every(b => b.dataset.texteFr.endsWith("— Rapport du mois de Radar des conférences :") &&
        b.dataset.texteEn.endsWith("— Monthly report by Conference Radar:") && b.dataset.texteAr.endsWith("— تقرير الشهر من رادار المؤتمرات:")));
    check(`${chemin} : le texte partagé ne contient AUCUNE adresse (sinon Facebook montre l'aperçu de l'accueil) ; l'adresse va seulement dans « url »`,
      bs.every(b => ["Fr", "En", "Ar"].every(l => !/clicvia|https?:|www\.|\.com/i.test(b.dataset["texte" + l]))));
    const sig = D.querySelector(".hero .rp-signature");
    check(`${chemin} : signature « Un rapport de Radar des conférences · conferences.clicvia.com » sous le titre`,
      !!sig && sig.previousElementSibling && sig.previousElementSibling.tagName === "H1" && /Un rapport de Radar des conférences · conferences\.clicvia\.com/.test(texte(sig)) && sig.querySelectorAll("[data-l]").length === 3);
    const meta = n => (D.querySelector(`meta[name="${n}"],meta[property="${n}"]`) || {}).content || "";
    check(`${chemin} : description qui commence par « Radar des conférences — rapport du mois. », og:title / og:description / og:image / og:url justes`,
      meta("description").startsWith("Radar des conférences — rapport du mois.") && meta("og:description") === meta("description") && meta("og:title").length > 10 &&
      meta("og:url") === adresse && (chemin === "rapports/index.html" ? meta("og:image") === URL_SITE + "assets/og-image-v1.jpg" && existsSync(join(root, "assets/og-image-v1.jpg")) : meta("og:image").startsWith(adresse + "apercu-")));
    // image PROPRE à chaque rapport du mois (18/10/2026, Ahmed : sur Facebook, l'aperçu montrait l'image du site, pas l'article)
    if (chemin !== "rapports/index.html") {
      const og = meta("og:image").replace(URL_SITE, ""), dos = chemin.replace("index.html", ""), nom = og.split("/").pop();
      const art = [...D.querySelectorAll('script[type="application/ld+json"]')].map(x => JSON.parse(x.textContent)).find(x => x["@type"] === "Article") || {};
      const b = existsSync(join(root, og)) ? readFileSync(join(root, og)) : Buffer.alloc(0);
      let dim = null;
      for (let i = 2; b[0] === 0xFF && b[1] === 0xD8 && i < b.length - 8;) { if (b[i] !== 0xFF) break; const t = b[i + 1];
        if (t >= 0xC0 && t <= 0xC3) { dim = [b.readUInt16BE(i + 7), b.readUInt16BE(i + 5)]; break; } i += 2 + b.readUInt16BE(i + 2); }
      check(`${chemin} : image d'aperçu propre au rapport (apercu-<empreinte>.jpg dans son dossier, JPEG 1200 × 630 < 250 Ko, aussi dans le JSON-LD Article, og:type article)`,
        og === dos + nom && /^apercu-[0-9a-f]{8}\.jpg$/.test(nom) && b.length > 0 && b.length < 250 * 1024 && dim && dim[0] === 1200 && dim[1] === 630
        && art.image === meta("og:image") && meta("og:type") === "article" && readdirSync(join(root, dos)).filter(f => /^apercu-.*\.jpg$/.test(f)).length === 1);
    }
    // clic sur un téléphone : menu de partage avec titre, texte et lien ; clic compté dans GoatCounter
    let recu = null, compte = null;
    Object.defineProperty(w.navigator, "share", { value: o => { recu = o; return Promise.resolve(); }, configurable: true });
    w.goatcounter.count = o => { compte = o; };
    bs[0].dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    await new Promise(ok => setTimeout(ok, 20));
    check(`${chemin} : clic (téléphone) → menu de partage avec le lien et le texte qui nomme le site, compté « partage${new URL(adresse).pathname} »`,
      !!recu && recu.url === adresse && recu.text === bs[0].dataset.texteFr && !!recu.title && !!compte && compte.path === "partage" + new URL(adresse).pathname && compte.event === true);
    // ordinateur (pas de menu) : « texte + lien » copié et message « Lien copié ✓ »
    let copie = null;
    Object.defineProperty(w.navigator, "share", { value: undefined, configurable: true });
    Object.defineProperty(w.navigator, "clipboard", { value: { writeText: t => { copie = t; return Promise.resolve(); } }, configurable: true });
    bs[1].dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
    await new Promise(ok => setTimeout(ok, 20));
    const msg = bs[1].closest("section").querySelector(".rp-copie");
    check(`${chemin} : clic (ordinateur) → « texte + lien » copié et « Lien copié ✓ » affiché`,
      copie === bs[1].dataset.texteFr + " " + adresse && !!msg && !msg.hidden && /Lien copié ✓ — collez-le où vous voulez/.test(texte(msg)));
    w.close();
  }
  for (const k of avecPage) await testerPartage(`rapports/${k}/index.html`, URL_SITE + `rapports/${k}/`);
  await testerPartage("rapports/index.html", URL_SITE + "rapports/");
  check("rapports : lien depuis l'accueil et depuis le pied de page commun", lire("index.html").includes('href="rapports/"') && lire("assets/page.js").includes("${racine}rapports/"));
  const wl = await page("rapports/index.html", "lang=fr");
  check("rapports/ : un lien par mois avec rapport", avecPage.every(k => wl.document.querySelector(`#rp-liste a[href="${k}/"]`)) && wl.document.querySelectorAll("#rp-liste li").length === avecPage.length);
}

// ---- og:locale lisible par Facebook (18/10/2026) : « fr_TN » / « ar_TN » sont REJETÉS par Facebook (« n'a pas pu être analysée en tant
// que type enum ») et l'aperçu partagé était faux ; valeurs admises : fr_FR, ar_AR, en_US.
{ const pagesLoc = [...sitemap.matchAll(/<loc>https:\/\/[^/]+\/([^<]*)<\/loc>/g)].map(m => m[1] + "index.html").filter(f => existsSync(join(root, f)));
  const mauvaises = pagesLoc.filter(f => { const h = lire(f); return /_TN"/.test(h) || [...h.matchAll(/property="og:locale(?::alternate)?" content="([^"]+)"/g)].some(m => !["fr_FR", "ar_AR", "en_US"].includes(m[1])); });
  check(`og:locale admis par Facebook (fr_FR / ar_AR / en_US, jamais fr_TN ni ar_TN) sur les ${pagesLoc.length} pages du plan du site`, pagesLoc.length > 3 && mauvaises.length === 0);
  if (mauvaises.length) console.log("   og:locale refusé : " + mauvaises.slice(0, 5).join(", "));
}

// 25/10/2026 (RÈGLE d'Ahmed : « la page Comment fonctionne le site doit être mise à jour chaque fois qu'on modifie le site », règle commune § 44) :
// chaque fonction visible du site (repère dans les pages ou le code) doit être expliquée dans a-propos/ (FR, EN, AR) ; nouvelle fonction = une ligne ici + la page
{ const apx = lire("a-propos/index.html"), acc2 = lire("index.html"), js = lire("assets/app.js") + lire("assets/page.js");
  const FONCTIONS = [
    ["e-mail de confirmation automatique (A.17, 25/11/2026)", /var EMAIL_AUTO = true;/.test(lire("assets/pass-reglages.js")),
      /E-mail de confirmation<\/b>[\s\S]*Confirmation e-mail<\/b>[\s\S]*بريد التأكيد<\/b>[\s\S]*Resend/],
    ["résumé du jour", /id="r-avenir"/.test(acc2), /Résumé du jour[\s\S]*Today's summary[\s\S]*ملخص اليوم/],
    ["dates limites cette semaine", /id="bientot"/.test(acc2), /Dates limites cette semaine[\s\S]*Deadlines this week/],
    ["recherche (aussi « au son »)", /id="f-q"/.test(acc2) && existsSync(join(root, "assets/son.js")), /Rechercher<\/b>[^<]*écritures proches/],
    ["filtres domaine, spécialité, continent, format, date limite, mois", ["f-dom", "f-spec", "f-cont", "f-mode", "f-limite", "f-mois"].every(f => acc2.includes(`id="${f}"`)),
      /Filtres<\/b> : domaine, spécialité, continent, format[^<]*date limite[^<]*mois/],
    ["tri", /id="f-tri"/.test(acc2), /Tri<\/b> par date limite/],
    ["prochaine date limite sur chaque carte", true, /prochaine date limite de soumission/],
    ["une fiche par conférence", existsSync(join(root, "conference")), /Une fiche par conférence/],
    ["pages domaine / spécialité / continent / pays / mois", ["domaine", "specialite", "continent", "pays", "mois"].every(d => existsSync(join(root, d))), /Pages par domaine, par spécialité, par continent, par pays et par mois/],
    ["flux RSS gratuits", existsSync(join(root, "flux/index.html")), /Flux RSS gratuits/],
    ["rapports du mois", existsSync(join(root, "rapports/index.html")), /Rapports du mois<\/b>/],
    ["signaler une conférence (organisateurs)", existsSync(join(root, "publier/index.html")), /Signaler une conférence<\/b>/],
    ["Alertes Pro (gratuites pour le moment ou payantes)", existsSync(join(root, "abonnement/index.html")),
      /Gratuit pour le moment/.test(lire("abonnement/index.html")) ? /Alertes Pro sur Telegram : gratuites pour le moment/ : /Payant : Alertes Pro sur Telegram/],
    ["commande en attente gardée par le téléphone (code, Telegram)", /pass-commande/.test(PASS_JS) && /id="abo-attente"/.test(lire("abonnement/index.html")),
      /Commande en attente<\/b>[\s\S]*60.jours[\s\S]*Nouvelle commande[\s\S]*Pending order<\/b>[\s\S]*طلب في الانتظار/],
    ["bouton Partager", /class="partager"/.test(js), /Partager<\/b>/],
    ["trois langues FR / EN / AR", /langue-conferences/.test(js), /Trois langues<\/b>/],
    ["vidéo de présentation", existsSync(join(root, "video/index.html")), /Vidéo de présentation/],
    ["votre avis", /id="avis-form"/.test(acc2), /Votre avis<\/b>/],
    ["installation sur le téléphone (service worker)", existsSync(join(root, "sw.js")) && /serviceWorker/.test(js), /Installer le site/],
    ["sources ouvertes (MIT, INSPIRE-HEP, sélection officielle)", true, /MIT[\s\S]*INSPIRE-HEP[\s\S]*Sélection officielle/],
    ["vos données (GoatCounter, Formspree)", true, /GoatCounter[\s\S]*Formspree/],
    ["confidentialité et conditions d'utilisation (pages communes)", true, /Confidentialité et conditions d(&#x27;|&#39;|')utilisation[\s\S]*Privacy and terms of use/],
    ["mises à jour automatiques", true, /Mises à jour automatiques/],
    ["site indépendant", true, /Ce site est indépendant/],
    ["encadré « Recevoir ces alertes » des pages spécialité, domaine, continent, pays, mois (§ 71, 28/11/2026)", /id="encadre-pro"/.test(lire("specialite/banque-islamique/index.html")),
      /Encadré « Recevoir ces alertes »<\/b>[^<]*déjà coché[\s\S]*“Get these alerts” box<\/b>[\s\S]*إطار «تلقَّ هذه التنبيهات»<\/b>/],
    ["clics vers les Alertes Pro comptés (GoatCounter, § 71)", /\/conferences-alertes\/clic\//.test(js), /Les clics vers la page des Alertes Pro[^<]*GoatCounter[\s\S]*Clicks towards the Pro Alerts page[\s\S]*النقرات نحو صفحة تنبيهات Pro/],
    ["éditeur Clicvia (données pour Google, 22/11/2026)", /clicvia\.com\/#organisation/.test(acc2), /Publié par <a href="https:\/\/clicvia\.com\/"/]];
  const manque = FONCTIONS.filter(([, sur, re]) => sur && !re.test(apx)).map(([n]) => n);
  check(`page « Comment fonctionne le site ? » à jour : chaque fonction du site y est expliquée (${FONCTIONS.length} fonctions)` + (manque.length ? " — manque : " + manque.join(", ") : ""),
    manque.length === 0);
  check("page « Comment fonctionne le site ? » : titre h1 (FR, EN, AR), lien dans le pied de page (page.js) et sur l'accueil, dans le plan du site",
    /<h1><span data-l="fr">Comment fonctionne le site \?<\/span><span data-l="en">How does the site work\?<\/span><span data-l="ar">كيف يعمل الموقع؟<\/span><\/h1>/.test(apx)
    && /a-propos\/">\$\{T\("Comment fonctionne le site \?"/.test(lire("assets/page.js")) && /<a href="a-propos\/"><span data-l="fr">Comment fonctionne le site \?/.test(acc2)
    && lire("sitemap.xml").includes("https://conferences.clicvia.com/a-propos/")
    && !/alertes personnalisées sur Telegram[^<]*sont payantes/.test(apx) === /Gratuit pour le moment/.test(lire("abonnement/index.html"))); }

// ---- Page 404 du site + liens Confidentialité / Conditions en bas de CHAQUE page (17/11/2026, règle commune § 58 ; § 55 : test qui bloque) ----
check("page 404 du site : 404.html + 404.js (« Recherche de la page »)", existsSync(join(root, "404.html")) && existsSync(join(root, "404.js"))
  && /src="\/404\.js"/.test(lire("404.html")) && /Recherche de la page/.test(lire("404.js")));
{
  const LIENS = { fr: ["https://clicvia.com/confidentialite/", "https://clicvia.com/conditions/"], en: ["https://clicvia.com/en/confidentialite/", "https://clicvia.com/en/conditions/"],
                  ar: ["https://clicvia.com/ar/confidentialite/", "https://clicvia.com/ar/conditions/"] };
  const tous = Object.values(LIENS).flat(), pages = [];
  const parcourir = d => { for (const n of readdirSync(join(root, d))) { const r = d ? d + "/" + n : n;
    if (["node_modules", "tools", "captures", ".git"].includes(n)) continue;
    if (statSync(join(root, r)).isDirectory()) parcourir(r); else if (n === "index.html") pages.push(r); } };
  parcourir("");
  const sans = pages.filter(p => { const pied = (lire(p).match(/<footer id="pied">[\s\S]*?<\/footer>/) || [""])[0]; return !tous.every(u => pied.includes(`href="${u}"`)); });
  check(`pied de page : liens Confidentialité + Conditions d'utilisation (fr, en, ar) sur les ${pages.length} pages` + (sans.length ? " — manquent : " + sans.slice(0, 5).join(", ") : ""), pages.length > 50 && !sans.length);
  for (const [l, mot] of [["fr", "Confidentialité"], ["en", "Privacy"], ["ar", "الخصوصية"]]) {
    const w = await page("index.html", "lang=" + l); const p = w.document.getElementById("pied");
    check(`pied affiché (${l}) : « ${mot} » et conditions vers clicvia.com`, LIENS[l].every(u => p.querySelector(`a[href="${u}"]`)) && texte(p).includes(mot));
  }
}


// ---- 25/11/2026 (plan Google B.1 + B.2) : plan du site HONNÊTE.
//      B.2 : <lastmod> = dernier VRAI changement de la page (robot/lastmod.py, mémoire donnees/lastmod.json), jamais « aujourd'hui » partout ;
//      B.1 : fiche maigre (ni date limite, ni rang, ni vérification officielle) et catégorie d'une seule conférence = en ligne, mais noindex, hors du plan.
{
  const urlsD = [...sitemap.matchAll(/<url><loc>([^<]+)<\/loc>(?:<lastmod>([^<]+)<\/lastmod>)?/g)];
  const jour = new Date().toISOString().slice(0, 10), datesSm = urlsD.map(m => m[2]);
  check(`plan du site : chaque adresse a sa date (${urlsD.length} adresses)`, urlsD.length > 10 && datesSm.every(d => /^\d{4}-\d{2}-\d{2}$/.test(d)));
  check("plan du site : les dates ne sont pas toutes celles du jour, ni toutes identiques (date du dernier vrai changement)",
    !datesSm.every(d => d === jour) && new Set(datesSm).size > 1);
  const LMJ = existsSync(join(root, "donnees/lastmod.json")) ? JSON.parse(lire("donnees/lastmod.json")) : {};
  const fichierDe = u => u.replace(URL_SITE, "") + "index.html";
  const faux = urlsD.filter(m => !/\/rapports\//.test(m[1]) && (!LMJ[fichierDe(m[1])] || LMJ[fichierDe(m[1])].date !== m[2])).map(m => m[1]);
  check("plan du site : la date de chaque page = celle de donnees/lastmod.json (rapports du mois : date de leurs chiffres)" + (faux.length ? " — " + faux.slice(0, 3).join(", ") : ""), !faux.length);
  check("robot/construire_site.py : dates fabriquées par robot/lastmod.py (pas la date du jour pour tout)", /import lastmod as LM/.test(lire("robot/construire_site.py")) && !/lastmod\.get\(chemin, jour\)/.test(lire("robot/construire_site.py")));
  const noidx = f => /<meta name="robots" content="[^"]*noindex/.test(lire(f));
  const avecNoindex = urlsD.filter(m => existsSync(join(root, fichierDe(m[1]))) && noidx(fichierDe(m[1]))).map(m => m[1]);
  check("plan du site : aucune page en noindex" + (avecNoindex.length ? " — " + avecNoindex.slice(0, 3).join(", ") : ""), !avecNoindex.length);
  const jamais = ["index.html", "a-propos/index.html", "abonnement/index.html", "rapports/index.html", ...readdirSync(join(root, "domaine")).map(d => `domaine/${d}/index.html`)]
    .filter(f => !existsSync(join(root, f)) || noidx(f));
  check("accueil, domaines, alertes, a-propos, rapports : jamais en noindex" + (jamais.length ? " — " + jamais.slice(0, 3).join(", ") : ""), !jamais.length);
  const mal = avenir.filter(c => existsSync(join(root, `conference/${c.id}/index.html`)) && noidx(`conference/${c.id}/index.html`) !== maigre(c)).map(c => c.id);
  check(`fiches : noindex seulement sans date limite, sans rang et sans vérification officielle (${avenir.filter(maigre).length} sur ${avenir.length})` + (mal.length ? " — " + mal.slice(0, 3).join(", ") : ""), !mal.length);
  const cats = ["specialite", "pays", "mois", "continent", "domaine"].flatMap(d => readdirSync(join(root, d)).map(x => `${d}/${x}/index.html`)).filter(f => existsSync(join(root, f)));
  const malC = cats.filter(f => noidx(f) !== ((lire(f).match(/<article class="cf/g) || []).length < 2));
  check(`catégories : noindex seulement avec moins de 2 conférences (${cats.filter(noidx).length} sur ${cats.length})` + (malC.length ? " — " + malC.slice(0, 3).join(", ") : ""), !malC.length);
  // données inventées : une page inchangée garde sa date (même si sa date / heure de relevé, son ?v= et son compte à rebours changent)
  const { execFileSync } = await import("node:child_process");
  const { mkdirSync, rmSync } = await import("node:fs");
  const tmp = mkdtempSync(join(tmpdir(), "lastmod-"));
  try {
    mkdirSync(join(tmp, "a"), { recursive: true }); mkdirSync(join(tmp, "b"), { recursive: true });
    writeFileSync(join(tmp, "a/index.html"), '<p>Mis à jour le 01/11/2026 16:42</p><small class="reste">encore 5 jours</small><link href="s.css?v=1">');
    writeFileSync(join(tmp, "b/index.html"), "<p>ICPADS : Tokyo</p>");
    const py = jr => JSON.parse(execFileSync(process.platform === "win32" ? "python" : "python3", ["-c",
      `import sys,json,re;sys.path.insert(0,${JSON.stringify(join(root, "robot"))});import lastmod;print(json.dumps(lastmod.dates(${JSON.stringify(tmp)},["a/index.html","b/index.html"],"${jr}","m.json",[re.compile(r'<small class="reste">.*?</small>')])))`], { encoding: "utf-8" }));
    const j1 = py("2026-11-01");
    writeFileSync(join(tmp, "a/index.html"), '<p>Mis à jour le 02/11/2026 07:05</p><small class="reste">encore 4 jours</small><link href="s.css?v=2">');
    writeFileSync(join(tmp, "b/index.html"), "<p>ICPADS : Kyoto</p>");
    const j2 = py("2026-11-02");
    check("robot/lastmod.py (données inventées) : page dont seuls la date, l'heure, le ?v= et le compte à rebours changent = date gardée ; contenu changé = date du jour",
      j1["a/index.html"] === "2026-11-01" && j2["a/index.html"] === "2026-11-01" && j2["b/index.html"] === "2026-11-02");
  } catch (e) { check("robot/lastmod.py (données inventées) : " + e.message, false); }
  finally { rmSync(tmp, { recursive: true, force: true }); }
}
console.log(`\n${total - erreurs}/${total} vérifications réussies` + (erreurs ? ` — ${erreurs} ÉCHEC(S) : ne pas publier.` : " — tout est bon."));
process.exit(erreurs ? 1 : 0);
