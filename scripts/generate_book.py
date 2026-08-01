from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.doctemplate import SimpleDocTemplate as ReportLabSimpleDocTemplate


ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "recipes.json"
OUTPUT_DIR = ROOT / "output"
PDF_FILE = OUTPUT_DIR / "Les_Recettes_de_Sophie.pdf"
HTML_FILE = OUTPUT_DIR / "Les_Recettes_de_Sophie.html"
HTML_DIR = OUTPUT_DIR / "html"
HTML_ASSETS_DIR = HTML_DIR / "assets"
HTML_RECIPES_DIR = HTML_DIR / "recettes"
HTML_DATA_DIR = HTML_DIR / "data"
HTML_PDF_DIR = HTML_DIR / "pdf"

COLORS = {
    "cream": colors.HexColor("#FBF6EE"),
    "brown": colors.HexColor("#4A2E21"),
    "orange": colors.HexColor("#D97A35"),
    "green": colors.HexColor("#DDEBD7"),
    "green_dark": colors.HexColor("#3F7A4A"),
    "blue": colors.HexColor("#DDEAF6"),
    "gold": colors.HexColor("#F3DEAA"),
    "text": colors.HexColor("#3A302A"),
    "line": colors.HexColor("#E4D8C8"),
}

DAY_COLORS = {
    "Jour Bas": COLORS["green"],
    "Jour Modere": COLORS["gold"],
    "Jour Haut": COLORS["blue"],
}

COOKING_MODES = ["Sans cuisson", "Micro-ondes", "Poele", "Four", "Air Fryer"]
RECIPE_FILE_OVERRIDES = {
    "R001": "acai-bowl.html",
    "R003": "clafouflan.html",
    "R007": "bowlcake-nuage.html",
}


def register_fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\DejaVuSans.ttf")
    bold = Path(r"C:\Windows\Fonts\DejaVuSans-Bold.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("BookRegular", str(regular)))
        pdfmetrics.registerFont(TTFont("BookBold", str(bold)))
        return "BookRegular", "BookBold"
    return "Helvetica", "Helvetica-Bold"


FONT_REGULAR, FONT_BOLD = register_fonts()


def load_book_data(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    latest_by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for recipe in data["recipes"]:
        recipe_id = recipe["id"]
        if recipe_id not in latest_by_id:
            order.append(recipe_id)
        latest_by_id[recipe_id] = recipe

    data["recipes"] = [latest_by_id[recipe_id] for recipe_id in order]
    data["recipes"].sort(key=lambda item: item["id"])
    return data


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=30,
            leading=36,
            textColor=COLORS["brown"],
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName=FONT_REGULAR,
            fontSize=13,
            leading=18,
            textColor=COLORS["orange"],
            alignment=TA_CENTER,
            spaceAfter=24,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=20,
            leading=26,
            textColor=COLORS["brown"],
            spaceBefore=8,
            spaceAfter=12,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=12,
            leading=14,
            textColor=COLORS["orange"],
            spaceBefore=5,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=8.6,
            leading=11,
            textColor=COLORS["text"],
            spaceAfter=3,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName=FONT_REGULAR,
            fontSize=8,
            leading=10,
            textColor=COLORS["text"],
        ),
        "recipe_title": ParagraphStyle(
            "RecipeTitle",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=17,
            leading=21,
            textColor=COLORS["brown"],
            spaceAfter=5,
        ),
        "box_title": ParagraphStyle(
            "BoxTitle",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=9,
            leading=11,
            textColor=COLORS["brown"],
            spaceAfter=2,
        ),
    }


STYLES = styles()


class RecipeDocTemplate(ReportLabSimpleDocTemplate):
    def afterFlowable(self, flowable: Any) -> None:
        if not isinstance(flowable, Paragraph):
            return
        text = flowable.getPlainText()
        if text == "Sommaire":
            self.canv.bookmarkPage("sommaire")
            self.canv.addOutlineEntry("Sommaire", "sommaire", level=0, closed=False)
        match = re.match(r"^(R\d{3}) - (.+)$", text)
        if match:
            recipe_id = match.group(1)
            self.canv.bookmarkPage(recipe_id)
            self.canv.addOutlineEntry(text, recipe_id, level=1, closed=False)


def p(text: Any, style: str = "body") -> Paragraph:
    value = str(text)
    if "<link " in value or "<a name=" in value:
        return Paragraph(value.replace("\n", "<br/>"), STYLES[style])
    return Paragraph(html.escape(value).replace("\n", "<br/>"), STYLES[style])


