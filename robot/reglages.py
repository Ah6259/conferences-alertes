# -*- coding: utf-8 -*-
"""
Réglages à remplir par Ahmed — UN SEUL fichier (voir README, « Ce qu'Ahmed doit faire »).
Laisser "" tant que ce n'est pas prêt : le site cache alors le bouton ou affiche « Bientôt ».
Après une modification : attendre le passage du robot quotidien (ou python robot/construire_site.py).

Rien de secret ici (dépôt public) : le JETON du robot Telegram va dans les Secrets GitHub
(TELEGRAM_BOT_TOKEN), jamais dans ce fichier.
"""

# Canaux Telegram PUBLICS gratuits, un par grand domaine, ex. "https://t.me/radarconf_informatique".
# Vide -> pas de bouton Telegram pour ce domaine (les flux RSS gratuits restent toujours là).
TELEGRAM_CANAUX_URL = {
    "informatique": "",
    "ingenierie": "",
    "physique": "",
    "vie-sante": "",
    "mathematiques": "",
    "shs": "",
    "economie": "",
    "terre-environnement": "",
}

# Alertes Pro (abonnement) : NOM D'UTILISATEUR du robot Telegram des alertes personnalisées, sans @,
# ex. "RadarConferencesBot" (donné par @BotFather, finit toujours par « bot »).
# Vide -> la page abonnement/ dit « le lien Telegram vous est envoyé à l'activation ».
TELEGRAM_ROBOT_ALERTES = ""

# Organisateurs : formulaire Google « Signaler une conférence » (lien court https://forms.gle/…)
# et la feuille des réponses publiée en CSV. Vides -> la page « Signaler une conférence » affiche « Bientôt ».
FORMULAIRE_ORGANISATEURS_URL = ""
CSV_ORGANISATEURS_URL = ""
