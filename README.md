# Radar des conférences / Conference Radar

Site gratuit, sans inscription, pour les **professeurs et chercheurs du monde entier** : les **conférences scientifiques des
18 prochains mois**, par **domaine**, **spécialité**, **continent / pays** et **mois**, avec la **date limite de soumission**
(rappels J-7 … J-1), le **lien officiel** et une fiche par conférence. Anglais (par défaut), français et arabe.

Thèmes mis en avant : **Comptabilité et audit**, **Finance**, **Finance islamique** (banque islamique, sukuk, takaful,
zakat/waqf, normes AAOIFI et gouvernance charia).

- Adresse : https://conferences.clicvia.com/
- Alertes **gratuites** sans données personnelles : flux RSS (Atom) par domaine et par spécialité (`flux/`).
- Alertes **personnalisées** sur Telegram (« Alertes Pro », `abonnement/`) : 9 DT / mois ou 79 DT / an, 14 jours d'essai gratuit,
  sans renouvellement automatique. La consultation reste gratuite.

## Sources (licences)
| Source | Domaines | Licence / conditions |
|---|---|---|
| Listes ouvertes sur GitHub (CCF Deadlines, AI Deadlines, HCI Deadlines, Neuro Deadlines, Bioinformatics Conferences, RoboDDL) | informatique, IA, IHM, robotique, neurosciences, bioinformatique | MIT (avis reproduits dans `donnees/LICENCES-SOURCES.md`) |
| INSPIRE-HEP (API publique) | physique, astronomie | métadonnées CC0 (aucun contact ni description repris) |
| Sélection officielle (`donnees/selection-officielle.json`) | comptabilité, finance, finance islamique | faits publiés par chaque organisateur, vérifiés sur sa page officielle |
| Formulaire des organisateurs (quand Ahmed l'ouvre) | tous | publication demandée par l'organisateur |

Aucune base d'un autre site n'est recopiée ; aucun robots.txt ni protection n'est contourné ; User-Agent honnête.

## Comment ça marche
| Étape | Fichier | Rôle |
|---|---|---|
| 1 | `robot/collecter.py` (+ `sources.py`, `classement.py`, `organisateurs.py`) | lit les sources, garde les conférences à venir, normalise les dates (jamais devinées), fusionne les doublons, écarte les organisateurs douteux, classe (domaine, spécialité, pays) -> `donnees/conferences.json` |
| 2 | `robot/construire_site.py` | fabrique les pages, les flux Atom, `sitemap.xml`, `assets/textes.js` |
| 3 | `tools/test_site.mjs`, `test_sw.mjs`, `test_avis.mjs`, `test_pannes.py` | tests : rien n'est publié si un test échoue |
| 4 | `robot/telegram.py` | canaux Telegram gratuits par domaine (inactif tant que les secrets n'existent pas) |
| 5 | `.github/workflows/maj.yml` | 1 → 4 chaque jour à 5h20 (Tunis), puis commit ; GitHub Pages republie |
| 6 | `robot/verifier_officiels.py` + `verif-officiels.yml` | chaque mois : les liens de la sélection officielle répondent-ils encore ? |

Réglages d'Ahmed : **un seul fichier**, `robot/reglages.py` (canaux Telegram publics, robot des Alertes Pro, formulaire des
organisateurs). Les jetons secrets vont dans les **Secrets GitHub**, jamais dans un fichier.

## Lancer à la main (PC)
```
python robot/collecter.py                         (télécharge les sources ; --cache dossier pour réutiliser des archives)
python robot/construire_site.py
npm install --no-save --no-package-lock jsdom     (une fois par PC)
node tools/test_site.mjs
node tools/test_sw.mjs
node tools/test_avis.mjs
python tools/test_pannes.py
python robot/telegram.py --essai                  (affiche les messages sans rien envoyer)
python robot/verifier_officiels.py                (vérifie les liens de la sélection officielle)
bash tools/captures.sh                            (captures Edge 360/500 px, FR/EN/AR, dans captures/)
```

## Plan de continuité
Objectif : le site reste **en vie et honnête** même si une source tombe en panne ou si personne ne s'en occupe.

**Ce qui tourne tout seul** : `maj.yml` (chaque jour), `verif-officiels.yml` (le 3 du mois), `battement-de-coeur.yml`
(le 1er du mois, pour que GitHub ne mette pas les robots en pause après 60 jours), `tests.yml` (à chaque envoi). Groupe de
concurrence commun `maj-site`.

**Ce qui protège le site**
- Source injoignable, vide, format changé, ou < 30 % de ses conférences habituelles : c'est une **panne** ; ses anciennes
  conférences restent affichées 30 jours au plus (les conférences terminées disparaissent seules, aussi selon la date du
  visiteur) ; issue GitHub « Sources des conférences en panne depuis le … » ouverte puis refermée automatiquement.
- Collecte totale inférieure à la moitié de la précédente : **publication refusée**, ancienne liste gardée.
- Fichier de données illisible ou qui fond de plus de moitié : reprise de `donnees/conferences.sauvegarde.json` ;
  sans sauvegarde, le site publié n'est pas touché.
- Bandeau daté « les sources n'ont pas pu être lues depuis le … » dès 2 jours sans lecture réussie.
- Dates jamais devinées, lien officiel https obligatoire, textes échappés, organisateurs douteux écartés.
- Telegram : sans secrets, rien ; en erreur, « échec » au journal et renvoi au passage suivant (jamais deux fois).
- Sécurité : robots.txt (moteurs oui, robots d'IA et aspirateurs non), `noai`, CSP stricte, anti-iframe, anti-copie légère,
  aucun secret ni donnée personnelle dans le dépôt (vérifié par le test). Abonnés : dépôt privé.

**Si Ahmed n'est plus là** : tout continue sur GitHub. Conseil : désigner un successeur GitHub (Settings → Account →
Successor settings). La sélection officielle (comptabilité, finance, finance islamique) vieillit si personne ne l'enrichit :
les conférences passées disparaissent seules, les autres sources continuent.

© 2026 Ahmed (Ah6259) — tous droits réservés (voir LICENSE). Les données des sources restent sous leurs licences d'origine.
