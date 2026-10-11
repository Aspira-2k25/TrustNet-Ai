FROM python:3.11-slim
WORKDIR /app
COPY shared /app/shared
COPY gateway/requirements.txt /app/gateway/requirements.txt
RUN pip install --no-cache-dir -r gateway/requirements.txt
COPY gateway /app/gateway
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "gateway.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
