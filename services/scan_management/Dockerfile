FROM python:3.11-slim
WORKDIR /app
COPY shared /app/shared
COPY services/scan_management/requirements.txt /app/services/scan_management/requirements.txt
RUN pip install --no-cache-dir -r services/scan_management/requirements.txt
COPY services/scan_management /app/services/scan_management
COPY models /app/models
COPY services/trust_engine /app/services/trust_engine
RUN pip install --no-cache-dir -r models/image_deepfake/requirements.txt PyYAML
ENV PYTHONPATH=/app
EXPOSE 8002
CMD ["uvicorn", "services.scan_management.app.main:app", "--host", "0.0.0.0", "--port", "8002"]
