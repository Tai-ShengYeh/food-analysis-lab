"""W15 independent numerical and real offline Chromium acceptance tests.
Run: /path/to/venv/bin/python -m unittest discover -s tests -p test_w15_sweetener.py -v
Requires node, numpy, playwright and installed Chromium. No HTTP server needed.
Optional W15_SCREENSHOT_DIR writes settled desktop/mobile screenshots.
"""
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import unittest
from collections import Counter
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / 'labs/w15_sweetener_prep'
MATH = LAB / 'sweetener_math.js'


def js(expression):
    return json.loads(subprocess.check_output(['node', '-e',
        f'const M=require({json.dumps(str(MATH))});console.log(JSON.stringify({expression}));'], text=True))


class NumericalTests(unittest.TestCase):
    def test_01_exact_source_calibration_and_notebook(self):
        raw = (ROOT / 'data/nb13_demo_spectra.csv').read_bytes()
        rows = list(csv.DictReader(io.StringIO(raw.decode())))
        data = js('(()=>{global.window={};require(' + json.dumps(str(LAB / 'sweetener_data.js')) + ');return window.W15Data;})()')
        self.assertEqual(data['sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(len(rows), 68)
        source = {r['sample_id']: r for r in rows if r['split'] == 'calibration'}
        self.assertEqual(len(source), 25)
        for row in data['calibration']:
            for col in ('aspartame_pct', 'sucralose_pct', 'erythritol_pct'):
                self.assertEqual(row[col], float(source[row['sample_id']][col]))
        self.assertEqual(len(data['blindIDs']), 7)
        self.assertTrue(all(set(r) == {'sample_id', 'aspartame_pct', 'sucralose_pct', 'erythritol_pct'} for r in data['calibration']))
        nb = json.loads((ROOT / 'notebooks/NB13_sweetener_model.ipynb').read_text())
        code = '\n'.join(''.join(c['source']) for c in nb['cells'])
        match = re.search(r'SAMPLE_CSV = """(.*?)"""', code, re.S)
        self.assertIsNotNone(match)
        embedded = match.group(1)
        self.assertEqual(list(csv.DictReader(io.StringIO(embedded))), rows)
        for r in js('M.bottles()'):
            if r['sample_id'].startswith('BLIND'):
                self.assertEqual(set(r), {'sample_id', 'group', 'withheld'})

    def test_02_design_correlations_ranks_all_missing_extremes(self):
        cases = js("['full','diagonal'].flatMap(mode=>Array.from({length:26},(_,missing)=>({mode,missing,rows:M.design(mode,missing),stats:M.designStats(M.design(mode,missing))})))")
        for case in cases:
            with self.subTest(mode=case['mode'], missing=case['missing']):
                rows, actual = case['rows'], case['stats']
                if not rows:
                    self.assertEqual(actual, {'n': 0, 'corr': None, 'rank': 0, 'closureRank': 0})
                    continue
                a = np.array([[1, r['A'], r['S'], r['E']] for r in rows])
                self.assertEqual(actual['rank'], np.linalg.matrix_rank(a[:, :3]))
                self.assertEqual(actual['closureRank'], np.linalg.matrix_rank(a))
                if len(rows) > 1 and np.std(a[:, 1]) > 0 and np.std(a[:, 2]) > 0:
                    self.assertAlmostEqual(actual['corr'], np.corrcoef(a[:, 1], a[:, 2])[0, 1], places=12)
                else:
                    self.assertIsNone(actual['corr'])
        self.assertEqual(js('M.designStats(M.design())')['corr'], 0)
        self.assertAlmostEqual(js("M.designStats(M.design('diagonal'))")['corr'], 1)

    def test_03_latin_groups_unique_coverage_nonorthogonality(self):
        rows = js('M.design()')
        self.assertEqual(len({r['sample_id'] for r in rows}), 25)
        for g in range(1, 6):
            group = [r for r in rows if r['group'] == f'G{g}']
            self.assertEqual(len(group), 5)
            for col in ['A', 'S']:
                self.assertEqual(sorted(r[col] for r in group), [0, 2.5, 5, 7.5, 10])
            self.assertAlmostEqual(np.corrcoef([r['A'] for r in group], [r['S'] for r in group])[0, 1], [1, 0, -.5, -.5, 0][g-1])
        self.assertEqual(rows[17], {'sample_id': 'CAL-17', 'group': 'G5', 'A': 7.5, 'S': 5, 'E': 87.5})
        for target in [.1, 2, 20]:
            np.testing.assert_allclose(target*np.array([rows[17][k] for k in ['A', 'S', 'E']])/100, np.array([.075, .05, .875])*target)

    def test_04_actual_fraction_uncertainty_finite_difference(self):
        for masses in [[.1523, .0997, 1.7489], [0, 0, 2], [20, .0001, .5], [.0001, 20, 20]]:
            for halfwidth in [0, .1, 10]:
                with self.subTest(masses=masses, halfwidth=halfwidth):
                    out = js(f'M.mass({",".join(map(str,masses))},{halfwidth})')
                    a = np.array(masses, dtype=float)
                    frac = a / a.sum()
                    step = 1e-7
                    jac = np.column_stack([((a+np.eye(3)[j]*step)/(a+np.eye(3)[j]*step).sum() - (a-np.eye(3)[j]*step)/(a-np.eye(3)[j]*step).sum())/(2*step) for j in range(3)])
                    cov = jac @ jac.T * (halfwidth/1000/np.sqrt(3))**2
                    np.testing.assert_allclose(out['fractions'], frac, rtol=1e-13)
                    np.testing.assert_allclose(out['jacobian'], jac, rtol=1e-6, atol=1e-9)
                    np.testing.assert_allclose(out['uFraction'], np.sqrt(np.diag(cov)), rtol=1e-6, atol=1e-12)
                    np.testing.assert_allclose(out['covariance'], cov, rtol=1e-6, atol=1e-15)
                    self.assertAlmostEqual(sum(out['fractions']), 1)
        self.assertAlmostEqual(js('M.mass(.1523,.0997,1.7489)')['total'], 2.0009)
        self.assertIsNone(js('M.mass(0,0,0)'))
        self.assertIsNone(js('M.mass(-1,2,3)'))
        self.assertIsNone(js('M.mass(1,2,3,-1)'))

    def test_05_geometric_mass_conservation_and_portion_bound(self):
        for masses in [[.1523, .0997, 1.7489], [0, .1, 1.9], [.2, 0, 1.8], [0, 0, 2], [.0001, 20, 20], [20, .0001, 0], [0, 0, 0]]:
            steps = js(f'M.mixing({",".join(map(str,masses))})')
            if not any(masses):
                self.assertEqual(steps, [])
                continue
            added = np.array([r['add'] for r in steps])
            np.testing.assert_allclose(added.sum(axis=0), masses, rtol=1e-12, atol=1e-12)
            np.testing.assert_allclose(np.cumsum(added, axis=0), [r['cumulative'] for r in steps], atol=1e-12)
            for i in range(1, len(steps)):
                self.assertLessEqual(sum(steps[i]['add']), steps[i-1]['total']+1e-12)
            self.assertAlmostEqual(steps[-1]['total'], sum(masses))

    def test_06_seed_shuffle_reference_determinism_and_coverage(self):
        original = js('M.bottles()')
        for seed in [0, 1, 15, 123456, 4294967295]:
            with self.subTest(seed=seed):
                ref = original.copy()
                x = seed
                for i in range(len(ref)-1, 0, -1):
                    x = (1664525*x+1013904223) % (2**32)
                    j = int(x/(2**32)*(i+1))
                    ref[i], ref[j] = ref[j], ref[i]
                actual = js(f'M.shuffle(M.bottles(),{seed})')
                self.assertEqual(actual, ref)
                self.assertEqual(actual, js(f'M.shuffle(M.bottles(),{seed})'))
                racks = js(f'M.racks({seed})')
                self.assertEqual(list(map(len, racks)), [6, 6, 5, 5, 5, 5])
                self.assertEqual(len({r['sample_id'] for rack in racks for r in rack}), 32)
        self.assertNotEqual(js('M.racks(15)'), js('M.racks(16)'))

    def test_07_rotation_file_uniqueness_and_six_station_coverage(self):
        for seed in [0, 15, 4294967295]:
            for ordered in ['true', 'false']:
                rows = js(f'M.manifest({seed},{ordered})')
                self.assertEqual(len(rows), 384)
                self.assertEqual(len({r['filename'] for r in rows}), 384)
                self.assertEqual(set(Counter(r['instrument'] for r in rows).values()), {64})
                counts = Counter((r['sample_id'], r['instrument']) for r in rows)
                self.assertEqual(len(counts), 32*6)
                self.assertEqual(set(counts.values()), {2})
                for r in rows:
                    stations = ['NIR-1', 'NIR-2', 'NIR-3', 'NIR-4', 'NIR-5', 'Raman785']
                    self.assertEqual(r['instrument'], stations[(r['rack']-1+r['round']-1) % 6])
                    self.assertNotIn('A', r)

    def test_08_timing_bottleneck_budget_boundary(self):
        for scan in [.1, 1.5, 2, 5, (115/6-1)/12]:
            for reference in [0, 1, 10]:
                for budget in [1, 114, 115, 300]:
                    v = js(f'M.timing({scan},{reference},{budget})')
                    self.assertAlmostEqual(v['round'], 12*scan+reference)
                    self.assertAlmostEqual(v['elapsed'], 6*(12*scan+reference))
                    self.assertAlmostEqual(v['workload'], 64*scan+6*reference)
                    self.assertEqual(v['fits'], v['elapsed'] <= budget)
        self.assertEqual(js('M.timing()')['elapsed'], 114)
        self.assertEqual(js('M.timing()')['workload'], 102)
        self.assertEqual(js('M.timing(2)')['elapsed'], 150)
        self.assertTrue(js('M.timing(1.5,1,114)')['fits'])
        self.assertFalse(js('M.timing(1.5,1,113.999)')['fits'])

    def test_09_qc_ddof1_pair_five_pooled_zero_edges(self):
        groups = [[102, 98], [102, 98, 105, 95, 100], [202, 198, 201], [0, 0], [-1, 1], [1], []]
        for g in groups:
            v = js(f'M.stats({json.dumps(g)})')
            if len(g) > 1:
                self.assertAlmostEqual(v['sd'], np.std(g, ddof=1))
            else:
                self.assertIsNone(v['sd'])
            if g and np.mean(g) != 0 and len(g) > 1:
                self.assertAlmostEqual(v['rsd'], np.std(g, ddof=1)/abs(np.mean(g))*100)
            else:
                self.assertIsNone(v['rsd'])
        self.assertAlmostEqual(js('M.stats([102,98,105,95,100])')['sd'], 3.8078865529319543)
        use = groups[:3]
        q = js(f'M.qc({json.dumps(use)},10)')
        df = sum(len(g)-1 for g in use)
        pooled = np.sqrt(sum(np.sum((np.array(g)-np.mean(g))**2) for g in use)/df)
        self.assertAlmostEqual(q['pooled'], pooled)
        self.assertEqual(q['df'], df)
        self.assertAlmostEqual(q['betweenBottleMeansSD'], np.std([np.mean(g) for g in use], ddof=1))
        self.assertAlmostEqual(q['ratioToGap'], pooled/10)
        self.assertIsNone(js('M.qc([[0,0]],0)')['ratioToGap'])
        self.assertIsNone(js('M.qc([[1]],10)')['pooled'])

    def test_10_synthetic_drift_formula_and_correlations(self):
        for ordered in ['true', 'false']:
            for seed in [0, 15, 4294967295]:
                for slope in [-5, 0, 5]:
                    d = js(f'M.drift({seed},{ordered},{slope})')
                    p = d['points']
                    x = (seed+91) % 2**32
                    for i, row in enumerate(p):
                        x = (1664525*x+1013904223) % 2**32
                        expected = row['A']*3+row['S']*2+slope*i+(x/2**32-.5)*2
                        self.assertAlmostEqual(row['syntheticFeature'], expected)
                    self.assertAlmostEqual(d['timeA'], np.corrcoef([r['order'] for r in p], [r['A'] for r in p])[0, 1])
                    self.assertAlmostEqual(d['timeS'], np.corrcoef([r['order'] for r in p], [r['S'] for r in p])[0, 1])
                    self.assertTrue(all(not r['sample_id'].startswith('BLIND') for r in p))


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def assert_no_overflow(self, page):
        self.assertTrue(page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), page.evaluate('({scroll:document.documentElement.scrollWidth,width:innerWidth})'))

    def run_ui(self, filename, width):
        context = self.browser.new_context(viewport={'width': width, 'height': 900}, accept_downloads=True, offline=True)
        page = context.new_page()
        errors, network = [], []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.on('request', lambda r: network.append(r.url) if r.url.startswith(('http:', 'https:')) else None)
        page.route('http://**/*', lambda route: route.abort())
        page.route('https://**/*', lambda route: route.abort())
        page.goto((LAB / filename).as_uri())
        page.wait_for_selector('#qcResult table')
        self.assertEqual(page.locator('section[id^=act]').count(), 6)
        self.assertEqual(page.locator('svg > title').count(), 3)
        self.assert_no_overflow(page)
        # Every select option, including 25 recipes and all Latin groups.
        for field in ['mode', 'group', 'sample', 'order', 'qcMode', 'qcSource']:
            opts = page.locator(f'#{field} option').evaluate_all('(es)=>es.map(e=>e.value)')
            for option in opts:
                page.select_option(f'#{field}', option)
                self.assert_no_overflow(page)
        # Every numeric control at declared min/max, restore after each.
        for field in ['missing', 'target', 'a', 's', 'e', 'u', 'seed', 'slope', 'scan', 'ref', 'budget', 'gap']:
            el = page.locator('#'+field)
            old = el.input_value()
            for attr in ['min', 'max']:
                el.fill(el.get_attribute(attr))
                el.dispatch_event('input')
                self.assert_no_overflow(page)
                self.assertNotIn('NaN', page.locator('main').inner_text())
                self.assertNotIn('Infinity', page.locator('#massResult').inner_text())
            el.fill(old)
            el.dispatch_event('input')
        page.select_option('#mode', 'full')
        page.fill('#missing', '0')
        page.fill('#a', '0')
        page.fill('#s', '0')
        page.fill('#e', '0')
        self.assertEqual(page.locator('#massResult table').count(), 0)
        page.fill('#a', '.1523')
        page.fill('#s', '.0997')
        page.fill('#e', '1.7489')
        page.fill('#scan', '2')
        self.assertIn('150', page.locator('#timingResult').inner_text())
        self.assertIn('warning', page.locator('#timingResult').get_attribute('class'))
        page.fill('#scan', '1.5')
        page.select_option('#qcMode', 'pair')
        page.fill('#feature', '0,0')
        self.assertIn('undefined' if filename.endswith('.en.html') else '未定義', page.locator('#qcResult').inner_text())
        for invalid in ['abc', '', '1', '1,2,3', 'Infinity,0']:
            page.fill('#feature', invalid)
            self.assertEqual(page.locator('#qcResult table').count(), 0)
        page.select_option('#qcMode', 'five')
        self.assertIn('3.80788655', page.locator('#qcResult').inner_text())
        page.select_option('#qcMode', 'multiple')
        page.fill('#feature', '102,98\n202,198\n302,298')
        self.assertIn('2.82842712', page.locator('#qcResult').inner_text())
        page.fill('#featureName', 'Measured selected feature / a.u.')
        # All six wrong/right responses, notes, and persistence.
        for i in range(6):
            page.select_option(f'#prediction{i}', 'yes')
            page.click(f'[data-check="{i}"]')
            self.assertIn('Reconsider' if filename.endswith('.en.html') else '再想一想', page.locator(f'#feedback{i}').inner_text())
            page.select_option(f'#prediction{i}', 'no')
            page.click(f'[data-check="{i}"]')
            self.assertIn('Correct' if filename.endswith('.en.html') else '正確', page.locator(f'#feedback{i}').inner_text())
            page.fill(f'#note{i}', f'Evidence act {i+1}: compare numerical results.')
        for i in range(5):
            page.check(f'#checkpoint{i}')
        self.assertEqual(page.locator('#progress').get_attribute('value'), '6')
        page.reload()
        self.assertEqual(page.locator('#progress').get_attribute('value'), '6')
        self.assertEqual(page.locator('#note5').input_value(), 'Evidence act 6: compare numerical results.')
        self.assertTrue(page.locator('#checkpoint4').is_checked())
        # Actual Blob downloads, not just event handlers.
        downloaded = {}
        for kind in ['design', 'mass', 'racks', 'measure', 'qc', 'report']:
            with page.expect_download() as event:
                page.click(f'[data-export="{kind}"]')
            download = event.value
            text = Path(download.path()).read_text(encoding='utf-8-sig')
            self.assertGreater(len(text), 50)
            downloaded[kind] = json.loads(text) if kind == 'report' else list(csv.DictReader(io.StringIO(text)))
        self.assertEqual(len(downloaded['design']), 25)
        self.assertEqual(len(downloaded['mass']), 1)
        self.assertEqual(downloaded['mass'][0]['sample_id'], 'CAL-17')
        self.assertAlmostEqual(float(downloaded['mass'][0]['A_pct']), .1523/2.0009*100)
        self.assertEqual(len(downloaded['racks']), 32)
        manifests = downloaded['measure']
        self.assertEqual(len(manifests), 384)
        self.assertEqual(len({r['filename'] for r in manifests}), 384)
        self.assertEqual(set(Counter(r['instrument'] for r in manifests).values()), {64})
        self.assertEqual(len(downloaded['qc']), 6)
        self.assertEqual(downloaded['qc'][0]['source'], 'entered')
        report = downloaded['report']
        self.assertEqual(report['timing']['elapsed'], 114)
        self.assertEqual(len(report['reflections']), 6)
        self.assertEqual(len(report['measurementManifest']), 384)
        self.assertEqual(report['qc']['inputs'], [[102, 98], [202, 198], [302, 298]])
        for kind in ['racks', 'measure']:
            for r in downloaded[kind]:
                self.assertFalse(any(k in r for k in ['A', 'S', 'E', 'aspartame_pct', 'sucralose_pct', 'erythritol_pct']))
        def check_blind_nodes(value):
            if isinstance(value, dict):
                if str(value.get('sample_id', '')).startswith('BLIND'):
                    self.assertFalse(any(k in value for k in ['A', 'S', 'E', 'aspartame_pct', 'sucralose_pct', 'erythritol_pct', 'fractions']))
                for v in value.values():
                    check_blind_nodes(v)
            elif isinstance(value, list):
                for v in value:
                    check_blind_nodes(v)
        check_blind_nodes(report)
        # All 7 real source synthetic blind truth PAIRS must be absent from data bundle.
        bundle = (LAB / 'sweetener_data.js').read_text()
        blind_rows = [r for r in csv.DictReader(io.StringIO((ROOT / 'data/nb13_demo_spectra.csv').read_text())) if r['split'] == 'blind_test']
        for r in blind_rows:
            self.assertNotIn('"aspartame_pct": '+r['aspartame_pct']+',', bundle)
        # Screenshot settled plots, then test reset cancellation and acceptance.
        screenshot_dir = os.getenv('W15_SCREENSHOT_DIR')
        if screenshot_dir:
            dest = Path(screenshot_dir)
            dest.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(dest / f'{filename}-{width}.png'), full_page=True)
        self.assert_no_overflow(page)
        page.once('dialog', lambda d: d.dismiss())
        page.click('#reset')
        self.assertEqual(page.locator('#progress').get_attribute('value'), '6')
        page.once('dialog', lambda d: d.accept())
        page.click('#reset')
        page.wait_for_selector('#qcResult table')
        self.assertEqual(page.locator('#progress').get_attribute('value'), '0')
        self.assertEqual(page.locator('#note5').input_value(), '')
        self.assertFalse(page.locator('#checkpoint4').is_checked())
        self.assertEqual(page.locator('#feature').input_value(), '102,98')
        self.assertEqual(network, [], 'Offline lab attempted HTTP(S) requests')
        self.assertEqual(errors, [])
        context.close()

    def test_11_zh_desktop(self):
        self.run_ui('sweetener_lab.html', 1366)

    def test_12_en_desktop(self):
        self.run_ui('sweetener_lab.en.html', 1366)

    def test_13_zh_mobile(self):
        self.run_ui('sweetener_lab.html', 375)

    def test_14_en_mobile(self):
        self.run_ui('sweetener_lab.en.html', 375)


if __name__ == '__main__':
    unittest.main(verbosity=2)
