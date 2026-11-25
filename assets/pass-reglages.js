/* Réglage de Radar des conférences (Alertes Pro) pour le parcours commun du Pass (assets/pass-commun.js, copie du module de
   projets-ahmed : « outils communs/pass-commun/ » ; NE PAS modifier pass-commun.js ici, voir son LISEZMOI.md). Page abonnement/
   (une seule adresse, langue choisie par le visiteur : en / fr / ar). Ici seulement ce qui est PROPRE à ce site : nom en 3 langues,
   alertes GRATUITES pour commencer (formules 1 mois / 1 an prêtes si le site redevient payant), format du code (6 caractères sans
   O/0/I/1 : celui des codes déjà donnés), téléphone international, établissement, pays, spécialités, lien Telegram avec les choix, ligne
   « pour_activer » du bouton « activer-abonne » du dépôt privé « conferences-abonnes », liens WhatsApp « depuis l'étranger ».
   Fichier externe : aucun script en ligne (CSP). */
(function () {
  var PC = window.PassCommun;
  if (!PC) return;
  // E-mail automatique (A.17) EN SERVICE depuis le 25/11/2026 ; false = phrases [data-email-auto] cachées et rien envoyé
  var EMAIL_AUTO = true;
  var EMAIL_OK = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
  PC.brancher({
    site: "conferences",                            // clé du site dans email-clients/sites.json (e-mail automatique)
    type: "alertes-gratuit",                        // alertes sur Telegram, gratuites pour commencer (pas de code à taper sur le site)
    langues: ["en", "fr", "ar"],                    // 1re = langue d'une page sans langue connue
    nomSite: { fr: "Radar des conférences", en: "Conference Radar", ar: "رادار المؤتمرات" },
    emailAuto: EMAIL_AUTO,
    ids: { form: "abo-form", statut: "abo-status", apres: "apres-abo", attente: "abo-attente", nouvelle: "abo-nouvelle" },
    code: { alphabet: "ABCDEFGHJKLMNPQRSTUVWXYZ23456789", longueur: 6 },
    formules: { "1 mois": { fr: "1 mois", en: "1 month", ar: "شهر" }, "1 an": { fr: "1 an", en: "1 year", ar: "سنة" } },
    telephone: "international",
    etapes: ["nom",
      function (c) { return c.val("etablissement") ? null : { fr: "Indiquez votre université ou institution.", en: "Enter your university or institution.", ar: "اكتب جامعتك أو مؤسستك.", champ: "etablissement" }; },
      function (c) { return c.val("pays") ? null : { fr: "Indiquez votre pays.", en: "Enter your country.", ar: "اكتب بلدك.", champ: "pays" }; },
      "telephone",
      // e-mail : même message vide ou invalide (« … : vous y recevez votre code et le lien Telegram. » quand l'e-mail automatique marche)
      function (c) {
        if (EMAIL_OK.test(c.email)) return null;
        return EMAIL_AUTO
          ? { fr: "Indiquez une adresse e-mail valide : vous y recevez votre code et le lien Telegram.", en: "Enter a valid e-mail address: you receive your code and the Telegram link there.", ar: "اكتب بريدًا إلكترونيًا صحيحًا: يصلك عليه رمزك ورابط تيليغرام.", champ: "email" }
          : { fr: "Indiquez une adresse e-mail valide.", en: "Enter a valid e-mail address.", ar: "اكتب بريدًا إلكترونيًا صحيحًا.", champ: "email" };
      },
      function (c) { return c.extra.specs.length ? null : { fr: "Cochez au moins une spécialité.", en: "Tick at least one specialty.", ar: "اختر تخصصًا واحدًا على الأقل." }; },
      "conditions"],
    // champs du site : spécialités cochées
    lire: function (c) { c.extra.specs = PC.coches(c.form, "specialites"); },
    // lien Telegram qui contient les choix (vide si le robot n'est pas réglé) : le robot crée l'inscription
    telegram: function (c) {
      var f = c.form, robot = f.getAttribute("data-robot");
      if (!robot) return "";
      return "https://t.me/" + robot + "?start=e" + c.code + "_" + PC.encoder(c.extra.specs, (f.getAttribute("data-specs") || "").split(","));
    },
    // Formspree : spécialités en UNE ligne (ex. « vision, langage ») + langue de la page ; « pour_activer » réservé ici pour garder
    // l'ordre des champs de toujours (pour_activer puis code ; le module le remplit ensuite)
    formspree: function (d, c) {
      d.delete("specialites");
      d.set("specialites", c.extra.specs.join(", "));
      d.set("langue", c.langue);
      d.set("pour_activer", "");
    },
    // ligne prête pour le bouton « activer-abonne » (dépôt privé)
    pourActiver: function (c) {
      return "nom: " + c.nom + " (" + c.val("etablissement") + ", " + c.val("pays") + ") ; telephone: " + c.tel + " ; specialites: " +
        c.extra.specs.join(",") + " ; langue: " + c.langue + " ; code: " + c.code;
    },
    // champs du site dans la demande d'e-mail automatique (noms attendus par verifier() du service, sites.json « champs »)
    email: function (c) { return { specialites: c.extra.specs, etablissement: c.val("etablissement"), pays: c.val("pays") }; },
    // message WhatsApp de la preuve (seulement si le site redevient payant) : code + formule, sans nom
    nomWa: function () { return ""; },
    selecteurWa: "#abo-preuve, #abo-preuve-apres, #abo-preuve-attente",
    // liens WhatsApp « depuis l'étranger » (si payant) : texte de la page (data-texte) + « code X »
    apresRemplir: function (x) {
      var l = document.querySelectorAll("#abo-etranger, #abo-etranger-apres, #abo-etranger-attente");
      for (var i = 0; i < l.length; i++)
        l[i].setAttribute("href", "https://wa.me/" + PC.whatsapp + "?text=" + encodeURIComponent((l[i].getAttribute("data-texte") || "") + "code " + x.code));
    }
  });
})();
