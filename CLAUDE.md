# Mémoire du projet — Radar des conférences / Conference Radar

## EN TOUT PREMIER (24/11/2026, problème vu par Ahmed)
- La mémoire générale, les « update workflow » et le journal de TOUS les sites sont dans le dépôt PRIVÉ **`Ah6259/projets-ahmed`**
  (le dépôt général), PAS ici. Une session ouverte sur ce seul dépôt ne voit donc pas le dernier travail d'Ahmed (le 24/11, une session
  a répondu « dernier update workflow : 22/11 » alors qu'il y en avait deux le jour même dans projets-ahmed).
- **Au début de CHAQUE session, avant de répondre quoi que ce soit** : si `../projets-ahmed` n'existe pas, le brancher
  (`add_repo` Ah6259/projets-ahmed, puis `git clone --depth 30 https://github.com/Ah6259/projets-ahmed ../projets-ahmed`) ; sinon `git pull` ;
  puis `python3 "debut de session.py" conferences` dans `../projets-ahmed` et en résumer le résultat à Ahmed.
- « Dernier workflow / dernière mise à jour » = regarder `git log` de projets-ahmed ET de ce dépôt (toutes branches), jamais un seul.

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
- **21/10/2026 — ALERTES PRO GRATUITES (décision d'Ahmed : site international, un prix en dinars et un paiement D17/IZI n'ont pas de sens pour l'étranger).** Interrupteur `ABO["gratuit"]` de robot/construire_site.py (page « Gratuit pour le moment », ni formule, ni paiement, ni facture ; conditions 1-6 de la version gratuite) et `GRATUIT` de tools/alertes.py du dépôt privé (inscription active tout de suite, sans fin ni rappel ; code en attente ou terminé qui revient = réactivé). Le code du paiement est gardé : remettre les DEUX à False pour revenir au payant. Tests : blocs « GRATUIT » de test_site.mjs et test_alertes.py.
- 9 DT / mois ou 79 DT / an, plus d'essai gratuit depuis le 20/10/2026, sans engagement au-delà d'un an, pas de renouvellement automatique.
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

## Visiteur simulé (18/10/2026, règle générale)
- `python tools/visiteur_simule.py` (outil COMMUN, copie identique dans chaque site : ne pas le modifier ici) : liens/images morts, puis Chromium à 390 px (page trop large, image cassée, « NaN/undefined », page vide) + scénarios `tools/scenarios-visiteur.json` (recherche, filtres, résultat affiché, groupes « croissant »). Lancé par tests.yml. Nouvelle recherche, nouveau filtre ou nouveau formulaire → ajouter un scénario. Page `video/` : `preload="none"` (la couverture reste affichée ; la page finit de charger sans attendre la vidéo, moins de données sur téléphone ; le visiteur simulé la voyait « non chargée » avec `metadata`).

## Code personnel des Alertes Pro (18/10/2026, contrôle commun « case du code »)
- Ce site n'a AUCUNE case où le visiteur tape un code : `abonnement/` CRÉE le code (6 caractères, module commun `assets/pass-commun.js` réglé par `assets/pass-reglages.js`), l'affiche
  (`#abo-code`) et le met dans le lien Telegram ; rien dans localStorage. Plus d'essai gratuit depuis le 20/10/2026.
- Corrigé : la page (bloc « Paiement » et après l'inscription) et les conditions disaient « motif = votre nom » alors que les étapes
  disent « Motif : votre code personnel » -> partout « code personnel » (FR, EN, AR ; test dans test_site.mjs).

- **Recherche « au son » (18/10/2026, règle commune § 27)** : la case « Rechercher » utilise `assets/son.js` (outil commun de projets-ahmed, copié TEL QUEL, chargé avant app.js, compté dans le `?v=`) : Djerba = Jerba, Kairouan = Qairouan, Hammamet = Hamamet (l'ancienne recherche « mot contenu » reste valable en plus). Test dans test_site.mjs (paires + mot réel avec consonne doublée + « zzzzqqq » = 0). Sans Pillow, construire_site.py remplace l'aperçu du rapport : construire avec un Python 3.12 qui a Pillow.

- **19/10/2026 — Visiteur simulé : contrôle des ESPACES (règle commune § 29)** : nouvelle copie commune installée, 0 anomalie, aucun défaut d'espace sur ce site.

- **20/10/2026 — PLUS D'ESSAI GRATUIT** (Ahmed : « Enlève tous les essais gratuits ») : aucune mention d'essai sur le site en FR, EN et AR
  (bouton doré, page `abonnement/`, conditions renumérotées 1-8, page `flux/`, titres, descriptions, FAQ JSON-LD) ; formule 1 mois
  (cochée) ou 1 an ; le code reste créé sur la page, le robot privé le met « en attente » jusqu'au paiement. Pour refaire les pages :
  `python3.12 robot/construire_site.py` (sans Pillow, les aperçus des rapports sont remplacés par l'image du site : ne pas les envoyer).
  Test : « aucune page ne parle d'essai gratuit » dans test_site.mjs.

- **RÈGLE D'AHMED (25/10/2026, règle commune § 44) : la page « Comment fonctionne le site ? » (`a-propos/`, bloc « Comment fonctionne
  le site ? » de robot/construire_site.py, FR + EN + AR ; elle sert aussi de modèle à la page `video/`) est mise à jour à CHAQUE
  modification visible du site, dans le même envoi** : à quoi sert le site, mode d'emploi, une ligne par fonction visible (liste
  `fonctions`), sources, méthode, gratuit / payant (Alertes Pro : texte selon `ABO["gratuit"]`), vos données, mises à jour, site
  indépendant, crédits des photos. Lien « Comment fonctionne le site ? » dans le pied de page (page.js) et sur l'accueil (carte
  « Comment ça marche ? »). Test `FONCTIONS` dans tools/test_site.mjs (repère dans le site -> phrase attendue dans la page) : une
  fonction absente = test rouge. Nouvelle fonction = une ligne dans `FONCTIONS` + son explication dans `fonctions`.
  Construire : `uv run --python 3.12 --with pillow python robot/construire_site.py --aujourdhui <date des données>` (Python 3.12 + Pillow).

- **08/11/2026 — plan SEO d'Ahmed appliqué à ce site (phase 2 ; contrôle commun `outils visibilite/controle_seo.mjs` de projets-ahmed ;
  plan : `consignes des taches/seo-conferences.md`)** : `titre_seo()` / `desc_seo()` dans `page()` (titre <= 70 caractères : suffixe
  « | nom du site » retiré puis coupe à un séparateur ; description <= 165 coupée en fin de phrase) ; h2 « La liste » au-dessus des
  cartes (plus de saut h1 -> h3). Avant : titres de 94 à 122 caractères. Tests verts (5).

