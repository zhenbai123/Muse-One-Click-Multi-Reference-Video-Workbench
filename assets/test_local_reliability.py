"""Offline regressions: one submission and no automatic account retry."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

with tempfile.TemporaryDirectory() as tmp:
    os.environ.update(MUSE2API_HOME=tmp, MUSE2API_PROFILE_ROOT=tmp, MUSE2API_KEY='test-only')
    import engine
    from config import CFG
    class Page:
        def __init__(self, ready):
            self.ready = ready
            self.events = []
        def js(self, script):
            if 'Math.round(r.left+r.width/2)' in script:
                return json.dumps({'x': 12, 'y': 13})
            if 'HTMLTextAreaElement.prototype' in script:
                return 6
            if 'function(expected)' in script:
                return json.dumps({'x': 22, 'y': 23}) if self.ready else ''
            return None
        def send(self, method, params):
            self.events.append((method, params))
    obj = engine.MuseEngine(CFG)
    obj.page = Page(True)
    with patch.object(engine.time, 'sleep'):
        assert obj._send('prompt') == 'clicked'
    clicks = [(event[1]['x'], event[1]['y'], event[1]['type']) for event in obj.page.events]
    assert clicks == [(12, 13, 'mousePressed'), (12, 13, 'mouseReleased'),
                      (22, 23, 'mousePressed'), (22, 23, 'mouseReleased')], clicks
    obj.page = Page(False)
    with patch.object(engine.time, 'sleep'), patch.object(engine.time, 'monotonic', side_effect=[0, 11]):
        try:
            obj._send('prompt')
        except engine.MuseGenerationError:
            pass
        else:
            raise AssertionError('unready input was sent')
    assert all(event[1]['x'] != 22 for event in obj.page.events)

    spec = importlib.util.spec_from_file_location('local_reliability_app', ROOT / 'app.py')
    app = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = app
    spec.loader.exec_module(app)
    first = app.store.add_account({'hatch_sess': 'one', 'hatch_vml': 'one'}, 'one')
    app.store.add_account({'hatch_sess': 'two', 'hatch_vml': 'two'}, 'two')
    calls = []
    def uncertain(cookies, prompt, **kwargs):
        calls.append(cookies['hatch_sess'])
        raise app.MuseGenerationError('发送状态未确认')
    with patch.object(app, '_renew_and_persist', side_effect=lambda ident, **_: app.store.get_account(ident)), \
         patch.object(app.engine, 'start'), patch.object(app.engine, 'generate', side_effect=uncertain), \
         patch.object(app.engine, 'reset_thread'), patch.object(app.engine, 'close_current_page'):
        try:
            app._run_generation_locked('test', 'video', 30, account_id=first['id'],
                                       deadline=app.time.monotonic() + 30)
        except app.MuseGenerationError:
            pass
        else:
            raise AssertionError('uncertain result was not propagated')
    assert calls == ['one'], calls
print('PASS: submit once, reject unready input, do not retry uncertain generation')
