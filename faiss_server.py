import os
import logging
from tempfile import gettempdirb
from time import time

import pandas as pd
import numpy as np
from pandas import read_csv

from faiss_index import FaissIndex
import faissindex_pb2 as pb2
import faissindex_pb2_grpc as pb2_grpc

import boto3

# Disable debug logs of the boto lib
logging.getLogger('botocore').setLevel(logging.WARN)
logging.getLogger('boto3').setLevel(logging.INFO)
logging.getLogger('s3transfer').setLevel(logging.INFO)

def down_if_remote_path(save_path):
    remote_path, local_path = parse_remote_path(save_path)
    if not remote_path:
        return None, local_path

    s3 = boto3.resource('s3')
    tokens = remote_path.replace('s3://', '').split('/')
    bucket_name = tokens[0]
    key = '/'.join(tokens[1:])
    s3.Bucket(bucket_name).download_file(key, local_path)
    return remote_path, local_path

def parse_remote_path(save_path):
    if save_path is None or not save_path.startswith('s3://'):
        return None, save_path
    remote_path = save_path
    filename = os.path.basename(remote_path)
    save_path = "%s/%d-%s" % (gettempdirb().decode("utf-8"), time(), filename)
    return remote_path, save_path

class FaissServer(pb2_grpc.ServerServicer):
    def __init__(self, dim, save_path, keys_path, nprobe):
        logging.debug('dim: %d', dim)
        logging.debug('save_path: %s', save_path)
        logging.debug('keys_path: %s', keys_path)
        logging.debug('nprobe: %d', nprobe)

        remote_path, save_path = down_if_remote_path(save_path)

        self._remote_path = remote_path
        self._save_path = save_path
        self._index = FaissIndex(dim, save_path)
        if nprobe > 1:
            self._index.set_nprobe(nprobe)
        self._keys, self._key_index = self._load_keys(keys_path)
        logging.debug('ntotal: %d', self._index.ntotal())

    def _load_keys(self, keys_path):
        if not keys_path:
            return None, None
        _, keys_path = down_if_remote_path(keys_path)
        keys = pd.read_csv(keys_path, header=None, squeeze=True, dtype=('str'))
        key_index = pd.Index(keys)
        return keys.values, key_index

    def Total(self, request, context):
        return pb2.TotalResponse(count=self._index.ntotal())

    def Dimension(self, request, context):
        return pb2.DimensionResponse(dim=self._index.dim())

    def Add(self, request, context):
        logging.debug('add - id: %d', request.id)
        xb = np.expand_dims(np.array(request.embedding, dtype=np.float32), 0)
        ids = np.array([request.id], dtype=np.int64)
        self._index.replace(xb, ids)

        return pb2.SimpleResponse(message='Added, %d!' % request.id)

    def Remove(self, request, context):
        logging.debug('remove - id: %d', request.id)
        ids = np.array([request.id], dtype=np.int64)
        removed_count = self._index.remove(ids)

        if removed_count < 1:
            return pb2.SimpleResponse(message='Not existed, %s!' % request.id)
        return pb2.SimpleResponse(message='Removed, %s!' % request.id)

    def Search(self, request, context):
        logging.debug('search - id: %d, %s', request.id, request.key)
        if request.key:
            if not self._key_index.contains(request.key):
                return pb2.SearchResponse()
            request.id = self._key_index.get_loc(request.key)
        D, I = self._index.search_by_id(request.id, request.count)
        K = None
        if request.key:
            K = self._keys[I[0]]
        return pb2.SearchResponse(ids=I[0], scores=D[0], keys=K)

    def SearchByEmbedding(self, request, context):
        logging.debug('search_by_emb - embedding: %s', request.embedding[:10])
        emb = np.array(request.embedding, dtype=np.float32)
        emb = np.expand_dims(emb, axis=0)
        D, I = self._index.search(emb, request.count)
        return pb2.SearchResponse(ids=I[0], scores=D[0])

    def Restore(self, request, context):
        logging.debug('restore - %s', request.save_path)
        remote_path, save_path = down_if_remote_path(request.save_path)
        self._remote_path = remote_path
        self._save_path = save_path
        self._index.restore(request.save_path)
        return pb2.SimpleResponse(message='Restored, %s!' % request.save_path)

    def Import(self, request, context):
        logging.debug('importing - %s, %s', request.embs_path, request.ids_path)
        _, embs_path = down_if_remote_path(request.embs_path)
        _, ids_path = down_if_remote_path(request.ids_path)
        df = read_csv(embs_path, delimiter="\t", header=None)
        X = df.values
        df = read_csv(ids_path, header=None)
        ids = df[0].values
        logging.debug('%s', ids)

        X = np.ascontiguousarray(X, dtype=np.float32)
        ids = np.ascontiguousarray(ids, dtype=np.int64)

        self._index.replace(X, ids)
        return pb2.SimpleResponse(message='Imported, %s, %s!' % (request.embs_path, request.ids_path))

    def save(self):
        logging.debug('saving index to %s', self._save_path)
        self._index.save(self._save_path)

