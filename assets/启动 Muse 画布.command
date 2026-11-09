#!/bin/zsh
cd "$(dirname "$0")" || exit 1
workspace_dir="$PWD"
bridge_dir="$workspace_dir/muse2api"
bridge_python="$bridge_dir/.venv/bin/python"
if [[ ! -x "$bridge_python" ]]; then
  print 'Muse 桥接环境不存在，请联系协助修复。'
  exit 1
fi
if ! lsof -nP -iTCP:18610 -sTCP:LISTEN >/dev/null 2>&1; then
  (cd "$bridge_dir" && umask 077 && nohup "$bridge_python" -m uvicorn app:app --host 127.0.0.1 --port 18610 >> muse2api.log 2>&1 </dev/null &)
fi
bridge_ready=0
for attempt in {1..25}; do
  if (cd "$bridge_dir" && "$bridge_python" check_bridge.py >/dev/null 2>&1); then
    bridge_ready=1
    break
  fi
  sleep 1
done
if (( bridge_ready )); then
  print 'Muse 本地桥接已就绪。'
else
  print 'Muse 桥接未能通过检查，视频和图片生成可能无法使用。'
  (cd "$bridge_dir" && "$bridge_python" check_bridge.py)
  print "请查看日志：$bridge_dir/muse2api.log"
fi
if [[ -d /Applications/BeefTV.app ]]; then
  open /Applications/BeefTV.app
else
  open "$workspace_dir/BeefTV.app"
fi
if (( ! bridge_ready )); then exit 1; fi
