
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
