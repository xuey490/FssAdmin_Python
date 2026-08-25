import httpx

base = "http://127.0.0.1:8181"
r = httpx.post(
    base + "/core/login",
    json={"username": "admin", "password": "123456", "tenant_id": 1, "code": "1", "uuid": "x"},
    timeout=30,
)
print("login", r.status_code, r.json().get("code"), list((r.json().get("data") or {}).keys()))
data = r.json().get("data") or {}
token = data.get("access_token")
h = {"Authorization": f"Bearer {token}", "X-Tenant-Id": "1"}

checks = [
    ("GET", "/core/tenants-by-username?username=admin"),
    ("GET", "/core/system/user"),
    ("GET", "/core/system/menu"),
    ("GET", "/core/system/permissions"),
    ("GET", "/system/user/list?page=1&limit=3"),
    ("GET", "/system/dept/tree"),
    ("GET", "/system/dept/access-dept"),
    ("GET", "/system/role/list?page=1&limit=3"),
    ("GET", "/system/role/access-role"),
    ("GET", "/system/menu/tree"),
    ("GET", "/system/menu/access-menu"),
    ("GET", "/system/tenant/list?page=1&limit=3"),
    ("GET", "/core/server/monitor"),
    ("GET", "/core/server/redis"),
    ("GET", "/monitor/online/list?page=1&limit=10"),
]
for method, path in checks:
    rr = httpx.request(method, base + path, headers=h, timeout=30)
    body = rr.json()
    code = body.get("code")
    preview = str(body.get("data"))[:80]
    print(f"{path} -> http={rr.status_code} code={code} data={preview}")
