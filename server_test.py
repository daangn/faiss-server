import unittest

import grpc
import grpc_testing

import faissindex_pb2 as pb2
from faiss_server import FaissServer

SERVICE_NAME = 'Server'


class ServerTest(unittest.TestCase):

    @classmethod
    def _get_server(cls, remote_embedding_path=None):
        save_path = '/data/test.index'
        keys_path = '/data/test.key'
        nprobe = 8

        servicer = FaissServer(0, save_path, keys_path, nprobe)
        servicers = {
            pb2.DESCRIPTOR.services_by_name[SERVICE_NAME]: servicer,
        }

        return grpc_testing.server_from_dictionary(
            servicers, grpc_testing.strict_real_time())

    @classmethod
    def setUpClass(cls):
        super(ServerTest, cls).setUpClass()
        cls._server = ServerTest._get_server()

    def setUp(self):
        self._server = ServerTest._server

    def test_total(self):
        request = pb2.EmptyRequest()
        response, metadata, code, details = self._call_method(request, 'Total')
        self.assertEqual(code, grpc.StatusCode.OK)
        print(response)

    def test_dimension(self):
        request = pb2.EmptyRequest()
        response, metadata, code, details = self._call_method(request, 'Dimension')
        self.assertEqual(code, grpc.StatusCode.OK)
        print(response)

    def test_search(self):
        request = pb2.SearchRequest(id=5)
        response, metadata, code, details = self._call_method(request, 'Search')
        self.assertEqual(code, grpc.StatusCode.OK)
        print(response)

    def _call_method(self, request, method_name, server=None):
        descriptor = pb2.DESCRIPTOR.services_by_name[SERVICE_NAME].methods_by_name[method_name]
        method = (server or self._server).invoke_unary_unary(
            method_descriptor=(descriptor),
            invocation_metadata={},
            request=request, timeout=2)

        return method.termination()


if __name__ == '__main__':
    unittest.main(verbosity=2)
