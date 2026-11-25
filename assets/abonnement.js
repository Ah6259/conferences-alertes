/* Inscription « Alertes Pro » (page abonnement/) — même mécanique que le site Appels d'offres.
   - Rien n'est envoyé sans clic sur « Envoyer mon inscription ».
   - Envoi à Formspree (formulaire mwlpakqj, le même que « Votre avis ») sans quitter la page.
   - Les spécialités cochées sont envoyées en UNE ligne (ex. « vision, langage »), et une ligne « pour_activer »
     prête à recopier dans le bouton GitHub « activer-abonne » du dépôt privé.
   - Après l'envoi : confirmation, code en GROS + « Vous le recevez aussi par e-mail » (parcours commun des Pass, règle commune § 70,
     25/11/2026), instructions Telegram (et, si le site redevient payant : paiement avec le code pour motif, WhatsApp pré-rempli).
   - Le téléphone se souvient de la commande (localStorage « pass-commande » : code, formule, date, lien Telegram ; JAMAIS nom,
     institution, pays, téléphone ni e-mail ; gardée 60 jours) : en revenant, bandeau « Votre commande en attente » + « Ouvrir
     Telegram » + « Nouvelle commande ». Pas de vérification d'activation sur ce site (alertes sur Telegram).
   - Fichier externe : aucun script en ligne (CSP). Textes en français, anglais et arabe selon la langue de la page. */
