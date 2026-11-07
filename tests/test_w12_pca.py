"""Reproduce: pip install numpy playwright; python -m playwright install chromium
python tests/test_w12_pca.py
Offline file:// browser tests (HTTP(S) blocked), plus independent NumPy SVD.
Optional: W12_SCREENSHOTS=<directory>. No server, network or canned PCA output.
"""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import numpy as np
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'labs/w12_pca'
checks = 0

def check(ok, message):
    global checks
    assert ok, message
    checks += 1

rows = list(csv.DictReader((ROOT/'data/nb10_demo_spectra.csv').open()))
cols = sorted([k for k in rows[0] if k[0].isdigit()], key=float)
X = np.array([[float(r[k]) for k in cols] for r in rows])
axis = np.array(list(map(float, cols)))
script = """
const M=require('./labs/w12_pca/pca_math.js'),D=require('./labs/w12_pca/pca_data.js');
let results=[];
for(const mode of ['center','autoscale'])for(const exclude of [false,true]){
 const X=D.X.filter((_,i)=>!exclude||i!==17),m=M.fit(X,mode,D.axis);
 results.push({mode,exclude,m,recon:Array.from({length:m.rank+1},(_,k)=>M.reconstruct(m,k)),projection:M.project(m,D.X)});
}
console.log(JSON.stringify({D,results,constant:M.fit([[1,1],[1,1]],'autoscale')}));
"""
actual = json.loads(subprocess.check_output(['node', '-e', script], cwd=ROOT))
check(actual['D']['csv'] == (ROOT/'data/nb10_demo_spectra.csv').read_text(), 'embedded CSV exact bytes as text')
check(np.array_equal(X, actual['D']['X']), 'all 1080 embedded intensities exact')
check(actual['D']['meta'] == [{k:v for k,v in r.items() if k not in cols} for r in rows], 'all metadata exact')
check(actual['constant']['rank'] == 0, 'constant matrix: rank zero, no invalid eigenvalues')
for result in actual['results']:
    xx = X[:-1] if result['exclude'] else X
    mean = xx.mean(axis=0)
    scale = xx.std(axis=0, ddof=1) if result['mode'] == 'autoscale' else np.ones(60)
    z = (xx-mean)/scale
    u, s, vt = np.linalg.svd(z, full_matrices=False)
    rank = np.sum(s*s > s[0]*s[0]*1e-11)
    m = result['m']
    check(m['rank'] == rank, 'numerical rank')
    check(np.allclose(m['mean'], mean, atol=1e-14), 'refit mean')
    check(np.allclose(m['scale'], scale, atol=1e-14), 'sample scale ddof=1')
    if result['mode'] == 'autoscale':
        check(np.allclose(z.std(axis=0, ddof=1), 1, atol=1e-12), 'unit sample variance')
        check(abs(sum(m['eigenvalues'])-60) < 1e-10, 'autoscale total variance = 60 with ddof=1')
    eigerr = np.max(np.abs(np.array(m['eigenvalues'])-s[:rank]**2/(len(xx)-1)))
    check(eigerr < 1e-10, f'eigenvalue error {eigerr}')
    ll = np.array(m['loadings'])
    # Canonicalize NumPy signs independently, using the documented rule.
    for a in range(rank):
        anchor = np.argmin(np.abs(axis-(1655 if a == 0 else 1520))) if a < 2 else np.argmax(abs(vt[a]))
        if vt[a, anchor] < 0:
            vt[a] *= -1
    loadingerr = np.max(abs(ll-vt[:rank]))
    check(loadingerr < 1e-9, f'loading orientation {loadingerr}')
    check(np.allclose(ll@ll.T, np.eye(rank), atol=1e-10), 'orthonormal loadings')
    check(np.allclose(np.array(m['scores']), z@vt[:rank].T, atol=1e-9), 'scores = Z V; sign orientation')
    for k in [1,2,3,rank]:
        check(np.allclose(ll[:k].T@ll[:k], vt[:k].T@vt[:k], atol=1e-9), f'subspace k={k}')
    check(np.allclose(result['projection'], ((X-mean)/scale)@vt[:rank].T, atol=1e-9), 'excluded projection uses refit mean / scale')
    errs=[]
    for k, rec in enumerate(result['recon']):
        expected=((z@vt[:k].T)@vt[:k])*scale+mean
        check(np.allclose(rec,expected,atol=1e-9),f'reconstruction k={k}')
        errs.append(float(np.sqrt(np.mean((xx-rec)**2))))
    check(all(a >= b-1e-12 for a,b in zip(errs,errs[1:])), 'monotonic reconstruction RMSE')
    check(errs[-1]<1e-10, 'full rank reconstructs original')
    print(f"NumPy SVD {result['mode']} n={len(xx)}: rank={rank}, max eigenvalue error={eigerr:.3e}, loading error={loadingerr:.3e}, full-rank RMSE={errs[-1]:.3e}; PASS")
    print('  PC1/PC2/PC3 explained %:', ', '.join(f'{v*100:.6f}' for v in m['explained'][:3]))

