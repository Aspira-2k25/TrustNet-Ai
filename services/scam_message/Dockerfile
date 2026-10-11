FROM python:3.11-slim
WORKDIR /app
COPY shared /app/shared
RUN mkdir -p /app/models && touch /app/models/__init__.py
COPY services/scam_message/requirements.txt /app/services/scam_message/requirements.txt
RUN pip install --no-cache-dir torch==2.6.0 --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r services/scam_message/requirements.txt
COPY services/scam_message /app/services/scam_message
COPY models/scam_message /app/models/scam_message
ENV PYTHONPATH=/app
EXPOSE 8005
CMD ["uvicorn", "services.scam_message.app.main:app", "--host", "0.0.0.0", "--port", "8005"]