## Page 404 + Confidentialité / Conditions (17/11/2026, règle commune § 58)
- `404.html` + `404.js` à la racine = page 404 COMMUNE (`outils communs/page-404/installer.py`, projets-ahmed) : ne pas les modifier ici, réinstaller.
- Liens « Confidentialité / Privacy / الخصوصية » et « Conditions d'utilisation / Terms of use / شروط الاستعمال » (pages communes clicvia.com,
  fr / en / ar) dans le pied de CHAQUE page (pied statique de `construire_site.py` + pied de `assets/page.js`). Test qui bloque dans
  `tools/test_site.mjs` ; test_sw / test_avis ignorent 404.html.

- **19/11/2026 — ACCUEIL LÉGER (Ahmed, CV.3)** : l'accueil écrivait ses 459 conférences (876 Ko, 20 000 éléments : 13 s avant d'être utilisable
  sur un téléphone moyen). Toute liste de plus de `SEUIL_LISTE` (60) conférences n'écrit que les `PREMIERES_LISTE` (30) plus proches (date limite) ;
  les autres vont dans `liste.json` à côté de la page (accueil, Informatique, Physique, Europe, Asie…), chargé par app.js au 1er geste (filtre,
  recherche, « Afficher plus », lien #conférence), puis TRADUIT (data-t, dates) comme le reste ; compteurs des filtres et résumé = chiffres de la
  construction tant que le reste n'est pas là. Tests : page() du test charge le reste (sauf { leger: true }), vérification de l'état de départ.

- **21/11/2026 — Espagne (Ahmed : « pas de conférences en Espagne »)** : cause = l'Espagne avait 8 conférences (informatique, physique,
  neurosciences) mais AUCUNE en comptabilité / finance / finance islamique : ces thèmes ne viennent QUE de la sélection officielle faite à
  la main (vérifiée le 06/10, jamais complétée depuis) dont la seule conférence espagnole (RIARF, Palma, 19/10/2026) était passée.
  Ajoutées après vérification de la page officielle : IPA 2027 (Burgos), IESE–ECGI 2027 (Madrid), atelier SJFA « The Value of ESG »
  (Valladolid), AMaMeF 2027 (Barcelone). Les « Islamic Banking… » annoncées en Espagne (organisateur en série) ne sont PAS ajoutées.
  Lecture des lieux : « España / Espanya » + ~50 villes espagnoles (Sevilla/Seville, Valencia, Bilbao, Málaga, Palma…) ; Venezuela et
  Nicaragua ajoutés (Valencia, Granada homonymes). Garde-fous : section H de test_pannes.py (lieux espagnols, couverture, ≥ 5 conférences
  ES dans la sélection) ; `couverture()` de robot/verifier_officiels.py (`THEMES_SUIVIS`, `PAYS_SUIVIS`) -> issue « Sélection officielle :
  à enrichir » le 3 du mois (refermée seule).

