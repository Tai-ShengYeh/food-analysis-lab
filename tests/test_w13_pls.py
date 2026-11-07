"""Reproduce W13 against sklearn/SciPy and exercise offline bilingual UI.
Run: LD_LIBRARY_PATH=.../w11-browser-libs/root/usr/lib/x86_64-linux-gnu \
  .../w11-test-venv/bin/python tests/test_w13_pls.py
Requires node, numpy, scipy, scikit-learn, playwright + Chromium. No server needed.
"""
import csv
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import numpy as np
from numpy.testing import assert_allclose
from scipy.signal import savgol_filter
from scipy.spatial.distance import cdist
from sklearn.cross_decomposition import PLSRegression
from sklearn.model_selection import LeaveOneGroupOut

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'labs/w13_pls_acetic'


def node(code):
    return json.loads(subprocess.check_output(['node', '-e', code], cwd=ROOT, text=True))


PREAMBLE = "const M=require('./labs/w13_pls_acetic/pls_math.js'),D=require('./labs/w13_pls_acetic/pls_data.js');"


class NumericalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = node(PREAMBLE + 'console.log(JSON.stringify(D))')
        cls.X = np.array(cls.data['X'])
        cls.y = np.array([m['acidity_pct'] for m in cls.data['meta']])
        cls.groups = np.array([m['sample_id'] for m in cls.data['meta']])
        cls.results = node(PREAMBLE + """
const s=M.split(D),y=s.cal.map(i=>D.meta[i].acidity_pct),g=s.cal.map(i=>D.meta[i].sample_id),out=[];
for(let prep of ['raw','SNV','SG'])for(let scale of [true,false])for(let lv=1;lv<=6;lv++){
let X=M.prep(s.cal.map(i=>D.X[i]),prep),Xt=M.prep(s.test.map(i=>D.X[i]),prep),model=M.fit(X,y,lv,scale),cv=M.cv(X,y,g,lv,scale),row=M.cv(X,y,g,lv,scale,true),pred=M.predict(model,Xt);
out.push({prep,scale,lv,X,model,pred,calPred:M.predict(model,X),cv,row,metrics:M.metrics(s.test.map(i=>D.meta[i].acidity_pct),pred),foldModels:cv.folds.map(f=>M.fit(f.train.map(i=>X[i]),f.train.map(i=>y[i]),lv,scale))});}
console.log(JSON.stringify({split:s,out}));
""")

    def test_exact_source_and_notebook_csv(self):
        text = (ROOT / 'data/nb11_demo_spectra.csv').read_text()
        self.assertEqual(self.data['csv'], text)
        rows = list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(len(rows), 48)
        self.assertEqual(self.X.shape, (48, 60))
        notebook = json.loads((ROOT / 'notebooks/NB11_pls_acetic.ipynb').read_text())
        code = next(''.join(c['source']) for c in notebook['cells'] if 'SAMPLE_CSV = """' in ''.join(c['source']))
        namespace = {}
        exec(code, namespace)
        self.assertEqual(namespace['SAMPLE_CSV'], text)
        for i, row in enumerate(rows):
            assert_allclose(self.X[i], [float(row[k]) for k in sorted([k for k in row if k[0].isdigit()], key=float)], rtol=0, atol=0)

    def test_ks_and_orange_split(self):
        ids = list(dict.fromkeys(self.groups))
        pool = [g for g in ids if g != 'VINEGAR_WHITE_W4REF']
        means = np.array([self.X[self.groups == g].mean(axis=0) for g in pool])
        d = cdist(means, means)
        selected = list(np.unravel_index(d.argmax(), d.shape))
        while len(selected) < 12:
            remain = [i for i in range(len(pool)) if i not in selected]
            selected.append(remain[np.argmax(d[np.ix_(remain, selected)].min(axis=1))])
        self.assertEqual([pool[i] for i in selected], self.results['split']['calIDs'])
        self.assertEqual(len(self.results['split']['cal']), 36)
        self.assertEqual(len(self.results['split']['test']), 12)
        orange = list(csv.DictReader(io.StringIO((ROOT / 'orange/or13_acetic.csv').read_text())))
        for row in orange:
            self.assertEqual(row['mD#split'], 'calibration' if row['mD#sample_id'] in self.results['split']['calIDs'] else 'test')
        self.assertNotIn('VINEGAR_WHITE_W4REF', self.results['split']['calIDs'])

    def test_all_36_full_models_and_grouped_folds(self):
        cal = self.results['split']['cal']
        test = self.results['split']['test']
        y, groups = self.y[cal], self.groups[cal]
        for r in self.results['out']:
            with self.subTest(prep=r['prep'], scale=r['scale'], lv=r['lv']):
                def prep(X):
                    if r['prep'] == 'SNV':
                        return (X-X.mean(axis=1, keepdims=True))/X.std(axis=1, keepdims=True)
                    if r['prep'] == 'SG':
                        return savgol_filter(X, 9, 2, deriv=1, delta=1, axis=1, mode='interp')
                    return X.copy()
                X, Xt = prep(self.X[cal]), prep(self.X[test])
                assert_allclose(r['X'], X, atol=3e-14, rtol=1e-10)
                m = PLSRegression(n_components=r['lv'], scale=r['scale']).fit(X, y)
                assert_allclose(r['model']['coef'], m.coef_.ravel(), atol=3e-8, rtol=2e-8)
                assert_allclose(r['model']['xmean'], m._x_mean, atol=1e-13)
                assert_allclose(r['model']['xscale'], m._x_std, atol=1e-13)
                assert_allclose(r['pred'], m.predict(Xt).ravel(), atol=2e-9, rtol=1e-9)
                assert_allclose(r['calPred'], m.predict(X).ravel(), atol=2e-9, rtol=1e-9)
                cp = np.zeros(len(y))
                for f, (tr, va) in enumerate(LeaveOneGroupOut().split(X, y, groups)):
                    fm = PLSRegression(n_components=r['lv'], scale=r['scale']).fit(X[tr], y[tr])
                    cp[va] = fm.predict(X[va]).ravel()
                    self.assertEqual(r['cv']['folds'][f]['overlap'], [])
                    assert_allclose(r['foldModels'][f]['coef'], fm.coef_.ravel(), atol=4e-8, rtol=3e-8)
                    assert_allclose(r['foldModels'][f]['xmean'], X[tr].mean(axis=0), atol=1e-13)
                assert_allclose(r['cv']['pred'], cp, atol=2e-9, rtol=1e-9)
                self.assertAlmostEqual(r['cv']['metrics']['rmse'], np.sqrt(np.mean((cp-y)**2)), places=9)
                rp = np.zeros(len(y))
                for k in range(5):
                    va = np.arange(len(y))[np.arange(len(y)) % 5 == k]
                    tr = np.arange(len(y))[np.arange(len(y)) % 5 != k]
                    rp[va] = PLSRegression(n_components=r['lv'], scale=r['scale']).fit(X[tr], y[tr]).predict(X[va]).ravel()
                    self.assertGreater(len(r['row']['folds'][k]['overlap']), 0)
                assert_allclose(r['row']['pred'], rp, atol=2e-9, rtol=1e-9)
                pred = np.array(r['pred'])
                residual = pred-self.y[test]
                expected = {'rmse': np.sqrt(np.mean(residual**2)), 'bias': residual.mean(), 'r2': 1-np.sum(residual**2)/np.sum((self.y[test]-self.y[test].mean())**2), 'rpd': np.std(self.y[test], ddof=1)/np.sqrt(np.mean(residual**2))}
                for key, value in expected.items():
                    self.assertAlmostEqual(r['metrics'][key], value, places=10)

    def test_course_baseline(self):
        raw = [r for r in self.results['out'] if r['prep'] == 'raw' and r['scale']]
        snv = [r for r in self.results['out'] if r['prep'] == 'SNV' and r['scale']]
        self.assertEqual(min(raw, key=lambda r:r['cv']['metrics']['rmse'])['lv'], 3)
        self.assertEqual(min(snv, key=lambda r:r['cv']['metrics']['rmse'])['lv'], 2)
        r = snv[1]
        self.assertAlmostEqual(raw[2]['cv']['metrics']['rmse'], .458, delta=.0005)
        self.assertAlmostEqual(r['cv']['metrics']['rmse'], .400, delta=.0005)
        for k, v in [('rmse',.427),('r2',.929),('bias',-.054),('rpd',3.91)]:
            self.assertAlmostEqual(r['metrics'][k], v, delta=.005 if k=='rpd' else .0005)
        self.assertAlmostEqual(np.sqrt(np.mean((np.array(r['calPred'])-self.y[self.results['split']['cal']])**2)), .269, delta=.0005)

    def test_edge_conventions(self):
        r = node(PREAMBLE + "console.log(JSON.stringify({flat:M.prep([[2,2,2]],'SNV'),zero:M.metrics([2,2],[2,2]),shift:M.prep([D.X[0],D.X[0].map(v=>v*3+7)],'SNV')}))")
        assert_allclose(r['flat'], [[0,0,0]])
        assert_allclose(r['shift'][0], r['shift'][1], atol=1e-13)
        self.assertIsNone(r['zero']['r2'])
        self.assertIsNone(r['zero']['rpd'])


