# 环境说明

- 项目语言：Python，运行在 Python 3.11+
- Docker 基础镜像：`python:3.12`
- 容器工作目录：`/app`
- 质检构建上下文为 `Dockerfile + repo/`,构建时通过 `COPY repo/ .` 把源码复制到 `/app`
- 项目只使用 Python 标准库，因此不需要安装第三方依赖
- 默认启动命令：`python -m inventory_alert.server`，监听 `0.0.0.0:8791`
- 默认验证命令：`python -m unittest discover -s tests`(在源码目录或独立验证流程中运行,不放进 Dockerfile)
- HTTP 端点：`GET /health`、`GET /items`、`GET /alerts`、`POST /items`、`PATCH /items/{sku}/stock`
- 低库存规则：`stock <= reorder_level` 时状态为 `low`
- Dockerfile 只初始化运行环境,不执行测试命令,也不执行 `git init` / `git commit`

## 手动验证命令

```bash
ROOT=$(pwd -P)
tmp=$(mktemp -d)
cp Dockerfile "$tmp/Dockerfile"
mkdir -p "$tmp/repo"
rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' ./ "$tmp/repo/"
docker build -t inventory-alert-py "$tmp"
docker run --rm -d -p 8791:8791 --name inventory-alert-qc inventory-alert-py
curl http://127.0.0.1:8791/health
curl http://127.0.0.1:8791/items
curl -X POST http://127.0.0.1:8791/items \
  -H 'content-type: application/json' \
  -d '{"sku":"TEA-250G","name":"红茶 250G","stock":3,"reorder_level":8,"location":"C-02"}'
curl http://127.0.0.1:8791/alerts
curl -X PATCH http://127.0.0.1:8791/items/TEA-250G/stock \
  -H 'content-type: application/json' \
  -d '{"delta":10,"reason":"补货入库"}'
curl 'http://127.0.0.1:8791/items?status=ok'
docker stop inventory-alert-qc
python -m unittest discover -s tests
```
