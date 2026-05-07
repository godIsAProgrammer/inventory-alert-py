FROM python:3.12

# 库存预警服务只使用 Python 标准库，源码、测试和项目元数据都在 /app 中运行。
WORKDIR /app

# 复制库存模型、HTTP 路由、测试和说明文档，形成可直接审阅的初始代码现场。
COPY . /app/

# 构建镜像时先跑库存规则和 HTTP 路由测试，再把通过验证的代码固化为干净 Git 仓库。
RUN python -m unittest discover -s tests \
    && git init -b main \
    && git config user.email "agent@example.invalid" \
    && git config user.name "Agent Fixture" \
    && git add . \
    && git commit -m "Initial inventory alert fixture"

EXPOSE 8791

# 默认启动库存预警 HTTP 服务，质检可通过 /health、/items 和 /alerts 验证运行状态。
CMD ["python", "-m", "inventory_alert.server"]