class BrowserTests(unittest.TestCase):
    def test_bilingual_desktop_mobile_offline(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
            for language in ['zh', 'en']:
                for width, height in [(1365,900),(390,844)]:
                    with self.subTest(language=language,width=width):
                        context = browser.new_context(viewport={'width':width,'height':height}, accept_downloads=True)
                        errors, net = [], []
                        context.route('http://**/*', lambda route:(net.append(route.request.url),route.abort()))
                        context.route('https://**/*', lambda route:(net.append(route.request.url),route.abort()))
                        page = context.new_page()
                        page.on('pageerror', lambda e:errors.append(str(e)))
                        page.on('console', lambda m:errors.append(m.text) if m.type=='error' else None)
                        page.goto((LAB / ('pls_lab.en.html' if language=='en' else 'pls_lab.html')).as_uri())
                        page.wait_for_function('window.plsLab && window.plsLab.curves')
                        self.assertEqual(page.locator('section').count(),6)
                        self.assertFalse(page.evaluate('document.documentElement.scrollWidth>innerWidth'))
                        self.assertEqual(page.locator('#testResults').inner_text(),'')
                        self.assertTrue(page.locator('#predDownload').is_disabled())
                        page.locator('#lock').click()
                        self.assertFalse(page.evaluate('plsLab.exposure.seen'))
                        for prep in ['raw','SNV','SG']:
                            page.select_option('#prep',prep)
                            for scale in ['false','true']:
                                page.select_option('#scale',scale)
                                for lv in range(1,7):
                                    page.select_option('#lv',str(lv))
                                    self.assertTrue(page.evaluate('Number.isFinite(plsLab.curves[plsLab.state.prep][plsLab.state.lv-1].rmsecv)'))
                        page.select_option('#sample','35')
                        page.select_option('#sample','0')
                        for id, vals in [('bias',['-1','1','0']),('noise',['0.5','0']),('dilution',['0','10','2']),('aliquot',['0.1','1000','5']),('final',['0.1','1000','25'])]:
                            for val in vals:
                                page.locator('#'+id).fill(val)
                                page.locator('#'+id).dispatch_event('change')
                        page.locator('#choose').click()
                        self.assertEqual(page.evaluate('[plsLab.state.prep,plsLab.state.lv]'),['SNV',2])
                        page.locator('#leakage').click()
                        self.assertEqual(page.locator('#folds tbody tr').count(),5)
                        self.assertTrue(page.evaluate('plsLab.rowResult.folds.every(f=>f.overlap.length>0)'))
                        for i in range(6):
                            page.locator(f'[name=q{i}][value=other]').check()
                            self.assertTrue(page.locator(f'#feedback{i}').inner_text())
                            page.locator(f'[name=q{i}][value=correct]').check()
                            page.locator(f'#note{i}').fill('Evidence '+str(i))
                        self.assertEqual(page.locator('#progress').get_attribute('value'),'6')
                        page.reload()
                        page.wait_for_function('window.plsLab')
                        self.assertEqual(page.locator('#note5').input_value(),'Evidence 5')
                        page.locator('#reason').fill('Grouped CV minimum; simulated aqueous vinegar only')
                        page.locator('#lock').click()
                        self.assertTrue(page.evaluate('plsLab.test.independent'))
                        self.assertAlmostEqual(page.evaluate('plsLab.test.metrics.rmse'),.4271707200378438,places=9)
                        self.assertEqual(page.locator('#testResults tbody tr').count(),12)
                        for id in ['predDownload','cvDownload','reportDownload','sourceDownload']:
                            with page.expect_download() as dl:
                                page.locator('#'+id).click()
                            text=Path(dl.value.path()).read_text()
                            if id=='predDownload':
                                rows=list(csv.DictReader(io.StringIO(text)))
                                self.assertEqual(len(rows),12)
                                self.assertTrue(all(r['independent']=='true' for r in rows))
                            elif id=='cvDownload':
                                self.assertEqual(len(list(csv.DictReader(io.StringIO(text)))),18)
                            elif id=='reportDownload':
                                report=json.loads(text)
                                self.assertEqual(report['settings']['lv'],2)
                                self.assertEqual(len(report['groupings']),48)
                                self.assertTrue(report['exposure']['seen'])
                            else:
                                self.assertEqual(text,(ROOT/'data/nb11_demo_spectra.csv').read_text())
                        self.assertTrue(page.evaluate("Array.from(document.querySelectorAll('svg path')).every(p=>!/[Nn]a[Nn]|Infinity/.test(p.getAttribute('d')))"))
                        for title in page.locator('svg > title').all_text_contents():
                            self.assertTrue(title.strip())
                        page.select_option('#lv','3')
                        self.assertTrue(page.evaluate('plsLab.exposure.reused'))
                        self.assertFalse(page.evaluate('plsLab.state.locked'))
                        self.assertEqual(page.locator('#testResults').inner_text(),'')
                        page.select_option('#lv','2')
                        page.locator('#lock').click()
                        self.assertFalse(page.evaluate('plsLab.test.independent'))
                        page.reload()
                        page.wait_for_function('window.plsLab')
                        self.assertFalse(page.evaluate('plsLab.test.independent'))
                        page.locator('nav a').last.click()
                        page.wait_for_function('window.plsLab')
                        self.assertTrue(page.evaluate('plsLab.exposure.reused'))
                        page.locator('#reset').click()
                        page.wait_for_function('window.plsLab && !plsLab.state.locked')
                        self.assertTrue(page.evaluate('plsLab.exposure.seen && plsLab.exposure.reused'))
                        self.assertEqual(page.locator('#note5').input_value(),'')
                        self.assertEqual(page.locator('#progress').get_attribute('value'),'0')
                        self.assertEqual(page.locator('#testResults').inner_text(),'')
                        with page.expect_download() as dl:
                            page.locator('#reportDownload').click()
                        report=json.loads(Path(dl.value.path()).read_text())
                        self.assertIsNone(report['test'])
                        self.assertTrue(report['exposure']['reused'])
                        self.assertEqual(errors,[])
                        self.assertEqual(net,[])
                        context.close()
            browser.close()


if __name__=='__main__':
    unittest.main(verbosity=2)
