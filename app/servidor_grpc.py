"""
Interface gRPC do servico de inferencia.

PRE-REQUISITO: gerar os stubs antes de rodar (veja scripts/gerar_stubs).

O QUE JA ESTA PRONTO: o metodo Prever.
O QUE VOCE PRECISA FAZER (TAREFAS.md, item 4): o metodo PreverLote.

Rodar:  python -m app.servidor_grpc
"""
import logging
import uuid
from concurrent import futures

import grpc

from app.modelo import carregar_modelo

try:
    import inferencia_pb2
    import inferencia_pb2_grpc
except ImportError:  # pragma: no cover
    raise SystemExit(
        "Stubs nao encontrados. Rode antes:\n"
        "  python -m grpc_tools.protoc -I proto --python_out=. "
        "--grpc_python_out=. proto/inferencia.proto"
    )

logger = logging.getLogger("app.grpc")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class ServicoInferencia(inferencia_pb2_grpc.InferenciaServicer):

    def __init__(self):
        print("[grpc] carregando modelo...")
        self.modelo = carregar_modelo()
        print("[grpc] modelo pronto")

    def _resultado_para_pb(self, resultado: dict):
        return inferencia_pb2.RespostaPrever(
            texto=resultado["texto"],
            sentimento=resultado["sentimento"],
            confianca=resultado["confianca"],
        )

    def Prever(self, request, context):
        request_id = str(uuid.uuid4())
        try:
            if not request.texto.strip():
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "texto vazio")

            r = self.modelo.prever(request.texto)
            logger.info("request_id=%s tipo=prever input=%s status=ok", request_id, request.texto)
            return self._resultado_para_pb(r)
        except grpc.RpcError:
            raise
        except Exception as erro:  # pragma: no cover
            logger.error("request_id=%s tipo=prever input=%s status=error erro=%s", request_id, request.texto, str(erro))
            context.abort(grpc.StatusCode.INTERNAL, "falha no processamento da inferencia")

    def PreverLote(self, request, context):
        request_id = str(uuid.uuid4())
        try:
            resultados = []
            for texto in request.textos:
                if not texto.strip():
                    context.abort(grpc.StatusCode.INVALID_ARGUMENT, "texto vazio em lote")
                r = self.modelo.prever(texto)
                resultados.append(self._resultado_para_pb(r))

            logger.info("request_id=%s tipo=prever_lote quantidade=%s status=ok", request_id, len(request.textos))
            return inferencia_pb2.RespostaLote(resultados=resultados)
        except grpc.RpcError:
            raise
        except Exception as erro:  # pragma: no cover
            logger.error("request_id=%s tipo=prever_lote input=%s status=error erro=%s", request_id, list(request.textos), str(erro))
            context.abort(grpc.StatusCode.INTERNAL, "falha no processamento em lote")


def servir(porta: int = 50051):
    servidor = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inferencia_pb2_grpc.add_InferenciaServicer_to_server(
        ServicoInferencia(), servidor)
    servidor.add_insecure_port(f"[::]:{porta}")
    servidor.start()
    print(f"[grpc] escutando na porta {porta}")
    servidor.wait_for_termination()


if __name__ == "__main__":
    servir()
