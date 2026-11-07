"""Independent NB13 numerical and offline browser checks. Run with unittest.
Requires numpy scipy sklearn playwright and node. Browser dependencies may use LD_LIBRARY_PATH.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
import numpy as np
from scipy.optimize import nnls
from scipy.stats import f, norm
from sklearn.cross_decomposition import PLSRegression
from sklearn.decomposition import PCA

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'labs/w16_sweetener_model'
JS = """
const M=require('./labs/w16_sweetener_model/w16_math.js'),D=require('./labs/w16_sweetener_model/w16_data.js'),B=M.build(D);
let nn=[false,true].map(n=>D.X.map(x=>M.nnls(B.refs,x,n))),pca={};
for(let mode of ['raw','baselineabs'])pca[mode]=[2,3,4].map(k=>({k,limits:M.limits(B.modes[mode].pca,k),diagnostics:D.X.map(x=>M.diagnose(B.modes[mode].pca,M.prep([x],mode)[0],k))}));
console.log(JSON.stringify({D,B,nn,pca,flat:M.prep([[3,3,3,3,3,3,3,3,3,3]],'baselineabs'),invalid:[M.lod([0,0,1,1],[1,1,0,0]),M.lod([0,0,0],[0,0,0])],decisions:[M.decision(48,false,{valid:true,LOD:2,LOQ:8}),M.decision(-1,true,{valid:true,LOD:2,LOQ:8}),M.decision(11,true,{valid:true,LOD:2,LOQ:8}),M.decision(4,true,{valid:false})]}));
"""
CACHE = None

def fixture():
    global CACHE
    if CACHE is None:
        CACHE = json.loads(subprocess.check_output(['node', '-e', JS], cwd=ROOT))
    return CACHE

def arrays(mode):
    d = fixture()['D']
    X = np.array(d['X'])
    if mode != 'raw':
        X = X - (X[:, :5].mean(1) + X[:, -5:].mean(1))[:, None] / 2
        X /= np.abs(X).sum(1)[:, None]
    return X

class Numerical(unittest.TestCase):
    def test_exact_data_and_design(self):
        r = fixture()
        data = (ROOT / 'data/nb13_demo_spectra.csv').read_bytes()
        self.assertEqual(r['D']['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(r['D']['csv'], data.decode())
        self.assertEqual(np.shape(r['D']['X']), (68, 71))
        self.assertEqual((len(r['B']['cal']),len(r['B']['blind'])),(50,14))
        self.assertEqual(len(set(m['sample_id'] for m in r['D']['meta'][:50])),25)
        np.testing.assert_allclose(r['B']['correlation'], [[1,0,-2**-.5],[0,1,-2**-.5],[-2**-.5,-2**-.5,1]],atol=1e-12)
        self.assertEqual(r['B']['recommended'],'raw')

    def test_flat_invalid_and_domain_first(self):
        r=fixture()
        self.assertEqual(r['flat'],[[0]*10])
        self.assertTrue(all(not x['valid'] and x['LOD'] is None and x['LOQ'] is None for x in r['invalid']))
        self.assertEqual(r['decisions'],['OUT_OF_DOMAIN','NEGATIVE','OUT_OF_RANGE','INVALID_SLOPE'])

def pls_test(mode,target,lv):
    def test(self):
        r=fixture(); X=arrays(mode); key=['aspartame_pct','sucralose_pct'][target]
        y=np.array([float(m[key]) for m in r['D']['meta'][:50]])
        a=r['B']['modes'][mode]['targets'][target][lv-1]
        m=PLSRegression(n_components=lv).fit(X[:50],y)
        pred=m.predict(X).ravel()
        np.testing.assert_allclose(a['pred'],pred,atol=2e-8,rtol=2e-8)
        np.testing.assert_allclose(a['model']['coef'],m.coef_.ravel(),atol=2e-7,rtol=2e-7)
        oof=np.zeros(50)
        self.assertEqual(len(a['cv']['folds']),25)
        for fold in a['cv']['folds']:
            tr,va=fold['train'],fold['validation']
            self.assertEqual(len(va),2);self.assertEqual(len(tr),48)
            self.assertFalse(set(r['D']['meta'][i]['sample_id'] for i in tr)&set(r['D']['meta'][i]['sample_id'] for i in va))
            self.assertEqual(fold['overlap'],[])
            oof[va]=PLSRegression(n_components=lv).fit(X[tr],y[tr]).predict(X[va]).ravel()
        np.testing.assert_allclose(a['cv']['pred'],oof,atol=2e-8)
        self.assertAlmostEqual(a['cv']['metrics']['rmse'],np.sqrt(np.mean((oof-y)**2)),places=8)
        w=m.x_weights_; ssy=np.sum(m.x_scores_**2,axis=0)*m.y_loadings_.ravel()**2
        vip=np.sqrt(X.shape[1]*((w*w/np.sum(w*w,axis=0))*ssy).sum(1)/ssy.sum())
        np.testing.assert_allclose(a['vip'],vip,atol=2e-8)
        self.assertAlmostEqual(np.mean(np.array(a['vip'])**2),1,places=10)
        slope=np.polyfit(y,oof,1)[0]; sigma=np.std(oof[y==0],ddof=1)
        for name,v in [('slope',slope),('sigma',sigma),('LOD',3.3*sigma/slope),('LOQ',10*sigma/slope)]:self.assertAlmostEqual(a['lod'][name],v,places=7)
        self.assertEqual(a['lod']['nZero'],10)
    return test

for mode in ['raw','baselineabs']:
    for target in range(2):
        for lv in range(1,9):setattr(Numerical,f'test_pls_{mode}_{target}_LV{lv}',pls_test(mode,target,lv))

def nnls_test(normalized,row):
    def test(self):
        r=fixture(); X=np.array(r['D']['X']); refs=X[64:67].T.copy()
        if normalized:refs/=np.linalg.norm(refs,axis=0)
        A=np.column_stack((refs,np.ones(71))); c,res=nnls(A,X[row]); a=r['nn'][int(normalized)][row]
        np.testing.assert_allclose(a['coef'],c,atol=2e-9)
        np.testing.assert_allclose(a['fit'],A@c,atol=2e-10)
        np.testing.assert_allclose(a['residual'],X[row]-A@c,atol=2e-10)
        self.assertAlmostEqual(a['sse'],res**2,places=10)
        gradient=A.T@(A@c-X[row]);self.assertGreaterEqual(min(a['coef']),0)
        self.assertGreaterEqual(gradient.min(),-1e-8)
        self.assertLess(np.max(np.abs(c*gradient)),1e-8)
        self.assertAlmostEqual(r['nn'][0][row]['sse'],r['nn'][1][row]['sse'],places=9)
    return test
for n in [False,True]:
    for row in range(68):setattr(Numerical,f'test_nnls_{int(n)}_{row:02}',nnls_test(n,row))

def pca_test(mode,k):
    def test(self):
        r=fixture();X=arrays(mode); p=PCA(svd_solver='full').fit(X[:50]);a=r['pca'][mode][k-2]; j=r['B']['modes'][mode]['pca']
        np.testing.assert_allclose(j['eigenvalues'],p.explained_variance_[:49],atol=1e-12)
        # Sign-independent projections and residuals against NumPy SVD.
        z=X-p.mean_; scores=z@p.components_[:k].T; recon=scores@p.components_[:k]
        T=(scores**2/p.explained_variance_[:k]).sum(1); Q=((z-recon)**2).sum(1)
        np.testing.assert_allclose([d['T2'] for d in a['diagnostics']],T,atol=2e-7)
        np.testing.assert_allclose([d['Q'] for d in a['diagnostics']],Q,atol=2e-9)
        np.testing.assert_allclose([d['reconstruction'] for d in a['diagnostics']],recon+p.mean_,atol=2e-8)
        tail=p.explained_variance_[k:49]; t1,t2,t3=[sum(tail**i) for i in [1,2,3]]
        h=1-2*t1*t3/(3*t2*t2); q=t1*(norm.ppf(.95)*np.sqrt(2*t2*h*h)/t1+1+t2*h*(h-1)/t1**2)**(1/h)
        train=k*49/(50-k)*f.ppf(.95,k,50-k)
        self.assertAlmostEqual(a['limits']['T2'],train,places=9)
        self.assertAlmostEqual(a['limits']['newT2'],train*51/50,places=9)
        self.assertAlmostEqual(a['limits']['Q'],q,places=10)
        self.assertTrue(T[67]>train*51/50 or Q[67]>q)
    return test
for mode in ['raw','baselineabs']:
    for k in [2,3,4]:setattr(Numerical,f'test_pca_{mode}_k{k}',pca_test(mode,k))

class Browser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw=sync_playwright().start(); cls.browser=cls.pw.chromium.launch(headless=True)
    @classmethod
    def tearDownClass(cls):cls.browser.close();cls.pw.stop()


def browser_test(lang,mobile):
    def test(self):
        suffix='.en' if lang=='en' else ''; context=self.browser.new_context(viewport={'width':390 if mobile else 1440,'height':844 if mobile else 1000},accept_downloads=True)
        errors=[];network=[];page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda req:network.append(req.url) if req.url.startswith(('http:','https:')) else None)
        context.route('http://**',lambda route:route.abort());context.route('https://**',lambda route:route.abort())
        page.goto((LAB/f'sweetener_model_lab{suffix}.html').as_uri());page.wait_for_selector('#report',state='attached')
        self.assertEqual(page.locator('main section').count(),6);self.assertTrue(page.locator('#lock').is_disabled())
        self.assertNotIn('RMSEP',page.locator('#metrics').inner_text())
        self.assertNotIn('BLIND-',page.evaluate("W16.exported('prediction')"))
        self.assertNotIn('BLIND-',page.evaluate("W16.exported('NNLS')"))
        page.select_option('#row','50')
        self.assertIn('SSE=',page.locator('#nninfo').inner_text())
        self.assertNotIn('100cA=',page.locator('#nninfo').inner_text())
        self.assertNotIn('[cA,cS,cE,offset]',page.locator('#nninfo').inner_text())
        for mode in ['raw','baselineabs']:
            page.select_option('#prep',mode)
            for id in ['a','s']:
                for v in ['1','8']:page.select_option('#'+id,v)
            for k in ['2','4']:page.select_option('#k',k)
        page.click('#recommend');self.assertEqual(page.input_value('#prep'),'raw')
        page.select_option('#row','67');page.check('#norm');self.assertIn('NOT percentages' if lang=='en' else '不再是百分比',page.locator('#body4').inner_text())
        for row in ['0','50','64','67']:page.select_option('#row',row)
        page.uncheck('#norm')
        for i in range(6):
            page.select_option(f'#q{i}','yes');self.assertTrue(page.locator(f'#f{i}').inner_text())
            page.select_option(f'#q{i}','no');page.fill(f'#note{i}','evidence '+str(i))
        self.assertIn('6/6',page.locator('#progress').inner_text())
        page.fill('#reason','Calibration grouped CV before blind errors');page.click('#lock');self.assertIn('RMSEP',page.locator('#metrics').inner_text())
        page.select_option('#a','8');self.assertTrue(page.evaluate('W16.audit.reused'))
        page.reload();page.wait_for_selector('#report',state='attached');self.assertTrue(page.evaluate('W16.audit.reused'));self.assertEqual(page.input_value('#note0'),'evidence 0')
        page.click('header nav a:first-child');page.wait_for_selector('#report',state='attached');self.assertTrue(page.evaluate('W16.audit.exposed && W16.audit.reused'))
        page.click('header nav a:first-child');page.wait_for_selector('#report',state='attached')
        page.fill('#value','-1');self.assertEqual(page.inner_text('#decision'),'NEGATIVE');page.fill('#value','11');self.assertEqual(page.inner_text('#decision'),'OUT_OF_RANGE');page.uncheck('#domainok');self.assertEqual(page.inner_text('#decision'),'OUT_OF_DOMAIN')
        page.fill('#value','');page.check('#domainok');self.assertEqual(page.inner_text('#decision'),'INVALID')
        for kind in ['VIP','prediction','CV','NNLS','domain','report']:
            with page.expect_download() as event:page.click(f'[data-export="{kind}"]')
            text=Path(event.value.path()).read_text();self.assertGreater(len(text),100)
            if kind=='report':self.assertTrue(json.loads(text)['audit']['reused'])
            else:
                rows=list(csv.reader(io.StringIO(text)));self.assertGreater(len(rows),2)
                self.assertIn('source_sha256',rows[0]);self.assertIn('test_reused',rows[0])
                self.assertTrue(all(len(row)==len(rows[0]) for row in rows))
                if kind=='prediction':self.assertIn('WITHHELD_DOMAIN',text)
        with page.expect_download() as event:page.click('#source')
        self.assertEqual(Path(event.value.path()).read_bytes(),(ROOT/'data/nb13_demo_spectra.csv').read_bytes())
        page.click('#reset');page.wait_for_selector('#report',state='attached');self.assertTrue(page.evaluate('W16.audit.exposed && W16.audit.reused'));self.assertEqual(page.input_value('#note0'),'');self.assertIn('0/6',page.inner_text('#progress'))
        self.assertEqual(page.locator('svg').count(),7)
        self.assertFalse(page.evaluate("[...document.querySelectorAll('polyline')].some(e=>/NaN|Infinity/.test(e.getAttribute('points')))"))
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),page.viewport_size['width']+1)
        self.assertIn('OUT_OF_DOMAIN',page.inner_text('#query'));self.assertFalse(errors);self.assertFalse(network)
        out=Path(os.environ.get('W16_SCREENSHOTS',str(Path.home()/'.hermes/cache/scratch/w16-screenshots')));out.mkdir(parents=True,exist_ok=True)
        page.screenshot(path=str(out/f'{lang}_{"mobile" if mobile else "desktop"}.png'),full_page=True)
        context.close()
    return test
for lang in ['zh','en']:
    for mobile in [False,True]:setattr(Browser,f'test_offline_{lang}_{"mobile" if mobile else "desktop"}',browser_test(lang,mobile))

if __name__=='__main__':unittest.main(verbosity=2)
