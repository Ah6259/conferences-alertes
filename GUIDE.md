# Guide d'Ahmed — Radar des conférences (étapes simples)

Le site tourne **tout seul** sur GitHub. Voici seulement ce qu'Ahmed peut faire, quand il le souhaite.

## 1. Voir le site
https://ah6259.github.io/conferences-alertes/ (anglais par défaut ; menu « FR / EN / ع » en haut à droite).

## 2. Canaux Telegram gratuits par domaine (facultatif, plus tard)
1. Telegram → Menu → **Nouveau canal**, public, par ex. `radarconf_finance_islamique` (un canal par domaine voulu).
2. **@BotFather** → `/newbot` → il donne un **jeton** (ne jamais le coller dans un fichier ni dans le chat).
3. Ajouter le robot comme **administrateur** de chaque canal (droit « Publier des messages »).
4. GitHub → dépôt `conferences-alertes` → Settings → Secrets and variables → Actions → **New repository secret** :
   - `TELEGRAM_BOT_TOKEN` = le jeton ;
   - `TELEGRAM_CANAUX` = `finance-islamique=@radarconf_finance_islamique;comptabilite=@radarconf_compta` (domaines possibles :
     comptabilite, finance, finance-islamique, informatique, ingenierie, physique, vie-sante, mathematiques, shs, economie,
     terre-environnement).
5. Dans `robot/reglages.py`, remplir `TELEGRAM_CANAUX_URL` (ex. `"finance-islamique": "https://t.me/radarconf_finance_islamique"`)
   -> le bouton Telegram apparaît sur le site au prochain passage du robot.

## 3. Alertes Pro (abonnement payant)
Voir le README du dépôt **privé** `conferences-abonnes` : créer le robot Telegram, mettre son jeton dans les Secrets du
dépôt privé, écrire son nom dans `robot/reglages.py` (`TELEGRAM_ROBOT_ALERTES`), puis activer chaque inscription avec le
bouton `activer-abonne` depuis l'application GitHub du téléphone.
**Paiement international** : aujourd'hui D17 / IZI (Tunisie) ; pour l'étranger le site dit « carte bancaire :
bientôt, écrivez-nous sur WhatsApp ». Choix à faire : Konnect (carte) ou un autre service (voir l'étude privée).

## 4. Ajouter une conférence de comptabilité, finance ou finance islamique (sélection officielle)
1. Ouvrir la **page officielle** de la conférence (site de l'association, de l'université, de l'AAOIFI…).
2. GitHub (téléphone ou PC) → dépôt `conferences-alertes` → `donnees/selection-officielle.json` → crayon (modifier).
3. Copier un bloc existant et changer : `acronyme`, `titre`, `debut` / `fin` (AAAA-MM-JJ), `ville`, `code_pays` (2 lettres,
   ex. `TN`, `QA`, `MY`), `mode` (`presentiel`, `en-ligne`, `hybride`), `specialites` (ex. `["sukuk", "banque-islamique"]`),
   `lien` (https), `dates_limites` (date + type `article` ou `resume`), `page_verifiee`, `verifie_le` (date du jour).
4. « Commit changes ». Le robot de tests vérifie tout ; la conférence apparaît au prochain passage du robot quotidien.
Ne jamais deviner une date : si elle n'est pas publiée, ne pas mettre la conférence (ou laisser `dates_limites` vide).

## 5. Formulaire des organisateurs (gratuit, plus tard)
Créer un formulaire Google « Signaler une conférence » avec ces questions (mots à garder) : *Nom de la conférence*, *Sigle*,
*Date de début*, *Date de fin*, *Ville*, *Pays*, *Format*, *Spécialité*, *Date limite*, *Lien officiel*, *J'accepte*
(case « Oui »). Réponses → Sheets → Fichier → Partager → **Publier sur le Web** → CSV. Mettre le lien du formulaire dans
`FORMULAIRE_ORGANISATEURS_URL` et celui du CSV dans `CSV_ORGANISATEURS_URL` (`robot/reglages.py`).

## 6. Quand GitHub envoie un e-mail
- « Sources des conférences en panne » : rien à faire en général (l'issue se ferme seule quand la source remarche).
- « Sélection officielle : liens à revérifier » : ouvrir le lien indiqué, retrouver la nouvelle page officielle, corriger
  `donnees/selection-officielle.json` (étape 4).
- Un test en échec : rien n'est publié tant que ce n'est pas corrigé ; demander à Claude.

## 7. Search Console
Propriété https://ah6259.github.io/ déjà vérifiée : envoyer `conferences-alertes/sitemap.xml` et demander l'indexation de
l'accueil.
