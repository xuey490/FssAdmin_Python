# FssAdmin后台管理系统(Python版）

当前目录已建立基于 `FastAPI + Starlette + SQLAlchemy 2` 的基础运行骨架，所有新代码均限制在 `fastapi` 目录内。

windows环境

## 1. 创建并激活虚拟环境
### Windows PowerShell
```powershell
python -m venv .venv
.venv\Scripts\activate
```

# 安装依赖
pip install -r ./requirements.txt


## 2. 安装依赖
```powershell
python -m pip install -r requirements.txt
```

## 3. 初始化环境变量
复制 `.env.example` 为 `.env` 后按实际数据库和 Redis 配置修改。

## 4. 启动开发服务
```powershell
.\.venv\Scripts\python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8001
```


### 第一次在本机跑起来

1. 复制 `env/.env.dev.example` → `env/.env.dev`，填写数据库、Redis 等（先在 DB 中建好空库）,导入数据库。
2. 在 **`backend/` 目录下** 安装依赖：推荐 **`uv sync`**；或 `pip install -r requirements.txt`。
3. **启动**：`uv run main.py run --env=dev`（或 `python main.py run --env=dev`）。
4. 接口文档示例：`http://127.0.0.1:8001/docs`（端口见 `.env.dev` 中 `SERVER_PORT`）。

Remove-Item -Recurse -Force .venv
uv venv
.\.venv\Scripts\Activate
uv run main.py run --env=dev


1、运行 which uv，得到：/root/.local/bin/uv
2、建立一个启动文件， 内容如下
```
#!/bin/bash
cd /www/wwwroot/fastapi-admin || exit 1
export PATH="/root/.local/bin:/usr/local/bin:$PATH"
# 把下面路径改成 which uv 的结果
exec /root/.local/bin/uv run main.py run --env=dev
```
宝塔的进程管理器：
启动命令：/www/wwwroot/fastapi-admin/start.sh（必须绝对路径）
进程目录：/www/wwwroot/fastapi-admin/
启动用户：若 uv 在 root 下、项目也是 root 部署，先用 root 能跑通再考虑 www
保存后点启动
注意： --env=prod 才会 reload=False，进程会一直挂着。--env=dev 会起一个文件监视父进程，Supervisor 很容易把子进程当成崩溃，反复 BACKOFF。


