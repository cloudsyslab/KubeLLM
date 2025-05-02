FROM ubuntu:20.04

RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv


COPY server.py /app
WORKDIR /app
RUN mkdir -p /data RUN mkdir -p /data/logsRUN mkdir -p /data/logs mkdir -p /data/logs

EXPOSE 8765

CMD ["python3", "server.py"]
