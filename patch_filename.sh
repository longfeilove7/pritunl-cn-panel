#!/bin/bash
# Pritunl 中文文件名补丁
# 修改下载文件名支持中文字符
# 用法: bash patch_filename.sh [rollback]

KEY_FILE="/usr/lib/pritunl/usr/lib/python3.9/site-packages/pritunl/handlers/key.py"
BACKUP_FILE="${KEY_FILE}.bak"

rollback() {
    if [ -f "$BACKUP_FILE" ]; then
        cp "$BACKUP_FILE" "$KEY_FILE"
        echo "已回滚到原始版本"
        systemctl restart pritunl
        echo "Pritunl已重启"
    else
        echo "没有找到备份文件"
        exit 1
    fi
}

if [ "$1" = "rollback" ]; then
    rollback
    exit 0
fi

# 检查是否已打补丁
if grep -q "filename\*=UTF-8" "$KEY_FILE" 2>/dev/null; then
    echo "补丁已应用，跳过"
    exit 0
fi

# 备份原始文件
if [ ! -f "$BACKUP_FILE" ]; then
    cp "$KEY_FILE" "$BACKUP_FILE"
    echo "已备份原始文件到 $BACKUP_FILE"
fi

# 检查是否需要添加 urllib.parse 导入
if ! grep -q "import urllib.parse" "$KEY_FILE"; then
    sed -i 's/^import flask$/import flask\nimport urllib.parse/' "$KEY_FILE"
    echo "已添加 urllib.parse 导入"
fi

# 应用补丁：将 ASCII-only 文件名改为同时支持 UTF-8
# 原始: filename="X.tar" (ASCII only)
# 补丁: filename="X.tar"; filename*=UTF-8''Y.tar (ASCII fallback + UTF-8)

python3 << 'PYEOF'
import re

filepath = "/usr/lib/pritunl/usr/lib/python3.9/site-packages/pritunl/handlers/key.py"

with open(filepath, 'r') as f:
    content = f.read()

# Patch _get_key_tar_archive
old = """    response.headers.add('Content-Disposition',
        'attachment; filename="%s.tar"' %
        unicodedata.normalize(
            'NFKD', usr.name).encode('ascii', 'ignore').decode())
    return (usr, response)"""

new = """    ascii_name = unicodedata.normalize('NFKD', usr.name).encode('ascii', 'ignore').decode() or 'user'
    utf8_name = urllib.parse.quote(usr.name)
    response.headers.add('Content-Disposition',
        "attachment; filename=\\"%s.tar\\"; filename*=UTF-8''%s.tar" % (ascii_name, utf8_name))
    return (usr, response)"""

content = content.replace(old, new)

# Patch _get_key_zip_archive
old = """    response.headers.add('Content-Disposition',
        'attachment; filename="%s_%s.zip"' % (
            unicodedata.normalize(
                'NFKD', org.name).encode('ascii', 'ignore').decode(),
            unicodedata.normalize(
                'NFKD', usr.name).encode('ascii', 'ignore').decode(),"""

new = """    ascii_org = unicodedata.normalize('NFKD', org.name).encode('ascii', 'ignore').decode() or 'org'
    ascii_usr = unicodedata.normalize('NFKD', usr.name).encode('ascii', 'ignore').decode() or 'user'
    utf8_org = urllib.parse.quote(org.name)
    utf8_usr = urllib.parse.quote(usr.name)
    response.headers.add('Content-Disposition',
        "attachment; filename=\\"%s_%s.zip\\"; filename*=UTF-8''%s_%s.zip" % (ascii_org, ascii_usr, utf8_org, utf8_usr),"""

content = content.replace(old, new)

# Patch _get_key_onc_archive
old = """    response.headers.add('Content-Disposition',
        'attachment; filename="%s_%s.onc"' % (
            unicodedata.normalize(
                'NFKD', org.name).encode('ascii', 'ignore').decode(),
            unicodedata.normalize(
                'NFKD', usr.name).encode('ascii', 'ignore').decode(),"""

new = """    ascii_org = unicodedata.normalize('NFKD', org.name).encode('ascii', 'ignore').decode() or 'org'
    ascii_usr = unicodedata.normalize('NFKD', usr.name).encode('ascii', 'ignore').decode() or 'user'
    utf8_org = urllib.parse.quote(org.name)
    utf8_usr = urllib.parse.quote(usr.name)
    response.headers.add('Content-Disposition',
        "attachment; filename=\\"%s_%s.onc\\"; filename*=UTF-8''%s_%s.onc" % (ascii_org, ascii_usr, utf8_org, utf8_usr),"""

content = content.replace(old, new)

with open(filepath, 'w') as f:
    f.write(content)

print("补丁已应用")
PYEOF

# 验证补丁
if grep -q "urllib.parse.quote" "$KEY_FILE"; then
    echo "补丁验证成功"
    systemctl restart pritunl
    echo "Pritunl已重启"
else
    echo "补丁验证失败，请检查"
    exit 1
fi
