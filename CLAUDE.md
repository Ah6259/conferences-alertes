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
  Paiement D17 / IZI / Wafacash 24 321 390 + preuve WhatsApp ; ligne « Paiement par carte pour l'étranger : bientôt ».
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
