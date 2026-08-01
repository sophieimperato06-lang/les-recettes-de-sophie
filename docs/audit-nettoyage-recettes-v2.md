# Audit nettoyage recettes v2

## Recettes historiques detectees avant nettoyage non destructif

- recettes/acai-bowl.html
- recettes/bowlcake-au-son-d-avoine.html
- recettes/bowlcake-nuage.html
- recettes/clafouflan.html
- recettes/granola-proteine-jour-bas.html
- recettes/piadina-ig-bas-sophie.html
- recettes/pudding-chia-pistache.html
- recettes/ricotta-de-tofu-au-basilic.html
- recettes/spaghetti-proteines-au-saumon-fume.html
- recettes/tartare-thon-rouge-avocat.html

## Assets historiques detectes

- assets/R001.png
- assets/R003.png
- assets/R004.png
- assets/R005.png
- assets/R006.png
- assets/R007.png
- assets/R008.png
- assets/R009.png
- assets/R010.png

## Dossiers source/scripts/output detectes

- source/assets/.gitkeep
- source/assets/R001.png
- source/assets/R003.png
- source/assets/R004.png
- source/assets/R005.png
- source/assets/R006.png
- source/assets/R007.png
- source/assets/R008.png
- source/assets/R009.png
- source/assets/R010.png
- source/data/recipes.json
- scripts/generate_book.py

## Decision appliquee

Passe non destructive : les anciennes recettes sont retirees des donnees et de la navigation active, mais les fichiers physiques historiques ne sont pas supprimes dans cette passe. Le commit de sauvegarde avant nettoyage est 94ef0ae.
