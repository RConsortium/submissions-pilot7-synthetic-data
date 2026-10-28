/** Worksheet tabs and independent tables inside the sandboxed Excel viewer. */
(() => {
  const tabs = [...document.querySelectorAll('.workbook-tabs [role="tab"]')];
  const panels = tabs.map((tab) => document.getElementById(tab.getAttribute("aria-controls")));
  const tablist = document.querySelector(".workbook-tabs");
  const panes = document.querySelector(".workbook-panes");
  const compare = document.getElementById("compare-worksheets");
  const status = document.getElementById("workbook-status");
  let active = 0, comparing = false;
  const selected = new Set([0]);

  const theme = new URLSearchParams(location.search).get("theme");
  document.documentElement.dataset.mdColorScheme = theme === "slate" ||
    (!theme && matchMedia("(prefers-color-scheme: dark)").matches) ? "slate" : "default";

  function render() {
    tabs.forEach((tab, i) => {
      tab.setAttribute("aria-selected", String(selected.has(i)));
      tab.tabIndex = i === active ? 0 : -1;
      panels[i].hidden = !selected.has(i);
    });
    tablist.setAttribute("aria-multiselectable", String(comparing));
    panes.classList.toggle("comparing", comparing);
    panes.style.setProperty("--sheet-count", selected.size);
    if (compare) {
      compare.textContent = comparing ? "Close worksheet comparison" : "Compare worksheets";
      compare.setAttribute("aria-pressed", String(comparing));
    }
    status.textContent = comparing
      ? `${selected.size} ${selected.size === 1 ? "worksheet" : "worksheets"} selected. Select tabs to add or remove worksheets.`
      : `${active + 1} of ${tabs.length} worksheets`;
  }

  function choose(index) {
    active = index;
    if (comparing) {
      if (selected.has(index) && selected.size > 1) selected.delete(index);
      else selected.add(index);
    } else {
      selected.clear();
      selected.add(index);
    }
    render();
  }

  tabs.forEach((tab, i) => tab.addEventListener("click", () => choose(i)));
  tablist.addEventListener("keydown", (event) => {
    const index = tabs.indexOf(event.target);
    if (index < 0 || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    active = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 :
      (index + (event.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
    if (comparing) render();
    else choose(active);
    tabs[active].focus();
  });
  compare?.addEventListener("click", () => {
    comparing = !comparing;
    if (comparing) selected.add((active + 1) % tabs.length);
    else {
      if (!selected.has(active)) active = [...selected][0];
      selected.clear();
      selected.add(active);
    }
    render();
  });

  function revealCitation() {
    const match = /^#sheet-(\d+)(?:-row-\d+)?$/.exec(location.hash);
    if (!match) return;
    const index = Number(match[1]) - 1;
    const target = document.getElementById(location.hash.slice(1));
    if (!panels[index] || !target) return;
    active = index;
    if (!comparing) selected.clear();
    selected.add(index);
    render();
    requestAnimationFrame(() => target.scrollIntoView({ block: "center", inline: "nearest" }));
  }
  addEventListener("hashchange", revealCitation);
  render();
  revealCitation();
})();
