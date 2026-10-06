// Test automatique de « Radar des conférences / Conference Radar » — à lancer après chaque modification :
//   node tools/test_site.mjs                 (teste le site de ce dossier)
//   node tools/test_site.mjs --racine X      (teste une copie, ex. pour le sabotage volontaire)
// jsdom s'installe une fois par PC (dans ce dossier) :  npm install --no-save --no-package-lock jsdom
import { JSDOM } from "jsdom";
import { readFileSync, existsSync, readdirSync, statSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import { createHash } from "crypto";

const i = process.argv.indexOf("--racine");
const root = i > 0 ? process.argv[i + 1] : join(dirname(fileURLToPath(import.meta.url)), "..");
const URL_SITE = "https://ah6259.github.io/conferences-alertes/";
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
async function page(chemin, params = "") {
  const dossier = dirname(join(root, chemin));
  const html = lire(chemin).replace(/<script([^>]*) src="(?!https?:)([^"?]+)(\?[^"]*)?"([^>]*)><\/script>/g,
    (_, a, src) => `<script>${readFileSync(join(dossier, src), "utf8")}</script>`);
  const dom = new JSDOM(html, { url: URL_SITE + chemin.replace("index.html", "") + "?" + params, runScripts: "dangerously", pretendToBeVisual: true });
  await new Promise(ok => dom.window.addEventListener("load", ok));
  return dom.window;
}
const texte = el => (el ? el.textContent : "").replace(/[⁦-⁩ ]/g, " ").replace(/\s+/g, " ").trim();
const visibles = d => [...d.querySelectorAll("#liste .cf")].filter(c => c.dataset.ok === "1");
const affichees = d => [...d.querySelectorAll("#liste .cf")].filter(c => !c.hidden);
const changer = (w, id, v) => { const s = w.document.getElementById(id); s.value = v; s.dispatchEvent(new w.Event("change")); };
const prochaine = (c, jour) => (c.dates_limites || []).filter(x => (x.type === "article" || x.type === "resume") && x.date >= jour).map(x => x.date).sort()[0] || "";

// ---- 1. Accueil ----------------------------------------------------------------------------
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
  check("Partager sans menu du téléphone : WhatsApp avec titre + adresse sans paramètre de langue, clic compté (partage/…)",
    ouverts.length === 1 && /^https:\/\/wa\.me\/\?text=/.test(ouverts[0]) && !/lang%3D/.test(ouverts[0]) && decodeURIComponent(ouverts[0]).includes(URL_SITE) &&
    comptes.length === 1 && comptes[0].path.startsWith("partage/") && comptes[0].event === true);
  const partages = [];
  Object.defineProperty(w.navigator, "share", { value: async o => { partages.push(o); }, configurable: true });
  b.dispatchEvent(new w.MouseEvent("click", { bubbles: true }));
  await new Promise(r => setTimeout(r, 10));
  check("Partager avec navigator.share : menu du téléphone (titre + adresse sans ?lang=)", partages.length === 1 && partages[0].url.startsWith(URL_SITE) && !/lang=/.test(partages[0].url) && ouverts.length === 1);
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

// ---- 3. Date du VISITEUR : fin, date limite passée, avertissement ---------------------------
const premiere = avenir.slice().sort((a, b) => a.fin.localeCompare(b.fin))[0];
w = await page("index.html", `lang=fr&jour=${plus(premiere.fin, 1)}`);
d = w.document;
check("une conférence terminée (date du visiteur) disparaît", d.getElementById(premiere.id).hidden && d.getElementById(premiere.id).dataset.ok === "");
check("données de plus de 2 jours : avertissement daté visible", d.getElementById("alerte-panne").classList.contains("on") && /depuis le \d\d\/\d\d\/\d{4}/.test(texte(d.getElementById("alerte-panne"))));
const avecDeux = avenir.find(c => c.dates_limites.filter(x => (x.type === "article" || x.type === "resume") && x.date >= JOUR).length >= 2);
if (avecDeux) {
  const ds = avecDeux.dates_limites.filter(x => (x.type === "article" || x.type === "resume") && x.date >= JOUR).map(x => x.date).sort();
  w = await page("index.html", `lang=fr&jour=${plus(ds[0], 1)}`);
  const c = w.document.getElementById(avecDeux.id);
  check(`date limite passée (${ds[0]}) : la suivante (${ds[1]}) est montrée`, c.dataset.prochaine === ds[1] && [...c.querySelectorAll(".dl")].filter(b => !b.hidden).map(b => b.dataset.d).join() === ds[1]);
}
w = await page("index.html", `lang=fr&jour=${plus(JOUR, 1)}`);
check("données d'hier : pas encore d'avertissement", !w.document.getElementById("alerte-panne").classList.contains("on"));
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
check(`sitemap : ${urls.length} pages dont ${nFiches} fiches (une par conférence à venir)`, nFiches === avenir.length && urls.includes(URL_SITE) && urls.includes(URL_SITE + "abonnement/"));
const v = createHash("sha1").update(Buffer.concat(["style.css", "textes.js", "page.js", "app.js", "avis.js", "abonnement.js"].map(f =>
  Buffer.from(readFileSync(join(root, "assets", f), "latin1").replace(/\r\n/g, "\n"), "latin1")))).digest("hex").slice(0, 8);
let ok = { en: true, seo: true, v: true, h1: true, fichiers: true, copy: true, trad: true, src: true, meta: true, gc: true, ios: true, ext: true };
for (const u of urls) {
  const chemin = u.replace(URL_SITE, "") + "index.html";
  if (!existsSync(join(root, chemin))) { ok.fichiers = false; console.log("   page manquante : " + chemin); continue; }
  const h = lire(chemin);
  if (!(/<title>[^<]{20,}<\/title>/.test(h) && /<meta name="description" content="[^"]{50,}"/.test(h) && h.includes(`<link rel="canonical" href="${u}">`) &&
      h.includes(`property="og:image" content="${URL_SITE}assets/og-image-v1.jpg"`) && h.includes('<meta property="og:image:type" content="image/jpeg">') && /name="viewport"/.test(h))) {
    ok.seo = false; console.log("   SEO incomplet : " + chemin); }
  if (!(h.match(/\?v=([0-9a-f]+)/g) || []).every(x => x === "?v=" + v) || !/\?v=/.test(h)) { ok.v = false; console.log("   ?v= périmé : " + chemin); }
  if (!/<h1>(<span data-l="fr">[^<]+<\/span><span data-l="en">[^<]+<\/span><span data-l="ar">.+?<\/span>)<\/h1>/.test(h)) { ok.h1 = false; console.log("   h1 FR+EN+AR : " + chemin); }
  if (!/INSPIRE-HEP/.test(h) || !/MIT/.test(h)) ok.src = false;
  const nFr = (h.match(/data-l="fr"/g) || []).length, nEn = (h.match(/data-l="en"/g) || []).length, nAr = (h.match(/data-l="ar"/g) || []).length;
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
check("fiche : bouton Alertes Pro et alerte RSS gratuite du domaine", !!w.document.querySelector('a.btn-pro[href="../../abonnement/"]') && !!w.document.querySelector(".btn-rss"));

// ---- 7. Pages de domaine, spécialité, continent, pays, mois ------------------------------------
let okListes = true;
for (const u of urls.filter(x => /\/(domaine|specialite|continent|pays|mois)\//.test(x))) {
  const chemin = u.replace(URL_SITE, "") + "index.html";
  const [, type, slug] = chemin.match(/^(domaine|specialite|continent|pays|mois)\/([^/]+)\//);
  const attendu = avenir.filter(c => type === "domaine" ? c.domaines.includes(slug) : type === "specialite" ? c.specialites.includes(slug) :
    type === "continent" ? c.continent === slug : type === "pays" ? c.pays === slug.toUpperCase() && c.mode !== "en-ligne" : c.debut.slice(0, 7) === slug).length;
  const h = lire(chemin);
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
check("manifeste : id unique /conferences-alertes/, icônes 192/512/maskable présentes", mani.id === "/conferences-alertes/" && mani.start_url === "./" &&
  mani.icons.length === 3 && mani.icons.every(ic => existsSync(join(root, ic.src))) && mani.icons.some(ic => ic.purpose === "maskable"));
check("icône de la famille (logo SVG avec accent doré #F2B33D, sans texte)", /#F2B33D/i.test(lire("assets/logo.svg")) && !/<text/.test(lire("assets/logo.svg")));

// ---- 10. Sécurité, robots d'IA, anti-copie, secrets, données personnelles, concurrents ----------------
const robots = lire("robots.txt");
const blocs = robots.split(/\n\s*\n/).map(b => b.trim());
const interdit = ua => blocs.some(b => b.split("\n").some(l => l.trim().toLowerCase() === "user-agent: " + ua.toLowerCase()) && /^Disallow: \/\s*$/m.test(b));
const IA = ["GPTBot", "ChatGPT-User", "OAI-SearchBot", "ClaudeBot", "Claude-Web", "anthropic-ai", "CCBot", "Google-Extended", "Applebot-Extended",
  "PerplexityBot", "Bytespider", "Amazonbot", "Meta-ExternalAgent", "FacebookBot", "Diffbot", "Omgilibot", "cohere-ai", "ImagesiftBot",
  "HTTrack", "WebCopier", "WebZIP", "Offline Explorer", "wget", "SiteSnagger"];
check(`robots.txt : les ${IA.length} robots d'IA et aspirateurs sont interdits`, IA.every(interdit));
check("robots.txt : Googlebot, Bingbot et les autres restent autorisés ; sitemap indiqué", ["Googlebot", "Bingbot", "*"].every(u => !interdit(u)) &&
  /Sitemap: https:\/\/ah6259\.github\.io\/conferences-alertes\/sitemap\.xml/.test(robots));
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
check("anti-copie : le texte copié reçoit « Source : … — © … tous droits réservés »", /Source : https:\/\/ah6259\.github\.io\/conferences-alertes\//.test(copie) && /tous droits réservés/.test(copie));
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
check("abonnement : prix tout de suite (9 DT / mois ou 79 DT / an), essai 14 jours, sans engagement au-delà d'un an, pas de renouvellement automatique",
  /9 DT \/ mois ou 79 DT \/ an/.test(texte(d.getElementById("abo-prix"))) && /14 jours d'essai gratuit/.test(ta) && /Sans engagement au-delà d'un an/.test(ta) && /Pas de renouvellement automatique/.test(ta));
const pay = d.getElementById("paiement");
check("bouton « Paiement » qui déplie D17, IZI, Wafacash au 24 321 390 + montant + motif", pay && pay.tagName === "DETAILS" && !pay.open &&
  ["D17", "IZI", "Wafacash"].every(m => texte(pay).includes(m)) && (texte(pay).match(/24 321 390/g) || []).length >= 3 && /Motif/.test(texte(pay)));
check("paiement : ligne honnête pour l'étranger (carte : bientôt ; WhatsApp)", /Paiement par carte pour l'étranger : bientôt ; écrivez-nous sur WhatsApp/.test(texte(pay)));
const wa = d.getElementById("abo-preuve");
check("bouton vert « preuve de paiement » vers wa.me/21624321390 avec texte prérempli", wa && /^https:\/\/wa\.me\/21624321390\?text=/.test(wa.href) && /preuve de paiement/.test(decodeURIComponent(wa.href)));
const fa = d.getElementById("abo-form");
check("formulaire : Formspree mwlpakqj, nom, institution, pays, téléphone, e-mail, spécialités, formule, conditions",
  fa.getAttribute("action") === "https://formspree.io/f/mwlpakqj" && ["nom", "etablissement", "pays", "telephone", "email", "conditions", "formule"].every(n => fa.querySelector(`[name="${n}"]`)) &&
  fa.querySelectorAll('input[name="specialites"]').length === new Set(avenir.flatMap(c => c.specialites)).size);
// envoi simulé
const envois = [];
w.fetch = (u, o) => { envois.push({ u, o }); return Promise.resolve({ ok: true, status: 200 }); };
fa.querySelector('[name="nom"]').value = "Pr Test"; fa.querySelector('[name="etablissement"]').value = "Université X"; fa.querySelector('[name="pays"]').value = "Tunisie";
fa.querySelector('[name="telephone"]').value = "+216 24 000 000"; fa.querySelector('[name="email"]').value = "prof@example.org";
fa.querySelector('input[name="specialites"]').checked = true; fa.querySelector('#abo-conditions').checked = true;
fa.dispatchEvent(new w.Event("submit", { bubbles: true, cancelable: true }));
await new Promise(r => setTimeout(r, 30));
const corps = envois[0] ? Object.fromEntries([...envois[0].o.body.entries()]) : {};
check("inscription simulée : envoi Formspree avec spécialités en une ligne et ligne « pour_activer »",
  envois.length === 1 && envois[0].u === "https://formspree.io/f/mwlpakqj" && corps.specialites && /specialites: /.test(corps.pour_activer || "") && corps.telephone === "+21624000000");
check("après l'envoi : confirmation, paiement et Telegram affichés", d.getElementById("abo-form").hidden && !d.getElementById("apres-abo").hidden);
w = await page("abonnement/conditions/index.html", "lang=fr");
const tc = texte(w.document.querySelector("main"));
check("conditions : vendeur = l'éditeur du site, prix, essai, paiement, pas de renouvellement, aucun remboursement, données personnelles, INPDP",
  /vendu par l'éditeur du site/.test(tc) && /9 DT par mois ou 79 DT par an/.test(tc) && /14 premiers jours sont gratuits/.test(tc) && /D17, IZI ou Wafacash/.test(tc) &&
  /aucun renouvellement automatique/.test(tc) && /Aucune période déjà payée n'est remboursée/.test(tc) && /Données personnelles/.test(tc) && /INPDP/.test(tc));

console.log(`\n${total - erreurs}/${total} vérifications réussies` + (erreurs ? ` — ${erreurs} ÉCHEC(S) : ne pas publier.` : " — tout est bon."));
process.exit(erreurs ? 1 : 0);
