"""Export an offline review using the production synthetic dashboard components."""

import base64
import json
from pathlib import Path
import shutil
import subprocess

from study_dashboard.synthetic import build_synthetic

ROOT = Path(__file__).resolve().parents[2]


def module_url(source):
    return 'data:text/javascript;base64,' + base64.b64encode(source.encode()).decode()


def export(root=ROOT):
    destination = root / '.build/synthetic-review'
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    records = build_synthetic(root, destination / 'review-assets', revision)
    models = [json.loads((destination / 'review-assets' / row['url']).read_text()) for row in records]
    assets = root / 'docs/assets/dashboard'
    ui = module_url((assets / 'ui.js').read_text())
    source = (assets / 'synthetic-development.js').read_text().replace('"./ui.js"', json.dumps(ui))
    development = module_url(source)
    css = (root / 'docs/stylesheets/dashboard.css').read_text()
    payload = json.dumps(models, ensure_ascii=True).replace('<', '\\u003c')
    html = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>KN189 / KN564 analysis review</title><style>
:root{--md-default-bg-color:#fff;--md-default-fg-color:#182c40;--md-default-fg-color--lightest:#ccd5df;--md-typeset-a-color:#245b83;--md-accent-fg-color--transparent:#edf3f7}
body{font:15px/1.55 system-ui,sans-serif;margin:0 auto;padding:1.5rem;max-width:1280px;background:#fff;color:#182c40}
a{color:#245b83}h1{font-size:1.7rem}h2{margin-top:2rem}table{border-collapse:collapse;width:100%}th,td{padding:.55rem;text-align:left;border-bottom:1px solid #ccd5df}th{background:#f2f5f8}
header{border-bottom:2px solid #245b83;padding-bottom:1rem}header select{font:inherit;padding:.4rem}.report-table{overflow:auto}pre{background:#f4f6f8;padding:1rem}button,select,textarea,input{font:inherit}textarea{width:100%;box-sizing:border-box}
''' + css + '''</style><header><h1>KN189 / KN564 analysis review</h1>
<p>Development outputs from synthetic data. Review open findings before primary analysis use.</p>
<label for="study">Study </label><select id="study"><option value="kn189">KN189 - 616 subjects</option><option value="kn564">KN564 - 994 subjects</option></select>
<p>Search findings, inspect protocol/SAP quotations, enter decision drafts and export notes. This HTML opens offline; retain the adjacent review-assets folder for source and download links.</p></header>
<main id="review" class="study-report synthetic-report md-typeset"></main>
<script type="module">
import {developmentReport,mountDevelopment} from ''' + json.dumps(development) + ''';
const models=''' + payload + ''';
const main=document.getElementById("review"), control=document.getElementById("study");
const dataRoot=new URL("./review-assets/",location.href);
function show(){const model=models.find(m=>m.id===control.value);main.innerHTML='<h2>'+model.title+' study review</h2>'+developmentReport(model,dataRoot);mountDevelopment(main,model);}
control.onchange=()=>{history.replaceState(null,"",location.pathname+location.search);show();};
show();
</script></html>'''
    (destination / 'review.html').write_text(html)
    (destination / 'README.txt').write_text(
        'Open review.html in a browser. Keep review-assets beside it for source and download links.\n'
        'No server or external scripts are required. Review drafts are local to the browser until exported.\n'
        'The study ZIPs include XPT/Parquet, both Define-XML files, yamaa specifications, source and build evidence.\n'
        'A successful development build is not approval for confirmatory analysis or regulatory submission.\n')
    archive = shutil.make_archive(str(root / '.build/kn189-kn564-review'), 'zip', destination)
    print(destination / 'review.html')
    print(archive)
    return destination


if __name__ == '__main__':
    export()
