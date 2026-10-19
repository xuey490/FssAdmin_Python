# FssAdmin后台管理系统(Python版）

当前目录已建立基于 `FastAPI + Starlette + SQLAlchemy 2` 的基础运行骨架，所有新代码均限制在 `fastapi` 目录内。

windows环境

## 1. 创建并激活虚拟环境
### Windows PowerShell
```powershell
python -m venv .venv

source .venv/bin/activate
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
.\.venv\Scripts\python -m uvicorn main:create_app --factory --reload --host 0.0.0.0 --port 8001
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

脚本迁移命令：uv run main.py revision --env=dev

如何执行迁移（命令行）
在 server/ 目录下，与 revision 同样指定环境：

cd C:\Users\Administrator\Desktop\fssadmin_nestjs\FastAdmin\FssAdmin_Python\server
set PYTHONIOENCODING=utf-8
uv run main.py upgrade --env=dev
成功后会输出：所有迁移已应用。

对应代码就是执行 command.upgrade(alembic_cfg, "head")，即跑到当前所有迁移脚本链的最新节点。

生产环境把 --env=dev 换成 --env=prod，会加载 .env.prod 里的数据库连接。

重要：你这份脚本先别直接 upgrade
你生成的 f66ea5c1b592_迁移脚本.py 有 3500+ 行，autogenerate 认为 ORM 里没有、但库里有的表都要删，例如：

apscheduler_jobs（调度器）
sa_article / sa_article_category（文章）
sa_tool_generate_*（代码生成）
platform_order、casbin_rule 等
如果直接 upgrade，会删表、改列，数据可能丢失。

原因是：数据库来自完整 fssoa.sql，而 ORM 模型已经精简，autogenerate 把差异都写进了这一个「首版迁移」。

建议怎么用
方案 A — 继续以 fssoa.sql 为准（你现在的做法）

表结构手动改 SQL / 在库里改
不要对这份 autogenerate 脚本跑 upgrade
可以删掉或移走 f66ea5c1b592_迁移脚本.py，避免误执行
方案 B — 正式启用 Alembic

先让「库结构」和「ORM 模型」对齐（或手工编辑迁移脚本，删掉所有 drop_table）
再 uv run main.py upgrade --env=dev
以后：改模型 → revision → 审阅脚本 → upgrade
方案 C — 只想标记「当前库已是 baseline、暂不执行 DDL」

需要把现有库「盖章」为已迁移状态（alembic stamp head），本项目 main.py 没封装该命令，要用原生 Alembic；且仍应先处理那份危险脚本。

小结
upgrade = 把 versions/ 里未执行的迁移真正跑进数据库
导入命令：uv run main.py upgrade --env=dev
当前这份 f66ea5c1b592 迁移：生成成功 ≠ 可以升级；务必先打开文件审阅，尤其所有 op.drop_table，确认无误再执行



# 安装最新的 Python 3.12
uv python install 3.12

root@C20260514161631:/www/wwwroot/fast-admin# uv venv
Using CPython 3.13.0
Creating virtual environment at: .venv
✔ A virtual environment already exists at `.venv`. Do you want to replace it? · yes
Activate with: source .venv/bin/activate


方案 1：uv 标准方式（推荐，fast-admin 项目直接用）
# 进入项目目录
cd /www/wwwroot/fast-admin

# 1. 创建 .venv 虚拟环境（uv会自动管理）
uv venv

# 2. 直接用uv安装requirements.txt，不用pip！
uv pip install -r requirements.txt

后续运行代码（两种任选）
# 方式A：uv run（推荐后台、脚本、systemd，不用激活）
uv run python main.py

# 方式B：手动激活环境，和以前一样
source .venv/bin/activate
# 激活后提示符变成 (.venv)，这时里面pip就正常了
python main.py


# uv 安装python


> 重点：**uv python install 安装的 Python 和系统Python完全隔离，不会触发那个 `externally-managed-environment` 报错！正好解决你刚才 fast-admin 的问题**
> 存放路径：`~/.local/share/uv/python/`，用户目录下，不用root改系统文件

## 1、先看可用版本
```bash
# 列出所有可下载的python版本
uv python list

# 只看已经装好了的
uv python list --installed
```

## 2、安装Python（常用命令）
```bash
# 安装最新3.12（推荐，fast-admin常用）
uv python install 3.12

# 精确小版本
uv python install 3.12.8

# 一次性装多个
uv python install 3.10 3.11 3.12

# 安装pypy
uv python install pypy@3.11
```
> 提示：**uv venv 的时候如果版本不存在，uv会自动帮你下载，不一定需要手动先 install**

## 3、给你的 fast-admin 项目使用（你当前场景）
```bash
cd /www/wwwroot/fast-admin

# 用uv自带的3.12创建虚拟环境
uv venv --python 3.12

# 安装依赖，不会报externally-managed
uv pip install -r requirements.txt
```

### 运行两种方式
```bash
# 方式1（推荐，后台、systemd）
uv run python main.py

# 方式2 激活环境
source .venv/bin/activate
python main.py
```

## 4、项目固定python版本（生成 .python-version）
```bash
uv python pin 3.12
```
之后在这个目录，uv默认自动使用3.12

## 5、查看/查找解释器路径
```bash
# 查看当前项目会用哪个python
uv python find

# 直接调用这个python
uv run --python 3.12 python
```

## 6、升级、卸载
```bash
# 升级3.12到最新补丁
uv python upgrade 3.12

# 删除某个版本
uv python uninstall 3.10
```

## 7、国内加速（下载慢必加）
设置pypi源是`uv pip`，python解释器下载镜像需要配置环境变量：
```bash
# 临时（当前shell）
export UV_PYTHON_BUILD_STANDALONE_MIRROR=[https://mirrors.tuna.tsinghua.edu.cn/github-release/indygreg/python-build-standalone/](https://mirrors.tuna.tsinghua.edu.cn/github-release/indygreg/python-build-standalone/)
uv python install 3.12
```

## ⚠️ 重要提醒
- 这个python**不是系统的 /usr/bin/python3**，是uv单独托管的独立编译版
- 不要用 `sudo uv python install`，装在root家目录会混乱，普通用户执行即可
- 你之前报错根源：一直在用系统 `/usr/bin/python3` 装包，换成uv自带解释器+uv venv就彻底避开PEP668保护

你这个fast-admin是用3.10还是3.12？我直接给你一条一键部署脚本。


