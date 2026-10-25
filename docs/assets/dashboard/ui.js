/** Shared escaped markup; components never interpolate raw clinical values. */
export const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export const byId = (id) => document.getElementById(id);
export const link = (url, label, classes = "text-link") =>
  `<a class="${classes}" href="${esc(url)}" target="_blank" rel="noreferrer">${esc(label)} <span aria-hidden="true">&#8599;</span></a>`;
export const metric = (value) =>
  value >= 1e6 ? (value / 1e6).toFixed(1) + "M" : value.toLocaleString("en-US");
