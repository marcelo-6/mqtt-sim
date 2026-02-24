FROM python:3.13-alpine

WORKDIR /usr/src/app
ENV PYTHONPATH=/usr/src/app/src

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT [ "python", "-m", "mqtt_simulator", "run" ]
