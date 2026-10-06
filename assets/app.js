/* Liste des conférences : recherche (sans accents, FR/EN/AR), filtres domaine / spécialité / lieu / format / date limite / mois, tri.
   Tout est calculé avec la date du VISITEUR : une conférence terminée disparaît, la prochaine date limite est choisie,
   étiquettes « J-7 … J-1 / Dernier jour », section « Dates limites cette semaine ». ?jour=AAAA-MM-JJ sert aux tests. */
(function () {
  const JOUR = 86400000;
  const params = new URLSearchParams(location.search);
  function aujourdHui() {
    const p = params.get("jour");
    if (p && /^\d{4}-\d{2}-\d{2}$/.test(p)) return p;
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  }
  const ecart = (a, b) => Math.round((Date.parse(a + "T00:00:00Z") - Date.parse(b + "T00:00:00Z")) / JOUR);
  const fr = d => `${d.slice(8, 10)}/${d.slice(5, 7)}/${d.slice(0, 4)}`;
  const normaliser = t => (t || "").toLowerCase().normalize("NFKD").replace(/[\p{M}ـ]/gu, "")
    .replace(/[أإآٱ]/g, "ا").replace(/ة/g, "ه").replace(/ى/g, "ي").replace(/[’'`]/g, " ").replace(/\s+/g, " ").trim();

  const PAR_PAGE = 15;
  const RAPPEL = 7;
  const FILTRES = ["f-dom", "f-spec", "f-cont", "f-mode", "f-limite", "f-mois", "f-tri"];
  let pret = false, cartes = [], liste = null, montrees = PAR_PAGE, cible = "";

  function rappel(reste) {
    if (reste === null || reste < 0 || reste > RAPPEL) return null;
    if (reste === 0) return T("Dernier jour", "Last day", "آخر يوم");
    return T(`J-${reste}`, `D-${reste}`, reste === 1 ? "بقي يوم" : reste === 2 ? "بقي يومان" : `بقيت ${iso(reste)} أيام`);
  }
  const dansJours = n => n === 0 ? T("aujourd'hui !", "today!", "اليوم!") : n === 1 ? T("demain !", "tomorrow!", "غدًا!")
    : T(`dans ${n} jours`, `in ${n} days`, `بعد ${iso(n)} يومًا`);

  // Prochaine date limite de soumission (date du visiteur) ; "" si toutes passées
  const prochaine = (c, jour) => (c.dataset.limites || "").split(" ").filter(Boolean).find(d => d >= jour) || "";

  function etatCarte(c, jour) {
    c.dataset.fini = c.dataset.fin && c.dataset.fin < jour ? "1" : "";
    const lim = prochaine(c, jour);
    const reste = lim ? ecart(lim, jour) : null;
    c.dataset.prochaine = lim;
    c.dataset.reste = reste === null ? "" : reste;
    c.classList.toggle("urgent", reste !== null && reste < 7);
    c.classList.toggle("ferme", !lim);
    c.querySelectorAll(".dl, .dl-quoi").forEach(b => { b.hidden = b.dataset.d !== lim; });
    const f = c.querySelector(".dl-ferme");
    if (f) f.hidden = !!lim;
    const s = c.querySelector(".reste");
    if (s) s.textContent = lim ? dansJours(reste) : "";
    const ev = c.querySelector(".reste-ev");
    if (ev && c.dataset.debut) {
      const n = ecart(c.dataset.debut, jour);
      ev.textContent = n > 0 ? dansJours(n) : T("en cours", "ongoing", "جارٍ الآن");
    }
    const r = c.querySelector(".rappel"), txt = rappel(reste);
    if (r) { r.hidden = !txt; r.textContent = txt || ""; r.classList.toggle("fort", reste !== null && reste <= 2); }
    const nv = c.querySelector(".nouveau");
    if (nv) nv.hidden = !(c.dataset.ajout && ecart(jour, c.dataset.ajout) <= 7 && ecart(jour, c.dataset.ajout) >= 0);
  }

  function remplirOptions(sel, garde) {
    if (!sel) return;
    sel.querySelectorAll("option").forEach(o => {
      const base = T(o.dataset.fr, o.dataset.en, o.dataset.ar);
      if (sel.id === "f-tri" || sel.id === "f-limite") { o.textContent = base; return; }
      const n = cartes.filter(c => garde(c, sel.id, o.value)).length;
      o.textContent = base + " (" + n + ")";
    });
  }

  const texteCarte = c => {
    if (c._q === undefined) {
      const copie = c.cloneNode(true);
      copie.querySelectorAll(".reste,.reste-ev,.rappel,.nouveau,.cf-liens,.source,.cf-infos > div > span").forEach(x => x.remove());
      // les petits textes (spécialité, pays…) sont cherchés dans les TROIS langues : « Japon » = « Japan » = « اليابان »
      const X = window.TEXTES || {};
      const trad = [...copie.querySelectorAll("[data-t]")].map(el => (X[el.dataset.t] || []).join(" ")).join(" ");
      c._q = normaliser(copie.textContent + " " + trad + " " + c.id);
    }
    return c._q;
  };

  function valeur(id) { const s = document.getElementById(id); return s ? s.value : ""; }

  function appliquer() {
    const jour = aujourdHui();
    cartes.forEach(c => etatCarte(c, jour));
    const v = {};
    FILTRES.forEach(id => { v[id] = valeur(id); });
    const fq = document.getElementById("f-q");
    if (fq) fq.placeholder = T(fq.dataset.fr, fq.dataset.en, fq.dataset.ar);
    const mots = normaliser(fq ? fq.value : "").split(" ").filter(Boolean);
    // garde(c, sauf, valeurForcee) : la carte passe-t-elle tous les filtres ? (sauf = filtre remplacé par valeurForcee, pour les compteurs)
    const garde = (c, sauf, forcee) => {
      const val = id => id === sauf ? forcee : v[id];
      if (c.dataset.fini) return false;
      const d = val("f-dom"), s = val("f-spec"), co = val("f-cont"), m = val("f-mode"), l = val("f-limite"), mo = val("f-mois");
      if (d && !c.dataset.dom.split(" ").includes(d)) return false;
      if (s && !c.dataset.spec.split(" ").includes(s)) return false;
      if (co && c.dataset.cont !== co) return false;
      if (m && c.dataset.mode !== m) return false;
      if (mo && (c.dataset.debut || "").slice(0, 7) !== mo) return false;
      if (l) {
        if (!c.dataset.prochaine) return false;
        if (l !== "ouverte" && +c.dataset.reste > +l) return false;
      }
      return mots.every(x => texteCarte(c).includes(x));
    };
    FILTRES.forEach(id => remplirOptions(document.getElementById(id), garde));
    let visibles = 0;
    cartes.forEach(c => { const ok = garde(c); c.dataset.ok = ok ? "1" : ""; if (ok) visibles++; });
    const tri = v["f-tri"] || "limite";
    const tries = cartes.slice().sort((a, b) => {
      if (tri === "limite") return (a.dataset.prochaine || "9999").localeCompare(b.dataset.prochaine || "9999") || a.dataset.debut.localeCompare(b.dataset.debut);
      if (tri === "ajout") return (b.dataset.ajout || "").localeCompare(a.dataset.ajout || "") || a.dataset.debut.localeCompare(b.dataset.debut);
      return a.dataset.debut.localeCompare(b.dataset.debut) || a.id.localeCompare(b.id);
    });
    tries.forEach(c => liste.appendChild(c));
    let rang = 0;
    tries.forEach(c => { c.hidden = !c.dataset.ok || (rang++ >= montrees && c.id !== cible); });
    const plus = document.getElementById("plus");
    if (plus) {
      const reste = visibles - Math.min(visibles, montrees);
      plus.hidden = reste <= 0;
      plus.textContent = T(`Afficher plus (${reste} autre${reste > 1 ? "s" : ""})`, `Show more (${reste} more)`, `عرض المزيد (${iso(reste)})`);
    }
    const compte = document.getElementById("compte");
    if (compte) {
      compte.innerHTML = "";
      const sp = document.createElement("span");
      sp.textContent = T(`${visibles} conférence${visibles > 1 ? "s" : ""} à venir`, `${visibles} upcoming conference${visibles > 1 ? "s" : ""}`, `${iso(visibles)} مؤتمر قادم`);
      compte.appendChild(sp);
      if (FILTRES.some(id => id !== "f-tri" && v[id]) || mots.length) {
        const b = document.createElement("button");
        b.type = "button"; b.id = "effacer"; b.textContent = T("Tout afficher", "Show all", "عرض الكل");
        compte.appendChild(b);
      }
    }
    const vide = document.getElementById("vide");
    if (vide) vide.hidden = visibles > 0;

    // Résumé (accueil), recalculé avec la date du visiteur
    const encore = cartes.filter(c => !c.dataset.fini);
    const rA = document.getElementById("r-avenir");
    if (rA) rA.querySelector("b").textContent = encore.length;
    const rL = document.getElementById("r-limites");
    if (rL) rL.querySelector("b").textContent = encore.filter(c => c.dataset.prochaine && +c.dataset.reste <= 30).length;

    // « Dates limites cette semaine » : les 6 plus proches dans les 7 jours
    const bt = document.getElementById("bientot");
    if (bt) {
      const proches = encore.filter(c => c.dataset.prochaine && +c.dataset.reste <= RAPPEL)
        .sort((a, b) => (+a.dataset.reste - +b.dataset.reste) || a.dataset.debut.localeCompare(b.dataset.debut)).slice(0, 6);
      const ol = document.getElementById("bientot-liste");
      ol.innerHTML = "";
      proches.forEach(c => {
        const li = document.createElement("li");
        const a = document.createElement("a");
        a.href = "#" + c.id;
        const et = document.createElement("span");
        et.className = "rappel" + (+c.dataset.reste <= 2 ? " fort" : "");
        et.textContent = rappel(+c.dataset.reste);
        const ob = document.createElement("span");
        ob.className = "b-objet";
        ob.dir = "ltr";
        const sg = c.querySelector("h3 .sigle");
        ob.textContent = sg ? sg.textContent : c.id;
        const pl = document.createElement("small");
        const p = c.querySelector(".pastille [data-t]");
        pl.textContent = p ? p.textContent : "";
        a.append(et, ob, pl);
        li.appendChild(a);
        ol.appendChild(li);
      });
      bt.hidden = proches.length === 0;
    }
    avertissement(jour);
  }

  // Avertissement daté : données anciennes (selon la date du visiteur) ou panne signalée par le robot
  function avertissement(jour) {
    const al = document.getElementById("alerte-panne");
    if (!al) return;
    const maj = (document.body.dataset.maj || "").slice(0, 10);
    const age = maj ? ecart(jour, maj) : 99;
    if (age >= 2 || document.body.dataset.panne === "1") {
      al.classList.add("on");
      al.textContent = maj
        ? T(`⚠️ Les sources n'ont pas pu être lues depuis le ${fr(maj)} : la liste peut être incomplète. Vérifiez toujours le site officiel de la conférence.`,
            `⚠️ The sources could not be read since ${fr(maj)}: the list may be incomplete. Always check the conference's official website.`,
            `⚠️ تعذّرت قراءة المصادر منذ ${iso(fr(maj))}: قد تكون القائمة ناقصة. تثبّت دائمًا من الموقع الرسمي للمؤتمر.`)
        : T("⚠️ Données indisponibles pour le moment.", "⚠️ Data unavailable for now.", "⚠️ المعطيات غير متوفرة حاليًا.");
    } else al.classList.remove("on");
  }

  // Fiche d'une conférence : dates limites passées barrées, prochaine mise en avant (date du visiteur)
  function fiche() {
    const jour = aujourdHui();
    document.querySelectorAll(".limites li[data-d]").forEach(li => li.classList.toggle("passe", li.dataset.d < jour));
    avertissement(jour);
  }

  function allerA() {
    let id = "";
    try { id = decodeURIComponent((location.hash || "").slice(1)); } catch (e) { return; }
    const c = id && document.getElementById(id);
    if (!c || !c.classList.contains("cf") || c.parentNode !== liste) return;
    cible = id;
    appliquer();
    document.querySelectorAll(".cf.visee").forEach(x => x.classList.remove("visee"));
    c.classList.add("visee");
    if (c.scrollIntoView) c.scrollIntoView({ block: "center" });
  }

  document.addEventListener("langue", () => {
    if (!pret) {
      liste = document.getElementById("liste");
      if (!liste) { fiche(); return; }
      cartes = Array.from(liste.querySelectorAll(".cf"));
      cartes.forEach(texteCarte);
      FILTRES.forEach(id => {
        const s = document.getElementById(id);
        if (s) s.addEventListener("change", () => { montrees = PAR_PAGE; appliquer(); });
      });
      const fq = document.getElementById("f-q");
      if (fq) {
        if (params.get("q")) fq.value = params.get("q").slice(0, 100);
        fq.addEventListener("input", () => { montrees = PAR_PAGE; appliquer(); });
      }
      const plus = document.getElementById("plus");
      if (plus) plus.addEventListener("click", () => { montrees += PAR_PAGE; appliquer(); });
      document.addEventListener("click", e => {
        if (e.target.id !== "effacer") return;
        FILTRES.concat("f-q").forEach(id => { const s = document.getElementById(id); if (s && id !== "f-tri") s.value = ""; });
        montrees = PAR_PAGE;
        appliquer();
      });
      // Filtres dans l'adresse : ?domaine=physique&specialite=astro&continent=europe&limite=30
      [["f-dom", "domaine"], ["f-spec", "specialite"], ["f-cont", "continent"], ["f-mode", "format"], ["f-limite", "limite"], ["f-mois", "mois"]].forEach(([id, p]) => {
        const s = document.getElementById(id), val = params.get(p);
        if (s && val && Array.from(s.options).some(o => o.value === val)) s.value = val;
      });
      window.addEventListener("hashchange", allerA);
      pret = true;
    }
    if (liste) appliquer(); else fiche();
    if (liste && location.hash) allerA();
  });
})();
