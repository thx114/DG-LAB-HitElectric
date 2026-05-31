import asyncio
import json
import os
import sys
import traceback

import dockdglab
import 挨打就电v4

plugin_name = "挨打就电"
author = "F_thx"


class App:
    author = "喵小夕-F_thx"
    html = ""
    ui = None
    config = None
    waveform = None
    server = None
    flask_app = None
    logger = None


app = App()


class DockLogger:
    def __init__(self, server):
        self.server = server

    def success(self, msg):
        self.server.log("success", msg)

    def info(self, msg):
        self.server.log("info", msg)

    def warn(self, msg):
        self.server.log("warning", msg)

    def error(self, msg):
        self.server.log("error", msg)

    def debug(self, msg):
        self.server.log("debug", msg)


def init():
    global app
    try:
        app.server = dockdglab.DockDGLab()
        app.config = app.server.get_config(plugin_name) or {}
        app.waveform = app.config.get("waveform", {})
        app.logger = DockLogger(app.server)

        main = sys.modules["__main__"]
        if hasattr(main, 'app') and hasattr(main.app, 'plugin_manager') and main.app.plugin_manager.flask_app:
            app.flask_app = main.app.plugin_manager.flask_app

        u = ui_init()
        f = function_init()

        if u == "success" and f == "success":
            app.server.log("success", f"{plugin_name} 插件初始化完成")
        else:
            app.server.log("warning", f"UI初始化:{u} | 功能初始化:{f}")
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"\n==================== {plugin_name} 初始化崩溃 ====================")
        print(f"错误信息：{str(e)}")
        print(f"详细堆栈：\n{error_detail}")
        print("==============================================================\n")
        try:
            if app.server:
                app.server.log("error", f"初始化失败：{str(e)}")
        except Exception:
            pass


def function_init():
    global app
    try:
        if app.flask_app:
            app.flask_app.add_url_rule(f'/plugins/{plugin_name}/save', view_func=save)
            app.flask_app.add_url_rule(f'/plugins/{plugin_name}/reload', view_func=reload_config)
        return "success"
    except Exception as e:
        if app.server:
            app.server.log("error", f"function_init错误: {e}")
        return str(e)


def save():
    return json.dumps({"message": "保存成功"})


def reload_config():
    挨打就电v4.trigger_config_reload()
    return json.dumps({"message": "配置重载已触发"})


def ui_init():
    global app
    try:
        plugin_dir = os.path.dirname(os.path.abspath(__file__))
        exe_path = os.path.join(plugin_dir, "dist", "config_tool.exe")
        exe_cwd = os.path.join(plugin_dir, "dist")
        exe_path_escaped = exe_path.replace("\\", "\\\\")
        exe_cwd_escaped = exe_cwd.replace("\\", "\\\\")
        app.html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{plugin_name}</title>
    <style>
        *{{margin:0;padding:0;box-sizing:border-box;font-family:"Microsoft YaHei",sans-serif;}}
        body{{background:#f7f8fa;height:100vh;display:flex;align-items:center;justify-content:center;}}
        .box{{text-align:center;max-width:500px;padding:32px;}}
        .icon{{font-size:40px;margin-bottom:12px;color:#1677ff;}}
        .status{{font-size:16px;color:#666;margin-bottom:16px;}}
        .msg{{font-size:14px;color:#f53f3f;margin-bottom:16px;white-space:pre-wrap;word-break:break-all;text-align:left;background:#fff1f0;padding:10px 14px;border-radius:8px;}}
        .msg.ok{{color:#00b42a;background:#f0f9ff;}}
        .close-btn{{background:#1677ff;color:#fff;border:none;border-radius:8px;height:36px;padding:0 20px;font-size:14px;cursor:pointer;display:none;}}
        .close-btn:hover{{opacity:0.85;}}
    </style>
</head>
<body>
<div class="box">
    <div class="icon" id="icon">&#9889;</div>
    <div class="status" id="status">正在启动配置工具...</div>
    <div class="msg" id="msg" style="display:none;"></div>
    <button class="close-btn" id="closeBtn">关闭窗口</button>
</div>
<script>
const {{ipcRenderer}} = require('electron');
const {{spawn}} = require('child_process');
const icon = document.getElementById('icon');
const status = document.getElementById('status');
const msg = document.getElementById('msg');
const closeBtn = document.getElementById('closeBtn');
closeBtn.onclick = () => ipcRenderer.send('window:close');

const exePath = "{exe_path_escaped}";
const exeCwd = "{exe_cwd_escaped}";

try{{
    const child = spawn(exePath, [], {{cwd: exeCwd, detached: true, stdio: 'ignore'}});
    child.unref();
    icon.textContent = '\\u2705';
    status.textContent = '配置工具已启动';
    msg.style.display = 'block';
    msg.className = 'msg ok';
    msg.textContent = 'config_tool.exe 已成功启动';
    setTimeout(() => ipcRenderer.send('window:close'), 1500);
}}catch(e){{
    icon.textContent = '\\u274C';
    status.textContent = '启动失败';
    msg.style.display = 'block';
    msg.textContent = e.message || String(e);
    closeBtn.style.display = 'inline-block';
}}
</script>
</body>
</html>'''
        return "success"
    except Exception as e:
        if app.server:
            app.server.log("error", f"ui_init错误: {e}")
        traceback.print_exc()
        return str(e)


def start():
    asyncio.run(挨打就电v4.main(app))


def stop():
    try:
        挨打就电v4.stop()
    except Exception:
        pass
