# 安装和多图视频接入

以下是一次经过验证的 macOS 本机方案，不是无需登录的全自动脚本。示例中的 `WORKSPACE` 是用户选择的项目目录，`SKILL_DIR` 是本 Skill 所在目录；不要把变量写成固定的其他用户路径。

## 1. 先检查环境

- 记录 macOS 版本、`uname -m`、可用空间、Chrome/Chromium 和 Python 版本。BeefTV 官方下载入口：[Releases](https://github.com/glanderness/BeefTV/releases)，按实际机器选择架构并校验官方校验值；安装到 `/Applications` 需按系统权限操作。既有安装不覆盖其用户数据。
- 原项目：[muse2api](https://github.com/czg86389-hub/muse2api)。第三方逆向桥接需要用户了解并同意导入 Muse 会话。不要让用户在聊天里粘贴密码、验证码、Cookie 或 API 密钥。
- 本方案的补丁基准为 `1795dab4139cc6de0e1527abb1317334453319dd`。以下命令只适用于新建目录，不对已有 checkout 执行 reset/checkout；已有安装先备份并审阅兼容差异。

```bash
mkdir -p "$WORKSPACE"
git clone https://github.com/czg86389-hub/muse2api.git "$WORKSPACE/muse2api"
git -C "$WORKSPACE/muse2api" checkout --detach 1795dab4139cc6de0e1527abb1317334453319dd
git -C "$WORKSPACE/muse2api" apply --check "$SKILL_DIR/assets/muse2api-beeftv.patch"
git -C "$WORKSPACE/muse2api" apply "$SKILL_DIR/assets/muse2api-beeftv.patch"
python3 -m venv "$WORKSPACE/muse2api/.venv"
"$WORKSPACE/muse2api/.venv/bin/python" -m pip install -r "$WORKSPACE/muse2api/requirements.txt"
cp "$SKILL_DIR/assets/check_bridge.py" "$WORKSPACE/muse2api/check_bridge.py"
cp "$SKILL_DIR/assets/test_beeftv_compat.py" "$WORKSPACE/muse2api/tests/test_beeftv_compat.py"
cp "$SKILL_DIR/assets/test_local_reliability.py" "$WORKSPACE/muse2api/tests/test_local_reliability.py"
cp "$SKILL_DIR/assets/启动 Muse 画布.command" "$WORKSPACE/启动 Muse 画布.command"
chmod 700 "$WORKSPACE/启动 Muse 画布.command"
```

该安装路径实测 Python 3.12；其他 Python 版本先检查依赖兼容性。若下载的上游已支持相同能力，先比对实现和测试，避免重复应用旧补丁。随附上游 MIT 许可 [muse2api-LICENSE.txt](../assets/muse2api-LICENSE.txt)。

## 2. 私密配置、启动与登录

仅在新安装、目标 `.env` 不存在时创建。随机密钥不可写死在 Skill、输出或 GitHub 仓库；不要输出该文件。优先配置常见的本机 Chrome 路径，其他系统和浏览器需探测后调整。`MUSE2API_PROFILE_ROOT` 应为安装用户可写的私有路径。

```bash
cd "$WORKSPACE/muse2api"
umask 077
.venv/bin/python - <<'PY'
from pathlib import Path
import secrets
p = Path('.env')
if p.exists():
    raise SystemExit('已有 .env，停止以保护现有配置')
profile = str(Path.cwd() / 'browser-profiles')
key = 'm2a_' + secrets.token_hex(24)
p.write_text('MUSE2API_KEY=' + key + '\nMUSE2API_HOST=127.0.0.1\nMUSE2API_PORT=18610\nMUSE2API_PUBLIC_BASE=http://127.0.0.1:18610\nMUSE2API_PROFILE_ROOT=' + profile + '\n', encoding='utf-8')
p.chmod(0o600)
PY
```

运行离线测试：

```bash
.venv/bin/python tests/test_beeftv_compat.py
.venv/bin/python tests/test_local_reliability.py
```

双击工作目录中的 `启动 Muse 画布.command`。它启动本机桥接、检查 `/healthz`、`/readyz` 和需要密钥的 `/v1/models`，然后启动 BeefTV。也可按需创建指向该启动文件的桌面别名；确认不会覆盖同名文件。检查成功不等于 Muse 会话有效或有额度；macOS 实际重启的可靠性应在用户环境中另行验证。

经用户明确同意后，按上游 README 的 Chrome/Edge 扩展步骤在 Muse 登录浏览器中加载项目 `extension/`，填写本机地址与密钥，执行导入并在管理界面确认账号有效。完成后可移除临时扩展；Cookie 持续保存在本机，登录失效时按同样流程重新导入。不要在公开场所或聊天中展示密钥，也不要从一个人的浏览器复制到其他人的设备。

## 3. BeefTV 渠道配置

在「模型配置 → 添加模型服务」创建第三方 OpenAI 兼容渠道，地址 `http://127.0.0.1:18610/v1`，使用新生成的本机密钥，读取模型并按能力添加 `muse-image`、`muse-video`、`muse-spark`。保留已有配置；不要泄露密钥。

为多图视频**另建渠道**，例如 `Muse 多图视频`，同样的地址和密钥，只选择 `muse-video`，在「高级模型设置与测试 → 配置使用」选择：

- 能力：视频；请求协议：`视频生成 JSON · ratio / duration`，其路径为 `POST /v1/video/generations`。
- 图片数量上限必须能容纳所需参考图；一次部署的协议模板为 9 张，实际仍受桥接及 Muse 限制。素材传输先使用协议自动模式；如遇需要公网链接、拒绝本地地址等情况，检查是否可安全使用直接素材/Base64，不要直接关闭 SSRF 安全限制。
- 保存并使用。在画布的视频模型选择器中先选 `Muse 多图视频` 渠道，再选 `muse-video`。两个渠道可能有相同模型名，仅看到 `muse-video` 不能证明选对渠道。
- 连接多张角色图，选择「全能参考模式」，在提示词中明确每张图对应的人物。`首帧/尾帧` 是起止画面，和人物外观参考不同。桥接会把素材顺序和角色描述转成文本提示，效果以实际视频为准；画幅、秒数、音频同样不能保证严格遵守。

## 4. 验收

1. 执行不计费的离线测试、健康和模型目录检查，确认两张参考图、顺序、角色标注和结果 URL 的模拟适配通过。
2. 在用户同意任务数量和可能费用后，提交一次真实测试。检查 BeefTV 任务诊断中的协议与 `imageCount`，并核对桥接是否接收任务、Muse 是否处理、画布是否收到可播放视频。不要把一次成功推广为所有环境或所有请求稳定成功。
3. 用户电脑重启后再次通过启动文件启动并检查。之前任务若因服务重启中断，先查 Muse 历史和计费状态，再决定是否重试。
