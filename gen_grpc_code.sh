#!/bin/bash
PROTO_FILEPATH=faissindex.proto
RUBY_LIB_PATH="$(pwd)/../hoian-webapp/lib"

docker run --rm -it -v $(pwd):/app -w /app \
  -v $RUBY_LIB_PATH:/ruby_out \
  -u $(id -u):$(id -g) \
  daangn/grpc-tools bash -c "python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. $PROTO_FILEPATH && \
grpc_tools_ruby_protoc -I. --ruby_out=/ruby_out --grpc_out=/ruby_out $PROTO_FILEPATH"