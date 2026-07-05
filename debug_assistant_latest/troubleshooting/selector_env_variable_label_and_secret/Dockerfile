FROM ubuntu:20.04
RUN apt-get update && apt-get install -y python3 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY server.py /app/server.py
EXPOSE 8765
CMD ["python3", "server.py"]
