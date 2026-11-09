#!/usr/bin/env python3
"""Check the expected local bridge without exposing its secret."""
import json
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen
from config import CFG

BASE = 'http://127.0.0.1:18610'
try:
    if not CFG.api_key:
        raise ValueError('未配置本机密钥')
    def get(path, auth=False):
        headers = {'Authorization': 'Bearer ' + CFG.api_key} if auth else {}
        with urlopen(Request(BASE + path, headers=headers), timeout=3) as response:
            return json.load(response)
    health = get('/healthz')
    ready = get('/readyz')
    models = get('/v1/models', True)
    ids = {entry.get('id') for entry in models.get('data', [])}
    if health.get('status') != 'ok' or not {'muse-image', 'muse-video'} <= ids:
        raise ValueError('端口响应不是预期的 Muse 桥接')
    if ready.get('status') != 'ready':
        raise ValueError('桥接没有可用的 Muse 账号')
except (URLError, OSError, ValueError, KeyError, TypeError) as exc:
    print('Muse 桥接检查未通过：' + str(exc), file=sys.stderr)
    sys.exit(1)
print('Muse 桥接已连接；账号会话和额度以实际使用情况为准。')
