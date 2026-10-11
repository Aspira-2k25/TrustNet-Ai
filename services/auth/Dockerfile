FROM python:3.11-slim
WORKDIR /app
COPY shared /app/shared
COPY services/auth/requirements.txt /app/services/auth/requirements.txt
RUN pip install --no-cache-dir -r services/auth/requirements.txt
COPY services/auth /app/services/auth
ENV PYTHONPATH=/app
EXPOSE 8001
CMD ["uvicorn", "services.auth.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
