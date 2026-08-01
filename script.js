
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

function setupKitchenMode() {
  const recipe = document.querySelector(".single-recipe");
  if (!recipe) return;

  const host = recipe.querySelector(".kitchen-mode-anchor") || recipe.querySelector(".recipe-head > div") || recipe;
  const wrapper = document.createElement("div");
  wrapper.className = "kitchen-mode";

  const button = document.createElement("button");
  button.type = "button";
  button.className = "kitchen-mode__button";
  button.setAttribute("aria-pressed", "false");
  button.textContent = "Mode cuisine — Garder l’écran allumé";

  const status = document.createElement("p");
  status.className = "kitchen-mode__status";
  status.setAttribute("aria-live", "polite");

  wrapper.append(button, status);
  const anchor = host.classList.contains("kitchen-mode-anchor") ? host : null;
  const favoriteButton = host.querySelector(".favorite-button");
  if (anchor) {
    anchor.appendChild(wrapper);
  } else if (favoriteButton) {
    favoriteButton.insertAdjacentElement("afterend", wrapper);
  } else {
    host.appendChild(wrapper);
  }

  let wakeLock = null;
  let kitchenModeRequested = false;

  function setState(active, message) {
    button.classList.toggle("active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.textContent = active
      ? "Mode cuisine actif — Désactiver"
      : "Mode cuisine — Garder l’écran allumé";
    status.textContent = message || "";
  }

  async function releaseWakeLock(message) {
    if (wakeLock) {
      const sentinel = wakeLock;
      wakeLock = null;
      try {
        await sentinel.release();
      } catch {
        // The lock may already have been released by the browser.
      }
    }
    setState(false, message || "Mode cuisine désactivé.");
  }

  async function requestWakeLock() {
    if (!navigator.wakeLock || typeof navigator.wakeLock.request !== "function") {
      kitchenModeRequested = false;
      setState(false, "Mode cuisine indisponible sur ce navigateur.");
      return;
    }

    if (document.visibilityState !== "visible") return;

    try {
      wakeLock = await navigator.wakeLock.request("screen");
      wakeLock.addEventListener("release", () => {
        wakeLock = null;
        if (kitchenModeRequested && document.visibilityState === "visible") {
          setState(false, "Le verrouillage a été interrompu par le navigateur ou l’économie d’énergie.");
        }
      });
      setState(true, "Écran maintenu allumé tant que cette recette reste ouverte.");
    } catch {
      wakeLock = null;
      kitchenModeRequested = false;
      setState(false, "Impossible d’activer le mode cuisine. Le navigateur, la batterie ou l’économie d’énergie peut le bloquer.");
    }
  }

  button.addEventListener("click", async () => {
    kitchenModeRequested = !kitchenModeRequested;
    if (kitchenModeRequested) {
      await requestWakeLock();
    } else {
      await releaseWakeLock("Mode cuisine désactivé.");
    }
  });

  document.addEventListener("visibilitychange", async () => {
    if (document.visibilityState === "visible" && kitchenModeRequested && !wakeLock) {
      await requestWakeLock();
    }
  });

  if (!navigator.wakeLock || typeof navigator.wakeLock.request !== "function") {
    status.textContent = "Mode cuisine disponible uniquement sur les navigateurs compatibles.";
  }
}

setupKitchenMode();

function formatQuantity(value) {
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : String(rounded).replace(".", ",");
}

function setupPortionCalculator() {
  const calculator = document.querySelector(".portion-calculator");
  if (!calculator) return;

  const buttons = [...calculator.querySelectorAll("button[data-servings]")];
  const ingredients = [...document.querySelectorAll("[data-base-quantity]")];
  const current = calculator.querySelector(".portion-calculator__current");

  function updatePortions(servings) {
    ingredients.forEach((item) => {
      const base = Number(item.dataset.baseQuantity);
      const unit = item.dataset.unit || "";
      const scaled = formatQuantity(base * servings);
      const quantity = item.querySelector(".ingredient-quantity");
      if (quantity) quantity.textContent = `${scaled}${unit ? ` ${unit}` : ""}`;
    });

    buttons.forEach((button) => {
      const active = Number(button.dataset.servings) === servings;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });

    if (current) {
      current.textContent = `${servings} portion${servings > 1 ? "s" : ""}`;
    }
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => updatePortions(Number(button.dataset.servings)));
  });

  updatePortions(1);
}

setupPortionCalculator();