def bullet_list(items: list[str]) -> ListFlowable:
    return ListFlowable(
        [ListItem(p(item), leftIndent=8) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=12,
        bulletFontName=FONT_REGULAR,
    )


def macro_table(macros: dict[str, Any], title: str) -> Table:
    def macro_value(key: str, suffix: str = "") -> str:
        value = str(macros.get(key, "a completer"))
        return f"{value}{suffix}" if numeric(value) > 0 else value

    rows = [
        [p(title, "box_title"), "", "", "", ""],
        [p("kcal", "small"), p("Prot.", "small"), p("Gluc.", "small"), p("Lip.", "small"), p("Fibres", "small")],
        [
            p(macro_value("kcal"), "small"),
            p(macro_value("proteins_g", " g"), "small"),
            p(macro_value("carbs_g", " g"), "small"),
            p(macro_value("fat_g", " g"), "small"),
            p(macro_value("fiber_g", " g"), "small"),
        ],
    ]
    table = Table(rows, colWidths=[2.1 * cm] * 5, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (-1, 0)),
                ("BACKGROUND", (0, 0), (-1, 0), COLORS["gold"]),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, COLORS["line"]),
                ("BOX", (0, 0), (-1, -1), 0.8, COLORS["line"]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def info_table(recipe: dict[str, Any]) -> Table:
    data = [
        [p("Categorie", "small"), p(recipe["category"], "small")],
        [p("Portions", "small"), p(recipe["servings"], "small")],
        [p("Preparation", "small"), p(recipe["prep_time"], "small")],
        [p("Cuisson", "small"), p(recipe["cook_time"], "small")],
        [p("Difficulte", "small"), p(recipe["difficulty"], "small")],
    ]
    table = Table(data, colWidths=[2.4 * cm, 4.4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), COLORS["cream"]),
                ("GRID", (0, 0), (-1, -1), 0.45, COLORS["line"]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def compatibility_table(recipe: dict[str, Any]) -> Table:
    cells = []
    backgrounds = []
    for day in ["Jour Bas", "Jour Modere", "Jour Haut"]:
        active = day in recipe.get("compatibility", [])
        label = ("OK " if active else "- ") + day
        cells.append(p(label, "small"))
        backgrounds.append(DAY_COLORS[day] if active else colors.white)
    table = Table([cells], colWidths=[3.2 * cm, 3.2 * cm, 3.2 * cm])
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, COLORS["line"]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    for index, background in enumerate(backgrounds):
        commands.append(("BACKGROUND", (index, 0), (index, 0), background))
    table.setStyle(TableStyle(commands))
    return table


def image_or_placeholder(recipe: dict[str, Any]) -> Table | Image:
    image_path = ROOT / recipe.get("image", "")
    if image_path.exists():
        img = Image(str(image_path), width=7 * cm, height=4.6 * cm)
        img.hAlign = "LEFT"
        return img
    placeholder = Table(
        [[p("Photo officielle a ajouter\n" + recipe["image"], "small")]],
        colWidths=[7 * cm],
        rowHeights=[3.5 * cm],
    )
    placeholder.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLORS["cream"]),
                ("BOX", (0, 0), (-1, -1), 0.8, COLORS["line"]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return placeholder


def section(title: str, content: Any) -> list[Any]:
    if isinstance(content, list):
        body = bullet_list(content)
    else:
        body = p(content)
    return [p(title, "h2"), body]


def recipe_flowables(recipe: dict[str, Any]) -> list[Any]:
    story: list[Any] = []
    story.append(p(f'<a name="{recipe["id"]}"/>{recipe["id"]} - {recipe["name"]}', "recipe_title"))
    story.append(p('<link href="#sommaire">Retour sommaire</link>', "small"))
    tags = " - ".join(recipe.get("tags", []))
    story.append(p(tags, "small"))
    story.append(Spacer(1, 0.18 * cm))
    story.append(Table([[image_or_placeholder(recipe), info_table(recipe)]], colWidths=[7.4 * cm, 7.2 * cm]))
    story.append(Spacer(1, 0.25 * cm))
    story.extend(section("Ingredients", recipe.get("ingredients", [])))
    story.extend(section("Preparation", recipe.get("preparation", [])))
    story.extend(section("Conseils de cuisson", recipe.get("cooking_tips", "a completer")))
    story.extend(section("Conservation", recipe.get("storage", "a completer")))
    story.append(Spacer(1, 0.1 * cm))
    story.append(macro_table(recipe.get("macros_total", {}), "Macros recette entiere"))
    story.append(Spacer(1, 0.15 * cm))
    story.append(macro_table(recipe.get("macros_per_serving", {}), "Macros par portion"))
    if recipe.get("macros_with_serving_suggestion"):
        story.append(Spacer(1, 0.15 * cm))
        extra = recipe["macros_with_serving_suggestion"]
        story.append(macro_table(extra, extra.get("label", "Macros avec accompagnement")))
    story.extend(section("Variantes", recipe.get("variants", [])))
    story.extend(section("Suggestions d'accompagnement", recipe.get("serving_suggestions", [])))
    story.append(p("Compatibilite", "h2"))
    story.append(compatibility_table(recipe))
    story.extend(section("Notes", recipe.get("notes", "a completer")))
    return story


def intro_story(data: dict[str, Any]) -> list[Any]:
    return [
        p(data["title"], "title"),
        p(data["subtitle"], "subtitle"),
        Spacer(1, 3 * cm),
        p("Un livre de recettes personnalise, pense pour une cuisine simple, lisible et compatible avec le carb cycling.", "body"),
        Spacer(1, 6 * cm),
        p("Version generee automatiquement a partir de recipes.json", "small"),
        PageBreak(),
        p("Introduction", "h1"),
        p(
            "Ce livre rassemble les recettes validees de Sophie dans un format homogene, imprimable en A4 et confortable sur tablette. Les champs non fournis restent volontairement indiques comme a completer.",
            "body",
        ),
        p(
            "Pour remplacer une recette, gardez le meme identifiant R001, R002, etc. Si un doublon existe dans recipes.json, le generateur conserve uniquement la derniere version rencontree.",
            "body",
        ),
        PageBreak(),
    ]


def toc_story(data: dict[str, Any]) -> list[Any]:
    story = [p('<a name="sommaire"/>Sommaire', "h1")]
    grouped = group_by_category(data["recipes"], data["categories"])
    rows = []
    for category, recipes in grouped.items():
        if recipes:
            rows.append([p(category, "box_title"), p(f"{len(recipes)} recette(s)", "small")])
            for recipe in recipes:
                rows.append([p(f'<link href="#{recipe["id"]}">{recipe["id"]} - {recipe["name"]}</link>', "small"), p("", "small")])
    table = Table(rows, colWidths=[12 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.35, COLORS["line"]),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([table, PageBreak()])
    return story


def group_by_category(recipes: list[dict[str, Any]], categories: list[str]) -> dict[str, list[dict[str, Any]]]:
    grouped = {category: [] for category in categories}
    for recipe in recipes:
        grouped.setdefault(recipe["category"], []).append(recipe)
    return grouped


def recipe_line(recipe: dict[str, Any]) -> str:
    return f"{recipe['id']} - {recipe['name']}"


def is_long_recipe(recipe: dict[str, Any]) -> bool:
    return len(recipe.get("ingredients", [])) > 8 or bool(recipe.get("macros_with_serving_suggestion"))


def index_block(title: str, entries: list[str]) -> list[Any]:
    if not entries:
        entries = ["Aucune recette pour le moment"]
    return [p(title, "h2"), bullet_list(entries), Spacer(1, 0.15 * cm)]


def index_story(data: dict[str, Any]) -> list[Any]:
    recipes = data["recipes"]
    story: list[Any] = [PageBreak(), p("Index automatiques", "h1")]

    grouped = group_by_category(recipes, data["categories"])
    for category, items in grouped.items():
        story.extend(index_block(f"Index par categorie - {category}", [recipe_line(item) for item in items]))

    for day in ["Jour Bas", "Jour Modere", "Jour Haut"]:
        story.extend(index_block(f"Index {day}", [recipe_line(recipe) for recipe in recipes if day in recipe.get("compatibility", [])]))

    ingredients = defaultdict(list)
    prep_times = defaultdict(list)
    cooking_modes = defaultdict(list)
    for recipe in recipes:
        ingredients[recipe.get("main_ingredient", "a completer")].append(recipe_line(recipe))
        prep_times[recipe.get("prep_time", "a completer")].append(recipe_line(recipe))
        cooking_modes[recipe.get("cooking_mode", "a completer")].append(recipe_line(recipe))

    for ingredient, entries in sorted(ingredients.items()):
        story.extend(index_block(f"Ingredient principal - {ingredient}", entries))
    for prep_time, entries in sorted(prep_times.items()):
        story.extend(index_block(f"Temps de preparation - {prep_time}", entries))
    for mode in COOKING_MODES:
        story.extend(index_block(f"Mode de cuisson - {mode}", cooking_modes.get(mode, [])))

    story.extend(index_block("Batch Cooking / Meal Prep", [recipe_line(recipe) for recipe in recipes if recipe.get("batch_cooking")]))
    story.extend(
        index_block(
            "Recettes >= 30 g de proteines",
            [recipe_line(recipe) for recipe in recipes if numeric(recipe.get("macros_per_serving", {}).get("proteins_g")) >= 30],
        )
    )
    story.extend(
        index_block(
            "Recettes < 300 kcal",
            [recipe_line(recipe) for recipe in recipes if 0 < numeric(recipe.get("macros_per_serving", {}).get("kcal")) < 300],
        )
    )
    return story


def numeric(value: Any) -> float:
    if value is None:
        return 0
    match = re.search(r"\d+(?:[,.]\d+)?", str(value))
    return float(match.group(0).replace(",", ".")) if match else 0


def footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFillColor(COLORS["cream"])
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.setFillColor(COLORS["text"])
    canvas.setFont(FONT_REGULAR, 8)
    canvas.drawCentredString(A4[0] / 2, 0.9 * cm, f"Les Recettes de Sophie - {doc.page}")
    canvas.restoreState()


def build_pdf(data: dict[str, Any]) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    doc = RecipeDocTemplate(
        str(PDF_FILE),
        pagesize=A4,
        rightMargin=1.7 * cm,
        leftMargin=1.7 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.4 * cm,
        title=data["title"],
        author="Sophie",
    )
    story: list[Any] = []
    story.extend(intro_story(data))
    story.extend(toc_story(data))
    grouped = group_by_category(data["recipes"], data["categories"])
    for category, recipes in grouped.items():
        if not recipes:
            continue
        story.append(p(category, "h1"))
        story.append(Spacer(1, 0.2 * cm))
        for index, recipe in enumerate(recipes):
            story.extend(recipe_flowables(recipe))
            if index < len(recipes) - 1:
                story.append(Spacer(1, 0.45 * cm) if is_long_recipe(recipe) else PageBreak())
        story.append(PageBreak())
    story.extend(index_story(data))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def recipe_filename(recipe: dict[str, Any]) -> str:
    return RECIPE_FILE_OVERRIDES.get(recipe["id"], f"{slug(recipe['name'])}.html")


def recipe_href(recipe: dict[str, Any], prefix: str = "") -> str:
    return f"{prefix}recettes/{recipe_filename(recipe)}"


def site_nav(prefix: str = "") -> str:
    links = [
        ("Accueil", "index.html"),
        ("Recettes", "recettes.html"),
        ("Guides", "guides.html"),
        ("Planning", "planning.html"),
        ("Courses", "liste-courses.html"),
        ("Favoris", "favoris.html"),
        ("Recherche", "recherche.html"),
    ]
    return "<nav class='site-nav'>" + "".join(f"<a href='{prefix}{href}'>{label}</a>" for label, href in links) + "</nav>"


def page_shell(title: str, body: str, prefix: str = "") -> str:
    return f"""<!doctype html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <link rel="stylesheet" href="{prefix}style.css">
</head>
<body>
  {site_nav(prefix)}
  {body}
  <script src="{prefix}script.js"></script>
</body>
</html>
"""


def local_image(recipe: dict[str, Any]) -> str:
    image = recipe.get("image", "")
    source = ROOT / image
    if not source.exists():
        return ""
    HTML_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    target = HTML_ASSETS_DIR / source.name
    shutil.copy2(source, target)
    return f"assets/{target.name}"


def list_html(items: list[str], ordered: bool = False) -> str:
    tag = "ol" if ordered else "ul"
    return f"<{tag}>" + "".join(f"<li>{esc(item)}</li>" for item in items) + f"</{tag}>"


def macros_html(title: str, macros: dict[str, Any]) -> str:
    labels = [
        ("Calories", "kcal", ""),
        ("Proteines", "proteins_g", " g"),
        ("Glucides", "carbs_g", " g"),
        ("Lipides", "fat_g", " g"),
        ("Fibres", "fiber_g", " g"),
    ]
    rows = []
    for label, key, suffix in labels:
        value = str(macros.get(key, "a completer"))
        if numeric(value) > 0:
            value = f"{value}{suffix}"
        rows.append(f"<tr><th>{label}</th><td>{esc(value)}</td></tr>")
    return f"<div class='macro-card'><h4>{esc(title)}</h4><table>{''.join(rows)}</table></div>"


def recipe_search_text(recipe: dict[str, Any]) -> str:
    parts = [
        recipe.get("name", ""),
        recipe.get("category", ""),
        recipe.get("main_ingredient", ""),
        recipe.get("cooking_mode", ""),
        " ".join(recipe.get("tags", [])),
        " ".join(recipe.get("ingredients", [])),
        " ".join(recipe.get("compatibility", [])),
    ]
    return " ".join(parts).lower()


def filter_flags(recipe: dict[str, Any]) -> list[str]:
    flags = [f"cat:{recipe['category']}", f"cook:{recipe.get('cooking_mode', '')}"]
    flags.extend(recipe.get("compatibility", []))
    tags = recipe.get("tags", [])
    if recipe.get("batch_cooking"):
        flags.append("Batch Cooking")
    if "meal prep" in [tag.lower() for tag in tags]:
        flags.append("Meal Prep")
    if "riche en proteines" in [tag.lower() for tag in tags]:
        flags.append("Riche en proteines")
    if numeric(recipe.get("macros_per_serving", {}).get("proteins_g")) >= 30:
        flags.append(">= 30 g proteines")
    if 0 < numeric(recipe.get("macros_per_serving", {}).get("kcal")) < 300:
        flags.append("< 300 kcal")
    return flags


def quick_links(data: dict[str, Any]) -> list[tuple[str, str]]:
    links = [(category, f"cat:{category}") for category in data["categories"]]
    links.extend(
        [
            ("Jour Bas", "Jour Bas"),
            ("Jour Modere", "Jour Modere"),
            ("Jour Haut", "Jour Haut"),
            ("Recettes >= 30 g proteines", ">= 30 g proteines"),
            ("Recettes < 300 kcal", "< 300 kcal"),
        ]
    )
    return links


def filter_options(data: dict[str, Any]) -> list[tuple[str, str]]:
    options = [(category, f"cat:{category}") for category in data["categories"]]
    options.extend(
        [
            ("Jour Bas", "Jour Bas"),
            ("Jour Modere", "Jour Modere"),
            ("Jour Haut", "Jour Haut"),
            ("Air Fryer", "cook:Air Fryer"),
            ("Four", "cook:Four"),
            ("Poele", "cook:Poele"),
            ("Micro-ondes", "cook:Micro-ondes"),
            ("Sans cuisson", "cook:Sans cuisson"),
            ("Batch Cooking", "Batch Cooking"),
            ("Meal Prep", "Meal Prep"),
            ("Riche en proteines", "Riche en proteines"),
            (">= 30 g proteines", ">= 30 g proteines"),
            ("< 300 kcal", "< 300 kcal"),
        ]
    )
    return options


def nav_links(recipes: list[dict[str, Any]], index: int, prefix: str = "") -> str:
    previous_recipe = recipes[index - 1] if index > 0 else None
    next_recipe = recipes[index + 1] if index < len(recipes) - 1 else None
    previous_link = f"<a href='{recipe_href(previous_recipe, prefix)}'>Recette precedente</a>" if previous_recipe else "<span>Recette precedente</span>"
    next_link = f"<a href='{recipe_href(next_recipe, prefix)}'>Recette suivante</a>" if next_recipe else "<span>Recette suivante</span>"
    return (
        "<nav class='recipe-nav'>"
        f"<a href='{prefix}index.html'>Accueil</a>"
        f"<a href='{prefix}recettes.html'>Toutes les recettes</a>"
        f"{previous_link}{next_link}"
        "</nav>"
    )


def index_section_html(title: str, entries: list[dict[str, Any]]) -> str:
    if not entries:
        body = "<p>Aucune recette pour le moment.</p>"
    else:
        body = "<ul>" + "".join(f"<li><a href='{recipe_href(recipe)}'>{esc(recipe_line(recipe))}</a></li>" for recipe in entries) + "</ul>"
    return f"<details open><summary>{esc(title)}</summary>{body}</details>"


def indexes_html(data: dict[str, Any]) -> str:
    recipes = data["recipes"]
    grouped = group_by_category(recipes, data["categories"])
    sections = ["<section id='index' class='panel'><h2>Index interactifs</h2>"]
    for category, entries in grouped.items():
        sections.append(index_section_html(f"Par categorie - {category}", entries))
    for day in ["Jour Bas", "Jour Modere", "Jour Haut"]:
        sections.append(index_section_html(day, [recipe for recipe in recipes if day in recipe.get("compatibility", [])]))

    ingredients: dict[str, list[dict[str, Any]]] = defaultdict(list)
    prep_times: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cooking_modes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for recipe in recipes:
        ingredients[recipe.get("main_ingredient", "a completer")].append(recipe)
        prep_times[recipe.get("prep_time", "a completer")].append(recipe)
        cooking_modes[recipe.get("cooking_mode", "a completer")].append(recipe)
    for ingredient, entries in sorted(ingredients.items()):
        sections.append(index_section_html(f"Ingredient principal - {ingredient}", entries))
    for prep_time, entries in sorted(prep_times.items()):
        sections.append(index_section_html(f"Temps de preparation - {prep_time}", entries))
    for mode in COOKING_MODES:
        sections.append(index_section_html(f"Mode de cuisson - {mode}", cooking_modes.get(mode, [])))
    sections.append(index_section_html("Batch Cooking / Meal Prep", [recipe for recipe in recipes if recipe.get("batch_cooking") or "meal prep" in " ".join(recipe.get("tags", [])).lower()]))
    sections.append(index_section_html("Recettes >= 30 g proteines", [recipe for recipe in recipes if numeric(recipe.get("macros_per_serving", {}).get("proteins_g")) >= 30]))
    sections.append(index_section_html("Recettes < 300 kcal", [recipe for recipe in recipes if 0 < numeric(recipe.get("macros_per_serving", {}).get("kcal")) < 300]))
    sections.append("</section>")
    return "\n".join(sections)


def recipe_card_html(recipe: dict[str, Any], recipes: list[dict[str, Any]], index: int) -> str:
    image = local_image(recipe)
    flags = filter_flags(recipe)
    compatibility = "".join(
        f"<span class='day {'active' if day in recipe.get('compatibility', []) else ''}'>{esc(day)}</span>"
        for day in ["Jour Bas", "Jour Modere", "Jour Haut"]
    )
    extra_macros = ""
    if recipe.get("macros_with_serving_suggestion"):
        extra = recipe["macros_with_serving_suggestion"]
        extra_macros = macros_html(extra.get("label", "Macros avec accompagnement"), extra)
    image_html = f"<img src='{esc(image)}' alt='Fiche {esc(recipe['name'])}'>" if image else "<div class='missing-image'>Image a ajouter</div>"
    return f"""
    <article id="{esc(recipe['id'])}" class="recipe-card" data-search="{esc(recipe_search_text(recipe))}" data-filters="{esc('|'.join(flags))}">
      {nav_links(recipes, index)}
      <div class="recipe-head">
        <div>
          <p class="kicker">{esc(recipe['id'])} - {esc(recipe['category'])}</p>
          <h2>{esc(recipe['name'])}</h2>
          <div class="tags">{''.join(f'<span>{esc(tag)}</span>' for tag in recipe.get('tags', []))}</div>
        </div>
        <div class="meta-grid">
          <span><strong>Portions</strong>{esc(recipe.get('servings', ''))}</span>
          <span><strong>Preparation</strong>{esc(recipe.get('prep_time', ''))}</span>
          <span><strong>Cuisson</strong>{esc(recipe.get('cook_time', ''))}</span>
          <span><strong>Difficulte</strong>{esc(recipe.get('difficulty', ''))}</span>
        </div>
      </div>
      <div class="recipe-layout">
        <figure class="recipe-image">{image_html}</figure>
        <div class="recipe-body">
          <section><h3>Ingredients</h3>{list_html(recipe.get('ingredients', []))}</section>
          <section><h3>Preparation</h3>{list_html(recipe.get('preparation', []), ordered=True)}</section>
          <section><h3>Conseils de cuisson</h3><p>{esc(recipe.get('cooking_tips', 'a completer'))}</p></section>
          <section><h3>Conservation</h3><p>{esc(recipe.get('storage', 'a completer'))}</p></section>
        </div>
      </div>
      <div class="macro-grid">
        {macros_html('Macros recette entiere', recipe.get('macros_total', {}))}
        {macros_html('Macros par portion', recipe.get('macros_per_serving', {}))}
        {extra_macros}
      </div>
      <div class="two-cols">
        <section><h3>Variantes</h3>{list_html(recipe.get('variants', []))}</section>
        <section><h3>Suggestions d'accompagnement</h3>{list_html(recipe.get('serving_suggestions', []))}</section>
      </div>
      <section><h3>Compatibilite</h3><div class="days">{compatibility}</div></section>
      <section><h3>Notes</h3><p>{esc(recipe.get('notes', 'a completer'))}</p></section>
      {nav_links(recipes, index)}
    </article>
    """


def recipe_tile(recipe: dict[str, Any]) -> str:
    image = local_image(recipe)
    image_html = f"<img src='{esc(image)}' alt='Fiche {esc(recipe['name'])}'>" if image else "<div class='missing-image'>Image a ajouter</div>"
    return f"""
    <a class="recipe-tile" href="{recipe_href(recipe)}">
      {image_html}
      <span>{esc(recipe['id'])}</span>
      <strong>{esc(recipe['name'])}</strong>
      <small>{esc(recipe['category'])} - {esc(recipe.get('prep_time', ''))}</small>
    </a>
    """


def recipe_page_html(recipe: dict[str, Any], recipes: list[dict[str, Any]], index: int) -> str:
    image = local_image(recipe)
    image_html = f"<img src='../{esc(image)}' alt='Fiche {esc(recipe['name'])}'>" if image else "<div class='missing-image'>Image a ajouter</div>"
    compatibility = "".join(
        f"<span class='day {'active' if day in recipe.get('compatibility', []) else ''}'>{esc(day)}</span>"
        for day in ["Jour Bas", "Jour Modere", "Jour Haut"]
    )
    extra_macros = ""
    if recipe.get("macros_with_serving_suggestion"):
        extra = recipe["macros_with_serving_suggestion"]
        extra_macros = macros_html(extra.get("label", "Macros avec accompagnement"), extra)
    body = f"""
    <main>
      <article id="{esc(recipe['id'])}" class="recipe-card single-recipe">
        {nav_links(recipes, index, '../')}
        <div class="recipe-head">
          <div>
            <p class="kicker">{esc(recipe['id'])} - {esc(recipe['category'])}</p>
            <h1>{esc(recipe['name'])}</h1>
            <button class="favorite-button" data-recipe-id="{esc(recipe['id'])}" type="button">Ajouter aux favoris</button>
            <div class="tags">{''.join(f'<span>{esc(tag)}</span>' for tag in recipe.get('tags', []))}</div>
          </div>
          <div class="meta-grid">
            <span><strong>Portions</strong>{esc(recipe.get('servings', ''))}</span>
            <span><strong>Preparation</strong>{esc(recipe.get('prep_time', ''))}</span>
            <span><strong>Cuisson</strong>{esc(recipe.get('cook_time', ''))}</span>
            <span><strong>Difficulte</strong>{esc(recipe.get('difficulty', ''))}</span>
          </div>
        </div>
        <div class="recipe-layout">
          <figure class="recipe-image">{image_html}</figure>
          <div class="recipe-body">
            <section><h2>Ingredients</h2>{list_html(recipe.get('ingredients', []))}</section>
            <section><h2>Preparation</h2>{list_html(recipe.get('preparation', []), ordered=True)}</section>
            <section><h2>Conseils de cuisson</h2><p>{esc(recipe.get('cooking_tips', 'a completer'))}</p></section>
            <section><h2>Conservation</h2><p>{esc(recipe.get('storage', 'a completer'))}</p></section>
          </div>
        </div>
        <div class="macro-grid">
          {macros_html('Macros recette entiere', recipe.get('macros_total', {}))}
          {macros_html('Macros par portion', recipe.get('macros_per_serving', {}))}
          {extra_macros}
        </div>
        <div class="two-cols">
          <section><h2>Variantes</h2>{list_html(recipe.get('variants', []))}</section>
          <section><h2>Suggestions d'accompagnement</h2>{list_html(recipe.get('serving_suggestions', []))}</section>
        </div>
        <section><h2>Compatibilite</h2><div class="days">{compatibility}</div></section>
        <section><h2>Notes</h2><p>{esc(recipe.get('notes', 'a completer'))}</p></section>
        {nav_links(recipes, index, '../')}
      </article>
    </main>
    """
    return page_shell(recipe["name"], body, "../")


def render_html(data: dict[str, Any]) -> None:
    for directory in [HTML_DIR, HTML_ASSETS_DIR, HTML_RECIPES_DIR, HTML_DATA_DIR, HTML_PDF_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    recipes = data["recipes"]
    grouped = group_by_category(recipes, data["categories"])
    quick = "".join(f"<button class='quick-filter' data-filter='{esc(value)}'>{esc(label)}</button>" for label, value in quick_links(data))
    filters = "".join(
        f"<label><input type='checkbox' value='{esc(value)}'> {esc(label)}</label>"
        for label, value in filter_options(data)
    )
    toc = []
    for category, entries in grouped.items():
        if not entries:
            continue
        toc.append(f"<div class='toc-group'><h3>{esc(category)}</h3><ul>")
        for recipe in entries:
            toc.append(f"<li><a href='{recipe_href(recipe)}'>{esc(recipe_line(recipe))}</a></li>")
        toc.append("</ul></div>")

    tiles = "".join(recipe_tile(recipe) for recipe in recipes)
    cards = "\n".join(recipe_card_html(recipe, recipes, index) for index, recipe in enumerate(recipes))

    home_body = f"""
    <header id="accueil" class="hero">
      <div>
        <h1>{esc(data['title'])}</h1>
        <p>{esc(data['subtitle'])}</p>
      </div>
      <div class="quick-actions">{quick}</div>
    </header>
    <main>
      <section class="panel action-grid">
        <a href="recettes.html">Toutes les recettes</a>
        <a href="recherche.html">Recherche avancee</a>
        <a href="planning.html">Menus de la semaine</a>
        <a href="liste-courses.html">Liste de courses</a>
        <a href="favoris.html">Favoris</a>
        <a href="pdf/Les_Recettes_de_Sophie.pdf">PDF</a>
      </section>
      <section class="panel">
        <h2>Dernieres fiches</h2>
        <div class="tile-grid">{tiles}</div>
      </section>
    </main>
    """

    recettes_body = f"""
    <main>
      <section id="sommaire" class="panel">
        <h1>Toutes les recettes</h1>
        <div class="toc">{''.join(toc)}</div>
      </section>
      <section class="panel">
        <h2>Galerie</h2>
        <div class="tile-grid">{tiles}</div>
      </section>
      {indexes_html(data)}
    </main>
    """

    recherche_body = f"""
    <main>
      <section class="toolbar">
        <label class="search-label" for="search">Recherche instantanee</label>
        <input id="search" type="search" placeholder="Nom, ingredient, categorie, tag, cuisson...">
        <div id="filters" class="filters">{filters}</div>
        <button id="resetFilters" type="button">Reinitialiser les filtres</button>
        <p id="resultCount" class="result-count"></p>
      </section>
      <section id="recettes" class="recipes">{cards}</section>
    </main>
    """

    guides_body = """
    <main>
      <section class="panel"><h1>Guides</h1><p>Cette page est prete a recevoir les guides carb cycling, batch cooking, equivalences et astuces de conservation.</p></section>
      <section class="panel"><h2>Guides prevus</h2><ul><li>Comprendre Jour Bas / Jour Modere / Jour Haut</li><li>Composer une assiette proteinee</li><li>Meal prep et conservation</li></ul></section>
    </main>
    """
    planning_body = """
    <main>
      <section class="panel"><h1>Menus de la semaine</h1><p>Zone de planning hebdomadaire. Les menus pourront etre ajoutes ici au fil du temps.</p></section>
      <section class="week-grid"><div>Lundi</div><div>Mardi</div><div>Mercredi</div><div>Jeudi</div><div>Vendredi</div><div>Samedi</div><div>Dimanche</div></section>
    </main>
    """
    courses_body = """
    <main>
      <section class="panel"><h1>Liste de courses</h1><p>Selectionne, copie ou imprime les ingredients utiles depuis les fiches recettes.</p></section>
      <section class="panel"><textarea class="shopping-notes" placeholder="Ajoute ici ta liste de courses..."></textarea></section>
    </main>
    """
    favoris_body = f"""
    <main>
      <section class="panel"><h1>Favoris</h1><p>Les recettes marquees en favoris sur ce navigateur apparaitront ici.</p></section>
      <section id="favoriteList" class="tile-grid" data-recipes='{esc(json.dumps([{"id": r["id"], "name": r["name"], "href": recipe_href(r), "category": r["category"]} for r in recipes], ensure_ascii=False))}'></section>
    </main>
    """

    (HTML_DIR / "index.html").write_text(page_shell(data["title"], home_body), encoding="utf-8")
    (HTML_DIR / "recettes.html").write_text(page_shell("Toutes les recettes", recettes_body), encoding="utf-8")
    (HTML_DIR / "guides.html").write_text(page_shell("Guides", guides_body), encoding="utf-8")
    (HTML_DIR / "planning.html").write_text(page_shell("Menus de la semaine", planning_body), encoding="utf-8")
    (HTML_DIR / "liste-courses.html").write_text(page_shell("Liste de courses", courses_body), encoding="utf-8")
    (HTML_DIR / "favoris.html").write_text(page_shell("Favoris", favoris_body), encoding="utf-8")
    (HTML_DIR / "recherche.html").write_text(page_shell("Recherche avancee", recherche_body), encoding="utf-8")
    for index, recipe in enumerate(recipes):
        (HTML_RECIPES_DIR / recipe_filename(recipe)).write_text(recipe_page_html(recipe, recipes, index), encoding="utf-8")
    (HTML_DIR / "style.css").write_text(css_text(), encoding="utf-8")
    (HTML_DIR / "script.js").write_text(js_text(), encoding="utf-8")
    (HTML_DATA_DIR / "recipes.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    if PDF_FILE.exists():
        shutil.copy2(PDF_FILE, HTML_PDF_DIR / PDF_FILE.name)
    HTML_FILE.write_text((HTML_DIR / "index.html").read_text(encoding="utf-8"), encoding="utf-8")


def css_text() -> str:
    return """
:root {
  --cream: #fbf6ee;
  --paper: #fffdf8;
  --brown: #4a2e21;
  --orange: #d97822;
  --green: #4b9258;
  --green-soft: #ddebd7;
  --gold: #f0d89a;
  --red-soft: #f4d8d2;
  --line: #e4d8c8;
  --text: #382f29;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  color: var(--text);
  background: var(--cream);
  font-family: Arial, Helvetica, sans-serif;
  line-height: 1.45;
}
a { color: var(--brown); }
.site-nav {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding: 10px 14px;
  background: rgba(251, 246, 238, .96);
  border-bottom: 1px solid var(--line);
}
.site-nav a {
  flex: 0 0 auto;
  text-decoration: none;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 12px;
  background: #fffaf2;
  font-weight: 800;
}
.hero {
  min-height: 52vh;
  padding: 56px min(7vw, 80px);
  display: grid;
  align-content: center;
  gap: 28px;
  background: linear-gradient(180deg, #fffdf8 0%, var(--cream) 100%);
  border-bottom: 1px solid var(--line);
}
.hero h1 {
  margin: 0;
  color: var(--brown);
  font-size: clamp(2.4rem, 7vw, 5rem);
  line-height: .95;
}
.hero p {
  margin: 14px 0 0;
  color: var(--orange);
  font-size: 1.2rem;
}
.quick-actions, .filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
button, .filters label, .recipe-nav a, .recipe-nav span {
  border: 1px solid var(--line);
  background: #fffaf2;
  color: var(--brown);
  border-radius: 8px;
  padding: 9px 12px;
  font-weight: 700;
}
button { cursor: pointer; }
button.active, .filters label.active {
  background: var(--green-soft);
  border-color: var(--green);
}
main {
  width: min(1180px, calc(100% - 28px));
  margin: 0 auto;
  padding: 24px 0 64px;
}
.toolbar, .panel, .recipe-card {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: 0 8px 28px rgba(74, 46, 33, .08);
}
.toolbar {
  position: sticky;
  top: 0;
  z-index: 5;
  padding: 18px;
  display: grid;
  gap: 12px;
}
.search-label {
  font-weight: 800;
  color: var(--brown);
}
#search {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 13px 14px;
  font-size: 1rem;
  background: white;
}
.result-count { margin: 0; color: #7a675a; }
.panel {
  margin-top: 22px;
  padding: 24px;
}
.action-grid, .tile-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 14px;
}
.action-grid a, .recipe-tile {
  text-decoration: none;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fffaf2;
  padding: 14px;
  font-weight: 800;
}
.recipe-tile {
  display: grid;
  gap: 8px;
}
.recipe-tile img {
  width: 100%;
  aspect-ratio: 4 / 5;
  object-fit: cover;
  object-position: top;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--cream);
}
.recipe-tile span {
  color: var(--orange);
}
.recipe-tile small {
  color: #7a675a;
}
.week-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-top: 22px;
}
.week-grid div {
  min-height: 130px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--paper);
  font-weight: 800;
}
.shopping-notes {
  width: 100%;
  min-height: 360px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  font: inherit;
}
h2, h3, h4 {
  color: var(--brown);
  letter-spacing: 0;
}
.panel h2, .recipe-card h3 {
  color: var(--orange);
}
.toc {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px 22px;
}
.toc-group ul, details ul { padding-left: 20px; }
.recipes {
  display: grid;
  gap: 24px;
  margin-top: 24px;
}
.recipe-card {
  padding: 22px;
  scroll-margin-top: 150px;
}
.recipe-card.hidden { display: none; }
.recipe-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.recipe-nav a { text-decoration: none; }
.recipe-nav span { opacity: .45; }
.recipe-head {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(260px, 420px);
  gap: 20px;
  align-items: start;
}
.kicker {
  margin: 0 0 6px;
  color: var(--orange);
  font-weight: 800;
}
.recipe-head h2 {
  margin: 0 0 10px;
  font-size: clamp(1.7rem, 4vw, 3rem);
  line-height: 1;
}
.recipe-head h1 {
  margin: 0 0 10px;
  color: var(--brown);
  font-size: clamp(2rem, 5vw, 3.7rem);
  line-height: 1;
}
.favorite-button.is-favorite {
  background: var(--green-soft);
  border-color: var(--green);
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.tags span {
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 5px 9px;
  background: var(--cream);
  font-size: .9rem;
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}
.meta-grid span {
  display: grid;
  gap: 3px;
  min-height: 64px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fffaf2;
}
.recipe-layout {
  display: grid;
  grid-template-columns: minmax(260px, 380px) 1fr;
  gap: 24px;
  margin-top: 18px;
}
.recipe-image {
  margin: 0;
}
.recipe-image img {
  width: 100%;
  max-height: 620px;
  object-fit: contain;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--cream);
}
.missing-image {
  display: grid;
  place-items: center;
  min-height: 220px;
  border: 1px dashed var(--line);
  border-radius: 8px;
  color: #7a675a;
}
.recipe-body {
  display: grid;
  gap: 12px;
}
ul, ol { margin-top: 6px; }
.macro-grid, .two-cols {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 14px;
  margin-top: 18px;
}
.macro-card {
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  background: white;
}
.macro-card h4 {
  margin: 0;
  padding: 10px 12px;
  color: white;
  background: var(--orange);
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  padding: 7px 12px;
  border-top: 1px solid var(--line);
  text-align: left;
}
td { text-align: right; }
.two-cols section, .recipe-card > section {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
  background: #fffdf8;
  margin-top: 14px;
}
.days {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.day {
  padding: 9px 12px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: white;
}
.day.active:nth-child(1) { background: var(--green-soft); border-color: var(--green); }
.day.active:nth-child(2) { background: var(--gold); }
.day.active:nth-child(3) { background: var(--red-soft); }
details {
  border-top: 1px solid var(--line);
  padding: 12px 0;
}
summary {
  cursor: pointer;
  color: var(--brown);
  font-weight: 800;
}

@media (max-width: 760px) {
  .hero { min-height: auto; padding: 34px 18px; }
  .toolbar { position: static; }
  .recipe-head, .recipe-layout { grid-template-columns: 1fr; }
  .meta-grid { grid-template-columns: 1fr; }
  .recipe-card { padding: 16px; }
}

@media print {
  body { background: white; }
  .hero, .toolbar, .panel, .recipe-nav, script { display: none !important; }
  main { width: auto; margin: 0; padding: 0; }
  .recipes { display: block; }
  .recipe-card {
    box-shadow: none;
    border: 0;
    border-radius: 0;
    page-break-inside: avoid;
    break-inside: avoid;
    padding: 1cm;
  }
  .recipe-card.hidden { display: block; }
  .recipe-layout { grid-template-columns: 7cm 1fr; }
  .recipe-image img { max-height: 12cm; }
}
"""


def js_text() -> str:
    return """
const searchInput = document.querySelector("#search");
const filterBox = document.querySelector("#filters");
const resetButton = document.querySelector("#resetFilters");
const resultCount = document.querySelector("#resultCount");
const cards = [...document.querySelectorAll(".recipe-card")];
const quickButtons = [...document.querySelectorAll(".quick-filter")];
const favoriteButtons = [...document.querySelectorAll(".favorite-button")];
const FAVORITES_KEY = "sophieRecipeFavorites";

function readFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY) || "[]");
  } catch {
    return [];
  }
}

function writeFavorites(ids) {
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(ids));
}

function updateFavoriteButtons() {
  const favorites = readFavorites();
  favoriteButtons.forEach((button) => {
    const active = favorites.includes(button.dataset.recipeId);
    button.classList.toggle("is-favorite", active);
    button.textContent = active ? "Retirer des favoris" : "Ajouter aux favoris";
  });
}

favoriteButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const id = button.dataset.recipeId;
    const favorites = readFavorites();
    const next = favorites.includes(id) ? favorites.filter((item) => item !== id) : [...favorites, id];
    writeFavorites(next);
    updateFavoriteButtons();
  });
});

const favoriteList = document.querySelector("#favoriteList");
if (favoriteList) {
  const recipes = JSON.parse(favoriteList.dataset.recipes || "[]");
  const favorites = readFavorites();
  const selected = recipes.filter((recipe) => favorites.includes(recipe.id));
  favoriteList.innerHTML = selected.length
    ? selected.map((recipe) => `<a class="recipe-tile" href="${recipe.href}"><span>${recipe.id}</span><strong>${recipe.name}</strong><small>${recipe.category}</small></a>`).join("")
    : "<p>Aucun favori pour le moment.</p>";
}

function selectedFilters() {
  if (!filterBox) return [];
  return [...filterBox.querySelectorAll("input:checked")].map((input) => input.value);
}

function refreshActiveLabels() {
  if (!filterBox) return;
  filterBox.querySelectorAll("label").forEach((label) => {
    const input = label.querySelector("input");
    label.classList.toggle("active", input.checked);
  });
  quickButtons.forEach((button) => {
    button.classList.toggle("active", selectedFilters().includes(button.dataset.filter));
  });
}

function applyFilters() {
  if (!searchInput || !filterBox || !resultCount) return;
  const query = searchInput.value.trim().toLowerCase();
  const filters = selectedFilters();
  let visible = 0;

  cards.forEach((card) => {
    const textMatch = !query || card.dataset.search.includes(query);
    const available = card.dataset.filters.split("|");
    const filterMatch = filters.every((filter) => available.includes(filter));
    const show = textMatch && filterMatch;
    card.classList.toggle("hidden", !show);
    if (show) visible += 1;
  });

  resultCount.textContent = `${visible} recette${visible > 1 ? "s" : ""} affichee${visible > 1 ? "s" : ""}`;
  refreshActiveLabels();
}

if (filterBox) filterBox.addEventListener("change", applyFilters);
if (searchInput) searchInput.addEventListener("input", applyFilters);
if (resetButton) {
  resetButton.addEventListener("click", () => {
    searchInput.value = "";
    filterBox.querySelectorAll("input").forEach((input) => { input.checked = false; });
    applyFilters();
  });
}

quickButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const value = button.dataset.filter;
    if (!filterBox) {
      window.location.href = `recherche.html?filter=${encodeURIComponent(value)}`;
      return;
    }
    const input = filterBox.querySelector(`input[value="${CSS.escape(value)}"]`);
    if (input) input.checked = !input.checked;
    document.querySelector(".toolbar").scrollIntoView({ behavior: "smooth", block: "start" });
    applyFilters();
  });
});

if (filterBox) {
  const params = new URLSearchParams(window.location.search);
  const initialFilter = params.get("filter");
  if (initialFilter) {
    const input = filterBox.querySelector(`input[value="${CSS.escape(initialFilter)}"]`);
    if (input) input.checked = true;
  }
}

updateFavoriteButtons();
applyFilters();
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Genere Les Recettes de Sophie.")
    parser.add_argument("--format", choices=["pdf", "html", "all"], default="all")
    args = parser.parse_args()
    data = load_book_data(DATA_FILE)
    if args.format in {"pdf", "all"}:
        build_pdf(data)
        print(f"PDF genere : {PDF_FILE}")
    if args.format in {"html", "all"}:
        render_html(data)
        print(f"HTML genere : {HTML_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
