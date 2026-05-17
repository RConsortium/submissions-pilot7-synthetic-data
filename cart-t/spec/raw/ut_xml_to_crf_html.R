#' =============================================================================
#' ut_xml_to_crf_html: Render OpenClinica ODM XML as a CRF-style review HTML
#'
#' Walks ClinicalData > SubjectData > StudyEventData > FormData > ItemGroupData
#' > ItemData and emits a reviewer-friendly page:
#'   - Sticky sidebar with subject filter
#'   - Per-subject card; events collapsed by default
#'   - Item/Value table per ItemGroup, with repeat-key and status chips
#'
#' Requires: xml2
#' =============================================================================

ut_xml_to_crf_html <- function(xml_path, html_path,
                               title = "CRF Data Review") {
  if (!file.exists(xml_path)) {
    stop("XML file not found: ", xml_path, call. = FALSE)
  }

  doc <- xml2::read_xml(xml_path)
  xml2::xml_ns_strip(doc)

  con <- file(html_path, open = "wb", encoding = "UTF-8")
  on.exit(close(con), add = TRUE)
  w <- function(...) cat(..., sep = "", file = con)

  esc <- function(s) {
    if (length(s) == 0L || is.na(s)) return("")
    s <- gsub("&",  "&amp;",  s, fixed = TRUE)
    s <- gsub("<",  "&lt;",   s, fixed = TRUE)
    s <- gsub(">",  "&gt;",   s, fixed = TRUE)
    s <- gsub('"',  "&quot;", s, fixed = TRUE)
    s
  }
  attr_or <- function(node, name, default = "") {
    v <- xml2::xml_attr(node, name)
    if (is.na(v)) default else v
  }

  studies <- xml2::xml_find_all(doc, ".//ClinicalData")

  # ----- Page head + styles -----
  w("<!DOCTYPE html>\n<html><head><meta charset=\"UTF-8\">\n",
    "<title>", esc(title), "</title>\n<style>\n",
    "*{box-sizing:border-box}\n",
    "body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;",
    "font-size:14px;color:#1f2937;background:#f8fafc}\n",
    ".layout{display:flex;min-height:100vh}\n",
    "aside.toc{width:280px;height:100vh;position:sticky;top:0;overflow-y:auto;",
    "background:#fff;border-right:1px solid #e5e7eb;padding:14px}\n",
    "aside.toc h2{font-size:11px;margin:14px 0 6px;color:#6b7280;",
    "text-transform:uppercase;letter-spacing:.06em;font-weight:600}\n",
    "aside.toc input{width:100%;padding:6px 8px;border:1px solid #d1d5db;",
    "border-radius:4px;font:inherit;margin-bottom:6px}\n",
    "aside.toc ul{list-style:none;margin:0;padding:0}\n",
    "aside.toc li a{display:block;padding:3px 6px;border-radius:3px;",
    "color:#1f2937;text-decoration:none;font-size:13px}\n",
    "aside.toc li a:hover{background:#eef2ff;color:#3730a3}\n",
    "main{flex:1;max-width:1100px;padding:18px 28px}\n",
    "h1.study{font-size:17px;margin:14px 0 8px;color:#0f172a;",
    "border-top:1px solid #e5e7eb;padding-top:14px}\n",
    "h1.study:first-of-type{border-top:0;padding-top:0;margin-top:0}\n",
    ".subject{background:#fff;border:1px solid #e5e7eb;border-radius:6px;margin:12px 0;",
    "box-shadow:0 1px 0 rgba(0,0,0,.02)}\n",
    ".subject>header{padding:10px 14px;border-bottom:1px solid #f1f5f9;",
    "background:#f8fafc;border-radius:6px 6px 0 0}\n",
    ".subject>header h2{margin:0;font-size:14px;color:#0f172a}\n",
    ".subject>header .meta{color:#6b7280;font-size:12px;margin-top:2px}\n",
    ".body{padding:8px 14px 14px}\n",
    "details.event{margin:6px 0;border:1px solid #eef0f4;border-radius:4px;",
    "background:#fff}\n",
    "details.event>summary{padding:6px 10px;cursor:pointer;font-weight:600;",
    "color:#0f172a;font-size:13px}\n",
    "details.event>summary:hover{background:#f1f5f9}\n",
    ".event-body{padding:4px 12px 10px}\n",
    ".form{margin:10px 0}\n",
    ".form h3{margin:6px 0 4px;font-size:13px;color:#1e3a8a;font-weight:600}\n",
    ".igroup{margin:6px 0 12px}\n",
    ".igroup h4{margin:0 0 4px;font-size:11.5px;color:#6b7280;font-weight:600;",
    "text-transform:uppercase;letter-spacing:.04em}\n",
    "table{width:100%;border-collapse:collapse;font-size:12.5px;",
    "border:1px solid #f1f5f9;border-radius:4px;overflow:hidden}\n",
    "th,td{text-align:left;padding:4px 8px;border-bottom:1px solid #f1f5f9;",
    "vertical-align:top}\n",
    "tr:last-child th,tr:last-child td{border-bottom:0}\n",
    "th{background:#f9fafb;font-weight:600;color:#374151;width:32%;",
    "font-family:ui-monospace,Menlo,Consolas,monospace}\n",
    "td.val{font-family:ui-monospace,Menlo,Consolas,monospace;color:#0f172a;",
    "white-space:pre-wrap;word-break:break-word}\n",
    "td.val.empty{color:#9ca3af}\n",
    ".chip{display:inline-block;padding:1px 7px;border-radius:10px;",
    "background:#e0f2fe;color:#075985;font-size:11px;margin-left:6px;",
    "font-weight:500}\n",
    ".chip.date{background:#ecfeff;color:#155e75}\n",
    ".chip.rep{background:#fef3c7;color:#92400e}\n",
    ".toolbar{display:flex;gap:8px;align-items:center;margin-bottom:10px}\n",
    "button{font:inherit;padding:4px 10px;border:1px solid #d1d5db;",
    "background:#fff;border-radius:4px;cursor:pointer}\n",
    "button:hover{background:#f3f4f6}\n",
    "</style></head><body><div class=\"layout\">\n")

  # ----- Sidebar (subject TOC) -----
  w("<aside class=\"toc\">\n",
    "<input id=\"filter\" placeholder=\"Filter subjects…\" ",
    "oninput=\"document.querySelectorAll('aside.toc li').forEach(li=>{",
    "li.style.display=li.textContent.toLowerCase().includes(this.value.toLowerCase())?'':'none'})\">\n")
  for (cd in studies) {
    study_oid <- attr_or(cd, "StudyOID", "?")
    subjs <- xml2::xml_find_all(cd, "./SubjectData")
    w("<h2>", esc(study_oid), " (", length(subjs), ")</h2><ul>\n")
    for (sd in subjs) {
      sk <- attr_or(sd, "SubjectKey")
      ssid <- attr_or(sd, "StudySubjectID")
      label <- if (nzchar(ssid)) paste0(sk, " · ", ssid) else sk
      w("<li><a href=\"#", esc(sk), "\">", esc(label), "</a></li>\n")
    }
    w("</ul>\n")
  }
  w("</aside>\n")

  # ----- Main column -----
  w("<main>\n",
    "<div class=\"toolbar\">",
    "<strong>", esc(title), "</strong>",
    "<button onclick=\"document.querySelectorAll('details').forEach(d=>d.open=true)\">",
    "Expand all events</button>",
    "<button onclick=\"document.querySelectorAll('details').forEach(d=>d.open=false)\">",
    "Collapse all events</button>",
    "</div>\n")

  for (cd in studies) {
    study_oid <- attr_or(cd, "StudyOID", "?")
    mdv_oid <- attr_or(cd, "MetaDataVersionOID")
    w("<h1 class=\"study\">", esc(study_oid),
      if (nzchar(mdv_oid)) paste0(" <span class='chip'>", esc(mdv_oid), "</span>") else "",
      "</h1>\n")

    for (sd in xml2::xml_find_all(cd, "./SubjectData")) {
      sk   <- attr_or(sd, "SubjectKey")
      ssid <- attr_or(sd, "StudySubjectID")
      stat <- attr_or(sd, "Status")
      w("<section class=\"subject\" id=\"", esc(sk), "\">",
        "<header><h2>", esc(sk), "</h2>",
        "<div class=\"meta\">StudySubjectID: ", esc(ssid),
        if (nzchar(stat)) paste0(" <span class='chip'>", esc(stat), "</span>") else "",
        "</div></header><div class=\"body\">\n")

      for (se in xml2::xml_find_all(sd, "./StudyEventData")) {
        ev_name <- attr_or(se, "EventName", attr_or(se, "StudyEventOID"))
        start   <- attr_or(se, "StartDate")
        rep_key <- attr_or(se, "StudyEventRepeatKey")
        ev_stat <- attr_or(se, "Status")
        w("<details class=\"event\"><summary>", esc(ev_name))
        if (nzchar(start))   w(" <span class=\"chip date\">", esc(start), "</span>")
        if (nzchar(rep_key)) w(" <span class=\"chip rep\">#", esc(rep_key), "</span>")
        if (nzchar(ev_stat)) w(" <span class=\"chip\">", esc(ev_stat), "</span>")
        w("</summary><div class=\"event-body\">\n")

        for (fd in xml2::xml_find_all(se, "./FormData")) {
          form_name <- attr_or(fd, "FormName", attr_or(fd, "FormOID"))
          w("<div class=\"form\"><h3>", esc(form_name), "</h3>\n")

          for (ig in xml2::xml_find_all(fd, "./ItemGroupData")) {
            ig_name <- attr_or(ig, "ItemGroupName", attr_or(ig, "ItemGroupOID"))
            ig_rep  <- attr_or(ig, "ItemGroupRepeatKey")
            w("<div class=\"igroup\"><h4>", esc(ig_name))
            if (nzchar(ig_rep)) w(" <span class=\"chip rep\">#", esc(ig_rep), "</span>")
            w("</h4><table><tbody>\n")

            for (it in xml2::xml_find_all(ig, "./ItemData")) {
              iname <- attr_or(it, "ItemName", attr_or(it, "ItemOID"))
              val   <- attr_or(it, "Value")
              empty <- if (!nzchar(val)) " empty" else ""
              w("<tr><th>", esc(iname), "</th><td class=\"val", empty, "\">",
                if (nzchar(val)) esc(val) else "&mdash;",
                "</td></tr>\n")
            }
            w("</tbody></table></div>\n")
          }
          w("</div>\n")
        }
        w("</div></details>\n")
      }
      w("</div></section>\n")
    }
  }

  w("</main></div></body></html>\n")
  invisible(html_path)
}

## Generate the CRF review HTML under spec/raw/ from the project root.
ut_xml_to_crf_html(
  xml_path  = "car-t-openclinica.xml",
  html_path = "spec/raw/crf_review.html"
)
