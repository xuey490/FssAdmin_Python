# 视频下载 — 菜单与表结构

可执行 SQL（推荐直接导入）：

| 文件 | 作用 |
|------|------|
| [`database/video_tables.sql`](../../../../../database/video_tables.sql) | `platform_video` / `platform_video_download` 建表 |
| [`database/video_menu.sql`](../../../../../database/video_menu.sql) | `sa_system_menu` 菜单与权限 |

```bash
mysql -u root -p your_db < FastAdmin/database/video_tables.sql
mysql -u root -p your_db < FastAdmin/database/video_menu.sql
```

权限 slug：

- `module_platform:video:query`
- `module_platform:video:create`
- `module_platform:video:update`
- `module_platform:video:delete`
- `module_platform:video:download`

菜单 ID：`420–426`（避开 cronjob 的 `400–416`）。

说明：应用启动时也会 `CREATE TABLE IF NOT EXISTS` 自动建表；菜单必须手工执行 `video_menu.sql`（或后台菜单管理录入）。
