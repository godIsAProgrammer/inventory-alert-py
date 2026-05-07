# 环境说明

- 项目语言：Python，运行在 Python 3.11+
- Docker 基础镜像：`python:3.12`
- 容器工作目录：`/app`
- 构建时会把项目根目录的仓库文件复制到 `/app`
- 项目只使用 Python 标准库，因此不需要安装第三方依赖
- 默认启动命令：`python -m inventory_alert.server`，监听 `0.0.0.0:8791`
- 默认验证命令：`python -m unittest discover -s tests`
- HTTP 端点：`GET /health`、`GET /items`、`GET /alerts`、`POST /items`、`PATCH /items/{sku}/stock`
- 低库存规则：`stock <= reorder_level` 时状态为 `low`
- Dockerfile 会把 `/app` 初始化为 `main` 分支 Git 仓库，并创建一个初始提交

## 手动验证命令

```bash
docker build -t inventory-alert-py .
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
docker run --rm inventory-alert-py python -m unittest discover -s tests
docker run --rm inventory-alert-py pwd
docker run --rm inventory-alert-py git status --short
```
