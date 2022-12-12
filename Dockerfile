FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt  /app

RUN mkdir -p /app/tmp/output
RUN mkdir -p /app/tmp/input
RUN apt-get update \
  && apt-get -y install espeak python3-pyaudio ffmpeg

RUN pip3 install -r requirements.txt
COPY service_worker.py /app
ENV PYTHONUNBUFFERED=1
# CMD [ "python3", "worker.py"]
ENTRYPOINT ["python3", "service_worker.py"]