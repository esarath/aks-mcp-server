FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .
COPY tools/ tools/

ENV PROMETHEUS_URL=http://prometheus-operated.monitoring.svc.cluster.local:9090

EXPOSE 8080

CMD ["python", "server.py"]
