#!/usr/lib/pritunl/usr/bin/python3
"""
Pritunl 中文管理面板 v3
完整功能版 - 对标英文版所有功能
每次请求重新认证，避免与英文版session冲突
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
        """验证用户名密码，只保存凭据不保存session"""
        s = requests.Session()
        s.verify = False
        resp = s.post(f'{PRITUNL_URL}/auth/session',
            json={'username': username, 'password': password})
        data = resp.json()
        if not data.get('authenticated'):
            return False, data.get('error_msg', '登录失败'), False
        session['pritunl_user'] = username
        session['pritunl_pass'] = password
        tf = bool(data.get('tf_enabled')) or bool(data.get('tf_mode'))
        return True, data.get('default', False), tf

    def _get_session(self):
        """每次请求重新登录获取新session"""
        username = session.get('pritunl_user', '')
        password = session.get('pritunl_pass', '')
        if not username or not password:
            return None, None
        s = requests.Session()
        s.verify = False
        resp = s.post(f'{PRITUNL_URL}/auth/session',
            json={'username': username, 'password': password})
        data = resp.json()
        if not data.get('authenticated'):
            return None, None
        state_resp = s.get(f'{PRITUNL_URL}/state')
        csrf = ''
        if state_resp.status_code == 200:
            csrf = state_resp.json().get('csrf_token', '')
        return s, csrf

    def req(self, method, path, data=None):
        s, csrf = self._get_session()
        if not s:
            return type('obj', (object,), {'status_code': 401, 'json': lambda: {'error': 'not authenticated'}})()
        h = {'Content-Type': 'application/json', 'PR-Validated': 'true'}
        if csrf:
            h['Csrf-Token'] = csrf
        url = f'{PRITUNL_URL}{path}'
        r = s.request(method, url, headers=h, json=data)
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

def oid(obj):
    """Get ID from object, handling both 'id' and '_id' fields"""
    if isinstance(obj, dict):
        return obj.get('id') or obj.get('_id') or ''
    return obj


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

# ====== 登录/登出 ======
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        d = request.get_json(silent=True) or request.form
        result = api.login(d.get('username',''), d.get('password',''))
        ok, is_default, tf = result[0], result[1], result[2] if len(result)>2 else False
        if ok:
            session['user'] = d.get('username','')
            if is_default:
                session['is_default'] = True
            return jsonify({'success': True, 'default': is_default, 'tf_needed': tf})
        return jsonify({'success': False, 'error': str(is_default)}), 401
    return '''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"><title>登录</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center;font-family:-apple-system,sans-serif}
.b{background:#fff;border-radius:12px;padding:36px;width:400px;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.b h1{text-align:center;margin-bottom:6px;font-size:22px}.b p{text-align:center;color:#999;margin-bottom:20px;font-size:13px}
.fg{margin-bottom:14px}.fg label{display:block;margin-bottom:4px;font-weight:600;font-size:12px}
.fg input{width:100%;padding:9px 11px;border:1px solid #d9d9d9;border-radius:6px;font-size:13px}
.fg input:focus{outline:none;border-color:#667eea;box-shadow:0 0 0 2px rgba(102,126,234,.1)}
.btn{width:100%;padding:11px;background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;border:none;border-radius:6px;font-size:14px;font-weight:600;cursor:pointer;margin-bottom:8px}
.btn:hover{opacity:.9}
.btn-sso{background:#fff;color:#333;border:1px solid #d9d9d9;display:flex;align-items:center;justify-content:center;gap:8px;font-weight:500;font-size:13px;padding:9px}
.btn-sso:hover{background:#f5f5f5}
.err{color:#ff4d4f;font-size:12px;text-align:center;margin-top:10px;display:none}
.alert-warn{background:#fff3cd;border:1px solid #ffc107;border-radius:8px;padding:12px;margin-bottom:14px;color:#856404;font-size:12px;display:none}
.alert-warn.show{display:block}
.alert-warn code{background:#f8f9fa;padding:2px 6px;border-radius:4px;font-size:11px}
.sso-divider{text-align:center;color:#999;font-size:12px;margin:12px 0;position:relative}
.sso-divider:before,.sso-divider:after{content:'';position:absolute;top:50%;width:35%;height:1px;background:#e8e8e8}
.sso-divider:before{left:0}.sso-divider:after{right:0}
.tf-form{display:none}
</style>
</head><body>
<div class="b">
<h1>🔐 VPN管理系统</h1>
<p>管理员登录</p>
<div class="alert-warn" id="defaultAlert">
⚠️ <b>首次登录提示</b><br>
系统正在使用默认凭据。请在服务器上运行以下命令获取默认用户名和密码：<br>
<code>sudo pritunl default-password</code><br>
登录后请立即修改密码！
</div>
<div id="loginForm">
<div class="fg"><label>用户名</label><input id="u" autofocus></div>
<div class="fg"><label>密码</label><input id="p" type="password" onkeydown="if(event.key==='Enter')go()"></div>
<button class="btn" onclick="go()">登 录</button>
<div class="sso-divider">或使用SSO登录</div>
<button class="btn btn-sso" onclick="sso('saml')">🔐 SAML登录</button>
<button class="btn btn-sso" onclick="sso('google')">🔵 Google登录</button>
<button class="btn btn-sso" onclick="sso('azure')">☁️ Azure登录</button>
<button class="btn btn-sso" onclick="sso('slack')">💬 Slack登录</button>
<button class="btn btn-sso" onclick="sso('okta')">🛡️ Okta登录</button>
<button class="btn btn-sso" onclick="sso('onelogin')">🔑 OneLogin登录</button>
<button class="btn btn-sso" onclick="sso('jumpcloud')">⚡ JumpCloud登录</button>
<button class="btn btn-sso" onclick="sso('duo')">📱 Duo登录</button>
<div class="err" id="e"></div>
</div>
<div id="tfForm" class="tf-form">
<p style="text-align:center;margin-bottom:16px;color:#666;font-size:13px">请输入双因素验证码</p>
<div class="fg"><label>验证码</label><input id="otp" autofocus onkeydown="if(event.key==='Enter')tfGo()"></div>
<button class="btn" onclick="tfGo()">验 证</button>
<div class="err" id="tfErr"></div>
</div>
</div>
<script>
function sso(provider){window.location.href='/sso/request?provider='+provider}
function go(){var u=document.getElementById('u').value,p=document.getElementById('p').value;if(!u||!p){document.getElementById('e').textContent='请输入用户名和密码';document.getElementById('e').style.display='block';return}
var x=new XMLHttpRequest();x.open('POST','/login');x.setRequestHeader('Content-Type','application/json');
x.onload=function(){var d=JSON.parse(x.responseText);if(d.success){if(d.default){document.getElementById('defaultAlert').classList.add('show')}if(d.tf_needed){document.getElementById('loginForm').style.display='none';document.getElementById('tfForm').style.display='block'}else{location.href='/'}}else{document.getElementById('e').textContent=d.error||'登录失败';document.getElementById('e').style.display='block'}}};
x.send(JSON.stringify({username:u,password:p}))}
function tfGo(){var otp=document.getElementById('otp').value;if(!otp){document.getElementById('tfErr').textContent='请输入验证码';document.getElementById('tfErr').style.display='block';return}
var x=new XMLHttpRequest();x.open('POST','/login/tf');x.setRequestHeader('Content-Type','application/json');
x.onload=function(){var d=JSON.parse(x.responseText);if(d.success)location.href='/';else{document.getElementById('tfErr').textContent=d.error||'验证失败';document.getElementById('tfErr').style.display='block'}}};
x.send(JSON.stringify({code:otp}))}</script></body></html>'''

@app.route('/login/tf', methods=['POST'])
def login_tf():
    d = request.get_json(silent=True) or request.form
    code = d.get('code', '')
    if not code:
        return jsonify({'success': False, 'error': '请输入验证码'}), 400
    s, csrf = api._get_session()
    if not s:
        return jsonify({'success': False, 'error': '会话已过期，请重新登录'}), 401
    h = {'Content-Type': 'application/json', 'PR-Validated': 'true'}
    if csrf:
        h['Csrf-Token'] = csrf
    resp = s.post(f'{PRITUNL_URL}/auth/session', json={'otp_code': code}, headers=h)
    data = resp.json()
    if data.get('authenticated'):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': data.get('error_msg', '验证码错误')}), 401

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

# ====== SSO路由 ======
@app.route('/sso/request')
def sso_request():
    provider = request.args.get('provider', '')
    r = api.get(f'/sso/request?provider={provider}')
    if r.status_code == 200:
        data = r.json() if r.headers.get('content-type','').startswith('application/json') else {}
        if 'url' in data:
            return redirect(data['url'])
    return redirect('/login')

@app.route('/sso/callback')
def sso_callback():
    r = api.get(f'/sso/callback?{request.query_string.decode()}')
    if r.status_code == 200:
        data = r.json()
        if data.get('authenticated'):
            session['pritunl_user'] = data.get('username', '')
            session['user'] = data.get('username', '')
            return redirect('/')
    return redirect('/login')

# ====== 仪表盘 ======
@app.route('/')
@login_req
def dash():
    servers = api_get('/server')
    orgs = api_get('/organization')
    total_users = 0
    for o in orgs:
        users = api_get(f'/user/{oid(o)}')
        total_users += len(users)
    running = sum(1 for s in servers if s.get('status') == 'running')
    tpl = '''
<div class="stats">
<div class="sc"><div class="n">{{ servers|length }}</div><div class="l">服务器总数</div></div>
<div class="sc"><div class="n">{{ running }}</div><div class="l">运行中</div></div>
<div class="sc"><div class="n">{{ orgs|length }}</div><div class="l">组织数量</div></div>
<div class="sc"><div class="n">{{ total_users }}</div><div class="l">用户总数</div></div>
</div>
<div class="card"><div class="card-hd"><h2>服务器列表</h2></div>
<div class="card-bd"><table><tr><th>名称</th><th>端口</th><th>协议</th><th>网络</th><th>状态</th><th>操作</th></tr>
{% for s in servers %}<tr>
<td><b>{{ s.name }}</b></td><td>{{ s.port }}</td><td>{{ s.protocol }}</td><td>{{ s.network }}</td>
<td><span class="tag {{'tag-g' if s.status=='running' else 'tag-r'}}">{{ '运行中' if s.status=='running' else '已停止' }}</span></td>
<td><a href="/sv/{{ oid(s) }}" class="btn btn-s">详情</a></td>
</tr>{% endfor %}
{% if not servers %}<tr><td colspan="6" class="empty">暂无服务器</td></tr>{% endif %}
</table></div></div>'''
    return R(tpl, p='d', servers=servers, orgs=orgs, running=running, total_users=total_users)

# ====== 服务器 ======
@app.route('/servers')
@login_req
def sv_page():
    servers = api_get('/server')
    orgs = api_get('/organization')
    tpl = '''
<div class="card"><div class="card-hd"><h2>服务器管理</h2>
<button class="btn btn-p" onclick="mo('mAdd')">+ 创建服务器</button></div>
<div class="card-bd"><table><tr><th>名称</th><th>端口</th><th>协议</th><th>网络</th><th>DNS</th><th>状态</th><th>操作</th></tr>
{% for s in servers %}<tr>
<td><b>{{ s.name }}</b></td><td>{{ s.port }}</td><td>{{ s.protocol }}</td><td>{{ s.network }}</td><td>{{ s.dns_server or '-' }}</td>
<td><span class="tag {{'tag-g' if s.status=='running' else 'tag-r'}}">{{ '运行中' if s.status=='running' else '已停止' }}</span></td>
<td class="btns"><a href="/sv/{{ oid(s) }}" class="btn btn-s">详情</a>
{% if s.status=='running' %}<button class="btn btn-s btn-d" onclick="svCmd('{{ oid(s) }}','stop')">停止</button>
<button class="btn btn-s" onclick="svCmd('{{ oid(s) }}','restart')">重启</button>
{% else %}<button class="btn btn-s btn-g" onclick="svCmd('{{ oid(s) }}','start')">启动</button>{% endif %}
<button class="btn btn-s btn-d" onclick="cd('{{ s.name }}',function(){api('DELETE','/api/sv/{{ oid(s) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})})">删除</button>
</td></tr>{% endfor %}
{% if not servers %}<tr><td colspan="7" class="empty">暂无服务器</td></tr>{% endif %}
</table></div></div>
<div class="mo" id="mAdd"><div class="md"><div class="md-hd"><h3>创建服务器</h3><button class="md-x" onclick="mc('mAdd')">×</button></div>
<div class="md-bd"><div class="fg"><label>名称</label><input id="aName"></div>
<div class="fg"><label>端口</label><input id="aPort" value="1194"></div>
<div class="fg"><label>协议</label><select id="aProto"><option value="udp">UDP</option><option value="tcp">TCP</option></select></div>
<div class="fg"><label>网络</label><input id="aNet" value="10.51.0.0/24"></div>
<div class="fg"><label>DNS</label><input id="aDns" value="114.114.114.114, 8.8.8.8"></div></div>
<div class="md-ft"><button class="btn" onclick="mc('mAdd')">取消</button>
<button class="btn btn-p" onclick="svCreate()">创建</button></div></div></div>
<script>
function svCmd(id,cmd){api('PUT','/api/sv/'+id+'/'+cmd,null,function(r){if(r.error)toast(r.error,'r');else{toast('操作成功');setTimeout(function(){location.reload()},500)}})}
function svCreate(){api('POST','/api/sv',{name:document.getElementById('aName').value,port:parseInt(document.getElementById('aPort').value),protocol:document.getElementById('aProto').value,network:document.getElementById('aNet').value,dns_server:document.getElementById('aDns').value},function(r){if(r&&(r.id||(r.id||r._id))){toast('创建成功');location.reload()}else toast('创建失败','r')})}
</script>'''
    return R(tpl, p='s', servers=servers, orgs=orgs)

# ====== 服务器详情 ======
@app.route('/sv/<sid>')
@login_req
def sv_detail(sid):
    sv = api_get(f'/server/{sid}')
    orgs = api_get('/organization')
    routes = api_get(f'/server/{sid}/route')
    attached = api_get(f'/server/{sid}/organization')
    attached_ids = [o.get('_id','') for o in attached]
    hosts = api_get('/host')
    bw = api_get(f'/server/{sid}/bandwidth/hour')
    output = api_get(f'/server/{sid}/output')
    tpl = '''
<div class="card"><div class="card-hd"><h2>{{ sv.name }} - 服务器详情</h2>
<div class="btns">{% if sv.status=='running' %}
<button class="btn btn-d" onclick="svCmd('{{ sid }}','stop')">停止</button>
<button class="btn" onclick="svCmd('{{ sid }}','restart')">重启</button>
{% else %}<button class="btn btn-g" onclick="svCmd('{{ sid }}','start')">启动</button>{% endif %}</div></div>
<div class="card-bd">
<div class="stats">
<div class="sc"><div class="n">{{ sv.port }}</div><div class="l">端口</div></div>
<div class="sc"><div class="n">{{ sv.protocol }}</div><div class="l">协议</div></div>
<div class="sc"><div class="n">{{ sv.network }}</div><div class="l">网络</div></div>
<div class="sc"><div class="n"><span class="tag {{'tag-g' if sv.status=='running' else 'tag-r'}}">{{ '运行中' if sv.status=='running' else '已停止' }}</span></div><div class="l">状态</div></div>
</div>
</div></div>

<div class="card"><div class="card-hd"><h2>基本设置</h2></div>
<div class="card-bd">
<div class="fg"><label>名称</label><input id="eName" value="{{ sv.name }}"></div>
<div class="fg"><label>端口</label><input id="ePort" value="{{ sv.port }}"></div>
<div class="fg"><label>协议</label><select id="eProto"><option value="udp" {{'selected' if sv.protocol=='udp'}}>UDP</option><option value="tcp" {{'selected' if sv.protocol=='tcp'}}>TCP</option></select></div>
<div class="fg"><label>网络</label><input id="eNet" value="{{ sv.network }}"></div>
<div class="fg"><label>DNS</label><input id="eDns" value="{{ sv.dns_server or '' }}"></div>
<div class="fg"><label>哈希算法</label><select id="eHash">
<option value="sha1" {{'selected' if sv.hash=='sha1'}}>SHA1</option>
<option value="sha256" {{'selected' if sv.hash=='sha256'}}>SHA256</option>
<option value="sha512" {{'selected' if sv.hash=='sha512'}}>SHA512</option>
</select></div>
<div class="fg"><label>加密算法</label><select id="eCipher">
<option value="aes128" {{'selected' if sv.cipher=='aes128'}}>AES-128</option>
<option value="aes192" {{'selected' if sv.cipher=='aes192'}}>AES-192</option>
<option value="aes256" {{'selected' if sv.cipher=='aes256'}}>AES-256</option>
</select></div>
<div class="fg"><label>DH参数</label><select id="eDh">
<option value="1" {{'selected' if sv.dh_param_bits==1}}>1</option>
<option value="2" {{'selected' if sv.dh_param_bits==2}}>2</option>
<option value="5" {{'selected' if sv.dh_param_bits==5}}>5</option>
</select></div>
<div class="fg"><label>最大客户端</label><input id="eMax" type="number" value="{{ sv.max_clients or 200 }}"></div>
<div class="fg"><label>虚拟网络接口</label><input id="eVnic" value="{{ sv.vnic or '' }}" placeholder="如: eth0"></div>
<div class="fg"><label>日志级别</label><select id="eVerb">
<option value="0" {{'selected' if sv.verb==0}}>0 - 静默</option>
<option value="1" {{'selected' if sv.verb==1}}>1 - 致命</option>
<option value="2" {{'selected' if sv.verb==2}}>2 - 错误</option>
<option value="3" {{'selected' if sv.verb==3}}>3 - 警告</option>
<option value="4" {{'selected' if sv.verb==4}}>4 - 信息</option>
<option value="5" {{'selected' if sv.verb==5}}>5 - 调试</option>
<option value="6" {{'selected' if sv.verb==6}}>6 - 详细</option>
</select></div>
<div class="fg"><label>Keepalive间隔(秒)</label><input id="eKa1" type="number" value="{{ sv.keepalive_interval or 10 }}"></div>
<div class="fg"><label>Keepalive超时(秒)</label><input id="eKa2" type="number" value="{{ sv.keepalive_timeout or 60 }}"></div>
<div class="fg"><label>MTU</label><input id="eMtu" type="number" value="{{ sv.mtu or 1500 }}"></div>
<div class="fg"><label>Txqueuelen</label><input id="eTxq" type="number" value="{{ sv.txqueuelen or 1000 }}"></div>
<div class="fg"><label>ping间隔(秒)</label><input id="ePing1" type="number" value="{{ sv.ping_interval or 10 }}"></div>
<div class="fg"><label>ping超时(秒)</label><input id="ePing2" type="number" value="{{ sv.ping_timeout or 60 }}"></div>
<button class="btn btn-p" onclick="svSave()">保存设置</button>
</div></div>

<div class="card"><div class="card-hd"><h2>WireGuard设置</h2></div>
<div class="card-bd">
<div class="fg"><label>启用WireGuard</label><select id="eWg"><option value="false" {{'selected' if not sv.wg}}>否</option><option value="true" {{'selected' if sv.wg}}>是</option></select></div>
<div class="fg"><label>WireGuard端口</label><input id="eWgPort" type="number" value="{{ sv.wg_port or '' }}" placeholder="自动"></div>
<div class="fg"><label>WireGuard网络</label><input id="eWgNet" value="{{ sv.wg_network or '' }}" placeholder="如: 10.52.0.0/24"></div>
<button class="btn btn-p" onclick="svSaveWg()">保存WireGuard</button>
</div></div>

<div class="card"><div class="card-hd"><h2>动态防火墙</h2></div>
<div class="card-bd">
<div class="fg"><label>启用动态防火墙</label><select id="eDf"><option value="false" {{'selected' if not sv.dynamic_firewall}}>否</option><option value="true" {{'selected' if sv.dynamic_firewall}}>是</option></select></div>
<button class="btn btn-p" onclick="svSaveDf()">保存防火墙</button>
</div></div>

<div class="card"><div class="card-hd"><h2>路由管理</h2>
<button class="btn btn-p" onclick="mo('mRt')">+ 添加路由</button></div>
<div class="card-bd"><table><tr><th>网络</th><th>注释</th><th>操作</th></tr>
{% for r in routes %}<tr><td>{{ r.network }}</td><td>{{ r.comment or '-' }}</td>
<td><button class="btn btn-s btn-d" onclick="cd('{{ r.network }}',function(){api('DELETE','/api/sv/{{ sid }}/rt/{{ r.network }}',null,function(x){if(x.error)toast(x.error,'r');else location.reload()})})">删除</button></td></tr>
{% endfor %}{% if not routes %}<tr><td colspan="3" class="empty">暂无路由</td></tr>{% endif %}
</table></div></div>

<div class="card"><div class="card-hd"><h2>关联组织</h2></div>
<div class="card-bd"><table><tr><th>组织</th><th>状态</th><th>操作</th></tr>
{% for o in orgs %}<tr><td>{{ o.name }}</td>
<td>{% if oid(o) in attached_ids %}<span class="tag tag-g">已关联</span>{% else %}<span class="tag tag-gray">未关联</span>{% endif %}</td>
<td>{% if oid(o) in attached_ids %}
<button class="btn btn-s btn-d" onclick="api('DELETE','/api/sv/{{ sid }}/org/{{ oid(o) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})">解除关联</button>
{% else %}
<button class="btn btn-s btn-g" onclick="api('PUT','/api/sv/{{ sid }}/org/{{ oid(o) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})">关联</button>
{% endif %}</td></tr>{% endfor %}
</table></div></div>

<div class="card"><div class="card-hd"><h2>带宽监控</h2></div>
<div class="card-bd"><table><tr><th>时间</th><th>入站</th><th>出站</th></tr>
{% for b in bw[:10] %}<tr><td>{{ b.timestamp }}</td><td>{{ b.bytes_recv }}</td><td>{{ b.bytes_sent }}</td></tr>
{% endfor %}{% if not bw %}<tr><td colspan="3" class="empty">暂无数据</td></tr>{% endif %}
</table></div></div>

<div class="card"><div class="card-hd"><h2>服务器日志</h2>
<button class="btn" onclick="api('DELETE','/api/sv/{{ sid }}/output',null,function(){location.reload()})">清空日志</button></div>
<div class="card-bd"><pre style="max-height:400px;overflow:auto;font-size:12px;background:#f8f9fa;padding:12px;border-radius:4px">{{ output|join('\\n') if output else '暂无日志' }}</pre></div></div>

<div class="mo" id="mRt"><div class="md"><div class="md-hd"><h3>添加路由</h3><button class="md-x" onclick="mc('mRt')">×</button></div>
<div class="md-bd"><div class="fg"><label>网络</label><input id="rNet" placeholder="如: 192.168.1.0/24"></div>
<div class="fg"><label>注释</label><input id="rComment"></div></div>
<div class="md-ft"><button class="btn" onclick="mc('mRt')">取消</button>
<button class="btn btn-p" onclick="api('POST','/api/sv/{{ sid }}/rt',{network:document.getElementById('rNet').value,comment:document.getElementById('rComment').value},function(r){if(r.error)toast(r.error,'r');else{mc('mRt');location.reload()}})">添加</button></div></div></div>
<script>
function svCmd(id,cmd){api('PUT','/api/sv/'+id+'/'+cmd,null,function(r){if(r.error)toast(r.error,'r');else{toast('操作成功');setTimeout(function(){location.reload()},500)}})}
function svSave(){api('PUT','/api/sv/{{ sid }}',{name:document.getElementById('eName').value,port:parseInt(document.getElementById('ePort').value),protocol:document.getElementById('eProto').value,network:document.getElementById('eNet').value,dns_server:document.getElementById('eDns').value,hash:document.getElementById('eHash').value,cipher:document.getElementById('eCipher').value,dh_param_bits:parseInt(document.getElementById('eDh').value),max_clients:parseInt(document.getElementById('eMax').value),vnic:document.getElementById('eVnic').value||null,verb:parseInt(document.getElementById('eVerb').value),keepalive_interval:parseInt(document.getElementById('eKa1').value),keepalive_timeout:parseInt(document.getElementById('eKa2').value),mtu:parseInt(document.getElementById('eMtu').value),txqueuelen:parseInt(document.getElementById('eTxq').value),ping_interval:parseInt(document.getElementById('ePing1').value),ping_timeout:parseInt(document.getElementById('ePing2').value)},function(r){if(r.error)toast(r.error,'r');else toast('保存成功')})}
function svSaveWg(){api('PUT','/api/sv/{{ sid }}',{wg:document.getElementById('eWg').value=='true',wg_port:parseInt(document.getElementById('eWgPort').value)||null,wg_network:document.getElementById('eWgNet').value||null},function(r){if(r.error)toast(r.error,'r');else toast('保存成功')})}
function svSaveDf(){api('PUT','/api/sv/{{ sid }}',{dynamic_firewall:document.getElementById('eDf').value=='true'},function(r){if(r.error)toast(r.error,'r');else toast('保存成功')})}
</script>'''
    return R(tpl, p='s', sid=sid, sv=sv, orgs=orgs, routes=routes, attached_ids=attached_ids, hosts=hosts, bw=bw, output=output)

# ====== 组织 ======
@app.route('/orgs')
@login_req
def orgs_page():
    orgs = api_get('/organization')
    tpl = '''
<div class="card"><div class="card-hd"><h2>组织管理</h2>
<button class="btn btn-p" onclick="mo('mOrg')">+ 创建组织</button></div>
<div class="card-bd"><table><tr><th>名称</th><th>用户数</th><th>操作</th></tr>
{% for o in orgs %}<tr>
<td><a href="/org/{{ oid(o) }}"><b>{{ o.name }}</b></a></td>
<td>{{ o.user_count or '-' }}</td>
<td class="btns"><a href="/org/{{ oid(o) }}" class="btn btn-s">用户</a>
<a href="/org/{{ oid(o) }}/bulk" class="btn btn-s">批量添加</a>
<a href="/org/{{ oid(o) }}/email" class="btn btn-s">发邮件</a>
<button class="btn btn-s btn-d" onclick="cd('{{ o.name }}',function(){api('DELETE','/api/org/{{ oid(o) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})})">删除</button></td>
</tr>{% endfor %}
{% if not orgs %}<tr><td colspan="3" class="empty">暂无组织</td></tr>{% endif %}
</table></div></div>
<div class="mo" id="mOrg"><div class="md"><div class="md-hd"><h3>创建组织</h3><button class="md-x" onclick="mc('mOrg')">×</button></div>
<div class="md-bd"><div class="fg"><label>名称</label><input id="oName"></div></div>
<div class="md-ft"><button class="btn" onclick="mc('mOrg')">取消</button>
<button class="btn btn-p" onclick="api('POST','/api/org',{name:document.getElementById('oName').value},function(r){if(r&&(r.id||(r.id||r._id))){toast('创建成功');location.reload()}else toast('创建失败','r')})">创建</button></div></div></div>'''
    return R(tpl, p='o', orgs=orgs)

# ====== 组织用户 ======
@app.route('/org/<oid>')
@login_req
def org_users(oid):
    org = api_get(f'/organization/{oid}')
    users = api_get(f'/user/{oid}')
    tpl = '''
<div class="card"><div class="card-hd"><h2>{{ org.name }} - 用户管理</h2>
<div class="btns"><a href="/org/{{ oid }}/bulk" class="btn">批量添加</a>
<a href="/org/{{ oid }}/email" class="btn">发邮件</a>
<button class="btn btn-p" onclick="mo('mUsr')">+ 添加用户</button></div></div>
<div class="card-bd"><table><tr><th>用户名</th><th>邮箱</th><th>状态</th><th>操作</th></tr>
{% for u in users %}<tr>
<td><a href="/usr/{{ oid }}/{{ oid(u) }}"><b>{{ u.name }}</b></a></td>
<td>{{ u.email or '-' }}</td>
<td><span class="tag {{'tag-g' if not u.disabled else 'tag-r'}}">{{ '正常' if not u.disabled else '已禁用' }}</span></td>
<td class="btns"><a href="/usr/{{ oid }}/{{ oid(u) }}" class="btn btn-s">详情</a>
<button class="btn btn-s {{'tag-r' if not u.disabled else 'tag-g'}}" onclick="api('PUT','/api/usr/{{ oid }}/{{ oid(u) }}',{disabled:{{ 'true' if not u.disabled else 'false' }}},function(r){if(r.error)toast(r.error,'r');else location.reload()})">{{ '禁用' if not u.disabled else '启用' }}</button>
<button class="btn btn-s btn-d" onclick="cd('{{ u.name }}',function(){api('DELETE','/api/usr/{{ oid }}/{{ oid(u) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})})">删除</button></td>
</tr>{% endfor %}
{% if not users %}<tr><td colspan="4" class="empty">暂无用户</td></tr>{% endif %}
</table></div></div>
<div class="mo" id="mUsr"><div class="md"><div class="md-hd"><h3>添加用户</h3><button class="md-x" onclick="mc('mUsr')">×</button></div>
<div class="md-bd"><div class="fg"><label>用户名</label><input id="uName"></div>
<div class="fg"><label>邮箱</label><input id="uEmail"></div>
<div class="fg"><label>PIN</label><input id="uPin" placeholder="可选"></div></div>
<div class="md-ft"><button class="btn" onclick="mc('mUsr')">取消</button>
<button class="btn btn-p" onclick="api('POST','/api/usr/{{ oid }}',{name:document.getElementById('uName').value,email:document.getElementById('uEmail').value,pin:document.getElementById('uPin').value||null},function(r){if(r&&(r.id||(r.id||r._id))){toast('添加成功');location.reload()}else toast('添加失败','r')})">添加</button></div></div></div>'''
    return R(tpl, p='o', oid=oid, org=org, users=users)

# ====== 用户列表 ======
@app.route('/users')
@login_req
def users_all():
    orgs = api_get('/organization')
    all_users = []
    for o in orgs:
        users = api_get(f'/user/{oid(o)}')
        for u in users:
            u['_org_name'] = o.get('name','')
            u['_org_id'] = o['_id']
            all_users.append(u)
    tpl = '''
<div class="card"><div class="card-hd"><h2>全部用户</h2></div>
<div class="card-bd"><table><tr><th>用户名</th><th>组织</th><th>邮箱</th><th>状态</th><th>操作</th></tr>
{% for u in users %}<tr>
<td><a href="/usr/{{ u._org_id }}/{{ oid(u) }}"><b>{{ u.name }}</b></a></td>
<td>{{ u._org_name }}</td>
<td>{{ u.email or '-' }}</td>
<td><span class="tag {{'tag-g' if not u.disabled else 'tag-r'}}">{{ '正常' if not u.disabled else '已禁用' }}</span></td>
<td><a href="/usr/{{ u._org_id }}/{{ oid(u) }}" class="btn btn-s">详情</a></td>
</tr>{% endfor %}
{% if not users %}<tr><td colspan="5" class="empty">暂无用户</td></tr>{% endif %}
</table></div></div>'''
    return R(tpl, p='u', users=all_users)

# ====== 用户详情 ======
@app.route('/usr/<oid>/<uid>')
@login_req
def user_detail(oid, uid):
    user = api_get(f'/user/{oid}/{uid}')
    org = api_get(f'/organization/{oid}')
    servers = api_get('/server')
    devices = api_get(f'/user/{oid}/{uid}/device')
    keys_info = {}
    for s in servers:
        try:
            r = api.get(f'/key/{oid}/{uid}/{oid(s)}.key')
            if r.status_code == 200:
                keys_info[s['_id']] = r.text[:200]
        except:
            pass
    tpl = '''
<div class="card"><div class="card-hd"><h2>{{ user.name }} - 用户详情</h2>
<div class="btns">
<a href="/data/{{ oid }}/{{ uid }}.tar" class="btn">下载配置(.tar)</a>
<a href="/data/{{ oid }}/{{ uid }}.zip" class="btn">下载配置(.zip)</a>
<a href="/data/{{ oid }}/{{ uid }}.onc" class="btn">下载配置(.onc)</a>
<a href="/usr/{{ oid }}/{{ uid }}/audit" class="btn">审计日志</a>
<button class="btn" onclick="api('PUT','/api/usr/{{ oid }}/{{ uid }}/otp',null,function(r){if(r.error)toast(r.error,'r');else toast('OTP已重置')})">重置OTP</button>
</div></div>
<div class="card-bd">
<div class="fg"><label>用户名</label><input id="eName" value="{{ user.name }}"></div>
<div class="fg"><label>邮箱</label><input id="eEmail" value="{{ user.email or '' }}"></div>
<div class="fg"><label>PIN</label><input id="ePin" value="{{ user.pin or '' }}" placeholder="留空表示无PIN"></div>
<div class="fg"><label>状态</label><select id="eDisabled">
<option value="false" {{'selected' if not user.disabled}}>正常</option>
<option value="true" {{'selected' if user.disabled}}>已禁用</option></select></div>
<div class="fg"><label>分组</label><input id="eGroups" value="{{ user.groups|join(', ') if user.groups else '' }}" placeholder="用逗号分隔"></div>
<div class="fg"><label>绕过二次验证</label><select id="eBypass">
<option value="false" {{'selected' if not user.bypass_secondary}}>否</option>
<option value="true" {{'selected' if user.bypass_secondary}}>是</option></select></div>
<div class="fg"><label>客户端互通</label><select id="eC2c">
<option value="false" {{'selected' if not user.client_to_client}}>否</option>
<option value="true" {{'selected' if user.client_to_client}}>是</option></select></div>
<div class="fg"><label>端口转发</label><textarea id="ePf" rows="3" placeholder="格式: 源端口:目标IP:目标端口/协议">{{ user.port_forwarding|join('\\n') if user.port_forwarding else '' }}</textarea></div>
<button class="btn btn-p" onclick="usrSave()">保存</button>
</div></div>

<div class="card"><div class="card-hd"><h2>关联服务器</h2></div>
<div class="card-bd"><table><tr><th>服务器</th><th>状态</th><th>操作</th></tr>
{% for s in servers %}<tr>
<td>{{ s.name }}</td>
<td>{% if oid(s) in keys_info %}<span class="tag tag-g">已配置</span>{% else %}<span class="tag tag-gray">未配置</span>{% endif %}</td>
<td class="btns">
<a href="/data/{{ oid }}/{{ uid }}.tar" class="btn btn-s">下载</a>
</td></tr>{% endfor %}
</table></div></div>

<div class="card"><div class="card-hd"><h2>设备管理</h2></div>
<div class="card-bd"><table><tr><th>设备ID</th><th>名称</th><th>平台</th><th>操作</th></tr>
{% for d in devices %}<tr>
<td>{{ oid(d) }}</td>
<td>{{ d.name or '-' }}</td>
<td>{{ d.platform or '-' }}</td>
<td><button class="btn btn-s btn-d" onclick="cd('{{ d.name or oid(d) }}',function(){api('DELETE','/api/device/{{ oid }}/{{ uid }}/{{ oid(d) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})})">删除</button></td>
</tr>{% endfor %}
{% if not devices %}<tr><td colspan="4" class="empty">暂无设备</td></tr>{% endif %}
</table></div></div>
<script>
function usrSave(){var pf=document.getElementById('ePf').value.split('\\n').filter(function(x){return x.trim()});api('PUT','/api/usr/{{ oid }}/{{ uid }}',{name:document.getElementById('eName').value,email:document.getElementById('eEmail').value,pin:document.getElementById('ePin').value||null,disabled:document.getElementById('eDisabled').value=='true',groups:document.getElementById('eGroups').value.split(',').map(function(x){return x.trim()}).filter(function(x){return x}),bypass_secondary:document.getElementById('eBypass').value=='true',client_to_client:document.getElementById('eC2c').value=='true',port_forwarding:pf},function(r){if(r.error)toast(r.error,'r');else toast('保存成功')})}
</script>'''
    return R(tpl, p='u', oid=oid, uid=uid, user=user, org=org, servers=servers, devices=devices, keys_info=keys_info)

# ====== 用户审计 ======
@app.route('/usr/<oid>/<uid>/audit')
@login_req
def user_audit(oid, uid):
    user = api_get(f'/user/{oid}/{uid}')
    audit = api_get(f'/user/{oid}/{uid}/audit')
    tpl = '''
<div class="card"><div class="card-hd"><h2>{{ user.name }} - 审计日志</h2></div>
<div class="card-bd"><table><tr><th>时间</th><th>事件</th><th>IP</th><th>详情</th></tr>
{% for a in audit %}<tr>
<td>{{ a.timestamp }}</td>
<td>{{ a.type or a.event }}</td>
<td>{{ a.remote_address or '-' }}</td>
<td>{{ a.message or '-' }}</td>
</tr>{% endfor %}
{% if not audit %}<tr><td colspan="4" class="empty">暂无审计记录</td></tr>{% endif %}
</table></div></div>'''
    return R(tpl, p='u', oid=oid, uid=uid, user=user, audit=audit)

# ====== 批量添加用户 ======
@app.route('/org/<oid>/bulk')
@login_req
def bulk_add_page(oid):
    org = api_get(f'/organization/{oid}')
    tpl = '''
<div class="card"><div class="card-hd"><h2>{{ org.name }} - 批量添加用户</h2></div>
<div class="card-bd">
<div class="fg"><label>用户列表</label><textarea id="bulk" rows="10" placeholder="每行一个用户名，格式: 用户名,邮箱,PIN&#10;例如:&#10;zhangsan,zhangsan@example.com,123456&#10;lisi,lisi@example.com"></textarea>
<div class="tip">支持格式: 用户名 或 用户名,邮箱 或 用户名,邮箱,PIN</div></div>
<button class="btn btn-p" onclick="bulkAdd()">批量添加</button>
<div id="bulkResult" style="margin-top:12px"></div>
</div></div>
<script>
function bulkAdd(){var lines=document.getElementById('bulk').value.split('\\n').filter(function(l){return l.trim()});var results=[];var done=0;
lines.forEach(function(line){var parts=line.split(',');var u={name:parts[0].trim()};if(parts[1])u.email=parts[1].trim();if(parts[2])u.pin=parts[2].trim();
api('POST','/api/usr/{{ oid }}',u,function(r){done++;if(r&&(r.id||(r.id||r._id)))results.push('<span class="tag tag-g">'+u.name+' ✓</span>');else results.push('<span class="tag tag-r">'+u.name+' ✗</span>');
if(done==lines.length)document.getElementById('bulkResult').innerHTML=results.join(' ')})})}
</script>'''
    return R(tpl, p='o', oid=oid, org=org)

# ====== 发送邮件 ======
@app.route('/org/<oid>/email')
@login_req
def email_users_page(oid):
    org = api_get(f'/organization/{oid}')
    tpl = '''
<div class="card"><div class="card-hd"><h2>{{ org.name }} - 发送配置邮件</h2></div>
<div class="card-bd">
<p style="margin-bottom:12px;color:#666">将向组织内所有用户发送VPN配置邮件</p>
<button class="btn btn-p" onclick="api('POST','/api/org/{{ oid }}/email',null,function(r){if(r.error)toast(r.error,'r');else toast('邮件已发送')})">发送邮件</button>
</div></div>'''
    return R(tpl, p='o', oid=oid, org=org)

# ====== 主机管理 ======
@app.route('/hosts')
@login_req
def hosts_page():
    hosts = api_get('/host')
    servers = api_get('/server')
    tpl = '''
<div class="card"><div class="card-hd"><h2>主机管理</h2></div>
<div class="card-bd"><table><tr><th>名称</th><th>地址</th><th>状态</th><th>可用性组</th><th>操作</th></tr>
{% for h in hosts %}<tr>
<td>{{ h.name or oid(h) }}</td>
<td>{{ h.public_address or h.address or '-' }}</td>
<td><span class="tag {{'tag-g' if h.status=='online' else 'tag-r'}}">{{ h.status or '未知' }}</span></td>
<td>{{ h.availability_group or '-' }}</td>
<td class="btns"><button class="btn btn-s" onclick="hostEdit('{{ oid(h) }}')">设置</button></td>
</tr>{% endfor %}
{% if not hosts %}<tr><td colspan="5" class="empty">暂无主机</td></tr>{% endif %}
</table></div></div>
<div class="mo" id="mHost"><div class="md"><div class="md-hd"><h3>主机设置</h3><button class="md-x" onclick="mc('mHost')">×</button></div>
<div class="md-bd">
<div class="fg"><label>公开地址</label><input id="hAddr"></div>
<div class="fg"><label>绑定地址</label><input id="hBind"></div>
<div class="fg"><label>可用性组</label><input id="hAg"></div></div>
<div class="md-ft"><button class="btn" onclick="mc('mHost')">取消</button>
<button class="btn btn-p" onclick="hostSave()">保存</button></div></div></div>
<script>
var hostId='';
function hostEdit(id){hostId=id;api('GET','/api/host/'+id,null,function(h){document.getElementById('hAddr').value=h.public_address||'';document.getElementById('hBind').value=h.bind_address||'';document.getElementById('hAg').value=h.availability_group||'';mo('mHost')})}
function hostSave(){api('PUT','/api/host/'+hostId,{public_address:document.getElementById('hAddr').value,bind_address:document.getElementById('hBind').value,availability_group:document.getElementById('hAg').value},function(r){if(r.error)toast(r.error,'r');else{mc('mHost');toast('保存成功')}})}
</script>'''
    return R(tpl, p='h', hosts=hosts, servers=servers)

# ====== 链接管理 ======
@app.route('/links')
@login_req
def links_page():
    links = api_get('/link')
    tpl = '''
<div class="card"><div class="card-hd"><h2>链接管理</h2>
<button class="btn btn-p" onclick="mo('mLink')">+ 创建链接</button></div>
<div class="card-bd"><table><tr><th>名称</th><th>URI ID</th><th>操作</th></tr>
{% for l in links %}<tr>
<td>{{ l.name or oid(l) }}</td>
<td>{{ l.uri_id or '-' }}</td>
<td class="btns"><button class="btn btn-s" onclick="linkEdit('{{ oid(l) }}')">编辑</button>
<button class="btn btn-s btn-d" onclick="cd('{{ l.name }}',function(){api('DELETE','/api/link/{{ oid(l) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})})">删除</button></td>
</tr>{% endfor %}
{% if not links %}<tr><td colspan="3" class="empty">暂无链接</td></tr>{% endif %}
</table></div></div>
<div class="mo" id="mLink"><div class="md"><div class="md-hd"><h3>创建链接</h3><button class="md-x" onclick="mc('mLink')">×</button></div>
<div class="md-bd"><div class="fg"><label>名称</label><input id="lName"></div></div>
<div class="md-ft"><button class="btn" onclick="mc('mLink')">取消</button>
<button class="btn btn-p" onclick="api('POST','/api/link',{name:document.getElementById('lName').value},function(r){if(r&&(r.id||(r.id||r._id))){toast('创建成功');location.reload()}else toast('创建失败','r')})">创建</button></div></div></div>
<div class="mo" id="mLinkEdit"><div class="md"><div class="md-hd"><h3>编辑链接</h3><button class="md-x" onclick="mc('mLinkEdit')">×</button></div>
<div class="md-bd"><div class="fg"><label>名称</label><input id="leName"></div></div>
<div class="md-ft"><button class="btn" onclick="mc('mLinkEdit')">取消</button>
<button class="btn btn-p" onclick="api('PUT','/api/link/'+linkId,{name:document.getElementById('leName').value},function(r){if(r.error)toast(r.error,'r');else{mc('mLinkEdit');location.reload()}})">保存</button></div></div></div>
<script>
var linkId='';
function linkEdit(id){linkId=id;api('GET','/api/link/'+id,null,function(l){document.getElementById('leName').value=l.name||'';mo('mLinkEdit')})}
</script>'''
    return R(tpl, p='l', links=links)

# ====== 设备管理 ======
@app.route('/devices')
@login_req
def devices_page():
    orgs = api_get('/organization')
    all_devices = []
    for o in orgs:
        users = api_get(f'/user/{oid(o)}')
        for u in users:
            devices = api_get(f'/user/{oid(o)}/{oid(u)}/device')
            for d in devices:
                d['_org'] = o.get('name','')
                d['_user'] = u.get('name','')
                d['_org_id'] = o['_id']
                d['_user_id'] = u['_id']
                all_devices.append(d)
    unregistered = api_get('/device/unregistered')
    tpl = '''
<div class="card"><div class="card-hd"><h2>设备管理</h2></div>
<div class="card-bd"><table><tr><th>设备ID</th><th>名称</th><th>平台</th><th>用户</th><th>组织</th><th>操作</th></tr>
{% for d in devices %}<tr>
<td>{{ oid(d) }}</td>
<td>{{ d.name or '-' }}</td>
<td>{{ d.platform or '-' }}</td>
<td>{{ d._user }}</td>
<td>{{ d._org }}</td>
<td><button class="btn btn-s btn-d" onclick="cd('{{ d.name or oid(d) }}',function(){api('DELETE','/api/device/{{ d._org_id }}/{{ d._user_id }}/{{ oid(d) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})})">删除</button></td>
</tr>{% endfor %}
{% if not devices %}<tr><td colspan="6" class="empty">暂无设备</td></tr>{% endif %}
</table></div></div>

{% if unregistered %}
<div class="card"><div class="card-hd"><h2>未注册设备</h2></div>
<div class="card-bd"><table><tr><th>设备ID</th><th>名称</th><th>平台</th></tr>
{% for d in unregistered %}<tr>
<td>{{ oid(d) }}</td>
<td>{{ d.name or '-' }}</td>
<td>{{ d.platform or '-' }}</td>
</tr>{% endfor %}
</table></div></div>
{% endif %}'''
    return R(tpl, p='dv', devices=all_devices, unregistered=unregistered)

# ====== 管理员 ======
@app.route('/admins')
@login_req
def admins_page():
    admins = api_get('/admin')
    tpl = '''
<div class="card"><div class="card-hd"><h2>管理员管理</h2>
<button class="btn btn-p" onclick="mo('mAdmin')">+ 添加管理员</button></div>
<div class="card-bd"><table><tr><th>用户名</th><th>操作</th></tr>
{% for a in admins %}<tr>
<td>{{ a.username or a.name }}</td>
<td class="btns"><a href="/admin/{{ oid(a) }}/audit" class="btn btn-s">审计</a>
<button class="btn btn-s btn-d" onclick="cd('{{ a.username }}',function(){api('DELETE','/api/admin/{{ oid(a) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})})">删除</button></td>
</tr>{% endfor %}
{% if not admins %}<tr><td colspan="2" class="empty">暂无管理员</td></tr>{% endif %}
</table></div></div>
<div class="mo" id="mAdmin"><div class="md"><div class="md-hd"><h3>添加管理员</h3><button class="md-x" onclick="mc('mAdmin')">×</button></div>
<div class="md-bd"><div class="fg"><label>用户名</label><input id="aName"></div>
<div class="fg"><label>密码</label><input id="aPass" type="password"></div>
<div class="fg"><label>密码(确认)</label><input id="aPass2" type="password"></div></div>
<div class="md-ft"><button class="btn" onclick="mc('mAdmin')">取消</button>
<button class="btn btn-p" onclick="if(document.getElementById('aPass').value!=document.getElementById('aPass2').value){toast('两次密码不一致','r');return}api('POST','/api/admin',{username:document.getElementById('aName').value,password:document.getElementById('aPass').value},function(r){if(r.error)toast(r.error,'r');else{mc('mAdmin');location.reload()}})">添加</button></div></div></div>'''
    return R(tpl, p='a', admins=admins)

# ====== 管理员审计 ======
@app.route('/admin/<aid>/audit')
@login_req
def admin_audit(aid):
    admin = api_get(f'/admin/{aid}')
    audit = api_get(f'/admin/{aid}/audit')
    tpl = '''
<div class="card"><div class="card-hd"><h2>{{ admin.username or admin.name }} - 审计日志</h2></div>
<div class="card-bd"><table><tr><th>时间</th><th>事件</th><th>IP</th><th>详情</th></tr>
{% for a in audit %}<tr>
<td>{{ a.timestamp }}</td>
<td>{{ a.type or a.event }}</td>
<td>{{ a.remote_address or '-' }}</td>
<td>{{ a.message or '-' }}</td>
</tr>{% endfor %}
{% if not audit %}<tr><td colspan="4" class="empty">暂无审计记录</td></tr>{% endif %}
</table></div></div>'''
    return R(tpl, p='a', admin=admin, audit=audit)

# ====== 日志 ======
@app.route('/logs')
@login_req
def logs_page():
    logs = api_get('/log')
    tpl = '''
<div class="card"><div class="card-hd"><h2>系统日志</h2></div>
<div class="card-bd"><table><tr><th>时间</th><th>级别</th><th>消息</th><th>操作</th></tr>
{% for l in logs %}<tr>
<td>{{ l.timestamp }}</td>
<td><span class="tag {{'tag-r' if l.level=='error' else 'tag-b' if l.level=='warning' else 'tag-gray'}}">{{ l.level }}</span></td>
<td>{{ l.message }}</td>
<td><button class="btn btn-s btn-d" onclick="api('DELETE','/api/log/{{ oid(l) }}',null,function(r){if(r.error)toast(r.error,'r');else location.reload()})">删除</button></td>
</tr>{% endfor %}
{% if not logs %}<tr><td colspan="4" class="empty">暂无日志</td></tr>{% endif %}
</table></div></div>'''
    return R(tpl, p='cfg', logs=logs)

# ====== 审计 ======
@app.route('/audit')
@login_req
def audit_page():
    audit = api_get('/audit')
    tpl = '''
<div class="card"><div class="card-hd"><h2>审计日志</h2></div>
<div class="card-bd"><table><tr><th>时间</th><th>事件</th><th>用户</th><th>IP</th><th>详情</th></tr>
{% for a in audit %}<tr>
<td>{{ a.timestamp }}</td>
<td>{{ a.type or a.event }}</td>
<td>{{ a.user_name or '-' }}</td>
<td>{{ a.remote_address or '-' }}</td>
<td>{{ a.message or '-' }}</td>
</tr>{% endfor %}
{% if not audit %}<tr><td colspan="5" class="empty">暂无审计记录</td></tr>{% endif %}
</table></div></div>'''
    return R(tpl, p='cfg', audit=audit)

# ====== 设置 ======
@app.route('/settings')
@login_req
def settings_page():
    settings = api_get('/settings')
    tpl = '''
<div class="card"><div class="card-hd"><h2>系统设置</h2></div>
<div class="card-bd">
<h3 style="margin-bottom:12px;font-size:14px">基本设置</h3>
<div class="fg"><label>服务器名称</label><input id="sName" value="{{ settings.server_name or '' }}"></div>
<div class="fg"><label>主题</label><select id="sTheme">
<option value="light" {{'selected' if settings.theme=='light'}}>浅色</option>
<option value="dark" {{'selected' if settings.theme=='dark'}}>深色</option></select></div>
<div class="fg"><label>自动更新</label><select id="sUpdate">
<option value="false" {{'selected' if not settings.auto_update}}>关闭</option>
<option value="true" {{'selected' if settings.auto_update}}>开启</option></select></div>

<h3 style="margin:16px 0 12px;font-size:14px">Let's Encrypt SSL</h3>
<div class="fg"><label>域名</label><input id="sLeDomain" value="{{ settings.lets_encrypt_domain or '' }}" placeholder="如: vpn.example.com"></div>

<h3 style="margin:16px 0 12px;font-size:14px">SSO配置</h3>
<div class="fg"><label>SSO模式</label><select id="sSso">
<option value="" {{'selected' if not settings.sso}}>关闭</option>
<option value="saml" {{'selected' if settings.sso=='saml'}}>SAML</option>
<option value="google" {{'selected' if settings.sso=='google'}}>Google</option>
<option value="azure" {{'selected' if settings.sso=='azure'}}>Azure</option>
<option value="slack" {{'selected' if settings.sso=='slack'}}>Slack</option>
<option value="okta" {{'selected' if settings.sso=='okta'}}>Okta</option>
<option value="onelogin" {{'selected' if settings.sso=='onelogin'}}>OneLogin</option>
<option value="jumpcloud" {{'selected' if settings.sso=='jumpcloud'}}>JumpCloud</option>
<option value="duo" {{'selected' if settings.sso=='duo'}}>Duo</option>
<option value="radius" {{'selected' if settings.sso=='radius'}}>Radius</option></select></div>
<div class="fg"><label>SSO组织</label><input id="sSsoOrg" value="{{ settings.sso_org or '' }}"></div>
<div class="fg"><label>SAML SSO URL</label><input id="sSamlUrl" value="{{ settings.saml_sso_url or '' }}"></div>
<div class="fg"><label>SAML Issuer</label><input id="sSamlIssuer" value="{{ settings.saml_issuer or '' }}"></div>
<div class="fg"><label>SAML Certificate</label><textarea id="sSamlCert" rows="4">{{ settings.saml_certificate or '' }}</textarea></div>
<div class="fg"><label>Duo Integration Key</label><input id="sDuoIkey" value="{{ settings.duo_ikey or '' }}"></div>
<div class="fg"><label>Duo Secret Key</label><input id="sDuoSkey" value="{{ settings.duo_skey or '' }}"></div>
<div class="fg"><label>Duo API Hostname</label><input id="sDuoApi" value="{{ settings.duo_api_hostname or '' }}"></div>
<div class="fg"><label>Radius服务器</label><input id="sRadius" value="{{ settings.radius_server or '' }}"></div>
<div class="fg"><label>Radius密钥</label><input id="sRadiusSecret" value="{{ settings.radius_secret or '' }}"></div>

<h3 style="margin:16px 0 12px;font-size:14px">邮件设置</h3>
<div class="fg"><label>SMTP服务器</label><input id="sSmtp" value="{{ settings.smtp_server or '' }}"></div>
<div class="fg"><label>SMTP端口</label><input id="sSmtpPort" type="number" value="{{ settings.smtp_port or 587 }}"></div>
<div class="fg"><label>SMTP用户名</label><input id="sSmtpUser" value="{{ settings.smtp_username or '' }}"></div>
<div class="fg"><label>SMTP密码</label><input id="sSmtpPass" type="password" value="{{ settings.smtp_password or '' }}"></div>
<div class="fg"><label>发件人邮箱</label><input id="sSmtpFrom" value="{{ settings.smtp_from_email or '' }}"></div>

<h3 style="margin:16px 0 12px;font-size:14px">认证设置</h3>
<div class="fg"><label>SSO客户端域名</label><input id="sSsoDomain" value="{{ settings.sso_client_domain or '' }}"></div>
<div class="fg"><label>DH参数位数</label><select id="sDhBits">
<option value="1536" {{'selected' if settings.dh_param_bits==1536}}>1536</option>
<option value="2048" {{'selected' if settings.dh_param_bits==2048}}>2048</option>
<option value="4096" {{'selected' if settings.dh_param_bits==4096}}>4096</option></select></div>

<button class="btn btn-p" onclick="saveSettings()">保存设置</button>
</div></div>
<script>
function saveSettings(){var d={server_name:document.getElementById('sName').value,theme:document.getElementById('sTheme').value,auto_update:document.getElementById('sUpdate').value=='true',lets_encrypt_domain:document.getElementById('sLeDomain').value,sso:document.getElementById('sSso').value,sso_org:document.getElementById('sSsoOrg').value,saml_sso_url:document.getElementById('sSamlUrl').value,saml_issuer:document.getElementById('sSamlIssuer').value,saml_certificate:document.getElementById('sSamlCert').value,duo_ikey:document.getElementById('sDuoIkey').value,duo_skey:document.getElementById('sDuoSkey').value,duo_api_hostname:document.getElementById('sDuoApi').value,radius_server:document.getElementById('sRadius').value,radius_secret:document.getElementById('sRadiusSecret').value,smtp_server:document.getElementById('sSmtp').value,smtp_port:parseInt(document.getElementById('sSmtpPort').value),smtp_username:document.getElementById('sSmtpUser').value,smtp_password:document.getElementById('sSmtpPass').value,smtp_from_email:document.getElementById('sSmtpFrom').value,sso_client_domain:document.getElementById('sSsoDomain').value,dh_param_bits:parseInt(document.getElementById('sDhBits').value)};api('PUT','/api/settings',d,function(r){if(r.error)toast(r.error,'r');else toast('保存成功')})}
</script>'''
    return R(tpl, p='cfg', settings=settings)

# ====== API路由 ======
@app.route('/api/org', methods=['POST'])
@login_req
def api_org_c():
    d = request.get_json(silent=True) or {}
    r = api.post('/organization', d)
    return jsonify(r.json() if r and r.status_code==200 else {'error':'创建失败'}), (200 if r and r.status_code==200 else 400)

@app.route('/api/org/<oid>', methods=['PUT'])
@login_req
def api_org_u(oid):
    d = request.get_json(silent=True) or {}
    r = api.put(f'/organization/{oid}', d)
    return jsonify(r.json() if r and r.status_code==200 else {'error':'更新失败'}), (200 if r and r.status_code==200 else 400)

@app.route('/api/org/<oid>', methods=['DELETE'])
@login_req
def api_org_d(oid):
    return jsonify({'ok': api_del(f'/organization/{oid}')})

@app.route('/api/usr/<oid>', methods=['POST'])
@login_req
def api_usr_c(oid):
    d = request.get_json(silent=True) or {}
    r = api.post(f'/user/{oid}', d)
    return jsonify(r.json() if r and r.status_code==200 else {'error':'创建失败'}), (200 if r and r.status_code==200 else 400)

@app.route('/api/usr/<oid>/<uid>', methods=['PUT'])
@login_req
def api_usr_u(oid, uid):
    d = request.get_json(silent=True) or {}
    r = api.put(f'/user/{oid}/{uid}', d)
    return jsonify(r.json() if r and r.status_code==200 else {'error':'更新失败'}), (200 if r and r.status_code==200 else 400)

@app.route('/api/usr/<oid>/<uid>', methods=['DELETE'])
@login_req
def api_usr_d(oid, uid):
    return jsonify({'ok': api_del(f'/user/{oid}/{uid}')})

@app.route('/api/usr/<oid>/<uid>/otp', methods=['PUT'])
@login_req
def api_usr_reset_otp(oid, uid):
    r = api.put(f'/user/{oid}/{uid}/otp_secret')
    return jsonify(r.json() if r and r.status_code==200 else {'error':'重置失败'})

@app.route('/api/usr/<oid>/<uid>/device/<did>', methods=['DELETE'])
@login_req
def api_usr_device_d(oid, uid, did):
    return jsonify({'ok': api_del(f'/user/{oid}/{uid}/device/{did}')})

@app.route('/api/sv', methods=['POST'])
@login_req
def api_sv_c():
    d = request.get_json(silent=True) or {}
    r = api.post('/server', d)
    return jsonify(r.json() if r and r.status_code==200 else {'error':'创建失败'}), (200 if r and r.status_code==200 else 400)

@app.route('/api/sv/<sid>', methods=['PUT'])
@login_req
def api_sv_u(sid):
    d = request.get_json(silent=True) or {}
    r = api.put(f'/server/{sid}', d)
    return jsonify(r.json() if r and r.status_code==200 else {'error':'更新失败'}), (200 if r and r.status_code==200 else 400)

@app.route('/api/sv/<sid>', methods=['DELETE'])
@login_req
def api_sv_d(sid):
    return jsonify({'ok': api_del(f'/server/{sid}')})

@app.route('/api/sv/<sid>/start', methods=['PUT'])
@login_req
def api_sv_start(sid):
    return jsonify(api_put(f'/server/{sid}/start') or {'error':'启动失败'})

@app.route('/api/sv/<sid>/stop', methods=['PUT'])
@login_req
def api_sv_stop(sid):
    return jsonify(api_put(f'/server/{sid}/stop') or {'error':'停止失败'})

@app.route('/api/sv/<sid>/restart', methods=['PUT'])
@login_req
def api_sv_restart(sid):
    return jsonify(api_put(f'/server/{sid}/restart') or {'error':'重启失败'})

@app.route('/api/sv/<sid>/rt', methods=['POST'])
@login_req
def api_rt_c(sid):
    d = request.get_json(silent=True) or {}
    r = api.post(f'/server/{sid}/route', d)
    return jsonify(r.json() if r and r.status_code==200 else {'error':'添加失败'})

@app.route('/api/sv/<sid>/rt/<path:net>', methods=['DELETE'])
@login_req
def api_rt_d(sid, net):
    return jsonify({'ok': api_del(f'/server/{sid}/route/{net}')})

@app.route('/api/sv/<sid>/org/<oid>', methods=['PUT'])
@login_req
def api_org_attach(sid, oid):
    return jsonify(api_put(f'/server/{sid}/organization/{oid}') or {'error':'关联失败'})

@app.route('/api/sv/<sid>/org/<oid>', methods=['DELETE'])
@login_req
def api_org_detach(sid, oid):
    return jsonify({'ok': api_del(f'/server/{sid}/organization/{oid}')})

@app.route('/api/sv/<sid>/output', methods=['DELETE'])
@login_req
def api_sv_output_d(sid):
    return jsonify({'ok': api_del(f'/server/{sid}/output')})

@app.route('/api/sv/<sid>/bw/<period>')
@login_req
def api_sv_bw(sid, period):
    return jsonify(api_get(f'/server/{sid}/bandwidth/{period}'))

@app.route('/api/host/<hid>', methods=['GET','PUT'])
@login_req
def api_host(hid):
    if request.method == 'PUT':
        d = request.get_json(silent=True) or {}
        r = api.put(f'/host/{hid}', d)
        return jsonify(r.json() if r and r.status_code==200 else {'error':'更新失败'})
    return jsonify(api_get(f'/host/{hid}'))

@app.route('/api/sv/<sid>/host/<hid>', methods=['PUT'])
@login_req
def api_host_attach(sid, hid):
    return jsonify(api_put(f'/server/{sid}/host/{hid}') or {'error':'关联失败'})

@app.route('/api/sv/<sid>/host/<hid>', methods=['DELETE'])
@login_req
def api_host_detach(sid, hid):
    return jsonify({'ok': api_del(f'/server/{sid}/host/{hid}')})

@app.route('/api/link', methods=['POST'])
@login_req
def api_link_c():
    d = request.get_json(silent=True) or {}
    r = api.post('/link', d)
    return jsonify(r.json() if r and r.status_code==200 else {'error':'创建失败'})

@app.route('/api/link/<lid>', methods=['GET','PUT','DELETE'])
@login_req
def api_link(lid):
    if request.method == 'GET':
        return jsonify(api_get(f'/link/{lid}'))
    elif request.method == 'PUT':
        d = request.get_json(silent=True) or {}
        r = api.put(f'/link/{lid}', d)
        return jsonify(r.json() if r and r.status_code==200 else {'error':'更新失败'})
    return jsonify({'ok': api_del(f'/link/{lid}')})

@app.route('/api/link/<lid>/location', methods=['GET','POST'])
@login_req
def api_link_locs(lid):
    if request.method == 'GET':
        return jsonify(api_get(f'/link/{lid}/location'))
    d = request.get_json(silent=True) or {}
    r = api.post(f'/link/{lid}/location', d)
    return jsonify(r.json() if r and r.status_code==200 else {'error':'创建失败'})

@app.route('/api/link/<lid>/location/<locid>', methods=['PUT','DELETE'])
@login_req
def api_link_loc(lid, locid):
    if request.method == 'PUT':
        d = request.get_json(silent=True) or {}
        r = api.put(f'/link/{lid}/location/{locid}', d)
        return jsonify(r.json() if r and r.status_code==200 else {'error':'更新失败'})
    return jsonify({'ok': api_del(f'/link/{lid}/location/{locid}')})

@app.route('/api/device/<oid>/<uid>/<did>', methods=['DELETE'])
@login_req
def api_device_d(oid, uid, did):
    return jsonify({'ok': api_del(f'/user/{oid}/{uid}/device/{did}')})

@app.route('/api/settings', methods=['GET','PUT'])
@login_req
def api_settings():
    if request.method == 'PUT':
        d = request.get_json(silent=True) or {}
        r = api.put('/settings', d)
        return jsonify(r.json() if r and r.status_code==200 else {'error':'保存失败'})
    return jsonify(api_get('/settings'))

@app.route('/api/admin', methods=['GET','POST'])
@login_req
def api_admin_list():
    if request.method == 'POST':
        d = request.get_json(silent=True) or {}
        r = api.post('/admin', d)
        return jsonify(r.json() if r and r.status_code==200 else {'error':'添加失败'})
    return jsonify(api_get('/admin'))

@app.route('/api/admin/<aid>', methods=['DELETE'])
@login_req
def api_admin_del(aid):
    return jsonify({'ok': api_del(f'/admin/{aid}')})

@app.route('/api/org/<oid>/email', methods=['POST'])
@login_req
def api_org_email(oid):
    r = api.post(f'/organization/{oid}/email')
    return jsonify(r.json() if r and r.status_code==200 else {'error':'发送失败'})

@app.route('/api/log/<lid>', methods=['DELETE'])
@login_req
def api_log_d(lid):
    return jsonify({'ok': api_del(f'/log/{lid}')})

# ====== 密钥下载 ======
@app.route('/data/<oid>/<uid>.tar')
@login_req
def dl_profile_tar(oid, uid):
    r = api.get(f'/data/{oid}/{uid}.tar')
    if r.status_code == 200:
        return send_file(io.BytesIO(r.content), mimetype='application/x-tar', as_attachment=True, download_name=f'{uid}.tar')
    return '下载失败', 404

@app.route('/data/<oid>/<uid>.zip')
@login_req
def dl_profile_zip(oid, uid):
    r = api.get(f'/data/{oid}/{uid}.zip')
    if r.status_code == 200:
        return send_file(io.BytesIO(r.content), mimetype='application/zip', as_attachment=True, download_name=f'{uid}.zip')
    return '下载失败', 404

@app.route('/data/<oid>/<uid>.onc')
@login_req
def dl_profile_onc(oid, uid):
    r = api.get(f'/data/{oid}/{uid}.onc')
    if r.status_code == 200:
        return send_file(io.BytesIO(r.content), mimetype='application/json', as_attachment=True, download_name=f'{uid}.onc')
    return '下载失败', 404

# ====== 状态/事件 ======
@app.route('/status')
@login_req
def status_page():
    status = api_get('/status')
    tpl = '''
<div class="card"><div class="card-hd"><h2>系统状态</h2></div>
<div class="card-bd">
<pre style="font-size:12px;background:#f8f9fa;padding:12px;border-radius:4px">{{ status|tojson(indent=2) }}</pre>
</div></div>'''
    return R(tpl, p='cfg', status=status)

@app.route('/events')
@login_req
def events_page():
    events = api_get('/event')
    tpl = '''
<div class="card"><div class="card-hd"><h2>事件通知</h2></div>
<div class="card-bd"><table><tr><th>时间</th><th>类型</th><th>详情</th></tr>
{% for e in events %}<tr>
<td>{{ e.timestamp }}</td>
<td>{{ e.type }}</td>
<td>{{ e.message or '-' }}</td>
</tr>{% endfor %}
{% if not events %}<tr><td colspan="3" class="empty">暂无事件</td></tr>{% endif %}
</table></div></div>'''
    return R(tpl, p='cfg', events=events)

# ====== 订阅管理 ======
@app.route('/subscription')
@login_req
def subscription_page():
    sub = api_get('/subscription')
    tpl = '''
<div class="card"><div class="card-hd"><h2>订阅管理</h2></div>
<div class="card-bd">
<pre style="font-size:12px;background:#f8f9fa;padding:12px;border-radius:4px">{{ sub|tojson(indent=2) if sub else '无订阅信息' }}</pre>
</div></div>'''
    return R(tpl, p='cfg', sub=sub)

# ====== Ping ======
@app.route('/ping')
def ping():
    r = api.get('/ping')
    try:
        return jsonify(r.json() if r.status_code==200 else {'error': 'unavailable'})
    except:
        return jsonify({'status': 'ok' if r.status_code==200 else 'error'})

# ====== 服务器输出 ======
@app.route('/sv/<sid>/output')
@login_req
def sv_output(sid):
    sv = api_get(f'/server/{sid}')
    output = api_get(f'/server/{sid}/output')
    link_output = api_get(f'/server/{sid}/link_output')
    tpl = '''
<div class="card"><div class="card-hd"><h2>{{ sv.name }} - 服务器输出</h2>
<div class="btns">
<button class="btn btn-d" onclick="api('DELETE','/api/sv/{{ sid }}/output',null,function(){location.reload()})">清空日志</button>
</div></div>
<div class="card-bd">
<h3 style="margin-bottom:8px;font-size:13px">服务器日志</h3>
<pre style="max-height:400px;overflow:auto;font-size:12px;background:#f8f9fa;padding:12px;border-radius:4px">{{ output|join('\\n') if output else '暂无日志' }}</pre>
{% if link_output %}
<h3 style="margin:16px 0 8px;font-size:13px">链接输出</h3>
<pre style="max-height:200px;overflow:auto;font-size:12px;background:#f8f9fa;padding:12px;border-radius:4px">{{ link_output|join('\\n') }}</pre>
{% endif %}
</div></div>'''
    return R(tpl, p='s', sid=sid, sv=sv, output=output, link_output=link_output)

# ====== 启动 ======
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=LISTEN_PORT, debug=False)
