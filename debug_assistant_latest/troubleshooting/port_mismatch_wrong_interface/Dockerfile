FROM python:3.9-slim

WORKDIR /app

COPY server.py .

# Correctly expose port 8765
EXPOSE 8765

CMD ["python3", "server.py"]