- **21/11/2026 — mode sombre lisible (Ahmed : « en sombre on ne peut pas lire certains mots », tous ses sites)** : bloc final de
  `assets/style.css` (`@media (prefers-color-scheme:dark){ :root:not([data-theme="light"]) … }`) : noms de spécialité des pastilles en
  `--texte` (contraste 1.0 avant), sigles en `--bleu`, « D-2 » / bouton « Send » / `.btn-publier` / `.btn-video-site` en texte foncé sur l'accent
  clair. Mode clair inchangé. Contrôle « contraste < 3 en sombre » : 25 -> 0 (accueil, abonnement, domaine, fiche, rapport, vidéo).
- **21/11/2026 — mode CLAIR plus lisible (accord d'Ahmed : « foncer un peu »)** : bloc clair `:root` de `assets/style.css` : `--rouge` #C2412F -> #B23A29
  (dates limites `b.dl`, « in N days »), `--or` #A8701A -> #8F5D14 (D-3/D-4), `.btn-rss` #E8730C -> #B4530A, WhatsApp #1F9D55 -> #15803D. Contrôle `--clair --seuil 4.5` : 0 ; sombre : 0.

## 22/11/2026 — Google + IA (demande d'Ahmed : « que Google et les IA indexent nos sites »)
- État Search Console (21/11) : accueil « Crawled - currently not indexed » (dernière visite de Google le 12/10) ; affichages réels sur des noms
  de conférences (« indocrypt 2026 » position ~8,7, « cscwd 2027 », « laces 2026 », « mobicom2027 » position 3,5).
- Accueil : 2e JSON-LD WebSite + éditeur `Organization` Clicvia (@id https://clicvia.com/#organisation, page Facebook), à côté de la FAQ.
- Titres « … 2026–2027 » : années tirées de la date du jour (`ANS` de construire(), plus jamais figées).
- « Comment fonctionne le site ? » (FR + EN + AR) : « Publié par Clicvia… pour nous écrire : Votre avis » + ligne `FONCTIONS` (éditeur Clicvia).
- `llms.txt` réécrit à la main SANS chiffre ni conférence datée (l'ancien, de l'outil commun du 20/10, disait « 485 upcoming » et listait des
  conférences d'octobre déjà passées). Si l'outil commun `outils visibilite/llms.py` est relancé, relire ce fichier.

## 22/11/2026 — Finance islamique dans le monde entier (Ahmed : « pas de conférences en Espagne ni en finance islamique », « fais 1 et 2 »)
- Cause : la finance islamique ne vient QUE de la sélection officielle faite à la main (6 conférences à venir, toutes Golfe / Turquie).
  Les « Islamic Banking, Finance and… » de Barcelone, Madrid, Séville, Rome… vues par Ahmed sur un site de listes = un organisateur
  en série (nom dans l'étude privée ; même conférence plusieurs mois et plusieurs villes) : JAMAIS ajoutées (expliqué à Ahmed).
- 1 : 6 conférences vérifiées sur leur page officielle ajoutées à `donnees/selection-officielle.json` : WIEFC 2027 (Lahore), ICIFS 2027
  (Brunéi), IFN Middle East 2027 (Dubaï), KazanForum 2027 (Kazan, volet finance islamique), IFN Asia 2027 (Kuala Lumpur), séminaire CILE
  2027 (HBKU, Doha). Les grands organisateurs (AAOIFI, IFSB, Durham, INCEIF/ISRA, IsDB, Al Baraka) n'avaient pas encore publié leurs dates 2027.
  `THEMES_SUIVIS["finance-islamique"]` 6 -> 8.
- 2 : `robot/surveiller_organisateurs.py` (appelé par verif-officiels.yml le 3 du mois) lit la page « événements » des 15 organisateurs de
  `donnees/organisateurs-suivis.json` (robots.txt respecté, pause / Crawl-delay, `filtrer` pour les pages multi-sujets, lignes « © » ignorées),
  garde les lignes vues dans `donnees/surveillance-organisateurs.json` et ouvre l'issue « Finance islamique : nouvelles éditions à vérifier »
  (Claude vérifie la page officielle puis ajoute ; rien n'est ajouté au site par le robot). 1er passage le 03/12/2026 : il signalera les
  annonces de ConfBay (iBAF, ICONIE, ZAWED, ISHEC 2027…) et le 5e Islamic Fintech Forum (Médine, janvier 2027, jours pas encore publiés).
  5 sites refusent les robots dans leur robots.txt (AAOIFI events, IFSB, REDmoney, Bank Negara, IsDB Institute) : notés « à vérifier à la main ».
  Tests : section I de tools/test_pannes.py (5).

## 25/11/2026 — e-mail de confirmation automatique EN SERVICE (A.17, méthode `outils communs/email-clients/BRANCHER-UN-SITE.md` de projets-ahmed)
- `assets/pass-reglages.js` (avant le 25/11 : `assets/abonnement.js`) : `EMAIL_AUTO = true` ; à l'inscription (après les vérifications, jamais si le piège anti-robot est rempli),
  `envoyerEmail()` envoie en JSON à `https://api-email.clicvia.com/inscription` (sans attendre, jamais bloquant) : site `conferences`,
  langue de la page (fr / en / ar), nom, e-mail, code, spécialités, établissement, pays, formule (vide : gratuit), lien Telegram.
  Service en panne -> `EMAIL_AUTO = false` (tout caché, rien envoyé). CSP `connect-src` + `EMAIL_API` dans robot/construire_site.py.
- « Vous le recevez aussi par e-mail » affiché ; « Comment fonctionne le site ? » : « E-mail de confirmation » + Resend dans « Vos données ».
- Tests (test_site.mjs) : sans e-mail = message long et rien envoyé ; JSON FR / EN / AR ; CSP ; JSON ACCEPTÉ par le vrai `verifier()` du
  Worker (lu dans ../projets-ahmed s'il existe, sinon « SAUTÉ », jamais rouge sur GitHub) ; ligne FONCTIONS. Aucune phrase de paiement.

## 25/11/2026 — PASS.1 : parcours d'achat par le MODULE COMMUN (règle commune § 70.8, 3e site migré après Concours et Appels d'offres)
- `assets/abonnement.js` est SUPPRIMÉ. La page `abonnement/` charge `assets/pass-commun.js` (COPIE EXACTE du module
  `outils communs/pass-commun/pass-commun.js` de projets-ahmed : **ne jamais la modifier ici**) puis `assets/pass-reglages.js` (ce qui est
  propre au site : 3 langues en / fr / ar, alertes GRATUITES (`type: "alertes-gratuit"`, formules 1 mois / 1 an prêtes si le site redevient
  payant), code 6 caractères sans O/0/I/1, téléphone international, établissement, pays, spécialités, lien Telegram, ligne `pour_activer`
  avec la langue, champs de l'e-mail, message e-mail « … vous y recevez votre code et le lien Telegram. », WhatsApp sans nom, liens
  « depuis l'étranger » ; `var EMAIL_AUTO = true`).
  `assets/pass-commun.empreinte` = empreinte écrite par `synchroniser.py` ; test_site.mjs échoue si la copie est modifiée (et, si projets-ahmed
  est à côté — ou `PROJETS_AHMED=<dossier>` —, si elle diffère du module) ; la demande d'e-mail reste vérifiée par le vrai `verifier()`.
- Améliorer le parcours : modifier le module dans projets-ahmed, `python3 "outils communs/pass-commun/synchroniser.py"`, reconstruire, tests,
  envoyer CHAQUE site (LISEZMOI.md du module). Rien n'a changé pour le visiteur (comparaison avant / après en EN, FR et AR, gratuit ET payant
  simulé, e-mail automatique en service et coupé : 330 étapes identiques ; seule différence voulue : piège anti-robot rempli = la commande
  n'est plus gardée dans le téléphone).

## 25/11/2026 — plan Google (chute d'octobre, fiche `memoire claude/chute-google-octobre-2026.md` de projets-ahmed)
- **B.2 lastmod honnête** : `robot/lastmod.py` (même fichier que dans Appels d'offres et Concours) appelé par construire_site.py : date d'une
  page = dernier VRAI changement (empreinte du HTML sans dates, heure, ?v=, `data-maj`, compte à rebours ni bandeau de panne ; mémoire
  `donnees/lastmod.json` ; page inconnue = date retrouvée dans git) ; les rapports gardent la date de leurs chiffres ; la page vidéo a sa date.
- **B.1 pages maigres** : `fiche_maigre()` = fiche SANS date limite, SANS rang et NON vérifiée sur le site officiel (surtout INSPIRE) ;
  catégorie (spécialité, pays, mois, continent, domaine) de moins de 2 conférences. En ligne, mais `noindex, follow` et hors du plan du site ;
  elles reviennent seules. Le 25/11 : 139 fiches sur 466 + 2 catégories ; plan du site 579 -> 438 adresses.
- Tests (test_site.mjs, vérifiés par sabotage) : dates pas toutes du jour, date = donnees/lastmod.json, aucune page noindex dans le plan,
  accueil / domaines / alertes… jamais noindex, règle des fiches et des catégories recalculée, lastmod.py avec données inventées.

## 28/11/2026 — ENCADRÉS VERS LES ALERTES PRO + CLICS COMPTÉS (règle commune § 71, « fais tout » d'Ahmed ; modèle : Alerte Concours)
- Constat de l'audit du 28/11 : aucune page n'amenait aux Alertes Pro (seulement le menu) et aucun clic vers `abonnement/` n'était compté.
- **Encadré « 🔔 … Recevoir ces alertes »** (`encadre_pro()` de robot/construire_site.py, + `encadre_specialite / encadre_domaine / encadre_lieu`,
  FR + EN + AR, classe `.encadre-pro`, `data-n` = nombre de la liste de la page) sur CHAQUE page `specialite/`, `domaine/`, `continent/`, `pays/`, `mois/` :
  spécialité / domaine : « N conférences à venir en « … ». Ne ratez plus une conférence de cette spécialité (ce domaine) : les nouvelles conférences
  et les rappels des dates limites, chaque matin sur Telegram. » ; pays / continent / mois : « … Ne ratez aucune conférence de VOTRE spécialité, où
  qu'elle ait lieu : … » (les Alertes Pro suivent des SPÉCIALITÉS, jamais un pays ni un mois : pas de fausse promesse). Ligne d'offre `offre_pro()` =
  l'interrupteur `ABO["gratuit"]` (aujourd'hui « Alertes Pro sur Telegram : gratuites pour le moment. », sinon le prix) ; aucune gratuité ajoutée.
- Bouton (`.btn-pro`) -> `abonnement/?specialite=<clé>#inscription` ou `?domaine=<clé>` (`lien_abo()`) ; pays / continent / mois : `abonnement/#inscription`.
  Fiche d'une conférence : son bouton Alertes Pro coche la 1re spécialité de la fiche.
- `assets/pass-reglages.js`, crochet `brancher` du module commun (pass-commun.js JAMAIS modifié) : coche les spécialités demandées (domaine = cases
  `data-domaine`) ; valeur inconnue ignorée ; phrase `#abo-repris` « Vos choix de la page précédente sont déjà cochés plus bas… » (FR, EN, AR).
- **Clics comptés** : chaque lien vers `abonnement/` a `data-clic` (abonnement-specialite, -domaine, -pays, -continent, -mois, -accueil, -entete pour le
  bouton doré, -pied, -fiche, -flux, -apropos) ; `assets/page.js` envoie l'ÉVÉNEMENT GoatCounter `/conferences-alertes/clic/<nom>` seulement si
  `goatcounter.count` existe (aucun script en ligne). Nouveau lien vers abonnement/ = un `data-clic` (le test le bloque sinon).
- « Comment fonctionne le site ? » (FR, EN, AR) : ligne « Encadré « Recevoir ces alertes » » + clics comptés dans « Vos données » ; 2 lignes FONCTIONS (27).
- Tests (bloc « 7 bis » de tools/test_site.mjs, chacun vérifié par sabotage) : encadré sur chaque page des 5 sortes en 3 langues, nombre = liste,
  bouton et pré-sélection, offre vraie, pas de « gratuit » dans le texte, data-clic partout, clic compté avec un FAUX goatcounter et rien sans lui,
  cases pré-cochées (spécialité, domaine), valeur inconnue ignorée.
