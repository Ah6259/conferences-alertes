/* Inscription « Alertes Pro » (page abonnement/) — même mécanique que le site Appels d'offres.
   - Rien n'est envoyé sans clic sur « Envoyer mon inscription ».
   - Envoi à Formspree (formulaire mwlpakqj, le même que « Votre avis ») sans quitter la page.
   - Les spécialités cochées sont envoyées en UNE ligne (ex. « vision, langage »), et une ligne « pour_activer »
     prête à recopier dans le bouton GitHub « activer-abonne » du dépôt privé.
   - Après l'envoi : confirmation, modes de paiement (avec la ligne « étranger ») et instructions Telegram.
   - Fichier externe : aucun script en ligne (CSP). Textes en français, anglais et arabe selon la langue de la page. */
(function () {
  var ADRESSE = "https://formspree.io/f/mwlpakqj";
  var lg = function () { var l = document.documentElement.lang; return l === "ar" || l === "fr" ? l : "en"; };
  var T = function (fr, en, a) { return lg() === "ar" ? a : lg() === "fr" ? fr : en; };

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

  // Essai IMMÉDIAT (14/10/2026, règle commune § 15) : même calcul que decoder_choix() du robot privé :
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
      var fini = function () {
        var c = document.getElementById("abo-code"), o = document.getElementById("abo-ouvrir-tg");
        if (c) c.textContent = code;
        if (o) o.setAttribute("href", lien);
        // liens WhatsApp : on ajoute le nom de l'abonné au message prérempli
        var liens = document.querySelectorAll("#abo-preuve, #abo-preuve-apres, #abo-etranger, #abo-etranger-apres");
        for (var i = 0; i < liens.length; i++) {
          var base = liens[i].getAttribute("data-texte") || "";
          liens[i].setAttribute("href", "https://wa.me/21624321390?text=" + encodeURIComponent(base + val("nom") + " (" + val("pays") + ") — code " + code));
        }
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
        " ; specialites: " + specs.join(",") + " ; langue: " + lg());
      donnees.set("code", code);                               // code de l'essai (motif du paiement)
      bouton.disabled = true;
      dire("", "Envoi…", "Sending…", "جارٍ الإرسال…");
      fetch(ADRESSE, { method: "POST", body: donnees, headers: { "Accept": "application/json" } })
        .then(function (r) {
          if (!r.ok) throw new Error("HTTP " + r.status);
          dire("ok", "Merci ! Votre inscription a bien été envoyée.", "Thank you! Your sign-up has been sent.", "شكرًا! تم إرسال تسجيلك.");
          fini();
        })
        .catch(function () {
          // l'essai ne dépend pas de cet envoi : le robot Telegram le crée seul ; on continue quand même
          dire("", "Inscription non envoyée (connexion), mais votre essai fonctionne : ouvrez Telegram ci-dessous.",
               "Sign-up not sent (connection), but your trial works: open Telegram below.",
               "لم يُرسل التسجيل (الاتصال)، لكن تجربتك تعمل: افتح تيليغرام أسفله.");
          fini();
        })
        .then(function () { bouton.disabled = false; });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", brancher);
  else brancher();
})();
