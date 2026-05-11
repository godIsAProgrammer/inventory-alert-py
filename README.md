# 库存预警服务

这是一个基于 Python 标准库实现的轻量 HTTP 服务，用于维护门店或仓库的商品库存，并
根据补货阈值生成低库存预警。它覆盖了库存管理服务里最常见的一条链路：录入商品、
查看库存、按状态过滤、调整库存数量、拉取需要补货的商品列表。

项目没有第三方运行时依赖，HTTP 服务使用 `http.server`，测试使用 `unittest`。代码面
保持较小，但已经包含数据校验、线程安全的内存存储、状态计算、JSON API 和 Docker
运行环境，适合继续扩展为文件持久化、访问日志或批量导入版本。

## 功能概览

- 创建或覆盖更新商品库存资料。
- 按 SKU 稳定排序返回库存列表。
- 支持 `status=low/ok` 过滤库存状态。
- 支持通过 `PATCH /items/{sku}/stock` 增减库存。
- 自动计算低库存预警：`stock <= reorder_level` 即为 `low`。
- 返回 `/alerts` 汇总当前需要补货的商品和数量。
- Docker 构建阶段会运行测试，并把容器内 `/app` 初始化为干净 Git 仓库。

## 项目结构

```text
.
├── Dockerfile
├── README.md
├── environment_notes.md
├── pyproject.toml
├── inventory_alert
│   ├── __init__.py
│   ├── router.py      # HTTP 路由、JSON 请求读取和响应输出
│   ├── server.py      # 服务入口、端口监听和访问日志
│   └── store.py       # 商品模型、字段校验、库存调整和预警计算
└── tests
    ├── test_router.py
    └── test_store.py
```

## 数据模型

`POST /items` 接收一个商品对象：

```json
{
  "sku": "MILK-1L",
  "name": "常温牛奶 1L",
  "stock": 8,
  "reorder_level": 10,
  "location": "A-01"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `sku` | string | 是 | 3-32 位，支持大写字母、数字和短横线；服务会自动转成大写 |
| `name` | string | 是 | 商品名称，最多 80 个字符 |
| `stock` | integer | 是 | 当前库存，不允许为负数 |
| `reorder_level` | integer | 是 | 补货阈值，不允许为负数 |
| `location` | string | 否 | 货位，默认 `main`，最多 40 个字符 |
| `status` | string | 响应字段 | `stock <= reorder_level` 时为 `low`，否则为 `ok` |

## HTTP 端点

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 健康检查，返回 `{"ok":true}` |
| GET | `/items` | 返回全部商品，按 SKU 稳定排序 |
| GET | `/items?status=low` | 只返回低库存商品 |
| GET | `/items?status=ok` | 只返回库存正常商品 |
| POST | `/items` | 创建或覆盖更新商品库存资料 |
| PATCH | `/items/{sku}/stock` | 通过 `delta` 增减库存 |
| GET | `/alerts` | 返回当前低库存预警列表和数量 |

错误响应统一使用 JSON，例如：

```json
{"error":"stock cannot be negative"}
```

## 库存状态规则

库存状态只由两个字段决定：

```text
stock <= reorder_level  => low
stock > reorder_level   => ok
```

例如 `stock=8`、`reorder_level=10` 时，商品会进入 `/alerts`；当库存调整到 `11` 后，
状态会变为 `ok` 并从预警列表中消失。

## 本地开发

本机需要 Python 3.11 或更高版本。项目只使用标准库，因此不需要安装依赖。

运行测试：

```bash
python -m unittest discover -s tests
```

启动服务：

```bash
python -m inventory_alert.server
```

默认监听 `0.0.0.0:8791`，可以通过 `PORT` 覆盖：

```bash
PORT=8891 python -m inventory_alert.server
```

## 请求示例

健康检查：

```bash
curl http://127.0.0.1:8791/health
```

查看默认库存：

```bash
curl http://127.0.0.1:8791/items
```

创建一个低库存商品：

```bash
curl -X POST http://127.0.0.1:8791/items \
  -H 'content-type: application/json' \
  -d '{"sku":"TEA-250G","name":"红茶 250G","stock":3,"reorder_level":8,"location":"C-02"}'
```

查看低库存预警：

```bash
curl http://127.0.0.1:8791/alerts
```

调整库存：

```bash
curl -X PATCH http://127.0.0.1:8791/items/TEA-250G/stock \
  -H 'content-type: application/json' \
  -d '{"delta":10,"reason":"补货入库"}'
```

按状态过滤库存正常商品：

```bash
curl 'http://127.0.0.1:8791/items?status=ok'
```

## Docker 环境

确保 Docker Desktop 已启动。质检上传上下文为 `Dockerfile + repo/`，Dockerfile 会把
`repo/` 内容复制到容器 `/app`，只初始化运行环境，不执行测试或 Git 初始化。

构建镜像：

```bash
ROOT=$(pwd -P)
tmp=$(mktemp -d)
cp Dockerfile "$tmp/Dockerfile"
mkdir -p "$tmp/repo"
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' ./ "$tmp/repo/"
docker build -t inventory-alert-py "$tmp"
```

启动 HTTP 服务：

```bash
docker run --rm -p 8791:8791 inventory-alert-py
```

服务启动后，在另一个终端验证健康检查：

```bash
curl http://127.0.0.1:8791/health
```

预期响应：

```json
{"ok":true}
```

运行测试：

```bash
python -m unittest discover -s tests
```

验证容器工作目录：

```bash
docker run --rm inventory-alert-py pwd
```

预期输出：

```text
/app
```

## 常见问题

### 为什么库存数据重启后会恢复默认值？

当前实现使用进程内内存存储，重启后会重新加载默认示例数据。这个取舍让项目保持轻量，
后续可以把 `InventoryStore` 替换为 JSON 文件、SQLite 或外部服务。

### 为什么库存调整使用 `delta`？

实际库存变化通常来自销售出库、补货入库或盘点修正。使用 `delta` 可以同时表达增加和
减少库存，并保留未来扩展库存流水的空间。

### 为什么 SKU 会自动转成大写？

统一 SKU 大小写可以避免 `milk-1l` 和 `MILK-1L` 被当成两个商品。接口会在入库和查询
库存调整时统一转成大写。
