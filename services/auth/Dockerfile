FROM python:3.11-slim

WORKDIR /app

# To allow the editable install to resolve correctly, we copy the shared 
# library into the container environment. We structure the container filesystem 
# similarly to the host repository structure.
COPY shared /shared
COPY services/auth/requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the service code
COPY services/auth/app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
