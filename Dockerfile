FROM alpine:3.15

ARG BUILD_DATE
ARG VCS_REF

ENV TZ=America/New_York

LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.vcs-url="https://github.com/jcostom/plugmon.git" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.schema-version="1.0.0"

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