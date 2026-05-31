import json
from typing import Dict, List, Optional

class PluginUI:
    def __init__(self, plugin_name: str):
        self.plugin_name = plugin_name
        self.items = []
        self.global_buttons = []

    # ------------------------------
    # 基础组件
    # ------------------------------
    def add_input(self, key: str, label: str, default="", button=None):
        self.items.append({
            "type": "input", "key": key, "label": label,
            "value": default, "it": "text", "button": button
        })

    def add_number(self, key: str, label: str, default=0, button=None):
        self.items.append({
            "type": "input", "key": key, "label": label,
            "value": default, "it": "number", "button": button
        })

    def add_switch(self, key: str, label: str, default=True):
        self.items.append({"type": "switch", "key": key, "label": label, "value": default})

    def add_select(self, key: str, label: str, options: List[str], default=""):
        self.items.append({"type": "select", "key": key, "label": label, "options": options, "value": default})

    def add_textarea(self, key: str, label: str, default="", rows=6):
        self.items.append({"type": "textarea", "key": key, "label": label, "value": default, "rows": rows})

    def add_waveform(self, initial: Dict = None):
        self.items.append({"type": "waveform", "data": initial or {}})

    # ------------------------------
    # 新增：文本、段落、标签、分割线、提示框
    # ------------------------------
    def add_title(self, text: str, level=2):
        """标题"""
        self.items.append({"type": "title", "text": text, "level": level})

    def add_text(self, text: str):
        """单行文本"""
        self.items.append({"type": "text", "text": text})

    def add_paragraph(self, text: str):
        """段落文本"""
        self.items.append({"type": "paragraph", "text": text})

    def add_label_tip(self, text: str, color="#666"):
        """小字提示标签"""
        self.items.append({"type": "label_tip", "text": text, "color": color})

    def add_divider(self, margin="8px 0"):
        """分割线"""
        self.items.append({"type": "divider", "margin": margin})

    def add_tip_box(self, text: str, box_type="info"):
        """彩色提示框: info/success/warning/error"""
        self.items.append({"type": "tip_box", "text": text, "box_type": box_type})

    # ------------------------------
    # 按钮构造
    # ------------------------------
    def make_fill_btn(self, text: str, action: str, target_key: str):
        return {"text": text, "action": action, "target": target_key}

    def make_normal_btn(self, text: str, action: str):
        return {"text": text, "action": action, "target": None}

    def add_global_btn(self, text: str, action: str):
        self.global_buttons.append({"text": text, "action": action})

    # ============================
    # 渲染
    # ============================
    def build(self):
        normal_items = []
        waveform_items = []
        for item in self.items:
            if item["type"] == "waveform":
                waveform_items.append(item)
            else:
                normal_items.append(item)

        normal_html = self._render_items(normal_items)
        waveform_html = self._render_items(waveform_items)

        return self._full_page(normal_html, waveform_html)

    def _render_items(self, items):
        html = ""
        for item in items:
            if item["type"] == "input":
                html += self._i(item)
            elif item["type"] == "switch":
                html += self._s(item)
            elif item["type"] == "select":
                html += self._se(item)
            elif item["type"] == "textarea":
                html += self._t(item)
            elif item["type"] == "waveform":
                html += self._wf(item["data"])
            # 渲染新增组件
            elif item["type"] == "title":
                lv = item["level"]
                html += f'<h{lv} style="margin:8px 0;">{item["text"]}</h{lv}>'
            elif item["type"] == "text":
                html += f'<span style="font-size:14px; color:#333;">{item["text"]}</span>'
            elif item["type"] == "paragraph":
                html += f'<p style="font-size:14px; line-height:1.6; color:#444; margin:4px 0;">{item["text"]}</p>'
            elif item["type"] == "label_tip":
                html += f'<div style="font-size:12px; color:{item["color"]}; margin:4px 0;">{item["text"]}</div>'
            elif item["type"] == "divider":
                html += f'<div style="height:1px;background:#e5e6eb;margin:{item["margin"]};"></div>'
            elif item["type"] == "tip_box":
                t = item["box_type"]
                bg_map = {"info":"#e6f7ff","success":"#f0f9ff","warning":"#fff7e6","error":"#fff1f0"}
                color_map = {"info":"#0078d4","success":"#008800","warning":"#d87800","error":"#c40000"}
                bg = bg_map.get(t, "#e6f7ff")
                color = color_map.get(t, "#0078d4")
                html += f'''
                <div style="background:{bg}; color:{color}; padding:10px 12px; border-radius:8px; margin:8px 0; font-size:13px;">
                    {item["text"]}
                </div>
                '''
        return html

    def _i(self, item):
        btn_html = ""
        if item.get("button"):
            b = item["button"]
            if b.get("target"):
                btn_html = f'<button class="inline-btn" onclick="doFillAction(\'{b["action"]}\',\'{b["target"]}\')">{b["text"]}</button>'
            else:
                btn_html = f'<button class="inline-btn" onclick="doNormalAction(\'{b["action"]}\')">{b["text"]}</button>'

        return f'''
        <div class="form-item">
            <label class="form-label">{item["label"]}</label>
            <div class="input-group">
                <input type="{item["it"]}" id="input_{item["key"]}" class="form-input" value="{item["value"]}" data-key="p.{item["key"]}">
                {btn_html}
            </div>
        </div>'''

    def _s(self, item):
        v = item["value"]
        return f'''
        <div class="form-item">
            <label class="form-label">{item["label"]}</label>
            <select class="form-input" data-key="p.{item["key"]}">
                <option value="true" {"selected" if v else ""}>是</option>
                <option value="false" {"selected" if not v else ""}>否</option>
            </select>
        </div>'''

    def _se(self, item):
        opts = "".join(f'<option value="{o}" {"selected" if o==item["value"] else ""}>{o}</option>' for o in item["options"])
        return f'''
        <div class="form-item">
            <label class="form-label">{item["label"]}</label>
            <select class="form-input" data-key="p.{item["key"]}">{opts}</select>
        </div>'''

    def _t(self, item):
        return f'''
        <div class="form-item">
            <label class="form-label">{item["label"]}</label>
            <textarea class="form-input" rows="{item["rows"]}" data-key="p.{item["key"]}">{item["value"]}</textarea>
        </div>'''

    def _wf(self, data):
        items = ""
        for k, v in data.items():
            if isinstance(v, list):
                tag, t = "tag-array", "数组"
                lines = "\n".join(str(x) for x in v)
                ctl = f'<textarea data-wave-key="{k}" data-format="array" class="form-input">{lines}</textarea>'
            elif isinstance(v, dict):
                tag, t = "tag-object", "对象"
                val = json.dumps(v, ensure_ascii=False, indent=2)
                ctl = f'<textarea data-wave-key="{k}" data-format="object" class="form-input">{val}</textarea>'
            else:
                tag, t = "tag-string", "字符串"
                ctl = f'<textarea data-wave-key="{k}" data-format="string" class="form-input">{v}</textarea>'

            items += f'''
            <div class="wave-item">
                <div class="wave-header">
                    <span>{k}</span>
                    <span class="{tag}">{t}</span>
                    <button class="wave-del" onclick="this.parentElement.parentElement.remove()">删除</button>
                </div>
                {ctl}
            </div>'''
        return f'''
        <div style="margin-top:10px;">
            <button class="primary-btn" onclick="addWaveModal()" style="margin-bottom:10px;">添加波形</button>
            <div id="waves">{items}</div>
        </div>'''

    # ============================
    # 页面 HTML
    # ============================
    def _full_page(self, normal, waveform):
        gbtn = ''.join([f'<button class="ghost-btn" onclick="doNormalAction(\'{b["action"]}\')">{b["text"]}</button>' for b in self.global_buttons])
        return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{self.plugin_name}</title>
    <link rel="stylesheet" href="https://cdn.bootcdn.net/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        *{{margin:0;padding:0;box-sizing:border-box;font-family: "Microsoft YaHei", sans-serif;}}
        :root{{
            --c:#1677ff;--bg:#f7f8fa;--card:#fff;--text:#333;--gray:#666;--bd:#e5e6eb;
            --success:#00b42a;--danger:#f53f3f;--warning:#ff7d00;
        }}
        body{{background:var(--bg);-webkit-app-region:drag;height:100vh;overflow:hidden;}}
        .loading{{position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;color:#fff;z-index:9999;}}
        .page{{height:100vh;display:flex;flex-direction:column;}}
        .header{{padding:16px 20px;background:var(--card);border-bottom:1px solid var(--bd);font-size:16px;font-weight:600;color:var(--text);}}
        .body{{flex:1;overflow-y:auto;padding:16px 20px;-webkit-app-region:no-drag;}}
        .footer{{padding:12px 20px;border-top:1px solid var(--bd);background:var(--card);display:flex;gap:10px;-webkit-app-region:no-drag;}}
        .fold-card{{background:var(--card);border-radius:12px;margin-bottom:12px;overflow:hidden;border:1px solid var(--bd);}}
        .fold-head{{padding:12px 16px;display:flex;justify-content:space-between;align-items:center;font-weight:500;cursor:pointer;background:#fafafa;}}
        .fold-body{{padding:12px 16px;display:none;}}
        .fold-card.open .fold-body{{display:block;}}
        .form-item{{margin-bottom:12px;}}
        .form-label{{font-size:14px;color:var(--text);margin-bottom:6px;display:block;}}
        .form-input{{width:100%;height:36px;padding:0 12px;border:1px solid var(--bd);border-radius:8px;outline:none;font-size:14px;}}
        .form-input:focus{{border-color:var(--c);box-shadow:0 0 0 2px rgba(22,119,255,.1);}}
        textarea.form-input{{height:auto;min-height:110px;resize:vertical;padding:10px 12px;}}
        .input-group{{display:flex;gap:8px;align-items:center;}}
        .inline-btn{{height:36px;padding:0 12px;background:var(--c);color:#fff;border:none;border-radius:8px;white-space:nowrap;}}
        .wave-item{{border:1px solid var(--bd);border-radius:8px;padding:10px 12px;margin-bottom:8px;}}
        .wave-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;}}
        .wave-del{{background:var(--danger);color:#fff;border:none;border-radius:6px;padding:2px 8px;font-size:12px;}}
        .tag-string{{background:var(--warning);color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;}}
        .tag-array{{background:var(--c);color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;}}
        .tag-object{{background:var(--success);color:#fff;padding:2px 6px;border-radius:4px;font-size:12px;}}
        .primary-btn{{background:var(--c);color:#fff;border:none;border-radius:8px;height:36px;padding:0 14px;}}
        .ghost-btn{{background:transparent;border:1px solid var(--bd);border-radius:8px;height:36px;padding:0 14px;color:var(--text);}}
        .modal{{position:fixed;inset:0;background:rgba(0,0,0,.5);display:flex;align-items:center;justify-content:center;z-index:999;}}
        .modal-box{{width:90%;max-width:380px;background:#fff;border-radius:12px;overflow:hidden;}}
        .modal-head{{padding:14px 16px;border-bottom:1px solid var(--bd);font-weight:500;}}
        .modal-body{{padding:16px;}}
        .modal-foot{{padding:12px 16px;display:flex;justify-content:flex-end;gap:8px;border-top:1px solid var(--bd);}}
        .window-controls {{ position: absolute; top: 16px; right: 16px; display: flex; gap: 8px; z-index: 9999; -webkit-app-region: no-drag; }}
        .win-btn {{ width: 24px; height: 24px; border-radius: 50%; border: none; cursor: pointer; transition: var(--transition-base); }}
        .win-btn.close {{ background: #EF4444; }}
        .win-btn:hover {{ opacity: 0.8; transform: scale(1.1); }}
    </style>
</head>
<body>
<div class="page">
<div class="window-controls">
        <button class="win-btn close" id="winClose"></button>
    </div>
    <div class="header"><i class="fa fa-sliders"></i> {self.plugin_name} </div>
    <div class="body">

        <!-- 常规配置 -->
        <div class="fold-card open">
            <div class="fold-head" onclick="toggleFold(this)">
                <span>常规配置</span>
                <i class="fa fa-chevron-down"></i>
            </div>
            <div class="fold-body">
                {normal}
            </div>
        </div>

        <!-- 波形配置 -->
        <div class="fold-card">
            <div class="fold-head" onclick="toggleFold(this)">
                <span>波形配置</span>
                <i class="fa fa-chevron-down"></i>
            </div>
            <div class="fold-body">
                {waveform}
            </div>
        </div>

    </div>
    <div class="footer">
        <button class="primary-btn" id="save">保存配置</button>
        <button class="ghost-btn" id="reset">重置配置</button>
        {gbtn}
    </div>
</div>

<script>
const plugin = "{self.plugin_name}";
const {{ ipcRenderer }} = require('electron');

document.getElementById('winClose').addEventListener('click', () => {{
    ipcRenderer.send('window:close');
}});
async function getPluginConfig(pluginName) {{
    try {{
        const response = await fetch('http://127.0.0.1:5000/plugin/config', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ plugin_name: pluginName }})
        }});
        const result = await response.json();
        return result.code === 200 ? result.msg : null;
    }} catch (error) {{
        console.error('获取插件配置出错:', error);
        return null;
    }}
}}

async function loadConfig() {{
    const cfg = await getPluginConfig(plugin);
    if (!cfg) return;

    document.querySelectorAll('[data-key^="p."]').forEach(el => {{
        const key = el.dataset.key.split('.')[1];
        if (cfg[key] !== undefined) {{
            el.value = cfg[key];
        }}
    }});

    document.querySelectorAll('select[data-key^="p."]').forEach(el => {{
        const key = el.dataset.key.split('.')[1];
        const val = cfg[key];
        if (val === undefined) return;
        for (let opt of el.options) {{
            if (opt.value == val || opt.textContent == val) {{
                opt.selected = true;
                break;
            }}
        }}
    }});
}}

function showLoading(){{
    const d=document.createElement("div");d.className="loading";d.innerText="处理中...";document.body.appendChild(d);return d;
}}
function hideLoading(l){{if(l)l.remove();}}

function toggleFold(el){{
    const p=el.closest(".fold-card");p.classList.toggle("open");
}}

function collect(){{
    const p={{}};
    document.querySelectorAll("[data-key^='p.']").forEach(e=>{{
        const k=e.dataset.key.split(".")[1];
        let v=e.value;
        if(e.type==="number")v=Number(v);
        if(e.tagName==="SELECT"&&e.innerText.includes("是"))v=e.value==="true";
        p[k]=v;
    }});
    const w={{}};
    document.querySelectorAll("[data-wave-key]").forEach(e=>{{
        const k=e.dataset.waveKey,f=e.dataset.format,v=e.value;
        if(f==="array")w[k]=v.split("\\n").map(i=>i.trim()).filter(Boolean);
        else if(f==="object")w[k]=JSON.parse(v);
        else w[k]=v;
    }});
    return {{plugins:p,waveform:w}};
}}

save.onclick=async()=>{{
    const l=showLoading();
    await fetch("http://127.0.0.1:5000/plugin/config/save",{{
        method:"POST",headers:{{"Content-Type":"application/json"}},
        body:JSON.stringify({{ plugin_name:plugin, config:collect() }})
    }});
    hideLoading(l);alert("保存成功");
}};

reset.onclick=async()=>{{
    if(!confirm("确定重置？"))return;
    const l=showLoading();
    await fetch("http://127.0.0.1:5000/plugin/config/reset",{{
        method:"POST",body:JSON.stringify({{ plugin_name:plugin }})
    }});
    hideLoading(l);location.reload();
}};

async function doNormalAction(action){{
    const l=showLoading();
    const res=await fetch("http://127.0.0.1:5000/plugin/"+plugin+"/"+action,{{
        method:"POST",body:JSON.stringify({{plugin:plugin,config:collect()}})
    }});
    const data=await res.json();
    hideLoading(l);alert(data.message||"成功");
}}

async function doFillAction(action,target){{
    const l=showLoading();
    const res=await fetch("http://127.0.0.1:5000/plugin/"+plugin+"/"+action,{{
        method:"POST",body:JSON.stringify({{plugin:plugin,config:collect()}})
    }});
    const data=await res.json();
    if(data.value!==undefined){{
        const inp=document.getElementById("input_"+target);
        if(inp)inp.value=data.value;
    }}
    hideLoading(l);alert(data.message||"成功");
}}

function addWaveModal(){{
    const m=document.createElement("div");m.className="modal";
    m.innerHTML=`<div class="modal-box">
        <div class="modal-head">添加波形</div>
        <div class="modal-body">
            <div class="form-item"><label class="form-label">波形名</label><input class="form-input" id="wn"></div>
            <div class="form-item"><label class="form-label">类型</label>
                <select class="form-input" id="wt">
                    <option value="string">字符串</option>
                    <option value="array">数组</option>
                    <option value="object">对象</option>
                </select>
            </div>
            <div class="form-item"><label class="form-label">内容</label><textarea class="form-input" id="wv" rows=4></textarea></div>
        </div>
        <div class="modal-foot">
            <button class="ghost-btn" onclick="this.closest('.modal').remove()">取消</button>
            <button class="primary-btn" onclick="addWave(this.closest('.modal'))">确认</button>
        </div>
    </div>`;
    document.body.appendChild(m);
}}

function addWave(m){{
    const n=document.getElementById("wn").value.trim();
    const t=document.getElementById("wt").value;
    const v=document.getElementById("wv").value;
    if(!n)return alert("请输入波形名");
    const list=document.getElementById("waves");
    const item=document.createElement("div");item.className="wave-item";
    const tag={{string:"tag-string",array:"tag-array",object:"tag-object"}}[t];
    item.innerHTML=`<div class="wave-header">
        <span>${{n}}</span>
        <span class="${{tag}}">${{t}}</span>
        <button class="wave-del" onclick="this.parentElement.parentElement.remove()">删除</button>
    </div>${{t==="string"?`<input data-wave-key="${{n}}" data-format="string" class="form-input" value="${{v}}">`:
    `<textarea data-wave-key="${{n}}" data-format="${{t}}" class="form-input">${{v}}</textarea>`}}`;
    list.appendChild(item);
    m.remove();
}}

window.addEventListener('DOMContentLoaded', loadConfig);
</script>
</body>
</html>'''