/** Pointer and keyboard resizing for the specification, dataset panes and columns. */
export function createResizing(ctx, refit) {
  const clamp = (n, min, max) => Math.max(min, Math.min(max, n));
  function rememberPanels() {
    for (const card of ctx.root()?.querySelectorAll("[data-panel]") || []) {
      const size = {};
      if (card.style.width) size.width = parseFloat(card.style.width);
      if (card.style.height) size.height = parseFloat(card.style.height);
      if (Object.keys(size).length)
        ctx.layout.panels[card.dataset.panel] = size;
    }
  }
  function split(kind, value) {
    const isSpec = kind === "spec",
      adjusted = clamp(value, 25, isSpec ? 60 : 75);
    ctx.layout[isSpec ? "spec" : "inputs"] = adjusted;
    ctx
      .root()
      .querySelector(".review-workbench")
      .style.setProperty(
        isSpec ? "--spec-width" : "--input-height",
        adjusted + "%",
      );
    refit();
    ctx
      .byId(isSpec ? "spec-resizer" : "data-resizer")
      ?.setAttribute("aria-valuenow", String(Math.round(adjusted)));
  }
  function column(handle, width) {
    const value = Math.round(clamp(width, 72, 640)),
      card = handle.closest("[data-panel]"),
      name = handle.dataset.resizeColumn;
    if (!card?.isConnected) return;
    const widths = (ctx.layout.columns[card.dataset.panel] ||= {});
    widths[name] = value;
    const cols = [...card.querySelectorAll("col[data-column]")];
    cols.find((c) => c.dataset.column === name).style.width = value + "px";
    card.querySelector("table").style.width =
      36 + cols.reduce((sum, c) => sum + parseFloat(c.style.width), 0) + "px";
    handle.setAttribute("aria-valuenow", String(value));
  }
  function panel(key, step) {
    const card = ctx.byId("panel-" + key);
    if (!card) return;
    card.style.width =
      clamp(
        card.getBoundingClientRect().width + step,
        260,
        Math.max(640, innerWidth * 1.5),
      ) + "px";
    rememberPanels();
    refit();
  }
  function pointer(event) {
    const handle = event.target.closest(
      "[data-resize-column],#spec-resizer,#data-resizer",
    );
    if (!handle) return;
    event.preventDefault();
    const startX = event.clientX,
      startWidth = Number(handle.getAttribute("aria-valuenow"));
    const move = (e) => {
      if (handle.hasAttribute("data-resize-column"))
        column(handle, startWidth + e.clientX - startX);
      else {
        const box = (
          handle.id === "spec-resizer"
            ? ctx.root().querySelector(".review-workbench")
            : ctx.root().querySelector(".data-panes")
        ).getBoundingClientRect();
        split(
          handle.id === "spec-resizer" ? "spec" : "inputs",
          100 *
            (handle.id === "spec-resizer"
              ? (e.clientX - box.left) / box.width
              : (e.clientY - box.top) / box.height),
        );
      }
    };
    const done = () => {
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerup", done);
      document.removeEventListener("pointercancel", done);
    };
    document.addEventListener("pointermove", move);
    document.addEventListener("pointerup", done);
    document.addEventListener("pointercancel", done);
  }
  function keyboard(event) {
    const handle = event.target;
    if (handle.hasAttribute("data-resize-column")) {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key))
        return;
      event.preventDefault();
      column(
        handle,
        event.key === "Home"
          ? 72
          : event.key === "End"
            ? 640
            : Number(handle.getAttribute("aria-valuenow")) +
              (event.key === "ArrowLeft" ? -10 : 10),
      );
      return;
    }
    if (!["spec-resizer", "data-resizer"].includes(handle.id)) return;
    const spec = handle.id === "spec-resizer",
      keys = spec ? ["ArrowLeft", "ArrowRight"] : ["ArrowUp", "ArrowDown"];
    if (![...keys, "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    split(
      spec ? "spec" : "inputs",
      event.key === "Home"
        ? 25
        : event.key === "End"
          ? spec
            ? 60
            : 75
          : Number(handle.getAttribute("aria-valuenow")) +
            (event.key === keys[0] ? -2 : 2),
    );
  }
  return { rememberPanels, split, column, panel, pointer, keyboard };
}
