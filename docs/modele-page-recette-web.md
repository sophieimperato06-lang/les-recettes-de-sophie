# Modèle officiel des pages recettes web

Cette documentation concerne uniquement le site web `les-recettes-de-sophie`.
Elle ne modifie pas le Design System, les fiches A4, les modèles vierges ni les fichiers sources du livre.

## Rôle de la page web

La page web sert à consulter et cuisiner la recette.
La fiche A4 sert uniquement au téléchargement ou à l'impression PDF.

Règles :

- ne pas afficher la fiche A4 comme miniature dans la page détaillée ;
- afficher le contenu de recette en vrai texte HTML ;
- utiliser une vraie photo de recette ;
- proposer la fiche A4 uniquement via un bouton PDF.

## Photo web avec cadre officiel

Pour toutes les futures pages détaillées de recettes, utiliser ce montage :

- conteneur : `.web-recipe-photo.web-recipe-photo--framed` ;
- photo réelle : `.web-recipe-photo__image` ;
- cadre officiel en overlay : `.web-recipe-photo__frame` ;
- asset cadre : `assets/cadres/cadre_photo_cercle_partiel_botanique_officiel.png`.

La photo doit être placée sous le cadre, masquée en cercle, puis le cadre doit être superposé au-dessus.

Axe validé du masque photo dans le cadre web :

- centre horizontal : `57.17 %` ;
- centre vertical : `49.45 %` ;
- diamètre : `89.66 %` du cadre ;
- CSS actuel : `left: 12.34%`, `top: 4.31%`, `width: 89.66%`, `height: 89.66%`.

Ne pas recentrer la photo au milieu du carré PNG du cadre : le cercle réel du cadre n'est pas centré dans le carré source.

## Titre web

La page web reprend l'esprit des fiches :

- titre principal : gros titre lisible ;
- ligne complémentaire : police Allura ;
- police locale : `assets/fonts/Allura/Allura-Regular.ttf` ;
- classe utilisée : `.web-recipe-title .subtitle` ;
- famille CSS : `"Allura Sophie"`.

La ligne complémentaire doit rester courte, élégante et lisible.

## Actions de recette

La zone `.web-recipe-actions` regroupe :

- `Ajouter aux favoris` ;
- `Mode cuisine — Garder l'écran allumé` ;
- `Télécharger la fiche PDF`.

Règles validées :

- le bouton Mode cuisine doit être aligné visuellement avec Ajouter aux favoris ;
- les boutons utilisent la même hauteur visuelle et le même style ;
- le Mode cuisine ne s'active jamais automatiquement ;
- le PDF pointe vers le fichier A4 officiel stocké dans `assets/fiches-pdf/`.

## Calculateur de portions

Le calculateur doit rester proche des ingrédients.

Règles validées :

- boutons de 1 à 6 portions ;
- recalcul dynamique des quantités avec `data-base-quantity` et `data-unit` ;
- ne pas réduire la lisibilité de la liste d'ingrédients ;
- conserver le vrai texte HTML.

## Champs de données

Chaque recette web doit pouvoir utiliser :

```json
"webImage": "assets/photos-recettes/nom-de-la-photo.png",
"recipePdf": "assets/fiches-pdf/nom-de-la-fiche.pdf"
```

`webImage` sert à la page web.
`recipePdf` sert uniquement au téléchargement de la fiche A4.

## Fichiers validés dans le test Bowlcake

- page test : `recettes/bowlcake-express-chocolat-skyr-avoine.html` ;
- photo web : `assets/photos-recettes/bowlcake-express-chocolat-skyr-avoine.png` ;
- PDF : `assets/fiches-pdf/bowlcake-express-chocolat-skyr-avoine.pdf` ;
- cadre web : `assets/cadres/cadre_photo_cercle_partiel_botanique_officiel.png` ;
- police Allura : `assets/fonts/Allura/Allura-Regular.ttf`.

Ces règles deviennent la base pour créer les prochaines pages recettes web du premier coup.


## Tableau nutritionnel web

Le tableau des valeurs nutritionnelles peut afficher 3 colonnes de macros au meme emplacement. Les intitules de colonnes sont variables selon la recette, par exemple `1 portion`, `+ topping`, `variante proteinee`, `version fruit`, ou `objectif 30 g prot.`. La structure HTML reste identique et seules les donnees changent dans `data/recipes.json`.

## Tags sous le titre

Les tags affiches sous le titre sont des libelles texte, sans pictogramme. Les pictogrammes de categorie sont trop petits a cet emplacement et ne doivent pas etre reintegres automatiquement.

Couleurs validees :

- `Jour Modere` : terracotta / orange pastel officiel `#E8A17A` ;
- `Jour Bas` : vert olive officiel `#6E7F63`.

Les autres tags restent dans le style doux neutre de la page.

## Page produits web

Le site contient un onglet `Produits` alimente par `data/products.json`. Chaque produit indique le nom, la marque, le lieu d'achat, la categorie, les notes et les tags. Les decors botaniques web reutilisent l'asset existant `assets/cadres/cadre_photo_cercle_partiel_botanique_officiel.png` en decoration legere ; aucun asset du Design System n'est modifie.

## Pictogrammes web

Les pages recettes web utilisent les copies locales des pictogrammes officiels dans `assets/pictos/` et leurs versions d'affichage dans `assets/pictos/web/`. Ces fichiers proviennent du Design System mais sont copies cote site pour ne jamais modifier les assets officiels.

Regles validees :

- les pictogrammes `Cuisson`, `Difficulte`, `Conservation` et `Jour Modere` doivent etre recadres cote web autour du dessin visible, afin de ne pas paraitre plus petits a cause de marges transparentes ou de fond residuel ;
- les pictogrammes du cartouche pratique doivent avoir une presence visuelle comparable entre eux ;
- les pictogrammes des modules de droite doivent etre assez grands et contrastes pour rester lisibles ;
- les tags sous le titre restent en texte seul ;
- les pictogrammes officiels du Design System ne sont jamais modifies directement.

Les chemins des pictogrammes utilises par chaque recette sont definis dans `data/recipes.json`.
