FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 && rm -rf /var/lib/apt/lists/*
COPY services/phishing_url/requirements-runtime.txt /tmp/phishing-requirements.txt
RUN pip install --no-cache-dir -r /tmp/phishing-requirements.txt
RUN pip install --no-cache-dir 'boto3>=1.40,<2'
ARG PHISHING_HYBRID=false
RUN if [ "$PHISHING_HYBRID" = "true" ]; then \
    pip install --no-cache-dir 'torch==2.14.1+cpu' --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir 'transformers==5.19.0' 'safetensors==0.8.0'; fi
RUN if [ "$PHISHING_HYBRID" = "true" ]; then python -c "import torch; from transformers import AutoModelForSequenceClassification, AutoTokenizer; assert not torch.cuda.is_available(); print('CPU hybrid runtime imports verified')"; fi
COPY shared /app/shared
COPY models/phishing_url /app/models/phishing_url
COPY services/phishing_url /app/services/phishing_url
RUN useradd --uid 10001 --create-home worker && mkdir -p /var/cache/trustnet && chown worker:worker /var/cache/trustnet
USER 10001
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONUNBUFFERED=1
EXPOSE 8007
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8007/ready',timeout=3)"
CMD ["uvicorn", "services.phishing_url.app.main:app", "--host", "0.0.0.0", "--port", "8007"]
