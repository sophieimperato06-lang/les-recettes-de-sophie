# les-recettes-de-sophie
Livre interactif de recettes – Nutrition • Recomposition corporelle • Carb Cycling

## Modele des pages recettes web

Le site et les fiches A4 ont deux roles distincts : la page web sert ? cuisiner, la fiche A4 sert au t?l?chargement ou ? l'impression.

Pour toutes les futures pages d?taill?es de recettes :

- utiliser une vraie photo de recette dans `assets/photos-recettes/` ;
- afficher la photo avec le cadre web officiel `assets/cadres/cadre_photo_cercle_partiel_botanique_officiel.png` ;
- conserver le montage HTML `web-recipe-photo web-recipe-photo--framed` avec une image de recette sous le cadre et le cadre en overlay ;
- conserver l'axe photo valide dans `style.css` : centre x=57.17 %, y=49.45 %, diam?tre=89.66 % du cadre ;
- ne pas afficher la fiche A4 en miniature dans la page web ;
- utiliser le PDF A4 uniquement via le bouton `T?l?charger la fiche PDF` ;
- aligner `Ajouter aux favoris` et `Mode cuisine ? Garder l??cran allum?` dans la barre `.web-recipe-actions` ;
- garder le calculateur de portions de 1 a 6 portions pr?s des ingr?dients.

Ces r?gles concernent uniquement le site web. Elles ne modifient pas le Design System, les modeles vierges ni les fiches A4 officielles.

## Références site web

- Modèle officiel des pages recettes web : docs/modele-page-recette-web.md.



## Nettoyage recettes v2

La branche `refonte-recettes-v2` conserve un commit de sauvegarde avant nettoyage. La collection active du site utilise maintenant une source de donnees partagee dans `data/recipes.json` et une page detaillee commune `recette.html`. La page web affiche du HTML lisible et la fiche A4 reste disponible uniquement via le PDF de telechargement.
