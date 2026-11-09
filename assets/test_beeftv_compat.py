import asyncio, os, tempfile, sys, json, base64, threading
from pathlib import Path
from unittest.mock import patch
from starlette.requests import Request
from fastapi import HTTPException
root=tempfile.mkdtemp(prefix='muse-compat-test-')
os.environ['MUSE2API_HOME']=root
os.environ['MUSE2API_PROFILE_ROOT']=root+'/profiles'
os.environ['MUSE2API_KEY']='test-key'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import app

def request_for(data, content_type, path='/v1/videos'):
    sent=False
    async def receive():
        nonlocal sent
        if not sent:
            sent=True
            return {'type':'http.request','body':data,'more_body':False}
        return {'type':'http.disconnect'}
    return Request({'type':'http','method':'POST','path':path,'headers':[(b'content-type',content_type.encode())],'query_string':b''},receive)

async def main():
    got=[]; event=threading.Event()
    def fake_generate(prompt, mode, timeout, **kwargs):
        got.append((prompt,kwargs.get('reference_images')))
        event.set()
        return {'filename':'sample.mp4','kind':'video','size':4},'test-account'
    png=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/a2wAAAAASUVORK5CYII=')
    boundary='muse-test-boundary'
    body=(f'--{boundary}\r\nContent-Disposition: form-data; name="model"\r\n\r\nmuse-video\r\n--{boundary}\r\nContent-Disposition: form-data; name="prompt"\r\n\r\nA moving cloud\r\n--{boundary}\r\nContent-Disposition: form-data; name="seconds"\r\n\r\n5\r\n--{boundary}\r\nContent-Disposition: form-data; name="input_reference"; filename="frame.png"\r\nContent-Type: image/png\r\n\r\n'.encode()+png+f'\r\n--{boundary}--\r\n'.encode())
    with patch.object(app,'_run_generation',fake_generate):
        result=await app.create_video(request_for(body,'multipart/form-data; boundary='+boundary),None)
        assert result['status']=='queued'
        assert event.wait(2) and len(got[0][1])==1 and got[0][1][0].startswith('data:image/png;base64,')
        event.clear()
        result2=await app.create_video(request_for(json.dumps({'model':'muse-video','prompt':'JSON test'}).encode(),'application/json'),None)
        assert result2['status']=='queued' and event.wait(2)
        event.clear()
        image = 'data:image/png;base64,' + base64.b64encode(png).decode()
        multi = {'model': 'muse-video', 'prompt': 'two people', 'ratio': '16:9',
                 'duration': 10, 'images': [{'url': image, 'role': 'reference_image'},
                                            {'url': image, 'role': 'last_frame'}]}
        result3=await app.create_video(request_for(json.dumps(multi).encode(),'application/json',
                                                  '/v1/video/generations'),None)
        assert result3['status']=='queued' and event.wait(2)
        prompt, refs = got[-1]
        assert len(refs)==2 and '16:9' in prompt and '10 秒' in prompt
        assert '[图1] 是第1张图片，为角色或内容参考' in prompt
        assert '[图2] 是第2张图片，为尾帧参考' in prompt
        assert '以第一张作为主要起始画面' not in prompt
    with open(os.path.join(app.CFG.media_dir,'sample.mp4'),'wb') as f: f.write(b'test')
    for _ in range(50):
        if (app.store.get_task(result['id']).get('status')=='completed'): break
        await asyncio.sleep(.01)
    response=app.get_video_content(result['id'],None)
    assert response.path.endswith('sample.mp4')
    for _ in range(50):
        if app.store.get_task(result3['id']).get('status')=='completed': break
        await asyncio.sleep(.01)
    assert app.get_video(result3['id'],None)['data'][0]['url'].endswith('/sample.mp4')
    try: app.get_video_content('does-not-exist',None)
    except HTTPException as e: assert e.status_code==404
    else: raise AssertionError('Missing video must return 404')
    print('PASS: single and multiple references, JSON protocol, task result download, missing task')
asyncio.run(main())
