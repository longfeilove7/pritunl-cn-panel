#!/usr/lib/pritunl/usr/bin/python3
"""
Pritunl 中文管理面板 v2
每个用户独立session，正确处理CSRF和cookie
"""
import os, sys, json, time, io
import requests, urllib3
urllib3.disable_warnings()

from flask import Flask, request, jsonify, render_template_string, redirect, url_for, session, send_file

app = Flask(__name__)
app.secret_key = 'pritunl_cn_panel_secret_key_2026'

PRITUNL_URL = 'https://127.0.0.1:443'
LISTEN_PORT = 8443

# ====== API Client ======
class PritunlAPI:
    def login(self, username, password):
        s = requests.Session()
        s.verify = False
        resp = s.post(f'{PRITUNL_URL}/auth/session',
            json={'username': username, 'password': password})
        data = resp.json()
        if not data.get('authenticated'):
            return False, data.get('error_msg', '登录失败')
        # 保存cookie
        cookies = {}
        for c in s.cookies:
            cookies[c.name] = c.value
        session['pritunl_cookies'] = cookies
        # 获取CSRF token
        state_resp = s.get(f'{PRITUNL_URL}/state')
        if state_resp.status_code == 200:
            state = state_resp.json()
            session['pritunl_csrf'] = state.get('csrf_token', '')
        return True, data.get('default', False)
    
    def _make_session(self):
        s = requests.Session()
        s.verify = False
        cookies = session.get('pritunl_cookies', {})
        # 用cookie jar设置正确的域名和路径
        for name, value in cookies.items():
            s.cookies.set(name, value, domain='127.0.0.1', path='/')
        return s
    
    def req(self, method, path, data=None):
        s = self._make_session()
        csrf = session.get('pritunl_csrf', '')
        h = {'Content-Type': 'application/json', 'PR-Validated': 'true'}
        if csrf:
            h['Csrf-Token'] = csrf
        url = f'{PRITUNL_URL}{path}'
        r = s.request(method, url, headers=h, json=data)
        # 更新cookie
        new_cookies = dict(session.get('pritunl_cookies', {}))
        for c in s.cookies:
            new_cookies[c.name] = c.value
        session['pritunl_cookies'] = new_cookies
        return r
    
    def get(self, p): return self.req('GET', p)
    def post(self, p, d=None): return self.req('POST', p, d)
    def put(self, p, d=None): return self.req('PUT', p, d)
    def delete(self, p): return self.req('DELETE', p)

api = PritunlAPI()

def api_get(path):
    r = api.get(path)
    return r.json() if r.status_code == 200 else []

def api_post(path, data):
    r = api.post(path, data)
    return r.json() if r.status_code == 200 else None

def api_put(path, data=None):
    r = api.put(path, data)
    return r.json() if r.status_code == 200 else None

def api_del(path):
    r = api.delete(path)
    return r.status_code == 200

