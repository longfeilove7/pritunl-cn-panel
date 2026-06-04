"""Pritunl API Client - 封装Pritunl内部API"""
import requests
import json
import time
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PritunlAPI:
    """Pritunl API客户端，通过Cookie认证调用内部API"""
    
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.token = None
    
    def login(self):
        """登录获取session cookie和CSRF token"""
        resp = self.session.post(
            f'{self.base_url}/auth/session',
            json={'username': self.username, 'password': self.password}
        )
        data = resp.json()
        if not data.get('authenticated'):
            raise Exception(f"登录失败: {data.get('error_msg', '未知错误')}")
        self.token = resp.headers.get('X-Csrf-Token', '')
        return True
    
    def _headers(self):
        """构建请求头"""
        h = {'Content-Type': 'application/json'}
        if self.token:
            h['X-Csrf-Token'] = self.token
        return h
    
    def _request(self, method, path, data=None):
        """发送API请求，自动重试登录"""
        url = f'{self.base_url}{path}'
        for attempt in range(2):
            resp = self.session.request(
                method, url, headers=self._headers(),
                json=data if data else None
            )
            if resp.status_code == 401 and attempt == 0:
                self.login()
                continue
            return resp
        return resp
    
    def get(self, path):
        return self._request('GET', path)
    
    def post(self, path, data=None):
        return self._request('POST', path, data)
    
    def put(self, path, data=None):
        return self._request('PUT', path, data)
    
    def delete(self, path):
        return self._request('DELETE', path)
    
    # ====== 组织管理 ======
    def get_organizations(self):
        resp = self.get('/organization')
        return resp.json() if resp.status_code == 200 else []
    
    def get_organization(self, org_id):
        resp = self.get(f'/organization/{org_id}')
        return resp.json() if resp.status_code == 200 else None
    
    def create_organization(self, name):
        resp = self.post('/organization', {'name': name})
        return resp.json() if resp.status_code == 200 else None
    
    def update_organization(self, org_id, name):
        resp = self.put(f'/organization/{org_id}', {'name': name})
        return resp.json() if resp.status_code == 200 else None
    
    def delete_organization(self, org_id):
        resp = self.delete(f'/organization/{org_id}')
        return resp.status_code == 200
    
    # ====== 用户管理 ======
    def get_users(self, org_id):
        resp = self.get(f'/user/{org_id}')
        return resp.json() if resp.status_code == 200 else []
    
    def get_user(self, org_id, user_id):
        resp = self.get(f'/user/{org_id}/{user_id}')
        return resp.json() if resp.status_code == 200 else None
    
    def create_user(self, org_id, user_data):
        resp = self.post(f'/user/{org_id}', user_data)
        return resp.json() if resp.status_code == 200 else None
    
    def update_user(self, org_id, user_id, user_data):
        resp = self.put(f'/user/{org_id}/{user_id}', user_data)
        return resp.json() if resp.status_code == 200 else None
    
    def delete_user(self, org_id, user_id):
        resp = self.delete(f'/user/{org_id}/{user_id}')
        return resp.status_code == 200
    
    def get_user_audit(self, org_id, user_id):
        resp = self.get(f'/user/{org_id}/{user_id}/audit')
        return resp.json() if resp.status_code == 200 else []
    
    # ====== 服务器管理 ======
    def get_servers(self):
        resp = self.get('/server')
        return resp.json() if resp.status_code == 200 else []
    
    def get_server(self, server_id):
        resp = self.get(f'/server/{server_id}')
        return resp.json() if resp.status_code == 200 else None
    
    def create_server(self, server_data):
        resp = self.post('/server', server_data)
        return resp.json() if resp.status_code == 200 else None
    
    def update_server(self, server_id, server_data):
        resp = self.put(f'/server/{server_id}', server_data)
        return resp.json() if resp.status_code == 200 else None
    
    def delete_server(self, server_id):
        resp = self.delete(f'/server/{server_id}')
        return resp.status_code == 200
    
    def start_server(self, server_id):
        resp = self.put(f'/server/{server_id}/start')
        return resp.json() if resp.status_code == 200 else None
    
    def stop_server(self, server_id):
        resp = self.put(f'/server/{server_id}/stop')
        return resp.json() if resp.status_code == 200 else None
    
    def restart_server(self, server_id):
        resp = self.put(f'/server/{server_id}/restart')
        return resp.json() if resp.status_code == 200 else None
    
    # ====== 服务器-组织绑定 ======
    def get_server_orgs(self, server_id):
        resp = self.get(f'/server/{server_id}/organization')
        return resp.json() if resp.status_code == 200 else []
    
    def attach_org(self, server_id, org_id):
        resp = self.put(f'/server/{server_id}/organization/{org_id}')
        return resp.status_code == 200
    
    def detach_org(self, server_id, org_id):
        resp = self.delete(f'/server/{server_id}/organization/{org_id}')
        return resp.status_code == 200
    
    # ====== 路由管理 ======
    def get_routes(self, server_id):
        resp = self.get(f'/server/{server_id}/route')
        return resp.json() if resp.status_code == 200 else []
    
    def add_route(self, server_id, network, nat=True, comment=''):
        resp = self.post(f'/server/{server_id}/route', {
            'network': network, 'nat': nat, 'comment': comment
        })
        return resp.json() if resp.status_code == 200 else None
    
    def delete_route(self, server_id, network):
        resp = self.delete(f'/server/{server_id}/route/{network}')
        return resp.status_code == 200
    
    # ====== 用户配置下载 ======
    def get_user_profile_url(self, org_id, user_id):
        return f'{self.base_url}/data/{org_id}/{user_id}.tar'
    
    def get_user_profile_uri(self, org_id, user_id):
        """获取用户的URI链接（用于Pritunl客户端导入）"""
        resp = self.get(f'/data/{org_id}/{user_id}')
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get('uri', '')
        return ''
    
    # ====== 设置 ======
    def get_settings(self):
        resp = self.get('/settings')
        return resp.json() if resp.status_code == 200 else {}
    
    # ====== 状态 ======
    def get_state(self):
        resp = self.get('/state')
        return resp.json() if resp.status_code == 200 else {}
