(() => {
  const groups = [...document.querySelectorAll(".publication-rail details")];
  const papers = document.querySelector(".publication-list");
  let currentLink = null;
  let currentPaper = null;

  function showLocation() {
    currentLink?.removeAttribute("aria-current");
    currentLink = null;
    currentPaper?.classList.remove("is-selected");
    const target = document.getElementById(location.hash.slice(1));
    currentPaper = target?.closest(".publication-list .paper");
    currentPaper?.classList.add("is-selected");
    const direction = target?.closest(".publication-direction");
    const group = direction && groups.find(item => item.dataset.direction === direction.id);
    if (!group) return;

    group.open = true;
    currentLink = [...group.querySelectorAll("a")].find(link => link.getAttribute("href") === location.hash)
      || group.querySelector("summary");
    currentLink.setAttribute("aria-current", "location");
  }

  papers.addEventListener("click", event => {
    if (event.defaultPrevented || event.button !== 0 || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
    if (event.target.closest("a, button, input, select, textarea, summary, [contenteditable]")) return;
    if (window.getSelection()?.isCollapsed === false) return;
    const paper = event.target.closest(".paper[id]");
    if (!paper) return;

    const fragment = "#" + paper.id;
    if (fragment !== location.hash) history.replaceState(history.state, "", fragment);
    showLocation();
  });

  window.addEventListener("hashchange", showLocation);
  window.addEventListener("popstate", showLocation);
  window.addEventListener("pageshow", showLocation);
  showLocation();
  document.body.classList.add("publication-selection-ready");
})();
