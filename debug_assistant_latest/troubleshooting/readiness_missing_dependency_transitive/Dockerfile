FROM ubuntu:20.04
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY helper_config.py /app/helper_config.py
COPY server.py /app/server.py
EXPOSE 8080
CMD ["python3", "server.py"]
