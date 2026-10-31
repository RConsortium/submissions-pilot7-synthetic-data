"""Exercise source popups over the real review dialog without validation artifacts."""

import argparse
import re
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[3]


def run(browser_path=None):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=browser_path, args=["--no-sandbox"])
            page = browser.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.route("**/rendered.html*", lambda route: route.fulfill(content_type="text/html", body="<h1>Rendered XML</h1>"))
            page.goto(f"http://127.0.0.1:{server.server_port}/docs/assets/dashboard/")
            page.evaluate("""async () => {
              document.head.innerHTML = `<link rel="stylesheet" href="/docs/stylesheets/dashboard.css"><style>
                :root { --md-default-fg-color:#24292f; --md-default-bg-color:#fff;
                  --md-default-fg-color--lightest:#e7ebef; --md-typeset-a-color:#326c9e;
                  --md-accent-fg-color--transparent:#eaf2f8; --md-code-font-family:monospace;
                  --md-text-font-family:Arial,sans-serif; font-family:Arial,sans-serif; }
              </style>`;
              document.body.innerHTML = '<div id="study-dashboard" class="study-dashboard"><button id="open">Start review</button></div>';
              const { createTraceReview } = await import('/docs/assets/dashboard/trace-review.js');
              const { createReviewSources, reviewComparisonEvidence } = await import('/docs/assets/dashboard/review-sources.js');
              const rule = {id:'rule', type:'specification', path:'spec/template.yaml', section:'AGE',
                quote:'old rule', context:'original', lines:[100,101], verified:true};
              const doc = {id:'doc', type:'document', path:'study/spec/define/define-adam.xml', section:'ADSL.AGE',
                quote:'Age rule', context:'Age rule', lines:[3588,3595], verified:true};
              const issue = {id:'age', dataset:'ADSL', variable:'AGE', kind:'conflict', title:'Age rule differs',
                summary:'Review age', expected:'Age follows the documented rule.', observed:'Age differs in generated data.', action:'Confirm rule', review:'agreed', check_ids:[],
                impact:{status:'observed',subjects:['01'],subject_count:1},
                trace:[{evidence_id:'rule',role:'context'},{evidence_id:'doc',role:'context'},{evidence_id:'comparison',role:'impact'}]};
              const comparison = {id:'comparison',type:'comparison',method:'derive',reading:'literal',target:'reference',differ:1,compared:2,subjects:['01']};
              const report = {review:{schema_version:1, issues:[issue], checks:[], evidence:[rule,doc,comparison]},
                documents:[{path:doc.path,name:'define-adam.xml',available:true,view:'rendered.html'}]};
              report.trace_examples = {'ADSL.AGE': {
                subject_key:'USUBJID', keys:['USUBJID','SEQ'], input_columns:['INPUT'],
                calculations:[{column:'AGE',reading:'literal'},{column:'OTHER',reading:'alternative'}],
                subjects:[{id:'01',total_rows:1,rows:[{
                  keys:{USUBJID:'01',SEQ:1},inputs:{INPUT:65},
                  reference:{present:true,value:64},
                  calculations:{AGE:{present:true,value:65},OTHER:{present:true,value:999}},
                }]}],
              }};
              const specifications = {ADSL:{domain:'ADSL',path:'study/adsl.yaml',documents:[{path:rule.path}],
                resolved:{path:'study/resolved/adsl.yaml',text:'domain: ADSL\\n- name: AGE\\n  derivation: age < 65',
                  lineage:{spans:{AGE:{start:2,end:3}}}}}};
              const ctx = {root:()=>document.querySelector('#study-dashboard'), report, specifications,
                model:{id:'study',title:'Study',revision:'test-revision',datasets:[{name:'ADSL',comparison:'passed'}]},index:{comments:{repo:'org/repo',discussion_url:'https://github.com/org/repo/discussions',review_url:'https://github.com/org/repo/discussions/new'}},
                resource:()=> '/rendered.html', sourceUrl:()=> 'https://github.com/org/repo'};
              const sources = createReviewSources(ctx);
              window.reviewContext = ctx;
              window.review = createTraceReview(ctx, sources);
              document.addEventListener('click', event => {
                const target = event.target.closest('[data-source-evidence]');
                if (!target) return;
                const evidence = reviewComparisonEvidence(issue, report, specifications);
                sources.open(evidence.find(e=>e.id===target.dataset.sourceEvidence), target);
              });
              window.review.open('age',document.querySelector('#open'));
            }""")
            sections = page.locator('.trace-review-content > section').evaluate_all('(items)=>items.map(s=>s.id)')
            assert sections == ['trace-finding', 'trace-sources', 'trace-examples']
            expect(page.locator('#trace-sources .trace-source-file')).to_have_count(2)
            expect(page.locator('.trace-data-table thead th')).to_have_text(['ADaM data', 'Documented Rule'])
            expect(page.locator('.trace-data-table tbody td')).to_have_count(2)
            expect(page.locator('.trace-cell-difference')).to_have_count(2)
            expect(page.locator('.trace-data-table')).not_to_contain_text('999')
            expect(page.locator('#trace-your-review h3')).to_have_text('Human Review')
            expect(page.locator('#trace-your-review legend')).to_have_text([
                'Do you agree with this finding? Required', 'Is this finding critical? Required',
                'Is current dataset correctly derived? Optional'])
            expect(page.locator('#trace-fix, #trace-specifications')).to_have_count(0)
            expect(page.locator('.trace-review-content')).not_to_contain_text('Agreement and criticality are separate decisions')
            assert page.locator('.issue-comparison').count() == 1
            assert 'Expected behavior' in page.locator('#trace-finding').inner_text()
            assert 'published reference' not in page.locator('.trace-review-content').inner_text()
            page.get_by_role('button', name='Subject examples', exact=True).click()
            page.wait_for_function("document.querySelector('.trace-scroll').scrollTop > 0")
            expect(page.locator('#trace-discussion, .trace-technical')).to_have_count(0)
            expect(page.locator('[data-trace-section="trace-discussion"]')).to_have_count(0)
            page.locator('#trace-review-comment').fill('Keep my review draft')
            expect(page.locator('.trace-introduction, .trace-basis, .trace-measurements, #trace-data, #trace-assessment')).to_have_count(0)
            assert page.locator('.trace-review-dialog [data-finding]').count() == 0
            rule = page.locator('#trace-sources [data-source-evidence="resolved:ADSL.AGE"]')
            rule.click()
            assert page.locator('.review-source-dialog').is_visible()
            assert 'study/resolved/adsl.yaml' in page.locator('#review-source-title').inner_text()
            assert 'domain: ADSL' in page.locator('.review-source-content').inner_text()
            assert 'age < 65' in page.locator('.review-source-content mark').last.inner_text()
            assert page.locator('.trace-review-dialog').evaluate('(d)=>d.open')
            page.keyboard.press('Escape')
            assert page.locator('.review-source-dialog').count() == 0
            assert page.locator('.trace-review-dialog').is_visible()
            assert rule.evaluate('(b)=>b===document.activeElement')
            assert page.locator('#trace-review-comment').input_value() == 'Keep my review draft'
            trigger = page.locator('#trace-sources [data-source-evidence="doc"]').last
            trigger.click()
            assert page.locator('.review-source-dialog iframe').get_attribute('src').endswith('/rendered.html#ADSL.AGE')
            assert page.frame_locator('.review-source-dialog iframe').locator('h1').inner_text() == 'Rendered XML'
            page.set_viewport_size({'width': 390, 'height': 844})
            page.locator('body').evaluate("(b)=>b.dataset.mdColorScheme='slate'")
            bounds = page.locator('.review-source-dialog').bounding_box()
            assert bounds['x'] >= 0 and bounds['x'] + bounds['width'] <= 390
            page.set_viewport_size({'width': 1280, 'height': 720})
            offset = page.locator('.trace-scroll').evaluate('(s)=>s.scrollTop')
            page.get_by_role('button', name='Close source', exact=True).click()
            assert page.locator('.trace-scroll').evaluate('(s)=>s.scrollTop') == offset
            assert trigger.evaluate('(b)=>b===document.activeElement')
            assert page.locator('#trace-review-comment').input_value() == 'Keep my review draft'
            assert len(browser.contexts[0].pages) == 1
            assert page.url.endswith('/docs/assets/dashboard/')
            # The review has a single sharing action and keeps selectable prepared text.
            expect(page.get_by_role('button', name='Copy review instead', exact=True)).to_have_count(0)
            expect(page.locator('.trace-review-actions button')).to_have_count(1)
            page.get_by_role('radio', name='Agree', exact=True).check()
            page.get_by_role('radio', name='Not critical', exact=True).check()
            page.evaluate("window.open=url=>{window.openedReview=url;return {}}")
            page.get_by_role('button', name='Submit review on GitHub', exact=True).click()
            assert 'body=' in page.evaluate('window.openedReview')
            prepared = page.locator('#trace-your-review #trace-github-comment')
            expect(prepared).to_have_value(re.compile('Keep my review draft'))
            # With no GitHub composer configured, the primary action still copies the review.
            page.evaluate("delete window.reviewContext.index.comments.review_url; window.review.open('age')")
            page.evaluate("Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async()=>{throw Error('Blocked')}}})")
            page.get_by_role('button', name='Copy review', exact=True).click()
            expect(page.locator('.trace-review-feedback')).to_contain_text('Clipboard access is unavailable')
            expect(prepared).to_be_focused()
            page.evaluate('window.review.close()')
            assert page.locator('dialog').count() == 0
            page.evaluate("window.review.open('age')")
            page.locator('body').evaluate("(b)=>b.dataset.mdColorScheme='default'")
            page.set_viewport_size({'width': 1440, 'height': 1000})
            page.screenshot(path=str(ROOT / '.build/review-desktop.png'))
            page.set_viewport_size({'width': 390, 'height': 844})
            page.screenshot(path=str(ROOT / '.build/review-mobile.png'))
            assert page.locator('.trace-review-dialog').evaluate('(d)=>d.scrollWidth<=d.clientWidth')
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    print('Source popup browser checks passed.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser-path')
    run(parser.parse_args().browser_path)
