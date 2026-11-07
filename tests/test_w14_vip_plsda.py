"""W14 independent sklearn/SciPy references + offline browser acceptance.
Run: python -m unittest discover -s tests -p test_w14_vip_plsda.py -v
Requires numpy, scipy, scikit-learn, Playwright/Chromium, node.
Screenshots: $W14_ARTIFACTS (default system scratch/w14-validation).
"""
import csv
import functools
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import subprocess
import threading
import unittest

import numpy as np
from numpy.testing import assert_allclose
from scipy import stats
from sklearn.cross_decomposition import PLSRegression
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import KFold, train_test_split

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'labs/w14_vip_plsda'
ART = Path(os.environ.get('W14_ARTIFACTS', Path(os.environ.get('TMPDIR', '/home/administrator/.hermes/cache/scratch')) / 'w14-validation'))
ART.mkdir(parents=True, exist_ok=True)
NODE = r"""
const M=require('./labs/w14_vip_plsda/w14_math.js'),D=require('./labs/w14_vip_plsda/w14_data.js'),P=require('./labs/w14_vip_plsda/pca_math.js');
let out={data:D,reg:[],da:[],thresholds:[],pca:null,diagnostics:[],limits:[],injected:[]};
for(let lv=1;lv<=8;lv++){let X=M.rows(D.vip.X,D.vip.train),Y=M.rows(D.vip.Y,D.vip.train),m=M.fit(X,Y,lv);out.reg.push({lv,model:m,vip:M.vip(m),bug:M.vip(m,true),pred:M.predict(m,D.vip.X),cv:M.cv(X,Y,D.vip.folds,lv)})}
for(let t of [.5,1,1.3,2,3]){let r=M.regression(D.vip,t);out.thresholds.push({threshold:t,vip:r.vip,mask:r.mask,fullCurve:r.fullCurve,selectedCurve:r.selectedCurve,fixed:r.fixed,nested:r.nested,fullPred:M.predict(r.full,D.vip.X),selectedPred:r.selected?M.predict(r.selected,M.cols(D.vip.X,r.mask)):null})}
for(let lv=2;lv<=8;lv++){let c=M.classification(D.oils,lv),pred=M.predict(c.model,D.oils.X);out.da.push({lv,model:c.model,pred,cvCurve:c.cvCurve,confusion:M.confusion(M.rows(D.oils.Y,D.oils.test),M.rows(pred,D.oils.test))})}
out.pca=P.fit(D.outlier.X.filter((r,i)=>D.outlier.meta[i].role==='calibration'));
for(let k=1;k<=4;k++){out.limits.push(M.limits(out.pca,k));out.diagnostics.push(D.outlier.X.map(x=>M.diagnose(out.pca,x,k)));out.injected.push(D.outlier.X.map(x=>M.diagnose(out.pca,x,k,true)))}
// Changing heldout values must not change training models, masks or CV.
let altered=JSON.parse(JSON.stringify(D.vip));altered.test.forEach(i=>{altered.X[i]=altered.X[i].map(v=>v+100);altered.Y[i]=[999]});let a=M.regression(altered);out.heldoutIndependent={vip:a.vip,mask:a.mask,fullCurve:a.fullCurve,selectedCurve:a.selectedCurve,nested:a.nested};
// A validation row's labels / spectrum cannot enter that fold's selection.
let X=M.rows(D.vip.X,D.vip.train),Y=M.rows(D.vip.Y,D.vip.train),f=D.vip.folds[0];f.valid.forEach(i=>{X[i]=X[i].map(v=>v+200);Y[i]=[777]});let r=M.cv(X,Y,D.vip.folds,3,(A,B)=>M.vip(M.fit(A,B,4)).flatMap((v,j)=>v>1?[j]:[]));out.modifiedFold0=r.details[0];
console.log(JSON.stringify(out));
"""

@functools.lru_cache(None)
def js_results():
    return json.loads(subprocess.check_output(['node', '-e', NODE], cwd=ROOT, text=True))


def ref_vip(m):
    s = np.sum(m.x_scores_ ** 2, axis=0) * np.sum(m.y_loadings_ ** 2, axis=0)
    return np.sqrt(m.x_weights_.shape[0] * ((m.x_weights_ / np.linalg.norm(m.x_weights_, axis=0)) ** 2 @ s) / s.sum())


