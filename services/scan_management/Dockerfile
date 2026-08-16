FROM python:3.11-slim

WORKDIR /app

# Copy shared library and service requirements
COPY shared /shared
COPY services/scan_management/requirements.txt /app/requirements.txt

# Install dependencies (this uses the editable install for /shared)
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/scan_management/app /app/app

# Expose port
EXPOSE 8000

# Run uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
