# Mémoire du projet — Radar des conférences / Conference Radar

Fichier lu automatiquement par Claude Code au début de chaque session dans ce dossier.
**Dépôt PUBLIC : rien de personnel ni de secret ici.** À tenir à jour avec README et GUIDE.

## Qui et comment travailler
- Propriétaire : Ahmed (compte GitHub `Ah6259`), débutant. Expliquer simplement, **en français**.
- **Demander l'accord d'Ahmed avant de modifier le site** (sauf s'il dit « fais »). **Demander avant d'installer un logiciel.**
- Appliquer les **règles communes à tous ses sites** (`regles communes a tous les sites.md`, dossier parent des projets).
- Ne jamais citer de site concurrent (site, README, code, tests). Le test le vérifie (empreintes dans `tools/concurrents.sha256` ;
  noms en clair seulement dans l'étude privée `../etude et plan.md`).
- Site demandé par Ahmed le 06/10/2026 pour sa femme, **professeure de comptabilité** : la **comptabilité**, la **finance** et
  SURTOUT la **finance islamique** sont des thèmes mis en avant (premières tuiles de l'accueil, cités dans l'intro).

## Le site
- https://ah6259.github.io/conferences-alertes/ — dépôt `Ah6259/conferences-alertes`. Ce dossier `site/` = racine du dépôt.
- But : conférences scientifiques des **18 prochains mois**, par domaine, spécialité, continent/pays, mois ; date limite de
  soumission (la prochaine, selon la date du visiteur), lien officiel, fiche par conférence (JSON-LD Event).
- **Trois langues** : anglais (par défaut si le navigateur n'est ni en français ni en arabe), français, arabe (`?lang=en|fr|ar`,
  menu FR/EN/ع). Textes longs : `L(fr, en, ar)` (spans data-l) ; petits textes répétés des cartes : `t(clé, fr, en, ar)` ->
  `<span data-t>` traduits par `assets/textes.js` (FABRIQUÉ par la construction) ; dates mises en forme par `page.js` (`fdate`).
- Couleur indigo #4A3DB0, icône de la famille (calendrier + cloche dorée), vraie photo Wikimedia (mosaïque de 2, crédits).

## Sources (légales, preuves dans `../preuves/2026-10-06/`, jamais publiées)
- Listes ouvertes **MIT** lues par l'API GitHub : ccfddl/ccf-deadlines, huggingface/ai-deadlines, hci-deadlines/conf-database,
  hyejuryu/neuro-deadlines, hlnicholls/bioinformatics-conferences, RoboDDL/RoboDDL. Avis de licence reproduits dans
  `donnees/LICENCES-SOURCES.md` (obligation MIT).
- **INSPIRE-HEP** (physique, CC0) : API `/api/conferences?start_date=upcoming` ; jamais de contact, e-mail ni description.
- **Sélection officielle** `donnees/selection-officielle.json` (comptabilité, finance, finance islamique) : chaque conférence
  vérifiée sur la page officielle de l'organisateur (faits seulement), avec `verifie_le` + `page_verifiee` affichés sur la fiche.
  Robot mensuel `robot/verifier_officiels.py` (+ `verif-officiels.yml`) : liens qui ne répondent plus -> issue GitHub.
  **À compléter à la main** (voir GUIDE) quand de nouvelles éditions sont annoncées.
- PAS de Wikidata : `query.wikidata.org/sparql` et `/w/api.php` interdits aux robots par leur robots.txt.
- Organisateurs douteux (« prédateurs ») écartés : empreintes SHA-256 de domaines dans `robot/collecter.py` (`ECARTES`) +
  motif « Nth Edition of ». Liste en clair dans l'étude privée.

## Robots (fichiers)
- `robot/collecter.py` -> `donnees/conferences.json` (+ `ajoute_le`, `premiere_collecte`), sources dans `robot/sources.py`,
  classement (domaines, spécialités, pays, mots-clés EN/FR/AR) dans `robot/classement.py`.
- `robot/construire_site.py` -> ~600 pages, flux Atom `flux/*.xml`, `sitemap.xml`, `assets/textes.js`, `donnees/etat-source.json`.
  Les dossiers générés (domaine, specialite, continent, pays, mois, conference, flux) sont REFAITS à chaque passage.
- `robot/telegram.py` : canaux Telegram GRATUITS par domaine (secrets `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CANAUX` =
  « informatique=@canal;finance-islamique=@canal2 »). Sans secrets : rien. Adresses publiques des canaux : `robot/reglages.py`.
- `robot/organisateurs.py` : formulaire Google des organisateurs (CSV publié, `reglages.py`) ; vide = « Bientôt ».
- `.github/workflows` : `maj.yml` (chaque jour 5h20 Tunis), `tests.yml` (push), `battement-de-coeur.yml` (mensuel),
  `verif-officiels.yml` (le 3 du mois) ; groupe de concurrence `maj-site`.

## Robustesse
- Source en panne (injoignable, vide, format changé, < 30 % d'habitude) : ses anciennes conférences gardées 30 jours max,
  `statut_source` panne -> issue « Sources des conférences en panne depuis le … » (ouverte / complétée / refermée par maj.yml).
- Collecte totale < 50 % de la précédente : **publication refusée** (ancien fichier gardé).
- Construction : JSON illisible ou chute > 50 % -> `donnees/conferences.sauvegarde.json` ; rien -> site existant gardé.
- Bandeau daté si la dernière lecture réussie a ≥ 2 jours (calcul refait avec la date du visiteur).

## Alertes Pro (payant, comme le site Appels d'offres)
- 9 DT / mois ou 79 DT / an, 14 jours d'essai, sans engagement au-delà d'un an, pas de renouvellement automatique.
  Paiement D17 / IZI 24 321 390 + preuve WhatsApp ; ligne « Paiement par carte pour l'étranger : bientôt ».
- Bouton doré « Alertes Pro » dans l'en-tête (page.js) + gros bouton dans le bandeau de l'accueil ; `abonnement/` + `conditions/`.
- Abonnés = dépôt **PRIVÉ** `Ah6259/conferences-abonnes` (dossier PC `../abonnes (prive)/`) : `alertes.yml`, `activer-abonne.yml`.
  Sa copie de `classement.py` (DOMAINES, SPECIALITES) doit rester identique (son test le vérifie sur le PC).
- Gratuit et sans données personnelles : consultation du site + flux RSS par domaine/spécialité (+ canaux Telegram plus tard).

## Avant chaque publication
1. `python robot/construire_site.py --aujourdhui <date des données>` puis :
   `node tools/test_site.mjs`, `node tools/test_sw.mjs`, `node tools/test_avis.mjs`, `python tools/test_pannes.py`
   (jsdom : `npm install --no-save --no-package-lock jsdom`).
2. `bash tools/captures.sh` (Edge, 360/500 px, FR/EN/AR) et regarder les images.
3. Image d'aperçu `assets/og-image-v1.jpg` (source `tools/og-image.html`, JPEG < 250 Ko) : si on la change, nouveau nom (-v2).
4. Service worker : `sw.js` (préfixe `conferences-alertes-`), changer `CACHE_VERSION` si une vieille version reste bloquée.

- **Vidéo de présentation** (06/10/2026) : `assets/video/presentation.mp4` (anglais) et `presentation-fr.mp4` (page en français), 1080 × 1920, + couverture et aperçu 1200 × 630 (`apercu-video.jpg`). Musique de fond : J. S. Bach, Aria des Variations Goldberg (enregistrement Musopen, CC0, Wikimedia Commons ; preuve dans le dossier privé `videos (outil)/preuves musique/`). Page **`video/`** (lecteur + gros bouton « Ouvrir le site » + Partager, og:video / og:image) : réglages `tools/page_video.json`, fabriquée par tools/page_video.py, appelé par robot/construire_site.py. Le bouton « Partager » envoie un LIEN : la page vidéo + l'adresse du site dans le texte (`window.partagerLien`, bloc « vidéo de présentation » en fin du JS commun), jamais le fichier. Test `node tools/test_video.mjs`.
  Pour la refaire : `python fabriquer.py conferences` puis `python brancher_partage.py conferences` dans le dossier PRIVÉ du PC `videos (outil)/`.

- **Adresse depuis le 11/10/2026 : https://conferences.clicvia.com/** (domaine clicvia.com d'Ahmed, ligne DNS `CNAME conferences → ah6259.github.io` nuage gris, fichier `CNAME`). L'ancienne adresse ah6259.github.io/conferences-alertes/ redirige seule. Site à la racine « / » : `BASE_SITE` de assets/page.js (sw.js, vidéo) ; GoatCounter garde le préfixe `/conferences-alertes`. Si l'outil vidéo réécrit le bloc VIDEO_SITE, remettre `"base": BASE_SITE` et l'ORIGINE conferences.clicvia.com.

- **Visibilité Google (12/10/2026, règle commune § 8)** : liens vers nos autres sites en `https://<site>.clicvia.com/` (jamais `ah6259.github.io`), lien « Tous nos services » → https://clicvia.com/ dans le pied de page, `robots.txt` avec ligne Sitemap, `sitemap.xml` daté, JSON-LD sur l'accueil, clé IndexNow `377f054ba9c5ed40d6796adc8d87d1e8.txt` à la racine (ne pas supprimer : robot `indexnow` du portail). Contrôle : `node "outils visibilite/controle.mjs"` (dépôt projets-ahmed). Sitemap envoyé dans Search Console par Ahmed le 12/10/2026.

- **Google + Bing (12/10/2026)** : sitemap envoyé par Ahmed dans Google Search Console et dans Bing Webmaster Tools (site clicvia.com/), indexation de l'accueil demandée. Pour un nouveau site : mêmes gestes, voir `nouveau site - procedure.md` § 4 étape 5 (dépôt projets-ahmed).

- **Image d'aperçu PROPRE à chaque rapport du mois (18/10/2026, Ahmed : Facebook montrait l'image du site)** : `robot/apercus.py` (Pillow,
  polices DejaVu dans `robot/polices/`, modèle d'Immobilier Tunisie) dessine `rapports/AAAA-MM/apercu-<empreinte 8>.jpg` 1200 × 630
  (événements · pays, dates limites, date des chiffres) ; og:image + `image` du JSON-LD Article ; sans Pillow : og-image-v1.jpg.
  maj.yml et tests.yml installent pillow. **og:locale** : jamais fr_TN / ar_TN (refusés par Facebook) → fr_FR / ar_AR (test).
  Construction : Python 3.12 obligatoire (f-strings de construire_site.py).
- **Rapports du mois (18/10/2026, règle commune § 25)** : `robot/rapports.py`, appelé par `construire_site.py` (donc par `maj.yml`, chaque jour).
  Pages `rapports/` (liste) et `rapports/AAAA-MM/` (événements qui COMMENCENT ce mois : types, formats, domaines, continents, pays ≥ 2,
  spécialités ≥ 3, Afrique/Tunisie, dates limites de soumission du mois, calendrier, FAQ, méthode, « Citer ces chiffres » ; JSON-LD
  fil d'Ariane + Article + FAQ). Décomptes seulement (pas de frais d'inscription : absents des sources), rien du dépôt privé.
  Historique `donnees/rapports.json` : mois en cours recalculé à chaque passage (conférence terminée = gardée, retirée avant sa fin =
  oubliée) ; mois fini = figé pour toujours ; pas de page sous 10 événements ; évolution seulement si le mois précédent a un rapport.
  Amorcé le 18/10 depuis l'historique git (`python robot/rapports.py --amorcer-git`, relevés depuis le 09/10/2026). Plan du site :
  lastmod = date des chiffres. Liens : pied de page (page.js), accueil (« Par mois ») et pages `mois/AAAA-MM/`. Le robot Facebook
  du portail publie chaque `rapports/AAAA-MM/`. Tests : bloc « Rapports du mois » de test_site.mjs + section F de test_pannes.py.
  **Partage (18/10/2026, demande d'Ahmed)** : UN SEUL bouton « Partager ce rapport » en haut ET en bas (`bloc_partage()` de rapports.py,
  `button[data-partage-rapport]`, classe `.rp-partager` — jamais `.partager`, bouton rond de l'en-tête) : menu du téléphone (`navigator.share`),
  sinon « texte + lien » copié (« Lien copié ✓ »), sinon fenêtre ; code dans page.js, clic compté `partage/rapports/…`. Texte partagé =
  « <titre> — Rapport du mois de Radar des conférences : », SANS AUCUNE adresse (Facebook prend la 1re adresse du
  texte et montre l'aperçu de l'ACCUEIL) : le lien du rapport va seulement dans `url` de navigator.share (copie sur ordinateur : texte + lien) ; signature `.rp-signature` sous le titre ;
  description qui commence par « Radar des conférences — rapport du mois. ». Pas de boutons Facebook/WhatsApp séparés (testé).