(function () {
  var ADRESSE = "https://formspree.io/f/mwlpakqj";
  var lg = function () { var l = document.documentElement.lang; return l === "ar" || l === "fr" ? l : "en"; };
  var T = function (fr, en, a) { return lg() === "ar" ? a : lg() === "fr" ? fr : en; };
  var SITE = ["Radar des conférences", "Conference Radar", "رادار المؤتمرات"], WA = "21624321390";
  var FORMULES = { "1 mois": ["1 mois", "1 month", "شهر"], "1 an": ["1 an", "1 year", "سنة"] };
  // « Vous le recevez aussi par e-mail » : l'e-mail automatique n'est pas encore en service (25/11/2026) -> phrase cachée.
  // Le jour où il marche : EMAIL_AUTO = true (les éléments [data-email-auto] s'affichent).
  var EMAIL_AUTO = false;
  var CLE = "pass-commande", JOURS = 60, FORMAT = /^[A-HJ-NP-Z2-9]{6}$/;
  var formuleLue = function (f) { var x = FORMULES[f]; return x ? T(x[0], x[1], x[2]) : (f || ""); };
  // message WhatsApp de la preuve de paiement (seulement si le site redevient payant) : code + formule déjà dedans
  function lienWa(code, formule) {
    var fo = formule ? " — " + formuleLue(formule) : "";
    return "https://wa.me/" + WA + "?text=" + encodeURIComponent(T(
      "Voici ma preuve de paiement — " + SITE[0] + " — code " + code + fo,
      "Here is my payment proof — " + SITE[1] + " — code " + code + fo,
      "هذا وصل الدفع — " + SITE[2] + " — الرمز " + code + fo));
  }
  // remplit toute la page : code (gros + motif), formule, liens WhatsApp, liens Telegram
  function remplir(code, formule, tg) {
    var i, x = document.querySelectorAll("[data-code]");
    for (i = 0; i < x.length; i++) x[i].textContent = code;
    x = document.querySelectorAll("[data-formule]");
    for (i = 0; i < x.length; i++) x[i].textContent = formuleLue(formule);
    x = document.querySelectorAll("#abo-preuve, #abo-preuve-apres, #abo-preuve-attente");
    for (i = 0; i < x.length; i++) x[i].setAttribute("href", lienWa(code, formule));
    x = document.querySelectorAll("#abo-etranger, #abo-etranger-apres, #abo-etranger-attente");
    for (i = 0; i < x.length; i++) x[i].setAttribute("href", "https://wa.me/" + WA + "?text=" + encodeURIComponent((x[i].getAttribute("data-texte") || "") + "code " + code));
    x = document.querySelectorAll("[data-email-auto]");
    for (i = 0; i < x.length; i++) x[i].hidden = !EMAIL_AUTO;
    x = document.querySelectorAll("a[data-tg]");
    for (i = 0; i < x.length; i++) if (tg) x[i].setAttribute("href", tg);
  }
  function aujourdhui() { return new Date().toISOString().slice(0, 10); }
  function memoriser(code, formule, tg) {
    try { localStorage.setItem(CLE, JSON.stringify({ code: code, formule: formule, date: aujourdhui(), tg: tg })); } catch (e) {}
  }
  function oublier() { try { localStorage.removeItem(CLE); } catch (e) {} }
  // commande gardée : seulement si le code est au bon format, le lien Telegram est le nôtre et elle a moins de 60 jours
  function relire() {
    var c = null;
    try { c = JSON.parse(localStorage.getItem(CLE) || "null"); } catch (e) { c = null; }
    if (!c) return null;
    var t = Date.parse(String(c.date || "") + "T00:00:00Z");
    if (!FORMAT.test(c.code || "") || !(t > 0) || Date.now() - t > JOURS * 864e5 || (c.tg && !/^https:\/\/t\.me\//.test(c.tg))) { oublier(); return null; }
    return c;
  }
  window.PASS_COMMANDE = { cle: CLE, jours: JOURS, relire: relire };

  function coches(form, nom) {
    var res = [], c = form.querySelectorAll('input[name="' + nom + '"]');
    for (var i = 0; i < c.length; i++) if (c[i].checked) res.push(c[i].value);
    return res;
  }
  // téléphone international : 8 à 15 chiffres (on garde le « + » de l'indicatif)
  function telephone(v) {
    var brut = String(v || "").trim();
    var n = brut.replace(/\D/g, "");
    if (n.length < 8 || n.length > 15) return "";
    return (brut.charAt(0) === "+" || n.length > 8 ? "+" : "") + n;
  }

  // Inscription immédiate (14/10/2026, règle commune § 15 ; aucun essai depuis le 20/10/2026) : même calcul que decoder_choix() du robot privé :
  // listes TRIÉES, 5 cases par caractère, « x » = tous
  var B32 = "0123456789abcdefghijklmnopqrstuv", ALPH = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  function encoder(choix, liste) {
    if (choix.indexOf("tous") >= 0) return "x";
    var s = "";
    for (var k = 0; k < Math.ceil(liste.length / 5); k++) {
      var v = 0;
      for (var j = 0; j < 5; j++) if (5 * k + j < liste.length && choix.indexOf(liste[5 * k + j]) >= 0) v |= 1 << j;
      s += B32[v];
    }
    return s;
  }
  function nouveauCode() {
    var t = new Uint8Array(6), c = "";
    try { crypto.getRandomValues(t); } catch (e) { for (var k = 0; k < 6; k++) t[k] = Math.floor(Math.random() * 256); }
    for (var i = 0; i < 6; i++) c += ALPH[t[i] % ALPH.length];
    return c;
  }
  window.ESSAI_ALERTES = { encoder: encoder };

  function brancher() {
    var form = document.getElementById("abo-form");
    if (!form || form.getAttribute("data-branche")) return;
    form.setAttribute("data-branche", "1");
    var statut = document.getElementById("abo-status");
    var bouton = form.querySelector("button[type=submit]");
    var apres = document.getElementById("apres-abo");
    var dire = function (classe, fr, en, a) { statut.className = classe; statut.textContent = T(fr, en, a); };

    // retour sur la page : la commande en attente est montrée à la place du formulaire
    var attente = document.getElementById("abo-attente"), cmd = relire();
    if (cmd && attente) { remplir(cmd.code, cmd.formule, cmd.tg); attente.hidden = false; form.hidden = true; }
    var nouvelle = document.getElementById("abo-nouvelle");
    if (nouvelle) nouvelle.addEventListener("click", function () {
      oublier();
      if (attente) attente.hidden = true;
      if (apres) apres.hidden = true;
      form.hidden = false;
      var n = form.querySelector('[name="nom"]'); if (n && n.focus) n.focus();
    });

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (bouton.disabled) return;
      var val = function (n) { var x = form.querySelector('[name="' + n + '"]'); return x ? String(x.value || "").trim() : ""; };
      var champ = function (n) { return form.querySelector('[name="' + n + '"]'); };
      var tel = telephone(val("telephone"));
      var specs = coches(form, "specialites");
      if (!val("nom")) { dire("err", "Indiquez votre nom.", "Enter your name.", "اكتب اسمك."); champ("nom").focus(); return; }
      if (!val("etablissement")) { dire("err", "Indiquez votre université ou institution.", "Enter your university or institution.", "اكتب جامعتك أو مؤسستك."); champ("etablissement").focus(); return; }
      if (!val("pays")) { dire("err", "Indiquez votre pays.", "Enter your country.", "اكتب بلدك."); champ("pays").focus(); return; }
      if (!tel) { dire("err", "Téléphone : 8 à 15 chiffres, avec l'indicatif (ex. +216 24 321 390).", "Phone: 8 to 15 digits, with country code (e.g. +216 24 321 390).", "الهاتف: من ⁦8⁩ إلى ⁦15⁩ رقمًا مع رمز البلد."); champ("telephone").focus(); return; }
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(val("email"))) { dire("err", "Indiquez une adresse e-mail valide.", "Enter a valid e-mail address.", "اكتب بريدًا إلكترونيًا صحيحًا."); champ("email").focus(); return; }
      if (!specs.length) { dire("err", "Cochez au moins une spécialité.", "Tick at least one specialty.", "اختر تخصصًا واحدًا على الأقل."); return; }
      if (!champ("conditions").checked) { dire("err", "Cochez « J'accepte les conditions de l'abonnement ».", "Tick “I accept the subscription terms”.", "يجب الموافقة على شروط الاشتراك."); return; }

      var code = nouveauCode();
      var lien = "https://t.me/" + form.getAttribute("data-robot") + "?start=e" + code + "_" + encoder(specs, (form.getAttribute("data-specs") || "").split(","));
      var coche = form.querySelector('input[name="formule"]:checked'), formule = coche ? coche.value : "";   // gratuit : pas de formule
      var tg = form.getAttribute("data-robot") ? lien : "";
      var fini = function () {
        remplir(code, formule, tg);                            // code en gros, « Ouvrir Telegram » (et WhatsApp si payant)
        memoriser(code, formule, tg);                          // le téléphone se souvient de la commande (rien de personnel)
        form.hidden = true;
        if (apres) { apres.hidden = false; if (apres.scrollIntoView) try { apres.scrollIntoView({ block: "start" }); } catch (x) {} }
      };
      var piege = champ("_gotcha");
      if (piege && piege.value) { fini(); return; }          // rempli = robot : rien n'est envoyé

      champ("page").value = location.href.split("#")[0];
      var donnees = new FormData(form);
      donnees.delete("specialites");
      donnees.set("telephone", tel);
      donnees.set("specialites", specs.join(", "));
      donnees.set("langue", lg());
      // ligne prête pour le bouton « activer-abonne » (dépôt privé)
      donnees.set("pour_activer", "nom: " + val("nom") + " (" + val("etablissement") + ", " + val("pays") + ") ; telephone: " + tel +
        " ; specialites: " + specs.join(",") + " ; langue: " + lg() + " ; code: " + code);
      donnees.set("code", code);                               // code personnel (motif du paiement)
      bouton.disabled = true;
      dire("", "Envoi…", "Sending…", "جارٍ الإرسال…");
      fetch(ADRESSE, { method: "POST", body: donnees, headers: { "Accept": "application/json" } })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          dire("ok", "Merci ! Votre inscription a bien été envoyée.", "Thank you! Your sign-up has been sent.", "شكرًا! تم إرسال تسجيلك.");
          fini();
        })
        .catch(function () {
          // l'inscription ne dépend pas de cet envoi : le robot Telegram la crée seul ; on continue quand même
          dire("", "Inscription non envoyée (connexion), mais votre code fonctionne : ouvrez Telegram ci-dessous.",
               "Sign-up not sent (connection), but your code works: open Telegram below.",
               "لم يُرسل التسجيل (الاتصال)، لكن رمزك يعمل: افتح تيليغرام أسفله.");
          fini();
        })
        .then(function () { bouton.disabled = false; });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", brancher);
  else brancher();
})();