screens = Path(os.environ.get('W12_SCREENSHOTS',str(Path.home()/'.hermes/cache/scratch/w12-verification')))
screens.mkdir(parents=True,exist_ok=True)
with sync_playwright() as pw:
    browser=pw.chromium.launch()
    for lang in ['zh','en']:
        for mobile in [False,True]:
            context=browser.new_context(viewport={'width':390 if mobile else 1440,'height':844 if mobile else 1000},accept_downloads=True,is_mobile=mobile,has_touch=mobile)
            network=[]
            def abort(route):
                network.append(route.request.url)
                route.abort()
            context.route('http://**/*',abort)
            context.route('https://**/*',abort)
            page=context.new_page();errors=[]
            page.on('pageerror',lambda err:errors.append(str(err)))
            page.goto((LAB/('pca_lab.en.html' if lang=='en' else 'pca_lab.html')).as_uri())
            page.wait_for_selector('#scores circle')
            check(page.locator('main section[id^=act]').count()==6,'six acts')
            check(page.locator('#matrix tbody tr').count()==18,'matrix rows')
            check(page.locator('#matrix thead th').count()==61,'matrix spectral columns + ID')
            for i in range(6):
                page.locator(f'[name=q{i}][value=other]').check()
                check(('Reconsider' if lang=='en' else '再想想') in page.locator(f'#feedback{i}').inner_text(),'wrong feedback')
                page.locator(f'[name=q{i}][value=correct]').check()
                check(('Correct' if lang=='en' else '正確') in page.locator(f'#feedback{i}').inner_text(),'correct feedback')
                page.locator(f'#note{i}').fill(f'Act {i+1}: observed evidence, not authenticity proof.')
                check(page.evaluate('document.documentElement.scrollWidth<=innerWidth'),'no horizontal overflow')
            check(page.locator('#progress').get_attribute('value')=='6','six answers saved')
            page.locator('#exclude').click()
            check(page.evaluate('pcaLab.model.n')==18,'no unexplained deletion')
            check(bool(page.locator('#exclusionStatus').inner_text()),'required reason feedback')
            # Every option and both slider extremes; all plots and model values finite.
            for id in ['sample','variable','px','py','mode']:
                values=page.locator(f'#{id} option').evaluate_all('(opts)=>opts.map(o=>o.value)')
                for value in values:
                    page.locator(f'#{id}').select_option(value)
                    check(page.evaluate('pcaLab.model.scores.flat().every(Number.isFinite) && [...document.querySelectorAll("svg path")].every(p=>!/NaN|Infinity/.test(p.getAttribute("d")))'),f'finite {id}={value}')
            for id in ['angle','k']:
                for attr in ['min','max']:
                    page.locator(f'#{id}').evaluate('(el,attr)=>{el.value=el.getAttribute(attr);el.dispatchEvent(new Event("input",{bubbles:true}));}',attr)
                    check(page.evaluate('pcaLab.model.eigenvalues.every(Number.isFinite)'),'slider extremes finite')
            page.locator('#bestAngle').click()
            check(page.evaluate('Math.abs(pcaLab.state.angle-pcaOptimalAngle)<1e-10'),'optimal-angle button')
            page.locator('#mode').select_option('center')
            page.locator('#px').select_option('0');page.locator('#py').select_option('1')
            page.locator('#labels').uncheck()
            before=page.evaluate('pcaLab.model.eigenvalues')
            page.locator('#labels').check()
            check(before==page.evaluate('pcaLab.model.eigenvalues'),'labels never used in fit')
            page.locator('#scores [data-sample="0"]').click()
            check(page.locator('#sample').input_value()=='0','click selectable score')
            page.locator('#scores [data-sample="1"]').focus()
            page.keyboard.press('Enter')
            check(page.locator('#sample').input_value()=='1','keyboard selectable score')
            page.locator('#sample').select_option('17')
            page.locator('#reason').fill('Sensitivity analysis: PEA_r3 differs from two replicates; request remeasurement and inspect raw records, no confirmed fault.')
            page.locator('#exclude').click()
            check(page.evaluate('pcaLab.model.n')==17,'excluded refit')
            check(page.evaluate('pcaLab.full.n')==18,'full comparison retained')
            check(page.evaluate('pcaLab.indices.includes(17)') is False,'PEA_r3 not fitted')
            check(page.locator('#refitScores circle').count()==17,'refit score points')
            check('17' in page.locator('#comparison').inner_text(),'full/excluded quantitative comparison')
            # Reason removal invalidates exclusion immediately.
            page.locator('#reason').fill('')
            check(page.evaluate('pcaLab.model.n')==18,'blanked reason restores full model')
            page.locator('#reason').fill('Documented sensitivity analysis; simulated anomaly, not a proven instrument fault.')
            page.locator('#exclude').click()
            page.locator('#k').evaluate('(el)=>{el.value=2;el.dispatchEvent(new Event("input",{bubbles:true}));}')
            page.reload();page.wait_for_selector('#scores circle')
            check(page.locator('#progress').get_attribute('value')=='6','progress persists')
            check(page.evaluate('pcaLab.model.n')==17,'exclusion with reason persists')
            check('Act 6' in page.locator('#note5').input_value(),'notes persist')
            for id in ['scoresDownload','loadingsDownload','recordDownload','sourceDownload']:
                with page.expect_download() as event:
                    page.locator('#'+id).click()
                content=Path(event.value.path()).read_text()
                if id=='recordDownload':
                    record=json.loads(content)
                    check(record['simulated'] and not record['labelsUsedInFit'],'record provenance')
                    check(record['autoscaleSD'].startswith('sample ddof=1'), 'record sample SD convention')
                    check(len(record['trainingIDs'])==17 and record['excluded']['n']==17 and record['full']['n']==18,'record both models')
                    check(record['state']['reason'] and len(record['state']['answers'])==6,'record reasons and predictions')
                    check(np.allclose(record['excluded']['eigenvalues'],actual['results'][1]['m']['eigenvalues'],atol=1e-10),'record actual numerical model')
                elif id=='sourceDownload':
                    check(content==(ROOT/'data/nb10_demo_spectra.csv').read_text(),'original CSV exact download')
                else:
                    data=list(csv.reader(io.StringIO(content)))
                    check(len(data)==(19 if id=='scoresDownload' else 61),'CSV complete row count')
                    if id=='scoresDownload':
                        check(data[-1][4]=='projection_only','excluded score exported as projection')
                        check(np.allclose(list(map(float,data[-1][5:])),actual['results'][1]['projection'][-1],atol=1e-9),'scores download actual values')
                    else:
                        check(np.allclose(np.array([list(map(float,r[3:])) for r in data[1:]]).T,actual['results'][1]['m']['loadings'],atol=1e-9),'loadings download actual values')
            page.screenshot(path=str(screens/f'w12-{lang}-{"mobile" if mobile else "desktop"}.png'),full_page=True)
            for id in ['scores','loadings','reconstruction','pea','fullScores','refitScores']:
                check(bool(page.locator(f'#{id} > title').text_content()),'SVG accessible title')
            page.locator('#restore').click()
            check(page.evaluate('pcaLab.model.n')==18,'restore full model')
            page.locator('#reset').click();page.wait_for_selector('#scores circle')
            check(page.locator('#progress').get_attribute('value')=='0','reset progress')
            check(page.locator('#note0').input_value()=='' and page.locator('#reason').input_value()=='','reset notes and reason')
            check(page.evaluate('pcaLab.state.mode==="center" && pcaLab.model.n===18 && pcaLab.state.k===2'),'reset model defaults')
            check(not errors,f'browser errors {errors}')
            check(not network,f'network attempts {network}')
            print(f'{lang} {"mobile 390x844" if mobile else "desktop 1440x1000"}: six acts, all options/extremes, predictions, notes, persistence, labels, point selection, reason guard/refit/restore, four actual downloads, reset; 0 JS errors; 0 HTTP(S) requests; PASS')
            context.close()
    browser.close()
print(f'Screenshots: {screens}')
print(f'PASS: {checks} assertions')
