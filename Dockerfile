FROM daangn/faiss:1.6.3

RUN cd && mkdir .pip && echo "[global]\nindex-url=http://ftp.daumkakao.com/pypi/simple\ntrusted-host=ftp.daumkakao.com" > ./.pip/pip.conf
#RUN sed -i 's/archive.ubuntu.com/ftp.daumkakao.com/g' /etc/apt/sources.list

RUN python -m pip install --upgrade pip
RUN pip install -q pandas gevent click boto3
RUN pip install -q grpcio grpcio-tools grpcio-testing grpcio-health-checking
RUN pip install --upgrade setuptools 2>/dev/null ; pip install -q google-cloud-storage

# for click library
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

# For gRPC health check on k8s
RUN GRPC_HEALTH_PROBE_VERSION=v0.3.1 && \
    wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 && \
    chmod +x /bin/grpc_health_probe

HEALTHCHECK --interval=3s --timeout=2s \
  CMD /bin/grpc_health_probe -addr localhost:50051

# for gRPC
EXPOSE 50051

ENTRYPOINT ["python"]
CMD ["server.py"]

RUN mkdir -p /app
WORKDIR /app

COPY *.py /app/
