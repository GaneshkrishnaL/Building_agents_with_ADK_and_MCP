FROM python:3.11-slim
WORKDIR /app

# Install Python deps first so Docker can cache this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY server.py .

# Cloud Run sets PORT at runtime; this is just a hint
ENV PORT=8080

CMD ["python3", "server.py"]
