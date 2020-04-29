# -*- coding: utf-8 -*-
import time
import logging
import sys
import signal
from concurrent import futures

import grpc
import click

from grpc_health.v1 import health
from grpc_health.v1 import health_pb2
from grpc_health.v1 import health_pb2_grpc

import faissindex_pb2_grpc as pb2_grpc
from faiss_server import FaissServer

_ONE_DAY_IN_SECONDS = 60 * 60 * 24

@click.command()
@click.option('--dim', default=0)
@click.option('--save-path', default='faiss_server.index', help='index save path')
@click.option('--keys-path', help='keys file path')
@click.option('--log', help='log filepath')
@click.option('--debug', is_flag=True, help='debug')
@click.option('--updateable', is_flag=False, help='no save when stop service')
@click.option('--max-workers', default=1, help='workers count')
@click.option('--nprobe', default=1, help='nprobe for the search quality')
def main(dim, save_path, keys_path, log, debug, updateable, max_workers, nprobe):
    if log:
        handler = logging.FileHandler(filename=log)
    else:
        handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s - %(message)s')
    handler.setFormatter(formatter)
    root = logging.getLogger()
    level = debug and logging.DEBUG or logging.INFO
    root.setLevel(level)
    root.addHandler(handler)

    logging.info('server loading...')
    logging.info('max workers: %d', max_workers)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))

    health_servicer = health.HealthServicer()
    health_servicer.set('', health_pb2.HealthCheckResponse.SERVING)
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    servicer = FaissServer(dim, save_path, keys_path, nprobe)
    pb2_grpc.add_ServerServicer_to_server(servicer, server)

    server.add_insecure_port('[::]:50051')
    server.start()
    logging.info('server started')

    def stop_serve(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGINT, stop_serve)
    signal.signal(signal.SIGTERM, stop_serve)

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        health_servicer.enter_graceful_shutdown()
        server.stop(0)
        if updateable:
            servicer.save()
        logging.info('server stopped')


if __name__ == '__main__':
    main()
