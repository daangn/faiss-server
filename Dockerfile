FROM continuumio/miniconda3

RUN conda install faiss-cpu==1.5.0 -c pytorch

RUN cd && mkdir .pip && echo "[global]\nindex-url=http://ftp.daumkakao.com/pypi/simple\ntrusted-host=ftp.daumkakao.com" > ./.pip/pip.conf
#RUN sed -i 's/archive.ubuntu.com/ftp.daumkakao.com/g' /etc/apt/sources.list

ENV GRPC_PYTHON_VERSION 1.19.0
RUN python -m pip install --upgrade pip
RUN pip install grpcio==${GRPC_PYTHON_VERSION} grpcio-tools==${GRPC_PYTHON_VERSION}

RUN mkdir -p /app
WORKDIR /app

RUN pip install pandas
RUN pip install gevent==1.4.0
RUN pip install click
RUN pip install boto3
RUN pip install --upgrade setuptools 2>/dev/null ; pip install google-cloud-storage

# for click library
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

ENTRYPOINT ["python"]
CMD ["server.py"]

HEALTHCHECK --interval=3s --timeout=2s \
  CMD ls /tmp/status || exit 1

COPY *.py /app/