# ====== HTML模板 ======
BASE = '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VPN管理系统</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f0f2f5;color:#333;font-size:14px}
.top{background:linear-gradient(135deg,#1a1a2e,#16213e);color:#fff;padding:0 24px;height:54px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,.15)}
.top h1{font-size:17px;font-weight:600}
.top .info{display:flex;align-items:center;gap:14px}
.top .info a{color:#aab;text-decoration:none;font-size:13px}.top .info a:hover{color:#fff}
.tabs{background:#fff;border-bottom:1px solid #e8e8e8;padding:0 24px;display:flex;gap:0;justify-content:center}
.tabs a{padding:11px 18px;color:#666;text-decoration:none;font-size:13px;border-bottom:2px solid transparent;transition:all .15s}
.tabs a:hover{color:#1890ff;background:#f0f5ff}
.tabs a.on{color:#1890ff;border-bottom-color:#1890ff;font-weight:600}
.wrap{max-width:1100px;margin:16px auto;padding:0 20px}
.card{background:#fff;border-radius:8px;box-shadow:0 1px 2px rgba(0,0,0,.06);margin-bottom:14px}
.card-hd{padding:14px 18px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center}
.card-hd h2{font-size:15px;font-weight:600}
.card-bd{padding:16px 18px}
table{width:100%;border-collapse:collapse}
th,td{padding:9px 10px;text-align:left;border-bottom:1px solid #f0f0f0;font-size:13px}
th{background:#fafafa;font-weight:600;color:#888;font-size:11px;text-transform:uppercase}
tr:hover{background:#f8f9ff}
.tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600}
.tag-g{background:#e6fffb;color:#00a854;border:1px solid #b7eb8f}
.tag-r{background:#fff1f0;color:#f5222d;border:1px solid #ffa39e}
.tag-b{background:#e6f7ff;color:#1890ff;border:1px solid #91d5ff}
.tag-gray{background:#f5f5f5;color:#999;border:1px solid #d9d9d9}
.btn{display:inline-block;padding:5px 14px;border-radius:4px;font-size:12px;cursor:pointer;border:1px solid #d9d9d9;background:#fff;color:#333;text-decoration:none;transition:all .15s}
.btn:hover{border-color:#1890ff;color:#1890ff}
.btn-p{background:#1890ff;color:#fff;border-color:#1890ff}.btn-p:hover{background:#40a9ff}
.btn-d{background:#ff4d4f;color:#fff;border-color:#ff4d4f}.btn-d:hover{background:#ff7875}
.btn-g{background:#52c41a;color:#fff;border-color:#52c41a}.btn-g:hover{background:#73d13d}
.btn-s{padding:3px 10px;font-size:11px}
.btns{display:flex;gap:5px;flex-wrap:wrap}
.fg{margin-bottom:12px}
.fg label{display:block;margin-bottom:3px;font-weight:600;font-size:12px;color:#555}
.fg input,.fg select,.fg textarea{width:100%;padding:7px 10px;border:1px solid #d9d9d9;border-radius:4px;font-size:13px}
.fg input:focus,.fg select:focus{outline:none;border-color:#1890ff;box-shadow:0 0 0 2px rgba(24,144,255,.1)}
.fg .tip{font-size:11px;color:#aaa;margin-top:2px}
.mo{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.4);z-index:1000;justify-content:center;align-items:center}
.mo.show{display:flex}
.md{background:#fff;border-radius:8px;width:480px;max-height:80vh;overflow-y:auto;box-shadow:0 8px 24px rgba(0,0,0,.2)}
.md-hd{padding:14px 18px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center}
.md-hd h3{font-size:15px;font-weight:600}
.md-x{cursor:pointer;font-size:18px;color:#999;background:none;border:none}
.md-x:hover{color:#333}
.md-bd{padding:16px 18px}
.md-ft{padding:10px 18px;border-top:1px solid #f0f0f0;text-align:right;display:flex;gap:6px;justify-content:flex-end}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.sc{background:#fff;border-radius:8px;padding:16px;box-shadow:0 1px 2px rgba(0,0,0,.06);text-align:center}
.sc .n{font-size:28px;font-weight:700;color:#1890ff}
.sc .l{font-size:12px;color:#999;margin-top:2px}
.toast{position:fixed;top:16px;right:16px;padding:10px 16px;border-radius:4px;color:#fff;font-size:12px;z-index:2000;display:none;box-shadow:0 4px 12px rgba(0,0,0,.15)}
.toast-g{background:#52c41a}.toast-r{background:#ff4d4f}.show{display:block;animation:fi .3s}
@keyframes fi{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
.empty{text-align:center;padding:32px;color:#bbb}
</style></head><body>
<div class="top"><h1>🔐 VPN管理系统</h1><div class="info"><span>{{ cu }}</span><a href="/logout">退出</a></div></div>
<div class="tabs">
<a href="/" class="{{'on' if p=='d' else ''}}">📊 仪表盘</a>
<a href="/servers" class="{{'on' if p=='s' else ''}}">🖥️ 服务器</a>
<a href="/orgs" class="{{'on' if p=='o' else ''}}">🏢 组织</a>
<a href="/users" class="{{'on' if p=='u' else ''}}">👥 用户</a>
<a href="/hosts" class="{{'on' if p=='h' else ''}}">🖧 主机</a>
<a href="/links" class="{{'on' if p=='l' else ''}}">🔗 链接</a>
<a href="/devices" class="{{'on' if p=='dv' else ''}}">📱 设备</a>
<a href="/admins" class="{{'on' if p=='a' else ''}}">👤 管理员</a>
<a href="/settings" class="{{'on' if p=='cfg' else ''}}">⚙️ 设置</a>
</div>
<div class="wrap">{% block c %}{% endblock %}</div>
<div class="toast" id="toast"></div>
{% block m %}{% endblock %}
<script>
function toast(m,t){var e=document.getElementById('toast');e.textContent=m;e.className='toast toast-'+(t||'g')+' show';setTimeout(function(){e.className='toast'},3000)}
function mc(id){document.getElementById(id).classList.remove('show')}
function mo(id){document.getElementById(id).classList.add('show')}
function api(m,u,d,cb){var x=new XMLHttpRequest();x.open(m,u);x.setRequestHeader('Content-Type','application/json');x.onload=function(){try{cb(JSON.parse(x.responseText||'{}'))}catch(e){cb({})}};x.send(d?JSON.stringify(d):null)}
function cd(n,cb){if(confirm('确定删除 "'+n+'" 吗？'))cb()}
</script></body></html>'''

def R(tpl, **kw):
    kw['cu'] = session.get('user','')
    return render_template_string(BASE.replace('{% block c %}{% endblock %}', tpl), **kw)

# ====== 登录 ======
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        d = request.get_json(silent=True) or request.form
        ok, msg = api.login(d.get('username',''), d.get('password',''))
        if ok:
            session['user'] = d.get('username','')
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': str(msg)}), 401
    return '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>登录</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:-apple-system,sans-serif}
.b{background:#fff;border-radius:12px;padding:36px;width:360px;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.b h1{text-align:center;margin-bottom:6px;font-size:22px}.b p{text-align:center;color:#999;margin-bottom:20px;font-size:13px}
.fg{margin-bottom:14px}.fg label{display:block;margin-bottom:4px;font-weight:600;font-size:12px}
.fg input{width:100%;padding:9px 11px;border:1px solid #d9d9d9;border-radius:6px;font-size:13px}
.fg input:focus{outline:none;border-color:#667eea;box-shadow:0 0 0 2px rgba(102,126,234,.1)}
.btn{width:100%;padding:11px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer}
.btn:hover{opacity:.9}.err{color:#ff4d4f;font-size:12px;text-align:center;margin-top:10px;display:none}
</style></head><body><div class="b"><h1>🔐 VPN管理系统</h1><p>管理员登录</p>
<div class="fg"><label>用户名</label><input id="u" autofocus></div>
<div class="fg"><label>密码</label><input id="p" type="password" onkeydown="if(event.key==='Enter')go()"></div>
<button class="btn" onclick="go()">登 录</button><div class="err" id="e"></div></div>
<script>function go(){var u=document.getElementById('u').value,p=document.getElementById('p').value;
if(!u||!p){document.getElementById('e').textContent='请输入用户名和密码';document.getElementById('e').style.display='block';return}
var x=new XMLHttpRequest();x.open('POST','/login');x.setRequestHeader('Content-Type','application/json');
x.onload=function(){var d=JSON.parse(x.responseText);if(d.success)location.href='/';else{document.getElementById('e').textContent=d.error||'登录失败';document.getElementById('e').style.display='block'}};
x.send(JSON.stringify({username:u,password:p}))}</script></body></html>'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def login_req(f):
    from functools import wraps
    @wraps(f)
    def w(*a, **k):
        if 'user' not in session: return redirect('/login')
        return f(*a, **k)
    return w

# ====== 仪表盘 ======
@app.route('/')
@login_req
def dash():
    sv = api_get('/server')
    org = api_get('/organization')
    nu = 0; nr = 0
    ss = sv if isinstance(sv, list) else []
    for s in ss:
        if s.get('status')=='running': nr += 1
    for o in (org if isinstance(org, list) else []):
        ud = api_get(f'/user/{o["id"]}')
        if isinstance(ud, dict): nu += len(ud.get('users',[]))
        elif isinstance(ud, list): nu += len(ud)
    return R('''
<div class="stats">
<div class="sc"><div class="n">{{ ns }}</div><div class="l">服务器</div></div>
<div class="sc"><div class="n" style="color:#52c41a">{{ nr }}</div><div class="l">运行中</div></div>
<div class="sc"><div class="n" style="color:#722ed1">{{ no }}</div><div class="l">组织</div></div>
<div class="sc"><div class="n" style="color:#fa8c16">{{ nu }}</div><div class="l">用户</div></div>
</div>
<div class="card"><div class="card-hd"><h2>服务器</h2><a href="/servers" class="btn btn-s">全部</a></div>
<div class="card-bd"><table><tr><th>名称</th><th>端口</th><th>协议</th><th>状态</th><th>操作</th></tr>
{% for s in ss %}<tr><td><b>{{ s.name }}</b></td><td>{{ s.port }}</td><td>{{ s.protocol|upper }}</td>
<td>{% if s.status=='running'%}<span class="tag tag-g">运行中</span>{%else%}<span class="tag tag-r">已停止</span>{%endif%}</td>
<td class="btns">{% if s.status=='running'%}
<button class="btn btn-s btn-d" onclick="api('PUT','/api/sv/{{s._id}}/stop',null,function(){location.reload()})">停止</button>
{%else%}<button class="btn btn-s btn-g" onclick="api('PUT','/api/sv/{{s._id}}/start',null,function(){location.reload()})">启动</button>{%endif%}</td></tr>
{%endfor%}{%if not ss%}<tr><td colspan="5" class="empty">暂无服务器</td></tr>{%endif%}</table></div></div>
''', p='d', ns=len(ss), nr=nr, no=len(org) if isinstance(org,list) else 0, nu=nu, ss=ss)

# ====== 服务器 ======
@app.route('/servers')
@login_req
def sv_page():
    sv = api_get('/server')
    ss = sv if isinstance(sv, list) else []
    return R('''
<div class="card"><div class="card-hd"><h2>🖥️ 服务器管理</h2>
<button class="btn btn-p" onclick="mo('addS')">+ 添加服务器</button></div>
<div class="card-bd"><table><tr><th>名称</th><th>端口</th><th>协议</th><th>网络</th><th>状态</th><th>操作</th></tr>
{%for s in ss%}<tr><td><b>{{s.name}}</b></td><td>{{s.port}}</td><td>{{s.protocol|upper}}</td><td>{{s.network}}</td>
<td>{%if s.status=='running'%}<span class="tag tag-g">运行中</span>{%else%}<span class="tag tag-r">已停止</span>{%endif%}</td>
<td class="btns">{%if s.status=='running'%}
<button class="btn btn-s btn-d" onclick="api('PUT','/api/sv/{{s._id}}/stop',null,function(){location.reload()})">停止</button>
<button class="btn btn-s" onclick="api('PUT','/api/sv/{{s._id}}/restart',null,function(){toast('已重启')})">重启</button>
{%else%}<button class="btn btn-s btn-g" onclick="api('PUT','/api/sv/{{s._id}}/start',null,function(){location.reload()})">启动</button>{%endif%}
<a href="/sv/{{s._id}}" class="btn btn-s">设置</a>
<button class="btn btn-s btn-d" onclick="cd('{{s.name}}',function(){api('DELETE','/api/sv/{{s._id}}',null,function(){location.reload()})})">删除</button></td></tr>
{%endfor%}{%if not ss%}<tr><td colspan="6" class="empty">暂无服务器</td></tr>{%endif%}</table></div></div>
<div class="mo" id="addS"><div class="md"><div class="md-hd"><h3>添加服务器</h3><button class="md-x" onclick="mc('addS')">&times;</button></div>
<div class="md-bd">
<div class="fg"><label>名称</label><input id="sn" placeholder="如：公司VPN"></div>
<div class="fg"><label>端口</label><input id="sp" type="number" value="1194"><div class="tip">每个服务器不同端口</div></div>
<div class="fg"><label>协议</label><select id="sc"><option value="udp">UDP（推荐）</option><option value="tcp">TCP</option></select></div>
<div class="fg"><label>虚拟网络</label><input id="snet" placeholder="留空自动生成"><div class="tip">如 10.51.0.0/24</div></div>
<div class="fg"><label>加密算法</label><select id="scipher"><option value="aes256">AES-256（推荐）</option><option value="aes128">AES-128</option><option value="chacha20poly1205">ChaCha20</option></select></div>
<div class="fg"><label>DNS</label><input id="sdns" value="114.114.114.114, 8.8.8.8"></div>
</div><div class="md-ft"><button class="btn" onclick="mc('addS')">取消</button>
<button class="btn btn-p" onclick="addS()">创建</button></div></div></div>
<script>function addS(){var d={name:document.getElementById('sn').value,port:parseInt(document.getElementById('sp').value),protocol:document.getElementById('sc').value,dns_server:document.getElementById('sdns').value,cipher:document.getElementById('scipher').value,hash:'sha256'};
var n=document.getElementById('snet').value;if(n)d.network=n;
api('POST','/api/sv',d,function(r){if(r._id)location.reload();else alert('创建失败: '+JSON.stringify(r))})}</script>
''', p='s', ss=ss)

# ====== 服务器详情 ======
@app.route('/sv/<sid>')
@login_req
def sv_detail(sid):
    sv = api_get(f'/server/{sid}')
    if not sv: return redirect('/servers')
    rt = api_get(f'/server/{sid}/route')
    so = api_get(f'/server/{sid}/organization')
    ao = api_get('/organization')
    bw = api_get(f'/server/{sid}/bandwidth/1')
    return R('''
<div class="card"><div class="card-hd"><h2>🖥️ {{sv.name}}</h2><div class="btns">
{%if sv.status=='running'%}<button class="btn btn-s btn-d" onclick="api('PUT','/api/sv/{{sv._id}}/stop',null,function(){location.reload()})">停止</button>
{%else%}<button class="btn btn-s btn-g" onclick="api('PUT','/api/sv/{{sv._id}}/start',null,function(){location.reload()})">启动</button>{%endif%}
<a href="/sv/{{sv._id}}/output" class="btn btn-s">📋 日志</a>
<a href="/servers" class="btn btn-s">返回</a></div></div>
<div class="card-bd"><div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
<div><h3 style="margin-bottom:10px">基本信息</h3>
<div class="fg"><label>名称</label><input id="dn" value="{{sv.name}}"></div>
<div class="fg"><label>端口</label><input id="dp" type="number" value="{{sv.port}}"></div>
<div class="fg"><label>协议</label><select id="dc"><option value="udp" {{'selected' if sv.protocol=='udp'}}>UDP</option><option value="tcp" {{'selected' if sv.protocol=='tcp'}}>TCP</option></select></div>
<div class="fg"><label>虚拟网络</label><input id="dnet" value="{{sv.network}}"></div>
<div class="fg"><label>DNS</label><input id="ddns" value="{{sv.dns_server or '114.114.114.114, 8.8.8.8'}}"></div>
<div class="fg"><label>Google验证器</label><select id="dotp"><option value="true" {{'selected' if sv.otp_auth}}>启用</option><option value="false" {{'selected' if not sv.otp_auth}}>禁用</option></select></div>
<div class="fg"><label>加密算法</label><select id="dcipher">
<option value="none" {{'selected' if sv.cipher=='none'}}>无</option>
<option value="bf128" {{'selected' if sv.cipher=='bf128'}}>BF-128</option>
<option value="bf256" {{'selected' if sv.cipher=='bf256'}}>BF-256</option>
<option value="aes128" {{'selected' if sv.cipher=='aes128'}}>AES-128</option>
<option value="aes192" {{'selected' if sv.cipher=='aes192'}}>AES-192</option>
<option value="aes256" {{'selected' if sv.cipher=='aes256'}}>AES-256</option>
<option value="chacha20poly1205" {{'selected' if sv.cipher=='chacha20poly1205'}}>ChaCha20</option>
</select></div>
<div class="fg"><label>哈希算法</label><select id="dhash">
<option value="sha1" {{'selected' if sv.hash=='sha1'}}>SHA1</option>
<option value="sha256" {{'selected' if sv.hash=='sha256'}}>SHA256</option>
<option value="sha384" {{'selected' if sv.hash=='sha384'}}>SHA384</option>
<option value="sha512" {{'selected' if sv.hash=='sha512'}}>SHA512</option>
</select></div>
<div class="fg"><label>DH参数</label><select id="ddh">
<option value="" {{'selected' if not sv.dh_param_bits}}>默认</option>
<option value="1536" {{'selected' if sv.dh_param_bits==1536}}>1536</option>
<option value="2048" {{'selected' if sv.dh_param_bits==2048}}>2048</option>
<option value="4096" {{'selected' if sv.dh_param_bits==4096}}>4096</option>
</select></div>
<div class="fg"><label>Ping间隔(秒)</label><input id="dpinterval" type="number" value="{{sv.ping_interval or 10}}"></div>
<div class="fg"><label>Ping超时(秒)</label><input id="dptimeout" type="number" value="{{sv.ping_timeout or 60}}"></div>
<div class="fg"><label>会话超时(秒)</label><input id="dstimeout" type="number" value="{{sv.session_timeout or 0}}"><div class="tip">0表示不超时</div></div>
<div class="fg"><label>最大客户端数</label><input id="dmaxclients" type="number" value="{{sv.max_clients or 0}}"><div class="tip">0表示不限制</div></div>
<div class="fg"><label>日志详细程度</label><select id="dloglevel">
<option value="1" {{'selected' if sv.verb==1}}>1 - 基本</option>
<option value="2" {{'selected' if sv.verb==2}}>2 - 正常</option>
<option value="3" {{'selected' if sv.verb==3}}>3 - 详细</option>
<option value="4" {{'selected' if sv.verb==4}}>4 - 调试</option>
</select></div>
<div class="fg"><label>Inter-Client通信</label><select id="dinterop"><option value="true" {{'selected' if sv.inter_client}}>允许</option><option value="false" {{'selected' if not sv.inter_client}}>禁止</option></select></div>
<div class="fg"><label>客户端到客户端</label><select id="dc2c"><option value="true" {{'selected' if sv.client_to_client}}>允许</option><option value="false" {{'selected' if not sv.client_to_client}}>禁止</option></select></div>
<div class="fg"><label>绑定地址</label><input id="dbindaddr" value="{{sv.bind_address or ''}}"><div class="tip">留空则绑定所有</div></div>
<div class="fg"><label>Network Gateway</label><input id="dngw" value="{{sv.network_gateway or ''}}"></div>
<h3 style="margin:16px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">🔒 WireGuard配置</h3>
<div class="fg"><label>WireGuard</label><select id="dwgen"><option value="true" {{'selected' if sv.wireguard}}>启用</option><option value="false" {{'selected' if not sv.wireguard}}>禁用</option></select></div>
<div class="fg"><label>WG端口</label><input id="dwgport" type="number" value="{{sv.wg_port or ''}}"><div class="tip">留空自动分配</div></div>
<div class="fg"><label>WG网络</label><input id="dwgnet" value="{{sv.wg_network or ''}}"><div class="tip">如 10.55.0.0/24，留空自动生成</div></div>
<h3 style="margin:16px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">🛡️ 动态防火墙</h3>
<div class="fg"><label>动态防火墙</label><select id="ddfw"><option value="true" {{'selected' if sv.dynamic_firewall}}>启用</option><option value="false" {{'selected' if not sv.dynamic_firewall}}>禁用</option></select><div class="tip">自动根据连接状态调整防火墙规则</div></div>
<button class="btn btn-p" onclick="saveS()">保存</button></div>
<div><h3 style="margin-bottom:10px">已绑定组织</h3>
<table><tr><th>组织</th><th>操作</th></tr>{%for o in so%}<tr><td>{{o.name}}</td><td>
<button class="btn btn-s btn-d" onclick="api('DELETE','/api/sv/{{sv._id}}/org/{{o._id}}',null,function(){location.reload()})">解绑</button></td></tr>
{%endfor%}{%if not so%}<tr><td colspan="2" class="empty">未绑定</td></tr>{%endif%}</table>
<h3 style="margin:14px 0 10px">绑定组织</h3>
<select id="ao" style="padding:5px;border:1px solid #d9d9d9;border-radius:4px;width:180px">{%for o in ao%}<option value="{{o._id}}">{{o.name}}</option>{%endfor%}</select>
<button class="btn btn-s btn-p" onclick="api('PUT','/api/sv/{{sv._id}}/org/'+document.getElementById('ao').value,null,function(){location.reload()})">绑定</button>
</div></div>
<h3 style="margin:16px 0 10px">路由</h3>
<table><tr><th>网络</th><th>NAT</th><th>操作</th></tr>{%for r in rt%}<tr><td>{{r.network}}</td><td>{{'是' if r.nat else '否'}}</td>
<td><button class="btn btn-s btn-d" onclick="api('DELETE','/api/sv/{{sv._id}}/rt/{{r.network}}',null,function(){location.reload()})">删除</button></td></tr>
{%endfor%}{%if not rt%}<tr><td colspan="3" class="empty">暂无路由</td></tr>{%endif%}</table>
<div style="margin-top:10px;display:flex;gap:6px"><input id="nr" placeholder="如: 192.168.33.0/24" style="padding:5px;border:1px solid #d9d9d9;border-radius:4px;width:220px">
<button class="btn btn-s btn-p" onclick="api('POST','/api/sv/{{sv._id}}/rt',{network:document.getElementById('nr').value,nat:true},function(){location.reload()})">添加</button></div>
<h3 style="margin:16px 0 10px">📊 带宽监控</h3>
<div style="margin-bottom:8px"><select id="bwperiod" onchange="loadBW()" style="padding:5px;border:1px solid #d9d9d9;border-radius:4px">
<option value="1">最近1小时</option><option value="6">最近6小时</option><option value="24">最近24小时</option><option value="168">最近7天</option></select></div>
<div id="bwinfo" style="font-size:12px;color:#666">
{%if bw and bw is mapping%}
<table><tr><th>指标</th><th>数值</th></tr>
{%for k,v in bw.items()%}<tr><td>{{k}}</td><td>{{v}}</td></tr>{%endfor%}</table>
{%elif bw and bw is sequence%}
<table><tr><th>时间</th><th>接收</th><th>发送</th></tr>
{%for b in bw[-20:]%}<tr><td>{{b.get('timestamp','')}}</td><td>{{b.get('bytes_recv','')}}</td><td>{{b.get('bytes_sent','')}}</td></tr>{%endfor%}</table>
{%else%}<p>暂无带宽数据</p>{%endif%}</div>
</div></div>
<script>function loadBW(){var p=document.getElementById('bwperiod').value;api('GET','/api/sv/{{sv._id}}/bw/'+p,null,function(r){var el=document.getElementById('bwinfo');if(!r||(!Array.isArray(r)&&typeof r!=='object')){el.innerHTML='<p>暂无数据</p>';return}if(Array.isArray(r)){var h='<table><tr><th>时间</th><th>接收</th><th>发送</th></tr>';r.slice(-20).forEach(function(b){h+='<tr><td>'+(b.timestamp||'')+'</td><td>'+(b.bytes_recv||0)+'</td><td>'+(b.bytes_sent||0)+'</td></tr>'});h+='</table>';el.innerHTML=h}else{var h='<table><tr><th>指标</th><th>数值</th></tr>';for(var k in r)h+='<tr><td>'+k+'</td><td>'+r[k]+'</td></tr>';h+='</table>';el.innerHTML=h}})}
function saveS(){var dhv=document.getElementById('ddh').value;var d={name:document.getElementById('dn').value,port:parseInt(document.getElementById('dp').value),protocol:document.getElementById('dc').value,network:document.getElementById('dnet').value,dns_server:document.getElementById('ddns').value,otp_auth:document.getElementById('dotp').value==='true',cipher:document.getElementById('dcipher').value,hash:document.getElementById('dhash').value,ping_interval:parseInt(document.getElementById('dpinterval').value),ping_timeout:parseInt(document.getElementById('dptimeout').value),session_timeout:parseInt(document.getElementById('dstimeout').value),max_clients:parseInt(document.getElementById('dmaxclients').value),verb:parseInt(document.getElementById('dloglevel').value),inter_client:document.getElementById('dinterop').value==='true',client_to_client:document.getElementById('dc2c').value==='true',bind_address:document.getElementById('dbindaddr').value||null,network_gateway:document.getElementById('dngw').value||null,wireguard:document.getElementById('dwgen').value==='true',dynamic_firewall:document.getElementById('ddfw').value==='true'};if(dhv)d.dh_param_bits=parseInt(dhv);var wgport=document.getElementById('dwgport').value;if(wgport)d.wg_port=parseInt(wgport);var wgnet=document.getElementById('dwgnet').value;if(wgnet)d.wg_network=wgnet;api('PUT','/api/sv/{{sv._id}}',d,function(){toast('已保存')})}</script>
''', p='s', sv=sv, rt=rt if isinstance(rt,list) else [], so=so if isinstance(so,list) else [], ao=ao if isinstance(ao,list) else [], bw=bw)

# ====== 组织 ======
@app.route('/orgs')
@login_req
def orgs_page():
    org = api_get('/organization')
    ol = org if isinstance(org, list) else []
    return R('''
<div class="card"><div class="card-hd"><h2>🏢 组织管理</h2>
<button class="btn btn-p" onclick="mo('addO')">+ 添加组织</button></div>
<div class="card-bd"><table><tr><th>名称</th><th>操作</th></tr>
{%for o in ol%}<tr><td><b>{{o.name}}</b></td><td class="btns">
<a href="/org/{{o._id}}" class="btn btn-s">用户</a>
<button class="btn btn-s btn-d" onclick="cd('{{o.name}}',function(){api('DELETE','/api/org/{{o._id}}',null,function(){location.reload()})})">删除</button></td></tr>
{%endfor%}{%if not ol%}<tr><td colspan="2" class="empty">暂无组织</td></tr>{%endif%}</table></div></div>
<div class="mo" id="addO"><div class="md"><div class="md-hd"><h3>添加组织</h3><button class="md-x" onclick="mc('addO')">&times;</button></div>
<div class="md-bd"><div class="fg"><label>名称</label><input id="on" placeholder="如：技术部"></div></div>
<div class="md-ft"><button class="btn" onclick="mc('addO')">取消</button>
<button class="btn btn-p" onclick="api('POST','/api/org',{name:document.getElementById('on').value},function(r){if(r._id)location.reload();else alert('失败')})">创建</button></div></div></div>
''', p='o', ol=ol)

# ====== 组织用户 ======
@app.route('/org/<oid>')
@login_req
def org_users(oid):
    org = api_get(f'/organization/{oid}')
    ud = api_get(f'/user/{oid}')
    ul = ud.get('users',ud) if isinstance(ud,dict) else (ud if isinstance(ud,list) else [])
    return R('''
<div class="card"><div class="card-hd"><h2>👥 {{org.name}} - 用户</h2><div class="btns">
<button class="btn btn-p" onclick="mo('addU')">+ 添加用户</button>
<a href="/org/{{oid}}/bulk" class="btn">📋 批量添加</a>
<a href="/org/{{oid}}/email" class="btn">📧 发送邮件</a>
<a href="/orgs" class="btn btn-s">返回</a></div></div>
<div class="card-bd"><table><tr><th>用户名</th><th>邮箱</th><th>状态</th><th>分组</th><th>操作</th></tr>
{%for u in ul%}<tr><td><b>{{u.name}}</b></td><td>{{u.email or '-'}}</td>
<td>{%if u.disabled%}<span class="tag tag-gray">禁用</span>{%else%}<span class="tag tag-g">启用</span>{%endif%}</td>
<td>{{(u.groups|join(', ')) if u.groups else '-'}}</td>
<td class="btns"><a href="/usr/{{oid}}/{{u._id}}" class="btn btn-s">详情</a>
<a href="/data/{{oid}}/{{u._id}}.tar" class="btn btn-s">下载配置</a>
<button class="btn btn-s" onclick="api('PUT','/api/usr/{{oid}}/{{u._id}}',{disabled:{{'false' if u.disabled else 'true'}}},function(){location.reload()})">{{'启用' if u.disabled else '禁用'}}</button>
<button class="btn btn-s btn-d" onclick="cd('{{u.name}}',function(){api('DELETE','/api/usr/{{oid}}/{{u._id}}',null,function(){location.reload()})})">删除</button></td></tr>
{%endfor%}{%if not ul%}<tr><td colspan="5" class="empty">暂无用户</td></tr>{%endif%}</table></div></div>
<div class="mo" id="addU"><div class="md"><div class="md-hd"><h3>添加用户</h3><button class="md-x" onclick="mc('addU')">&times;</button></div>
<div class="md-bd">
<div class="fg"><label>用户名</label><input id="un" placeholder="如：zhangsan"></div>
<div class="fg"><label>邮箱</label><input id="ue" placeholder="选填"></div>
<div class="fg"><label>PIN码</label><input id="up" placeholder="选填，连接时需要"></div>
<div class="fg"><label>分组</label><input id="ug" placeholder="多个逗号分隔"><div class="tip">用于服务器访问控制</div></div>
</div><div class="md-ft"><button class="btn" onclick="mc('addU')">取消</button>
<button class="btn btn-p" onclick="addU()">创建</button></div></div></div>
<script>function addU(){var d={name:document.getElementById('un').value};
var e=document.getElementById('ue').value;if(e)d.email=e;
var p=document.getElementById('up').value;if(p)d.pin=p;
var g=document.getElementById('ug').value;if(g)d.groups=g.split(',').map(function(x){return x.trim()});
api('POST','/api/usr/{{oid}}',d,function(r){if(r&&r.name)location.reload();else alert('失败')})}</script>
''', p='u', org=org, ul=ul, oid=oid)

# ====== 全部用户 ======
@app.route('/users')
@login_req
def users_all():
    org = api_get('/organization')
    all_u = []
    for o in (org if isinstance(org,list) else []):
        ud = api_get(f'/user/{o["id"]}')
        ul = ud.get('users',ud) if isinstance(ud,dict) else (ud if isinstance(ud,list) else [])
        for u in ul:
            u['_oid'] = o['id']; u['_on'] = o['name']
            all_u.append(u)
    return R('''
<div class="card"><div class="card-hd"><h2>👥 全部用户</h2></div>
<div class="card-bd"><table><tr><th>用户名</th><th>组织</th><th>邮箱</th><th>状态</th><th>操作</th></tr>
{%for u in ul%}<tr><td><b>{{u.name}}</b></td><td>{{u._on}}</td><td>{{u.email or '-'}}</td>
<td>{%if u.disabled%}<span class="tag tag-gray">禁用</span>{%else%}<span class="tag tag-g">启用</span>{%endif%}</td>
<td class="btns"><a href="/usr/{{u._oid}}/{{u._id}}" class="btn btn-s">详情</a>
<a href="/data/{{u._oid}}/{{u._id}}.tar" class="btn btn-s">下载配置</a>
<button class="btn btn-s btn-d" onclick="cd('{{u.name}}',function(){api('DELETE','/api/usr/{{u._oid}}/{{u._id}}',null,function(){location.reload()})})">删除</button></td></tr>
{%endfor%}{%if not ul%}<tr><td colspan="5" class="empty">暂无用户</td></tr>{%endif%}</table></div></div>
''', p='u', ul=all_u)

# ====== 设置 ======
@app.route('/settings')
@login_req
def settings_page():
    cfg = api_get('/settings')
    return R('''
<div class="card"><div class="card-hd"><h2>⚙️ 设置</h2></div><div class="card-bd">
<div style="display:flex;gap:10px;margin-bottom:16px">
<a href="/logs" class="btn btn-s">📋 系统日志</a>
<a href="/audit" class="btn btn-s">🔍 审计日志</a>
</div>
<div class="fg"><label>SSO认证</label><select id="sso"><option value="true" {{'selected' if cfg and cfg.sso}}>启用</option><option value="false" {{'selected' if not cfg or not cfg.sso}}>禁用</option></select></div>
<div class="fg"><label>域名</label><input id="sdomain" value="{{cfg.server_domain if cfg and cfg.server_domain else ''}}"><div class="tip">用于生成客户端配置URL</div></div>
<div class="fg"><label>邮件服务器(SMTP)</label><input id="ssmtp" value="{{cfg.email_smtp_server if cfg and cfg.email_smtp_server else ''}}"></div>
<div class="fg"><label>SMTP端口</label><input id="ssmtpport" type="number" value="{{cfg.email_smtp_port if cfg and cfg.email_smtp_port else 587}}"></div>
<div class="fg"><label>SMTP用户名</label><input id="ssmtpuser" value="{{cfg.email_smtp_username if cfg and cfg.email_smtp_username else ''}}"></div>
<div class="fg"><label>SMTP密码</label><input id="ssmtppass" type="password" value="{{cfg.email_smtp_password if cfg and cfg.email_smtp_password else ''}}"></div>
<div class="fg"><label>发件人地址</label><input id="sfrom" value="{{cfg.email_from if cfg and cfg.email_from else ''}}"></div>
<button class="btn btn-p" onclick="saveCfg()">保存设置</button>
</div></div>
<div class="card"><div class="card-hd"><h2>🔒 Let\'s Encrypt SSL证书</h2></div><div class="card-bd">
<div class="fg"><label>域名</label><input id="ledomain" value="{{cfg.lets_encrypt_domain if cfg and cfg.lets_encrypt_domain else ''}}"><div class="tip">用于自动申请SSL证书，如 vpn.example.com</div></div>
<button class="btn btn-p" onclick="saveLE()">保存</button>
</div></div>
<div class="card"><div class="card-hd"><h2>🔑 单点登录(SSO)配置</h2></div><div class="card-bd">
<h3 style="margin-bottom:10px">SAML</h3>
<div class="fg"><label>SAML SSO URL</label><input id="saml_sso_url" value="{{cfg.saml_sso_url if cfg and cfg.saml_sso_url else ''}}"></div>
<div class="fg"><label>SAML Issuer URL</label><input id="saml_issuer_url" value="{{cfg.saml_issuer_url if cfg and cfg.saml_issuer_url else ''}}"></div>
<div class="fg"><label>SAML Certificate (Base64)</label><textarea id="saml_cert" rows="3">{{cfg.saml_cert if cfg and cfg.saml_cert else ''}}</textarea></div>
<div class="fg"><label>SAML Audience URL</label><input id="saml_audience_url" value="{{cfg.saml_audience_url if cfg and cfg.saml_audience_url else ''}}"></div>
<h3 style="margin:14px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">Google Workspace</h3>
<div class="fg"><label>Google Client ID</label><input id="google_client_id" value="{{cfg.google_client_id if cfg and cfg.google_client_id else ''}}"></div>
<div class="fg"><label>Google Client Secret</label><input id="google_client_secret" type="password" value="{{cfg.google_client_secret if cfg and cfg.google_client_secret else ''}}"></div>
<h3 style="margin:14px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">Azure AD</h3>
<div class="fg"><label>Azure Client ID</label><input id="azure_client_id" value="{{cfg.azure_client_id if cfg and cfg.azure_client_id else ''}}"></div>
<div class="fg"><label>Azure Client Secret</label><input id="azure_client_secret" type="password" value="{{cfg.azure_client_secret if cfg and cfg.azure_client_secret else ''}}"></div>
<h3 style="margin:14px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">OneLogin</h3>
<div class="fg"><label>OneLogin Client ID</label><input id="onelogin_client_id" value="{{cfg.onelogin_client_id if cfg and cfg.onelogin_client_id else ''}}"></div>
<div class="fg"><label>OneLogin Client Secret</label><input id="onelogin_client_secret" type="password" value="{{cfg.onelogin_client_secret if cfg and cfg.onelogin_client_secret else ''}}"></div>
<h3 style="margin:14px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">Okta</h3>
<div class="fg"><label>Okta Client ID</label><input id="okta_client_id" value="{{cfg.okta_client_id if cfg and cfg.okta_client_id else ''}}"></div>
<div class="fg"><label>Okta Client Secret</label><input id="okta_client_secret" type="password" value="{{cfg.okta_client_secret if cfg and cfg.okta_client_secret else ''}}"></div>
<h3 style="margin:14px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">Duo</h3>
<div class="fg"><label>Duo Integration Key</label><input id="duo_ikey" value="{{cfg.duo_ikey if cfg and cfg.duo_ikey else ''}}"></div>
<div class="fg"><label>Duo Secret Key</label><input id="duo_skey" type="password" value="{{cfg.duo_skey if cfg and cfg.duo_skey else ''}}"></div>
<div class="fg"><label>Duo API Hostname</label><input id="duo_host" value="{{cfg.duo_host if cfg and cfg.duo_host else ''}}"></div>
<h3 style="margin:14px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">JumpCloud</h3>
<div class="fg"><label>JumpCloud Client ID</label><input id="jumpcloud_client_id" value="{{cfg.jumpcloud_client_id if cfg and cfg.jumpcloud_client_id else ''}}"></div>
<div class="fg"><label>JumpCloud Client Secret</label><input id="jumpcloud_client_secret" type="password" value="{{cfg.jumpcloud_client_secret if cfg and cfg.jumpcloud_client_secret else ''}}"></div>
<h3 style="margin:14px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">Radius</h3>
<div class="fg"><label>Radius Server</label><input id="radius_server" value="{{cfg.radius_server if cfg and cfg.radius_server else ''}}"></div>
<div class="fg"><label>Radius Secret</label><input id="radius_secret" type="password" value="{{cfg.radius_secret if cfg and cfg.radius_secret else ''}}"></div>
<button class="btn btn-p" onclick="saveSSO()">保存SSO配置</button>
</div></div>
<script>function saveCfg(){api('PUT','/api/settings',{sso:document.getElementById('sso').value==='true',server_domain:document.getElementById('sdomain').value,email_smtp_server:document.getElementById('ssmtp').value,email_smtp_port:parseInt(document.getElementById('ssmtpport').value)||587,email_smtp_username:document.getElementById('ssmtpuser').value,email_smtp_password:document.getElementById('ssmtppass').value,email_from:document.getElementById('sfrom').value},function(r){if(r)toast('已保存');else toast('保存失败','r')})}
function saveLE(){api('PUT','/api/settings',{lets_encrypt_domain:document.getElementById('ledomain').value},function(r){if(r)toast('已保存');else toast('保存失败','r')})}
function saveSSO(){var d={saml_sso_url:document.getElementById('saml_sso_url').value,saml_issuer_url:document.getElementById('saml_issuer_url').value,saml_cert:document.getElementById('saml_cert').value,saml_audience_url:document.getElementById('saml_audience_url').value,google_client_id:document.getElementById('google_client_id').value,google_client_secret:document.getElementById('google_client_secret').value,azure_client_id:document.getElementById('azure_client_id').value,azure_client_secret:document.getElementById('azure_client_secret').value,onelogin_client_id:document.getElementById('onelogin_client_id').value,onelogin_client_secret:document.getElementById('onelogin_client_secret').value,okta_client_id:document.getElementById('okta_client_id').value,okta_client_secret:document.getElementById('okta_client_secret').value,duo_ikey:document.getElementById('duo_ikey').value,duo_skey:document.getElementById('duo_skey').value,duo_host:document.getElementById('duo_host').value,jumpcloud_client_id:document.getElementById('jumpcloud_client_id').value,jumpcloud_client_secret:document.getElementById('jumpcloud_client_secret').value,radius_server:document.getElementById('radius_server').value,radius_secret:document.getElementById('radius_secret').value};api('PUT','/api/settings',d,function(r){if(r)toast('SSO配置已保存');else toast('保存失败','r')})}</script>
''', p='cfg', cfg=cfg)

# ====== API代理 ======
@app.route('/api/org', methods=['POST'])
@login_req
def api_org_c():
    r = api.post('/organization', request.json)
    return r.json() if r.status_code==200 else jsonify({'error':r.text}), r.status_code

@app.route('/api/org/<oid>', methods=['DELETE'])
@login_req
def api_org_d(oid):
    return jsonify({'ok': api.delete(f'/organization/{oid}').status_code==200})

@app.route('/api/usr/<oid>', methods=['POST'])
@login_req
def api_usr_c(oid):
    r = api.post(f'/user/{oid}', request.json)
    return r.json() if r.status_code==200 else jsonify({'error':r.text}), r.status_code

@app.route('/api/usr/<oid>/<uid>', methods=['PUT'])
@login_req
def api_usr_u(oid, uid):
    r = api.put(f'/user/{oid}/{uid}', request.json)
    return r.json() if r.status_code==200 else jsonify({'error':r.text}), r.status_code

@app.route('/api/usr/<oid>/<uid>', methods=['DELETE'])
@login_req
def api_usr_d(oid, uid):
    return jsonify({'ok': api.delete(f'/user/{oid}/{uid}').status_code==200})

@app.route('/api/sv', methods=['POST'])
@login_req
def api_sv_c():
    r = api.post('/server', request.json)
    return r.json() if r.status_code==200 else jsonify({'error':r.text}), r.status_code

@app.route('/api/sv/<sid>', methods=['PUT'])
@login_req
def api_sv_u(sid):
    r = api.put(f'/server/{sid}', request.json)
    return r.json() if r.status_code==200 else jsonify({'error':r.text}), r.status_code

@app.route('/api/sv/<sid>', methods=['DELETE'])
@login_req
def api_sv_d(sid):
    return jsonify({'ok': api.delete(f'/server/{sid}').status_code==200})

@app.route('/api/sv/<sid>/start', methods=['PUT'])
@login_req
def api_sv_start(sid):
    r = api.put(f'/server/{sid}/start')
    return r.json() if r.status_code==200 else jsonify({'error':r.text}), r.status_code

@app.route('/api/sv/<sid>/stop', methods=['PUT'])
@login_req
def api_sv_stop(sid):
    r = api.put(f'/server/{sid}/stop')
    return r.json() if r.status_code==200 else jsonify({'error':r.text}), r.status_code

@app.route('/api/sv/<sid>/restart', methods=['PUT'])
@login_req
def api_sv_restart(sid):
    r = api.put(f'/server/{sid}/restart')
    return r.json() if r.status_code==200 else jsonify({'error':r.text}), r.status_code

@app.route('/api/sv/<sid>/rt', methods=['POST'])
@login_req
def api_rt_c(sid):
    r = api.post(f'/server/{sid}/route', request.json)
    return r.json() if r.status_code==200 else jsonify({'error':r.text}), r.status_code

@app.route('/api/sv/<sid>/rt/<path:net>', methods=['DELETE'])
@login_req
def api_rt_d(sid, net):
    return jsonify({'ok': api.delete(f'/server/{sid}/route/{net}').status_code==200})

@app.route('/api/sv/<sid>/org/<oid>', methods=['PUT'])
@login_req
def api_org_attach(sid, oid):
    return jsonify({'ok': api.put(f'/server/{sid}/organization/{oid}').status_code==200})

@app.route('/api/sv/<sid>/org/<oid>', methods=['DELETE'])
@login_req
def api_org_detach(sid, oid):
    return jsonify({'ok': api.delete(f'/server/{sid}/organization/{oid}').status_code==200})

@app.route('/data/<oid>/<uid>.tar')
@login_req
def dl_profile(oid, uid):
    r = api.get(f'/data/{oid}/{uid}.tar')
    if r.status_code == 200:
        return send_file(io.BytesIO(r.content), mimetype='application/octet-stream', as_attachment=True, download_name=f'{uid}.tar')
    return '下载失败', 400

# ====== 管理员管理 ======
@app.route('/admins')
@login_req
def admins_page():
    ad = api_get('/administrators')
    al = ad if isinstance(ad, list) else []
    return R('''
<div class="card"><div class="card-hd"><h2>👤 管理员管理</h2>
<button class="btn btn-p" onclick="mo('addA')">+ 添加管理员</button></div>
<div class="card-bd"><table><tr><th>用户名</th><th>操作</th></tr>
{%for a in al%}<tr><td><b>{{a.username}}</b></td><td class="btns">
<button class="btn btn-s btn-d" onclick="cd('{{a.username}}',function(){api('DELETE','/api/admin/{{a._id}}',null,function(){location.reload()})})">删除</button></td></tr>
{%endfor%}{%if not al%}<tr><td colspan="2" class="empty">暂无管理员</td></tr>{%endif%}</table></div></div>
<div class="mo" id="addA"><div class="md"><div class="md-hd"><h3>添加管理员</h3><button class="md-x" onclick="mc('addA')">&times;</button></div>
<div class="md-bd">
<div class="fg"><label>用户名</label><input id="aun"></div>
<div class="fg"><label>密码</label><input id="apw" type="password"></div>
<div class="fg"><label>Secret</label><input id="asec"><div class="tip">管理员密钥，可留空</div></div>
</div><div class="md-ft"><button class="btn" onclick="mc('addA')">取消</button>
<button class="btn btn-p" onclick="addA()">创建</button></div></div></div>
<script>function addA(){var d={username:document.getElementById('aun').value,password:document.getElementById('apw').value};var s=document.getElementById('asec').value;if(s)d.secret=s;api('POST','/api/admin',d,function(r){if(r._id)location.reload();else alert('创建失败: '+JSON.stringify(r))})}</script>
''', p='a', al=al)

# ====== 日志 ======
@app.route('/logs')
@login_req
def logs_page():
    logs = api_get('/log')
    ll = logs if isinstance(logs, list) else []
    return R('''
<div class="card"><div class="card-hd"><h2>📋 系统日志</h2>
<button class="btn btn-s" onclick="location.reload()">刷新</button></div>
<div class="card-bd"><table><tr><th>时间</th><th>级别</th><th>消息</th></tr>
{%for l in ll%}<tr><td style="white-space:nowrap">{{l.timestamp or l.time or '-'}}</td>
<td>{%if l.level=='error'%}<span class="tag tag-r">错误</span>{%elif l.level=='warn'%}<span class="tag tag-b">警告</span>{%else%}<span class="tag tag-gray">{{l.level or '-'}}</span>{%endif%}</td>
<td style="font-size:12px">{{l.message or l.msg or '-'}}</td></tr>
{%endfor%}{%if not ll%}<tr><td colspan="3" class="empty">暂无日志</td></tr>{%endif%}</table></div></div>
''', p='cfg', ll=ll[-200:] if isinstance(ll, list) else ll)

# ====== 审计日志 ======
@app.route('/audit')
@login_req
def audit_page():
    logs = api_get('/log/audit')
    ll = logs if isinstance(logs, list) else []
    return R('''
<div class="card"><div class="card-hd"><h2>🔍 审计日志</h2>
<button class="btn btn-s" onclick="location.reload()">刷新</button></div>
<div class="card-bd"><table><tr><th>时间</th><th>类型</th><th>用户</th><th>IP</th><th>消息</th></tr>
{%for l in ll%}<tr><td style="white-space:nowrap">{{l.timestamp or '-'}}</td>
<td>{{l.type or '-'}}</td><td>{{l.user or '-'}}</td><td>{{l.remote_addr or '-'}}</td>
<td style="font-size:12px">{{l.message or '-'}}</td></tr>
{%endfor%}{%if not ll%}<tr><td colspan="5" class="empty">暂无审计日志</td></tr>{%endif%}</table></div></div>
''', p='cfg', ll=ll[-200:] if isinstance(ll, list) else ll)

# ====== 服务器日志 ======
@app.route('/sv/<sid>/output')
@login_req
def sv_output(sid):
    sv = api_get(f'/server/{sid}')
    if not sv: return redirect('/servers')
    r = api.get(f'/server/{sid}/output')
    output = r.json() if r.status_code == 200 else []
    return R('''
<div class="card"><div class="card-hd"><h2>📋 {{sv.name}} - 服务器日志</h2>
<div class="btns"><button class="btn btn-s" onclick="location.reload()">刷新</button>
<a href="/sv/{{sid}}" class="btn btn-s">返回</a></div></div>
<div class="card-bd"><pre style="background:#f5f5f5;padding:12px;border-radius:4px;font-size:11px;max-height:600px;overflow:auto;white-space:pre-wrap">{%for line in output%}{{line}}
{%endfor%}{%if not output%}暂无输出{%endif%}</pre></div></div>
''', p='s', sv=sv, sid=sid, output=output if isinstance(output, list) else [str(output)])

# ====== 用户详情 ======
@app.route('/usr/<oid>/<uid>')
@login_req
def user_detail(oid, uid):
    org = api_get(f'/organization/{oid}')
    u = api_get(f'/user/{oid}/{uid}')
    if not u: return redirect(f'/org/{oid}')
    servers = api_get('/server')
    org_servers = []
    for s in (servers if isinstance(servers, list) else []):
        org_servers.append(s)
    return R('''
<div class="card"><div class="card-hd"><h2>👤 {{u.name}}</h2>
<div class="btns"><a href="/org/{{oid}}" class="btn btn-s">返回</a></div></div>
<div class="card-bd"><div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
<div>
<h3 style="margin-bottom:10px">基本信息</h3>
<div class="fg"><label>用户名</label><input id="uname" value="{{u.name}}"></div>
<div class="fg"><label>邮箱</label><input id="uemail" value="{{u.email or ''}}"></div>
<div class="fg"><label>PIN码</label><input id="upin" value="{{u.pin or ''}}"><div class="tip">连接时需要输入</div></div>
<div class="fg"><label>分组</label><input id="ugroups" value="{{(u.groups|join(', ')) if u.groups else ''}}"><div class="tip">多个逗号分隔</div></div>
<div class="fg"><label>状态</label><select id="udisabled"><option value="false" {{'selected' if not u.disabled}}>启用</option><option value="true" {{'selected' if u.disabled}}>禁用</option></select></div>
<div class="fg"><label>Google验证器</label><select id="uotp"><option value="true" {{'selected' if u.otp_auth}}>启用</option><option value="false" {{'selected' if not u.otp_auth}}>禁用</option></select></div>
<div class="fg"><label>SSO认证绕过</label><select id="ubypass"><option value="false" {{'selected' if not u.bypass_secondary}}>否</option><option value="true" {{'selected' if u.bypass_secondary}}>是</option></select></div>
<div class="fg"><label>DNS服务器</label><input id="udns" value="{{u.dns_server or ''}}"></div>
<div class="fg"><label>虚拟网络</label><input id="uip" value="{{u.ip_address or ''}}"><div class="tip">留空自动分配</div></div>
<div class="fg"><label>发送验证密钥</label><select id="uemailkey"><option value="false">否</option><option value="true">是</option></select></div>
<h3 style="margin:14px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">🔌 端口转发</h3>
<div class="fg"><label>端口转发规则</label><input id="upfwd" value="{{u.port_forwarding if u.port_forwarding else ''}}"><div class="tip">格式: 协议:端口:目标IP:目标端口，多个用逗号分隔</div></div>
<h3 style="margin:14px 0 10px;border-top:1px solid #f0f0f0;padding-top:12px">🌐 网络链接</h3>
<div class="fg"><label>网络链接</label><input id="unetlink" value="{{u.network_links if u.network_links else ''}}"><div class="tip">格式: 网络地址/掩码，多个用逗号分隔</div></div>
<button class="btn btn-p" onclick="saveU()">保存</button>
</div>
<div>
<h3 style="margin-bottom:10px">快捷操作</h3>
<div class="btns" style="flex-direction:column;gap:8px">
<a href="/data/{{oid}}/{{u._id}}.tar" class="btn" style="text-align:center">📥 下载配置文件</a>
<button class="btn" style="text-align:center" onclick="api('PUT','/api/usr/{{oid}}/{{u._id}}',{disabled:{{'false' if u.disabled else 'true'}}},function(){location.reload()})">{{'✅ 启用此用户' if u.disabled else '🚫 禁用此用户'}}</button>
<button class="btn" style="text-align:center" onclick="api('PUT','/api/usr/{{oid}}/{{u._id}}/otp',{},function(){toast('已重置OTP')})">🔄 重置OTP密钥</a>
<button class="btn btn-d" style="text-align:center" onclick="cd('{{u.name}}',function(){api('DELETE','/api/usr/{{oid}}/{{u._id}}',null,function(){window.location='/org/{{oid}}'})})">🗑️ 删除用户</button>
<a href="/usr/{{oid}}/{{u._id}}/audit" class="btn" style="text-align:center">📋 用户审计</a>
</div>
<h3 style="margin:16px 0 10px">用户信息</h3>
<table><tr><td><b>组织</b></td><td>{{org.name}}</td></tr>
<tr><td><b>创建时间</b></td><td>{{u.timestamp or '-'}}</td></tr>
<tr><td><b>最后连接</b></td><td>{{u.last_active or '-'}}</td></tr>
<tr><td><b>MAC地址</b></td><td>{{u.mac_address or '-'}}</td></tr>
</table>
</div></div></div></div>
<script>function saveU(){var g=document.getElementById('ugroups').value;var pf=document.getElementById('upfwd').value;var nl=document.getElementById('unetlink').value;var d={name:document.getElementById('uname').value,email:document.getElementById('uemail').value||null,pin:document.getElementById('upin').value||null,groups:g?g.split(',').map(function(x){return x.trim()}):[],disabled:document.getElementById('udisabled').value==='true',otp_auth:document.getElementById('uotp').value==='true',bypass_secondary:document.getElementById('ubypass').value==='true',dns_server:document.getElementById('udns').value||null,ip_address:document.getElementById('uip').value||null};if(pf)d.port_forwarding=pf;if(nl)d.network_links=nl;api('PUT','/api/usr/{{oid}}/{{u._id}}',d,function(r){if(r)toast('已保存');else toast('保存失败','r')})}</script>
''', p='u', u=u, oid=oid, org=org if org else {})

# ====== 批量添加用户 ======
@app.route('/org/<oid>/bulk')
@login_req
def bulk_add_page(oid):
    org = api_get(f'/organization/{oid}')
    if not org: return redirect('/orgs')
    return R('''
<div class="card"><div class="card-hd"><h2>👥 批量添加用户 - {{org.name}}</h2>
<a href="/org/{{oid}}" class="btn btn-s">返回</a></div>
<div class="card-bd">
<div class="fg"><label>用户列表（每行一个，格式：用户名,邮箱,PIN）</label>
<textarea id="bulk" rows="12" placeholder="zhangsan,zhang@test.com,1234&#10;lisi,lisi@test.com&#10;wangwu"></textarea>
<div class="tip">邮箱和PIN可选，用逗号分隔。留空的字段将不设置。</div></div>
<button class="btn btn-p" onclick="bulkAdd()">批量添加</button>
<div id="bulkResult" style="margin-top:10px;font-size:12px"></div>
</div></div>
<script>function bulkAdd(){var lines=document.getElementById('bulk').value.trim().split('\n');var results=[];var done=0;var total=lines.length;lines.forEach(function(line,i){line=line.trim();if(!line){done++;return}var parts=line.split(',');var d={name:parts[0].trim()};if(parts[1])d.email=parts[1].trim();if(parts[2])d.pin=parts[2].trim();api('POST','/api/usr/{{oid}}',d,function(r){done++;if(r&&r.name){results.push('✅ '+d.name+' 成功')}else{results.push('❌ '+d.name+' 失败: '+(r&&r.error||'未知错误'))}if(done===total){document.getElementById('bulkResult').innerHTML=results.join('<br>')}})})}</script>
''', p='u', org=org, oid=oid)

# ====== 邮件发送 ======
@app.route('/org/<oid>/email')
@login_req
def email_users_page(oid):
    org = api_get(f'/organization/{oid}')
    if not org: return redirect('/orgs')
    return R('''
<div class="card"><div class="card-hd"><h2>📧 发送邮件 - {{org.name}}</h2>
<a href="/org/{{oid}}" class="btn btn-s">返回</a></div>
<div class="card-bd">
<div class="fg"><label>收件人</label><select id="eto"><option value="all">全部用户</option><option value="selected">选中用户</option></select></div>
<div class="fg"><label>用户列表（逗号分隔用户名，选择"选中用户"时生效）</label><input id="esel" placeholder="zhangsan,lisi,wangwu"></div>
<div class="fg"><label>主题</label><input id="esubj" placeholder="VPN配置更新通知"></div>
<div class="fg"><label>内容</label><textarea id="ebody" rows="8" placeholder="请输入邮件内容..."></textarea></div>
<button class="btn btn-p" onclick="sendEmail()">发送</button>
<div id="emailResult" style="margin-top:10px;font-size:12px"></div>
</div></div>
<script>function sendEmail(){var d={type:document.getElementById('eto').value,subject:document.getElementById('esubj').value,body:document.getElementById('ebody').value};if(d.type==='selected')d.users=document.getElementById('esel').value.split(',').map(function(x){return x.trim()});api('POST','/api/org/{{oid}}/email',d,function(r){if(r&&r.ok)toast('邮件已发送');else toast('发送失败','r')})}</script>
''', p='u', org=org, oid=oid)

# ====== 用户OTP重置 ======
@app.route('/api/usr/<oid>/<uid>/otp', methods=['PUT'])
@login_req
def api_usr_reset_otp(oid, uid):
    r = api.put(f'/user/{oid}/{uid}', {'otp_secret': ''})
    return jsonify({'ok': r.status_code == 200}) if r else jsonify({'error': 'failed'}), 400

# ====== Settings API ======
@app.route('/api/settings', methods=['GET','PUT'])
@login_req
def api_settings():
    if request.method == 'GET':
        r = api.get('/settings')
        return r.json() if r.status_code == 200 else jsonify({})
    r = api.put('/settings', request.json)
    return r.json() if r.status_code == 200 else jsonify({'error': r.text}), r.status_code

# ====== Admin API ======
@app.route('/api/admin', methods=['GET','POST'])
@login_req
def api_admin_list():
    if request.method == 'GET':
        r = api.get('/administrators')
        return r.json() if r.status_code == 200 else []
    r = api.post('/administrators', request.json)
    return r.json() if r.status_code == 200 else jsonify({'error': r.text}), r.status_code

@app.route('/api/admin/<aid>', methods=['DELETE'])
@login_req
def api_admin_del(aid):
    return jsonify({'ok': api.delete(f'/administrators/{aid}').status_code == 200})

# ====== Email API ======
@app.route('/api/org/<oid>/email', methods=['POST'])
@login_req
def api_org_email(oid):
    data = request.json or {}
    subject = data.get('subject', '')
    body = data.get('body', '')
    # Get users
    ud = api_get(f'/user/{oid}')
    ul = ud.get('users', ud) if isinstance(ud, dict) else (ud if isinstance(ud, list) else [])
    if data.get('type') == 'selected':
        names = data.get('users', [])
        ul = [u for u in ul if u.get('name') in names]
    emails = [u.get('email') for u in ul if u.get('email')]
    if not emails:
        return jsonify({'ok': False, 'error': '没有可发送的邮箱地址'}), 400
    # Send via pritunl email API if available, otherwise return info
    r = api.post(f'/user/{oid}/email', {'subject': subject, 'message': body, 'user_ids': [u['_id'] for u in ul]})
    if r and r.status_code == 200:
        return jsonify({'ok': True, 'count': len(emails)})
    return jsonify({'ok': False, 'error': '发送失败，请检查SMTP设置'})

# ====== 主机管理 ======
@app.route('/hosts')
@login_req
def hosts_page():
    hosts = api_get('/host')
    hl = hosts if isinstance(hosts, list) else []
    return R('''
<div class="card"><div class="card-hd"><h2>🖧 主机管理</h2>
<button class="btn btn-s" onclick="location.reload()">刷新</button></div>
<div class="card-bd"><table><tr><th>名称</th><th>主机名</th><th>公网地址</th><th>绑定地址</th><th>可用组</th><th>状态</th><th>操作</th></tr>
{%for h in hl%}<tr>
<td><b>{{h.name or h._id or '-'}}</b></td>
<td>{{h.hostname or '-'}}</td>
<td>{{h.public_address or '-'}}</td>
<td>{{h.bind_address or '-'}}</td>
<td>{{h.availability_group or '默认'}}</td>
<td>{%if h.status=='online'%}<span class="tag tag-g">在线</span>{%elif h.status%}<span class="tag tag-r">{{h.status}}</span>{%else%}<span class="tag tag-gray">未知</span>{%endif%}</td>
<td class="btns">
<button class="btn btn-s" onclick="mo('editH{{loop.index}}')">设置</button>
</td></tr>
<div class="mo" id="editH{{loop.index}}"><div class="md"><div class="md-hd"><h3>主机设置 - {{h.name or h._id}}</h3><button class="md-x" onclick="mc('editH{{loop.index}}')">&times;</button></div>
<div class="md-bd">
<div class="fg"><label>公网地址</label><input id="hpa{{loop.index}}" value="{{h.public_address or ''}}"></div>
<div class="fg"><label>绑定地址</label><input id="hba{{loop.index}}" value="{{h.bind_address or ''}}"></div>
<div class="fg"><label>可用组</label><input id="hag{{loop.index}}" value="{{h.availability_group or ''}}"></div>
</div><div class="md-ft"><button class="btn" onclick="mc('editH{{loop.index}}')">取消</button>
<button class="btn btn-p" onclick="saveH('{{h._id}}','{{loop.index}}')">保存</button></div></div></div>
{%endfor%}{%if not hl%}<tr><td colspan="7" class="empty">暂无主机</td></tr>{%endif%}</table></div></div>
<script>function saveH(hid,idx){var d={public_address:document.getElementById('hpa'+idx).value||null,bind_address:document.getElementById('hba'+idx).value||null,availability_group:document.getElementById('hag'+idx).value||null};api('PUT','/api/host/'+hid,d,function(r){if(r)toast('已保存');else toast('保存失败','r')})}</script>
''', p='h', hl=hl)

# ====== 链接管理 ======
@app.route('/links')
@login_req
def links_page():
    links = api_get('/link')
    ll = links if isinstance(links, list) else []
    servers = api_get('/server')
    sl = servers if isinstance(servers, list) else []
    return R('''
<div class="card"><div class="card-hd"><h2>🔗 链接管理</h2>
<button class="btn btn-p" onclick="mo('addL')">+ 添加链接</button></div>
<div class="card-bd"><table><tr><th>名称</th><th>服务器1</th><th>服务器2</th><th>状态</th><th>操作</th></tr>
{%for l in ll%}<tr>
<td><b>{{l.name or l._id or '-'}}</b></td>
<td>{{l.server_id or '-'}}</td>
<td>{{l.server_id_b or '-'}}</td>
<td>{%if l.status=='active'%}<span class="tag tag-g">活跃</span>{%elif l.status%}<span class="tag tag-b">{{l.status}}</span>{%else%}<span class="tag tag-gray">未知</span>{%endif%}</td>
<td class="btns">
<button class="btn btn-s" onclick="mo('editL{{loop.index}}')">设置</button>
<button class="btn btn-s btn-d" onclick="cd('{{l.name or l._id}}',function(){api('DELETE','/api/link/{{l._id}}',null,function(){location.reload()})})">删除</button>
</td></tr>
<div class="mo" id="editL{{loop.index}}"><div class="md"><div class="md-hd"><h3>链接设置</h3><button class="md-x" onclick="mc('editL{{loop.index}}')">&times;</button></div>
<div class="md-bd">
<div class="fg"><label>名称</label><input id="ln{{loop.index}}" value="{{l.name or ''}}"></div>
</div><div class="md-ft"><button class="btn" onclick="mc('editL{{loop.index}}')">取消</button>
<button class="btn btn-p" onclick="saveL('{{l._id}}','{{loop.index}}')">保存</button></div></div></div>
{%endfor%}{%if not ll%}<tr><td colspan="5" class="empty">暂无链接</td></tr>{%endif%}</table></div></div>
<div class="mo" id="addL"><div class="md"><div class="md-hd"><h3>添加链接</h3><button class="md-x" onclick="mc('addL')">&times;</button></div>
<div class="md-bd">
<div class="fg"><label>名称</label><input id="alname" placeholder="如：站点间链接"></div>
<div class="fg"><label>服务器A</label><select id="alsa">{%for s in sl%}<option value="{{s._id}}">{{s.name}}</option>{%endfor%}</select></div>
<div class="fg"><label>服务器B</label><select id="alsb">{%for s in sl%}<option value="{{s._id}}">{{s.name}}</option>{%endfor%}</select></div>
</div><div class="md-ft"><button class="btn" onclick="mc('addL')">取消</button>
<button class="btn btn-p" onclick="addL()">创建</button></div></div></div>
<script>function addL(){var d={name:document.getElementById('alname').value,server_id:document.getElementById('alsa').value,server_id_b:document.getElementById('alsb').value};api('POST','/api/link',d,function(r){if(r&&r._id)location.reload();else alert('创建失败: '+JSON.stringify(r))})}
function saveL(lid,idx){var d={name:document.getElementById('ln'+idx).value};api('PUT','/api/link/'+lid,d,function(r){if(r)toast('已保存');else toast('保存失败','r')})}</script>
''', p='l', ll=ll, sl=sl)

# ====== 设备管理 ======
@app.route('/devices')
@login_req
def devices_page():
    org = api_get('/organization')
    all_devs = []
    for o in (org if isinstance(org, list) else []):
        ud = api_get(f'/user/{o["id"]}')
        ul = ud.get('users', ud) if isinstance(ud, dict) else (ud if isinstance(ud, list) else [])
        for u in ul:
            devs = api_get(f'/user/{o["id"]}/{u["_id"]}/device')
            dl = devs if isinstance(devs, list) else []
            for d in dl:
                d['_uname'] = u.get('name', '')
                d['_oid'] = o['id']
                d['_uid'] = u['_id']
                d['_oname'] = o.get('name', '')
                all_devs.append(d)
    return R('''
<div class="card"><div class="card-hd"><h2>📱 设备管理</h2>
<button class="btn btn-s" onclick="location.reload()">刷新</button></div>
<div class="card-bd"><table><tr><th>用户</th><th>组织</th><th>设备名称</th><th>平台</th><th>设备ID</th><th>操作</th></tr>
{%for d in dl%}<tr>
<td><b>{{d._uname}}</b></td>
<td>{{d._oname}}</td>
<td>{{d.name or d.platform_device_name or '-'}}</td>
<td>{{d.platform or '-'}}</td>
<td style="font-size:11px">{{d._id or d.device_id or '-'}}</td>
<td class="btns">
<button class="btn btn-s btn-d" onclick="cd('此设备',function(){api('DELETE','/api/device/{{d._oid}}/{{d._uid}}/{{d._id}}',null,function(){location.reload()})})">移除</button>
</td></tr>
{%endfor%}{%if not dl%}<tr><td colspan="6" class="empty">暂无注册设备</td></tr>{%endif%}</table></div></div>
''', p='dv', dl=all_devs)

# ====== 用户审计 ======
@app.route('/usr/<oid>/<uid>/audit')
@login_req
def user_audit(oid, uid):
    org = api_get(f'/organization/{oid}')
    u = api_get(f'/user/{oid}/{uid}')
    if not u: return redirect(f'/org/{oid}')
    r = api.get(f'/user/{oid}/{uid}/audit')
    audit = r.json() if r.status_code == 200 else []
    al = audit if isinstance(audit, list) else []
    return R('''
<div class="card"><div class="card-hd"><h2>📋 {{u.name}} - 审计事件</h2>
<div class="btns"><button class="btn btn-s" onclick="location.reload()">刷新</button>
<a href="/usr/{{oid}}/{{uid}}" class="btn btn-s">返回</a></div></div>
<div class="card-bd"><table><tr><th>时间</th><th>类型</th><th>消息</th><th>IP地址</th></tr>
{%for a in al%}<tr>
<td style="white-space:nowrap">{{a.timestamp or '-'}}</td>
<td>{{a.type or a.event or '-'}}</td>
<td style="font-size:12px">{{a.message or a.msg or '-'}}</td>
<td>{{a.remote_addr or a.ip_address or '-'}}</td>
</tr>{%endfor%}{%if not al%}<tr><td colspan="4" class="empty">暂无审计事件</td></tr>{%endif%}</table></div></div>
''', p='u', u=u or {}, oid=oid, uid=uid, al=al[-200:])

# ====== Bandwidth API ======
@app.route('/api/sv/<sid>/bw/<period>')
@login_req
def api_sv_bw(sid, period):
    r = api.get(f'/server/{sid}/bandwidth/{period}')
    return r.json() if r.status_code == 200 else jsonify([])

# ====== Host API ======
@app.route('/api/host/<hid>', methods=['GET','PUT'])
@login_req
def api_host(hid):
    if request.method == 'GET':
        r = api.get(f'/host/{hid}')
        return r.json() if r.status_code == 200 else jsonify({})
    r = api.put(f'/host/{hid}', request.json)
    return r.json() if r.status_code == 200 else jsonify({'error': r.text}), r.status_code

@app.route('/api/sv/<sid>/host/<hid>', methods=['PUT'])
@login_req
def api_host_attach(sid, hid):
    r = api.put(f'/server/{sid}/host/{hid}')
    return r.json() if r.status_code == 200 else jsonify({'error': r.text}), r.status_code

@app.route('/api/sv/<sid>/host/<hid>', methods=['DELETE'])
@login_req
def api_host_detach(sid, hid):
    return jsonify({'ok': api.delete(f'/server/{sid}/host/{hid}').status_code == 200})

# ====== Link API ======
@app.route('/api/link', methods=['POST'])
@login_req
def api_link_c():
    r = api.post('/link', request.json)
    return r.json() if r.status_code == 200 else jsonify({'error': r.text}), r.status_code

@app.route('/api/link/<lid>', methods=['GET','PUT','DELETE'])
@login_req
def api_link(lid):
    if request.method == 'GET':
        r = api.get(f'/link/{lid}')
        return r.json() if r.status_code == 200 else jsonify({})
    elif request.method == 'PUT':
        r = api.put(f'/link/{lid}', request.json)
        return r.json() if r.status_code == 200 else jsonify({'error': r.text}), r.status_code
    return jsonify({'ok': api.delete(f'/link/{lid}').status_code == 200})

# ====== Device API ======
@app.route('/api/device/<oid>/<uid>/<did>', methods=['DELETE'])
@login_req
def api_device_d(oid, uid, did):
    return jsonify({'ok': api.delete(f'/user/{oid}/{uid}/device/{did}').status_code == 200})

if __name__=='__main__':
    app.run(host='0.0.0.0', port=LISTEN_PORT, debug=False)
