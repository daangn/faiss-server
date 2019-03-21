# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from concurrent import futures
import contextlib
import datetime
import logging
import math
import multiprocessing
import time
import socket
import sys

import grpc
import click

import faissindex_pb2_grpc as pb2_grpc
from faiss_server import FaissServer

_ONE_DAY = datetime.timedelta(days=1)
_PROCESS_COUNT = multiprocessing.cpu_count()
_THREAD_CONCURRENCY = _PROCESS_COUNT

def _wait_forever(server):
    try:
        while True:
            time.sleep(_ONE_DAY.total_seconds())
    except KeyboardInterrupt:
        server.stop(None)

def _run_server(bind_address, dim, save_path, keys_path, nprobe):
    """Start a server in a subprocess."""
    logging.info('Starting new server.')
    options = (('grpc.so_reuseport', 1),)

    # WARNING: This example takes advantage of SO_REUSEPORT. Due to the
    # limitations of manylinux1, none of our precompiled Linux wheels currently
    # support this option. (https://github.com/grpc/grpc/issues/18210). To take
    # advantage of this feature, install from source with
    # `pip install grpcio --no-binary grpcio`.

    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=_THREAD_CONCURRENCY,),
        options=options
        )
    servicer = FaissServer(dim, save_path, keys_path, 0, nprobe)
    pb2_grpc.add_ServerServicer_to_server(servicer, server)
    server.add_insecure_port(bind_address)
    server.start()
    _wait_forever(server)

@contextlib.contextmanager
def _reserve_port():
    """Find and reserve a port for all subprocesses to use."""
    import socket
    sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    if sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT) != 1:
        raise RuntimeError("Failed to set SO_REUSEPORT.")
    sock.bind(('', 50051))
    try:
        yield sock.getsockname()[1]
    finally:
        sock.close()


@click.command()
@click.argument('dim', type=int)
@click.option('--save-path', default='faiss_server.index', help='index save path')
@click.option('--keys-path', help='keys file path')
@click.option('--log', help='log filepath')
@click.option('--debug', is_flag=True, help='debug')
@click.option('--max-workers', default=1, help='workers count')
@click.option('--nprobe', default=1, help='nprobe for the search quality')
def main(dim, save_path, keys_path, log, debug, max_workers, nprobe):
    if log:
        handler = logging.FileHandler(filename=log)
    else:
        handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('[PID %(process)d] %(asctime)s:%(levelname)s:%(name)s - %(message)s')
    handler.setFormatter(formatter)
    root = logging.getLogger()
    level = debug and logging.DEBUG or logging.INFO
    root.setLevel(level)
    root.addHandler(handler)

    with _reserve_port() as port:
        bind_address = '0.0.0.0:{}'.format(port)
        logging.info("Binding to '%s'", bind_address)
        sys.stdout.flush()
        workers = []
        for _ in range(_PROCESS_COUNT):
            # NOTE: It is imperative that the worker subprocesses be forked before
            # any gRPC servers start up. See
            # https://github.com/grpc/grpc/issues/16001 for more details.
            worker = multiprocessing.Process(
                target=_run_server, args=(bind_address, dim, save_path, keys_path, nprobe))
            worker.start()
            workers.append(worker)
        for worker in workers:
            worker.join()


if __name__ == '__main__':
    main()