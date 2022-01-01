FROM alpine:3.15

ENV TZ=America/New_York

RUN \
    apk add --no-cache tzdata py3-requests libusb py3-usb py3-pip \
    && rm -rf /var/cache/apk/* \
    && cp /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && pip install python-kasa \
    && pip install influxdb-client

RUN mkdir /app
COPY ./sensate.py /app
RUN chmod 755 /app/sensate.py

ENTRYPOINT [ "python3", "-u", "/app/sensate.py" ]