def fit(X, Y, lv):
    return PLSRegression(n_components=lv, scale=False).fit(X, Y)


def cv(X, Y, folds, lv, selector=None):
    pred = np.zeros_like(Y, dtype=float)
    masks = []
    for f in folds:
        tr, va = np.array(f['train']), np.array(f['valid'])
        mask = np.arange(X.shape[1]) if selector is None else selector(X[tr], Y[tr])
        masks.append(mask.tolist())
        if len(mask) < lv:
            return None, None, masks
        pred[va] = fit(X[tr][:, mask], Y[tr], lv).predict(X[va][:, mask])
    return float(np.sqrt(np.mean((pred-Y)**2))), pred, masks


class Numerical(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = js_results()
        cls.data = cls.js['data']
        d = cls.data['vip']
        cls.Xall, cls.Yall = np.array(d['X']), np.array(d['Y'])
        cls.X, cls.Y = cls.Xall[d['train']], cls.Yall[d['train']]
        cls.folds = d['folds']
        d = cls.data['oils']
        cls.OX, cls.OY = np.array(d['X']), np.array(d['Y'])
        cls.Otr, cls.Ote = d['train'], d['test']
        cls.FO = d['folds']
        d = cls.data['outlier']
        cls.Zall = np.array(d['X'])
        cls.Z = cls.Zall[[r['role'] == 'calibration' for r in d['meta']]]
        cls.mu = cls.Z.mean(0)
        cls.U, cls.S, cls.Vt = np.linalg.svd(cls.Z-cls.mu, full_matrices=False)
        cls.eig = cls.S[:39]**2/39

    def test_01_exact_bundled_sources(self):
        for name, d in self.data.items():
            p = ROOT / d['source']
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), d['sha256'])
            source = list(csv.DictReader(io.StringIO(p.read_text())))
            cols = sorted([c for c in source[0] if c.replace('.', '', 1).isdigit()], key=float)
            assert_allclose([[float(r[c]) for c in cols] for r in source], d['X'], atol=0, rtol=0)
            self.assertEqual([{k:v for k,v in r.items() if k not in cols} for r in source], d['meta'])
        self.assertEqual([np.array(self.data[n]['X']).shape for n in ['vip','oils','outlier']], [(80,81),(90,70),(48,50)])

    def test_02_original_sklearn_splits_and_folds(self):
        for name, seed, size in [('vip',14,.25),('oils',1,.3)]:
            d=self.data[name]
            tr,te=train_test_split(np.arange(len(d['X'])),test_size=size,random_state=seed,stratify=None if name=='vip' else [r['oil'] for r in d['meta']])
            self.assertEqual(tr.tolist(),d['train']);self.assertEqual(te.tolist(),d['test'])
            expected=[{'train':a.tolist(),'valid':b.tolist()} for a,b in KFold(5,shuffle=True,random_state=seed).split(tr)]
            self.assertEqual(expected,d['folds'])
        self.assertEqual(self.data['oils']['classes'], ['CAN','COC','EVOO','PEA','ROO','SOY'])

    def test_03_pls1_models_predictions_all_lv(self):
        for r in self.js['reg']:
            m=fit(self.X,self.Y,r['lv'])
            assert_allclose(r['model']['coef'],m.coef_.T,atol=2e-8)
            assert_allclose(r['pred'],m.predict(self.Xall),atol=1e-9)
            assert_allclose(r['model']['W'],m.x_weights_.T,atol=1e-10)
            assert_allclose(r['model']['T'],m.x_scores_.T,atol=1e-10)

    def test_04_vip_formula_all_lv(self):
        for r in self.js['reg']:
            v=np.array(r['vip']);assert_allclose(v,ref_vip(fit(self.X,self.Y,r['lv'])),atol=1e-9)
            self.assertAlmostEqual(np.mean(v*v),1,places=12)
            self.assertTrue((v>=0).all())

    def test_05_bug_subset_and_necessary_not_sufficient(self):
        r=self.js['reg'][3];v=np.array(r['vip'])
        assert_allclose(r['bug'],9,atol=1e-12)
        self.assertAlmostEqual(np.mean(np.array(r['bug'])**2),81)
        self.assertGreater(np.mean(v[v>1]**2),1)
        # An arbitrary all-ones vector passes the identity but is not this VIP.
        self.assertEqual(np.mean(np.ones(81)**2),1)
        self.assertGreater(np.max(v)-np.min(v),1)

    def test_06_full_cv_curve_and_baseline(self):
        for r in self.js['reg']:
            error,pred,_=cv(self.X,self.Y,self.folds,r['lv'])
            assert_allclose(r['cv']['pred'],pred,atol=1e-9)
            self.assertAlmostEqual(r['cv']['rmse'],error,places=10)
        self.assertEqual(min(self.js['reg'],key=lambda r:r['cv']['rmse'])['lv'],4)
        te=self.data['vip']['test'];self.assertAlmostEqual(np.sqrt(np.mean((np.array(self.js['reg'][3]['pred'])[te]-self.Yall[te])**2)),float(np.sqrt(np.mean((fit(self.X,self.Y,4).predict(self.Xall[te])-self.Yall[te])**2))),places=10)

    def test_07_thresholds_fixed_mask_curves(self):
        for r in self.js['thresholds']:
            mask=np.flatnonzero(ref_vip(fit(self.X,self.Y,4))>r['threshold'])
            self.assertEqual(mask.tolist(),r['mask'])
            for point in r['selectedCurve']:
                error,_,_=cv(self.X[:,mask],self.Y,self.folds,point['lv'])
                self.assertAlmostEqual(point['rmse'],error,places=9)
            if len(mask)>=3:
                assert_allclose(r['selectedPred'],fit(self.X[:,mask],self.Y,3).predict(self.Xall[:,mask]),atol=1e-8)
            else:self.assertIsNone(r['selectedPred'])
        base=self.js['thresholds'][1];self.assertEqual(len(base['mask']),18)
        self.assertEqual(min(base['selectedCurve'],key=lambda r:r['rmse'])['lv'],3)

    def test_08_fold_local_selection_against_independent_reference(self):
        for r in self.js['thresholds']:
            threshold=r['threshold'];error,pred,masks=cv(self.X,self.Y,self.folds,3,lambda A,B:np.flatnonzero(ref_vip(fit(A,B,4))>threshold))
            if error is None:self.assertIsNone(r['nested']['rmse']);continue
            self.assertAlmostEqual(r['nested']['rmse'],error,places=9)
            assert_allclose(r['nested']['pred'],pred,atol=1e-8)
            self.assertEqual([d['mask'] for d in r['nested']['details']],masks)
        self.assertEqual(self.js['modifiedFold0']['mask'], self.js['thresholds'][1]['nested']['details'][0]['mask'])

    def test_09_heldout_never_enters_selection(self):
        a=self.js['heldoutIndependent'];b=self.js['thresholds'][1]
        for k in ['vip','mask','fullCurve','selectedCurve','nested']:self.assertEqual(a[k],b[k])

    def test_10_pls2_true_joint_models_all_lv(self):
        for r in self.js['da']:
            m=fit(self.OX[self.Otr],self.OY[self.Otr],r['lv'])
            assert_allclose(r['pred'],m.predict(self.OX),atol=2e-9)
            assert_allclose(r['model']['coef'],m.coef_.T,atol=2e-8)
            assert_allclose(r['model']['W'],m.x_weights_.T,atol=2e-9)
            assert_allclose(r['model']['Q'],m.y_loadings_.T,atol=2e-9)
        self.assertTrue(np.min(self.js['da'][4]['pred'])<0)

    def test_11_pls2_cv_all_lv(self):
        curve=self.js['da'][0]['cvCurve']
        for point in curve:
            error,_,_=cv(self.OX[self.Otr],self.OY[self.Otr],self.FO,point['lv'])
            self.assertAlmostEqual(point['rmse'],error,places=9)
        self.assertEqual(min(curve,key=lambda r:r['rmse'])['lv'],6)

    def test_12_confusion_and_class_metrics_all_lv(self):
        truth=np.argmax(self.OY[self.Ote],axis=1)
        for r in self.js['da']:
            pred=np.argmax(fit(self.OX[self.Otr],self.OY[self.Otr],r['lv']).predict(self.OX[self.Ote]),axis=1)
            cm=confusion_matrix(truth,pred,labels=range(6))
            assert_allclose(r['confusion']['cm'],cm,atol=0)
            self.assertAlmostEqual(r['confusion']['accuracy'],np.trace(cm)/27)
            for i,p in enumerate(r['confusion']['perClass']):
                tp=cm[i,i];fn=cm[i].sum()-tp;fp=cm[:,i].sum()-tp;tn=27-tp-fn-fp
                self.assertEqual([p[k] for k in ['TP','FN','FP','TN']],[tp,fn,fp,tn])
                assert_allclose([p['sensitivity'],p['specificity'],p['accuracy']],[tp/(tp+fn),tn/(tn+fp),(tp+tn)/27])
        self.assertEqual(np.trace(self.js['da'][4]['confusion']['cm']),24)

    def test_13_pca_calibration_svd_projectors(self):
        p=self.js['pca'];assert_allclose(p['mean'],self.mu,atol=1e-14);assert_allclose(p['eigenvalues'],self.eig,atol=1e-12)
        V=np.array(p['loadings']);assert_allclose(V@V.T,np.eye(39),atol=1e-9)
        for k in range(1,5):assert_allclose(V[:k].T@V[:k],self.Vt[:k].T@self.Vt[:k],atol=2e-9)
        assert_allclose(p['scores'],(self.Z-self.mu)@V.T,atol=1e-11)

    def test_14_pca_all_diagnostics_reconstruction(self):
        for k in range(1,5):
            scores=(self.Zall-self.mu)@self.Vt[:k].T;rec=self.mu+scores@self.Vt[:k];res=self.Zall-rec
            d=self.js['diagnostics'][k-1]
            assert_allclose([r['T2'] for r in d],np.sum(scores**2/self.eig[:k],axis=1),atol=2e-8)
            assert_allclose([r['Q'] for r in d],np.sum(res**2,axis=1),atol=1e-11)
            assert_allclose([r['reconstruction'] for r in d],rec,atol=1e-9)
            assert_allclose([r['residual'] for r in d],res,atol=1e-9)

    def test_15_limits_scipy_all_k(self):
        for k in range(1,5):
            tail=self.eig[k:];t1,t2,t3=[np.sum(tail**i) for i in [1,2,3]];h=1-2*t1*t3/(3*t2*t2)
            Q=t1*(stats.norm.ppf(.95)*np.sqrt(2*t2*h*h)/t1+1+t2*h*(h-1)/t1**2)**(1/h)
            T=k*39/(40-k)*stats.f.ppf(.95,k,40-k);lim=self.js['limits'][k-1]
            assert_allclose([lim['T2'],lim['newT2'],lim['Q']],[T,T*41/40,Q],rtol=1e-10,atol=1e-12)
        base=self.js['diagnostics'][1];meta=self.data['outlier']['meta'];lim=self.js['limits'][1]
        for d,m in zip(base,meta):
            if m['role']=='cross_instrument':self.assertGreater(d['Q'],lim['Q'])
            if m['role']=='leverage_outlier':self.assertGreater(d['T2'],lim['newT2']);self.assertLess(d['Q'],lim['Q'])

    def test_16_orthogonal_injection_all_samples_all_k(self):
        for k in range(1,5):
            V=np.array(self.js['pca']['loadings'])[:k]
            for a,b in zip(self.js['diagnostics'][k-1],self.js['injected'][k-1]):
                delta=np.array(b['original'])-a['original'];self.assertAlmostEqual(np.linalg.norm(delta),.2,places=10)
                assert_allclose(V@delta,0,atol=1e-10);self.assertAlmostEqual(a['T2'],b['T2'],places=8)
                assert_allclose(np.array(b['reconstruction'])+b['residual'],b['original'],atol=1e-12)
                self.assertGreater(b['Q'],a['Q'])


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


