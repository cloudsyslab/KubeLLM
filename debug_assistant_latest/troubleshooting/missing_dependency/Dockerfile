FROM python:3.9
RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install flask
WORKDIR /app
COPY server.py /app/
RUN python3 -m pip install flask
# Missing dependency, should include Flask
CMD ["python3", "server.py"]
