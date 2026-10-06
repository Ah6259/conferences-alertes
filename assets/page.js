/* Langue (français / anglais / arabe), en-tête et pied de page communs, protection légère contre la copie */
(function () {
  const html = document.documentElement;
  const racine = html.dataset.racine || "";
  const LANGUES = ["fr", "en", "ar"];
  let langue = "en";
  try {
    const n = (navigator.language || "").slice(0, 2);
    langue = localStorage.getItem("langue") || (LANGUES.includes(n) ? n : "en");
  } catch (e) {}
  const demande = new URLSearchParams(location.search).get("lang");
  if (LANGUES.includes(demande)) langue = demande;
  if (!LANGUES.includes(langue)) langue = "en";

  // T(fr, en, ar) : texte dans la langue de la page
  window.T = (fr, en, ar) => html.lang === "ar" ? ar : html.lang === "fr" ? fr : en;
  // Nombres et dates isolés dans un texte arabe (U+2066 … U+2069)
  window.iso = t => "⁦" + t + "⁩";

  function cadre() {
    const e = document.getElementById("entete");
    if (e) e.innerHTML = `
      <div class="wrap">
        <a class="logo" href="${racine || "./"}">
          <img class="logo-mark" src="${racine}assets/logo.svg" alt="" width="34" height="34">
          <span class="logo-nom">${T("Radar des conférences", "Conference Radar", "رادار المؤتمرات")}
            <small>${T("Conférences scientifiques · dates limites", "Academic conferences · deadlines", "مؤتمرات علمية · آجال الإرسال")}</small></span>
        </a>
        <div class="entete-boutons">
          <a class="entete-pro" href="${racine}abonnement/">${T("Alertes Pro", "Pro Alerts", "تنبيهات Pro")}</a>
          <select class="langue" aria-label="Langue / Language / اللغة">
            <option value="fr"${html.lang === "fr" ? " selected" : ""}>FR</option>
            <option value="en"${html.lang === "en" ? " selected" : ""}>EN</option>
            <option value="ar"${html.lang === "ar" ? " selected" : ""}>ع</option>
          </select>
        </div>
      </div>`;
    const p = document.getElementById("pied");
    const maj = document.body.dataset.majTexte || "";
    if (p) p.innerHTML = `
      <div class="wrap">
        <div class="pied-logo"><img src="${racine}assets/logo.svg" alt="" width="24" height="24"> ${T("Radar des conférences", "Conference Radar", "رادار المؤتمرات")}</div>
        <nav>
          <a href="${racine || "./"}">${T("Toutes les conférences", "All conferences", "كل المؤتمرات")}</a>
          <a href="${racine}#domaines">${T("Par domaine", "By field", "حسب المجال")}</a>
          <a href="${racine}#specialites">${T("Par spécialité", "By specialty", "حسب التخصص")}</a>
          <a href="${racine}#lieux">${T("Par pays", "By country", "حسب البلد")}</a>
          <a href="${racine}flux/">${T("Alertes gratuites (RSS)", "Free alerts (RSS)", "تنبيهات مجانية (RSS)")}</a>
          <a href="${racine}abonnement/">${T("Alertes Pro (abonnement)", "Pro Alerts (subscription)", "تنبيهات Pro (اشتراك)")}</a>
          <a href="${racine}publier/">${T("Signaler une conférence", "Submit a conference", "أضف مؤتمرًا")}</a>
          <a href="${racine}a-propos/">${T("À propos et sources", "About and sources", "من نحن والمصادر")}</a>
          <a href="${racine}#avis">${T("Votre avis", "Feedback", "رأيك")}</a>
        </nav>
        <p>${T("Sources : listes ouvertes de conférences (licence MIT : CCF Deadlines, AI Deadlines, HCI Deadlines, Neuro Deadlines, Bioinformatics Conferences, RoboDDL), base INSPIRE-HEP (CC0) et pages officielles des organisateurs (comptabilité, finance, finance islamique). Chaque conférence renvoie à son site officiel.",
               "Sources: open conference lists (MIT licence: CCF Deadlines, AI Deadlines, HCI Deadlines, Neuro Deadlines, Bioinformatics Conferences, RoboDDL), the INSPIRE-HEP database (CC0) and official organiser pages (accounting, finance, Islamic finance). Every conference links to its official website.",
               `المصادر: قوائم مؤتمرات مفتوحة (رخصة ${iso("MIT")}) وقاعدة ${iso("INSPIRE-HEP")} (${iso("CC0")}) والصفحات الرسمية للمنظمين (المحاسبة، المالية، التمويل الإسلامي). كل مؤتمر مرفق برابط موقعه الرسمي.`)} <a href="${racine}a-propos/">${T("Détails", "Details", "التفاصيل")}</a></p>
        ${maj ? `<p>${T("Dernière lecture des sources : ", "Sources last read: ", "آخر قراءة للمصادر: ")}${iso(maj)}</p>` : ""}
        <p>${T("Ce site n'est pas officiel : seul le site de chaque conférence fait foi. Les noms des conférences et organisateurs appartiennent à leurs propriétaires.",
               "This site is not official: only each conference's website is authoritative. Conference and organiser names belong to their owners.",
               "هذا الموقع ليس رسميًا: موقع كل مؤتمر هو المرجع الوحيد. أسماء المؤتمرات والمنظمين ملك لأصحابها.")}</p>
        <p>© 2026 ${T("Radar des conférences — tous droits réservés.", "Conference Radar — all rights reserved.", "رادار المؤتمرات — جميع الحقوق محفوظة.")}</p>
      </div>`;
    document.querySelectorAll("select.langue").forEach(s =>
      s.addEventListener("change", () => appliquer(s.value)));
  }

  // Dates dans la langue de la page : « 5–7 oct. 2026 », « 5–7 Oct 2026 », « ⁦5–7⁩ أكتوبر ⁦2026⁩ »
  const MOIS = {
    fr: ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
    en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    ar: ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"],
  };
  window.fdate = (d1, d2) => {
    const l = html.lang in MOIS ? html.lang : "en", ar = l === "ar";
    const n = x => ar ? iso(x) : String(x);
    const p = d => [+d.slice(0, 4), +d.slice(5, 7), +d.slice(8, 10)];
    const [a1, m1, j1] = p(d1);
    if (!d2 || d2 === d1) return `${n(j1)} ${MOIS[l][m1 - 1]} ${n(a1)}`;
    const [a2, m2, j2] = p(d2);
    if (a1 === a2 && m1 === m2) return `${n(j1 + "–" + j2)} ${MOIS[l][m1 - 1]} ${n(a1)}`;
    if (a1 === a2) return `${n(j1)} ${MOIS[l][m1 - 1]} – ${n(j2)} ${MOIS[l][m2 - 1]} ${n(a2)}`;
    return `${n(j1)} ${MOIS[l][m1 - 1]} ${n(a1)} – ${n(j2)} ${MOIS[l][m2 - 1]} ${n(a2)}`;
  };
  // Petits textes des cartes (attribut data-t) traduits grâce à assets/textes.js, dates mises en forme
  function traduire() {
    const i = { fr: 0, en: 1, ar: 2 }[html.lang] ?? 1;
    const X = window.TEXTES || {};
    document.querySelectorAll("[data-t]").forEach(el => { const v = X[el.dataset.t]; if (v) el.textContent = v[i]; });
    document.querySelectorAll(".dt[data-d1]").forEach(el => { el.textContent = fdate(el.dataset.d1, el.dataset.d2); });
    document.querySelectorAll(".dl[data-d]").forEach(el => { el.textContent = fdate(el.dataset.d); });
  }

  function appliquer(l) {
    if (!LANGUES.includes(l)) l = "en";
    html.lang = l; html.dir = l === "ar" ? "rtl" : "ltr";
    try { localStorage.setItem("langue", l); } catch (e) {}
    cadre();
    traduire();
    document.dispatchEvent(new Event("langue"));
  }
  document.addEventListener("DOMContentLoaded", () => appliquer(langue));

  // ---- Protection légère contre la copie (sans gêner les visiteurs) -------------------------
  // 1) Pas d'affichage dans le cadre (iframe) d'un autre site.
  try {
    if (window.top !== window.self && window.top.location.hostname !== location.hostname) window.top.location = location.href;
  } catch (e) { try { window.top.location = location.href; } catch (e2) {} }
  // 2) Images et photos : ni clic droit ni glisser-déposer.
  const estImage = t => t && t.closest && t.closest("img, svg, .hero-photo");
  document.addEventListener("contextmenu", e => { if (estImage(e.target) && !e.target.closest("a, input, textarea")) e.preventDefault(); });
  document.addEventListener("dragstart", e => { if (estImage(e.target)) e.preventDefault(); });
  // 3) Texte copié depuis une carte : on ajoute la source et la mention « tous droits réservés ».
  document.addEventListener("copy", e => {
    const sel = window.getSelection ? String(window.getSelection()) : "";
    const n = window.getSelection && window.getSelection().anchorNode;
    const el = n && (n.nodeType === 1 ? n : n.parentElement);
    if (!sel || !el || !el.closest || !el.closest(".cf, .liste, main") || el.closest("input, textarea")) return;
    if (!e.clipboardData) return;
    e.clipboardData.setData("text/plain", sel + "\n\nSource : " + location.href.split("#")[0] + " — © Conference Radar / Radar des conférences, tous droits réservés.");
    e.preventDefault();
  });
})();

/* Installation sur le téléphone : service worker PRUDENT (sw.js : réseau d'abord pour les pages et les données).
   Seulement en https (jamais en file: pendant les tests locaux). */
if ("serviceWorker" in navigator && location.protocol === "https:") {
  window.addEventListener("load", () => {
    try { navigator.serviceWorker.register("/conferences-alertes/sw.js", { scope: "/conferences-alertes/" }).catch(() => {}); } catch (e) { /* rien : le site marche sans */ }
  });
}
