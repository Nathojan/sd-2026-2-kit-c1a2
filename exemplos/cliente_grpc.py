import grpc

import inferencia_pb2
import inferencia_pb2_grpc


with grpc.insecure_channel("localhost:50051") as canal:
    stub = inferencia_pb2_grpc.InferenciaStub(canal)
    resposta = stub.PreverLote(
        inferencia_pb2.PedidoLote(
            textos=["otimo atendimento", "pessimo servico"]
        )
    )
    print(resposta)
