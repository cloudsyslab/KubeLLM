FROM ubuntu:20.04

RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv

WORKDIR /app

COPY server.py /app

EXPOSE 8765

CMD ["python3", "-u", "server.py"]
