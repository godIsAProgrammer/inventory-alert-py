FROM python:3.12

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY repo/ .

EXPOSE 8791

CMD ["python", "-m", "inventory_alert.server"]
