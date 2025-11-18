FROM python:3.9-slim

WORKDIR /app

COPY server.py .

# BUG: Missing 'RUN pip install requests'
# The application requires the requests package but it's not installed

EXPOSE 8080

CMD ["python3", "server.py"]
