#!/bin/bash
# Captures téléphone (Edge sans écran) : cadres de 360 et 500 px, en français, anglais et arabe.
#   bash tools/captures.sh            -> captures/*.png   (dossier ignoré par git)
#   bash tools/captures.sh accueil    -> seulement les pages dont le nom contient « accueil »
cd "$(dirname "$0")/.." || exit 1
EDGE="/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
SITE=$(cygpath -m "$PWD")
PROFIL=$(cygpath -m "${TEMP:-/tmp}/edge-captures-conf")
mkdir -p captures
JOUR=$(python -c "import json;print(json.load(open('donnees/etat-source.json',encoding='utf-8'))['construit_le'])")
# chemin:nom:hauteur
for page in "index.html:accueil:2600" "domaine/physique/index.html:domaine:2200" "specialite/vision/index.html:specialite:2000" \
            "conference/aaai-2027/index.html:fiche:2000" "abonnement/index.html:abonnement:3200" "flux/index.html:flux:1600" \
            "a-propos/index.html:a-propos:2600" "continent/afrique/index.html:continent:1800"; do
  IFS=: read -r chemin nom H <<< "$page"
  [ -n "$1" ] && [[ "$nom" != *"$1"* ]] && continue
  for lang in fr en ar; do
    cat > captures/cadre.html <<HTML
<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:#888;display:flex;gap:20px;padding:20px;align-items:flex-start}
iframe{border:0;background:#fff;height:${H}px}</style></head><body>
<iframe src="file:///$SITE/$chemin?lang=$lang&jour=$JOUR" width="360"></iframe>
<iframe src="file:///$SITE/$chemin?lang=$lang&jour=$JOUR" width="500"></iframe></body></html>
HTML
    "$EDGE" --headless=new --disable-gpu --allow-file-access-from-files --hide-scrollbars --user-data-dir="$PROFIL" \
      --virtual-time-budget=15000 --window-size=920,$((H + 40)) \
      --screenshot="$SITE/captures/$nom-$lang.png" "file:///$SITE/captures/cadre.html" >/dev/null 2>&1
    echo "captures/$nom-$lang.png"
  done
done
rm -f captures/cadre.html
