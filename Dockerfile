FROM python:3.12

# 库存预警服务只使用 Python 标准库,上传包中源码位于 repo/ 下。
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 质检构建上下文为 Dockerfile + repo/,这里只初始化运行环境,不执行测试或 Git 初始化。
COPY repo/ .

EXPOSE 8791

# 默认启动库存预警 HTTP 服务,质检可通过 /health、/items 和 /alerts 验证运行状态。
CMD ["python", "-m", "inventory_alert.server"]