class Browser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        handler=functools.partial(QuietHandler,directory=str(ROOT))
        cls.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}/labs/w14_vip_plsda/'
        cls.pw=sync_playwright().start()
        cls.browser=cls.pw.chromium.launch(headless=True,args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.pw.stop();cls.server.shutdown();cls.server.server_close()

    def open(self,en=False,mobile=False):
        context=self.browser.new_context(viewport={'width':390 if mobile else 1440,'height':844 if mobile else 1000},accept_downloads=True)
        self.addCleanup(context.close)
        errors=[];external=[]
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
        def route(r):
            if r.request.url.startswith(self.base.rsplit('/labs/',1)[0]):r.continue_()
            else:external.append(r.request.url);r.abort()
        context.route('**/*',route)
        page.goto(self.base+('vip_plsda_lab.en.html' if en else 'vip_plsda_lab.html'))
        page.wait_for_function('typeof reg!=="undefined" && !!reg && !!diag')
        return context,page,errors,external

    def exercise(self,en,mobile):
        context,p,errors,external=self.open(en,mobile)
        self.assertEqual(p.locator('main section').count(),6)
        self.assertTrue(p.locator('#reveal').is_disabled())
        self.assertEqual(p.evaluate('evidence().regression.test'),None)
        self.assertEqual(p.evaluate('evidence().classification.source'),'training_cv')
        p.locator('#lock').click();self.assertTrue(p.locator('#reveal').is_disabled())
        for i in range(6):
            p.locator(f'#q{i}').select_option('1');self.assertTrue(p.locator(f'#f{i}').text_content())
            p.locator(f'#q{i}').select_option('0');p.locator(f'#note{i}').fill(f'act {i+1}: investigate, retain all samples')
        for v in ['1','8','4']:p.locator('#fullLV').select_option(v)
        for v in ['1','8','3']:p.locator('#selectedLV').select_option(v)
        for v in [.5,3,1.3,1]:
            p.locator('#threshold').evaluate('(e,v)=>{e.value=v;e.dispatchEvent(new Event("input"));e.dispatchEvent(new Event("change"));}',v)
            self.assertTrue(p.locator('#cvSummary').text_content())
            if v == 3:
                self.assertEqual(p.evaluate('reg.mask.length'),0)
                self.assertIsNone(p.evaluate('reg.selected'))
                self.assertIsNone(p.evaluate('reg.nested.rmse'))
                self.assertEqual(p.locator('#selectedLV').input_value(),'3')
        p.locator('#bug').check();self.assertIn('81.0000000000',p.locator('#vipSummary').text_content())
        p.locator('#subset').check();p.locator('#bug').uncheck()
        self.assertGreater(p.evaluate('M.mean(reg.mask.map(j=>reg.vip[j]**2))'),1)
        p.locator('#subset').uncheck()
        for v in range(2,9):
            p.locator('#daLV').select_option(str(v));self.assertEqual(p.evaluate('conf.cm.flat().reduce((a,b)=>a+b,0)'),63)
        p.locator('#daLV').select_option('6')
        for i in range(63):p.locator('#oilSample').select_option(str(i))
        for k in range(1,5):
            p.locator('#k').select_option(str(k))
            p.locator('#sample').select_option('47');before=p.evaluate('diag[47].T2');p.locator('#inject').check()
            self.assertAlmostEqual(p.evaluate('diag[47].T2'),before,places=8);p.locator('#inject').uncheck()
        p.locator('#k').select_option('2')
        for i in range(48):p.locator('#sample').select_option(str(i))
        p.locator('#sample').select_option('40')
        self.assertFalse(p.evaluate('[...document.querySelectorAll("svg path")].some(e=>/NaN|Infinity/.test(e.getAttribute("d")))'))
        self.assertTrue(all(p.locator('svg > title').all_text_contents()))
        self.assertLessEqual(p.evaluate('document.documentElement.scrollWidth'),p.viewport_size['width'])
        p.reload();p.wait_for_selector('#progress');self.assertEqual(p.locator('#note0').input_value(),'act 1: investigate, retain all samples')
        self.assertIn('6/6',p.locator('#progress').text_content())
        # Keyboard manipulation of select is handled by native browser controls.
        p.locator('#daLV').focus();p.keyboard.press('Home');p.keyboard.press('ArrowDown');p.keyboard.press('Tab')
        self.assertEqual(p.locator('#daLV').input_value(),'3');p.locator('#daLV').select_option('6')
        p.locator('#reason').fill('Training CV suggests LV4/3 regression, LV6 PLS2; threshold predeclared 1.')
        p.locator('#lock').click();self.assertFalse(p.locator('#reveal').is_disabled());p.locator('#reveal').click()
        self.assertEqual(p.evaluate('evidence().classification.source'),'exposed_test')
        self.assertAlmostEqual(p.evaluate('conf.accuracy'),24/27)
        self.assertIsNotNone(p.evaluate('evidence().regression.test'))
        for i in range(27):p.locator('#oilSample').select_option(str(i))
        for kind in ['json','vip','cv','confusion','diagnostics']:
            with p.expect_download() as download:p.locator(f'[data-export="{kind}"]').click()
            path=ART/f'{"en" if en else "zh"}-{mobile}-{kind}.{ "json" if kind=="json" else "csv"}'
            download.value.save_as(path)
            text=path.read_text(encoding='utf-8-sig')
            if kind=='json':
                report=json.loads(text);self.assertEqual(report['exclusions'],[]);self.assertEqual(len(report['classification']['scores']),27)
                self.assertEqual(report['state']['notes'][0],'act 1: investigate, retain all samples')
            else:self.assertGreater(len(list(csv.reader(io.StringIO(text)))),5)
        # Invalidating the reason must immediately remove exposed CM / scores too.
        p.locator('#reason').fill('Changed reason')
        self.assertEqual(p.evaluate('evidence().classification.source'),'training_cv')
        self.assertEqual(p.evaluate('conf.cm.flat().reduce((a,b)=>a+b,0)'),63)
        p.locator('#daLV').select_option('7');self.assertTrue(p.evaluate('exposure.reused'))
        p.locator('#reset').click();self.assertEqual(p.locator('#note0').input_value(),'')
        self.assertTrue(p.evaluate('exposure.reused'));self.assertEqual(p.evaluate('exposure.events.length'),1)
        p.screenshot(path=str(ART/f'{"en" if en else "zh"}-{"mobile" if mobile else "desktop"}.png'),full_page=True)
        p.locator('#act5').screenshot(path=str(ART/f'{"en" if en else "zh"}-{"mobile" if mobile else "desktop"}-diagnostics.png'))
        p.locator('#act1').screenshot(path=str(ART/f'{"en" if en else "zh"}-{"mobile" if mobile else "desktop"}-vip.png'))
        p.locator('#language').click();p.wait_for_selector('#progress');self.assertTrue(p.evaluate('exposure.reused'))
        self.assertTrue(p.locator('#reveal').is_disabled())
        self.assertEqual(errors,[]);self.assertEqual(external,[])

    def test_17_zh_desktop(self):self.exercise(False,False)
    def test_18_en_desktop(self):self.exercise(True,False)
    def test_19_zh_mobile(self):self.exercise(False,True)
    def test_20_en_mobile(self):self.exercise(True,True)

    def test_21_file_offline_and_reveal_persistence(self):
        context=self.browser.new_context(viewport={'width':1000,'height':800});self.addCleanup(context.close)
        page=context.new_page();network=[];errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.route('http://**/*',lambda r:(network.append(r.request.url),r.abort()))
        page.route('https://**/*',lambda r:(network.append(r.request.url),r.abort()))
        page.goto((LAB/'vip_plsda_lab.en.html').as_uri());page.wait_for_selector('#cvSummary')
        self.assertIn('18/81',page.locator('#cvSummary').text_content());self.assertEqual(network,[])
        self.assertEqual(errors,[])
        context,p,errors,external=self.open(True,False)
        p.locator('#reason').fill('Prespecified baseline, training CV only');p.locator('#lock').click();p.locator('#reveal').click()
        p.reload();p.wait_for_selector('#cmSummary');self.assertEqual(p.evaluate('evidence().classification.source'),'exposed_test')
        p.locator('#language').click();p.wait_for_selector('#cmSummary');self.assertEqual(p.evaluate('evidence().classification.source'),'exposed_test')
        p.locator('#threshold').evaluate('(e)=>{e.value=1.3;e.dispatchEvent(new Event("change"))}')
        p.reload();p.wait_for_selector('#progress');self.assertTrue(p.evaluate('exposure.reused'))
        self.assertEqual(p.evaluate('evidence().classification.source'),'training_cv')
        self.assertEqual(errors,[]);self.assertEqual(external,[])


if __name__=='__main__':
    unittest.main(verbosity=2)
