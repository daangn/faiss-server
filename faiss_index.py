import logging
from os.path import isfile

import faiss
import numpy as np

class FaissIndex:
    def __init__(self, dim, save_path):
        if isfile(save_path):
            logging.debug('restore: %s', save_path)
            self._index = faiss.read_index(save_path)
        else:
            self._sub_index = faiss.IndexFlat(dim)
            self._index = faiss.IndexIDMap2(self._sub_index)

    def replace(self, xb, ids):
        logging.debug('replace: %s', ids)
        self.remove(ids)
        return self._index.add_with_ids(xb, ids)

    def add(self, xb, ids):
        return self._index.add_with_ids(xb, ids)

    def search(self, xq, k=10):
        return self._index.search(xq, k)

    def search_by_id(self, id, k=10):
        try:
            x = self._index.reconstruct(id)
            xq = np.expand_dims(x, axis=0)
        except RuntimeError as e:
            if str(e).endswith('not found'):
                return ([None], [None])
            else:
                raise e
        return self.search(xq, k)

    def ntotal(self):
        return self._index.ntotal

    def remove(self, ids):
        return self._index.remove_ids(ids)

    def restore(self, filepath):
        pre_index = self._index
        self._index = faiss.read_index(filepath)
        if pre_index:
            pre_index.reset()

    def save(self, filepath):
        if self.ntotal() > 0:
            faiss.write_index(self._index, filepath)

    def set_nprobe(self, nprobe):
        faiss.ParameterSpace().set_index_parameter(self._index, "nprobe", nprobe)

    def dim(self):
        return self._index.d
