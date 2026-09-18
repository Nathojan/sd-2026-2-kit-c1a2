"""
Worker: consome a fila e executa a inferencia.

O QUE JA ESTA PRONTO: o laco principal e o carregamento do modelo.
O QUE VOCE PRECISA FAZER (TAREFAS.md, itens 3 e 5):
  - guardar o resultado ao terminar
  - tratar erro com retentativa e fila de descarte (dead-letter)

Rodar:  python -m app.worker
Suba mais de um worker em terminais diferentes e veja a carga se dividir.
"""
import json
import logging
import time

from app import fila
from app.modelo import carregar_modelo

logger = logging.getLogger("app.worker")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

MAX_TENTATIVAS = 3


def processar_tarefa(tarefa: dict, modelo):
    """Executa a inferencia da tarefa e trata retries/dead-letter."""
    tarefa_id = tarefa["id"]
    texto = tarefa.get("texto", "")
    tentativa = fila.incrementar_tentativa(tarefa_id)
    inicio = time.time()

    try:
        resultado_modelo = modelo.prever(texto)
        resultado = {
            "status": "completed",
            "task_id": tarefa_id,
            "resultado": resultado_modelo,
            "tentativas": tentativa,
            "tempo_ms": round((time.time() - inicio) * 1000, 2),
        }
        fila.guardar_resultado(tarefa_id, resultado)
        logger.info("task_id=%s status=completed input=%s tentativas=%s", tarefa_id, texto, tentativa)
        return resultado
    except Exception as erro:  # noqa: BLE001
        mensagem = f"{type(erro).__name__}: {erro}"
        logger.warning("task_id=%s status=error input=%s tentativas=%s erro=%s", tarefa_id, texto, tentativa, mensagem)

        if tentativa >= MAX_TENTATIVAS:
            payload = {
                "status": "dead_letter",
                "task_id": tarefa_id,
                "resultado": None,
                "erro": mensagem,
                "tentativas": tentativa,
            }
            fila.guardar_dead_letter(tarefa_id, mensagem, {"texto": texto, "tentativas": tentativa})
            fila.guardar_resultado(tarefa_id, payload)
            logger.error("task_id=%s status=dead_letter input=%s erro=%s", tarefa_id, texto, mensagem)
            return payload

        payload = {
            "status": "retrying",
            "task_id": tarefa_id,
            "resultado": None,
            "erro": mensagem,
            "tentativas": tentativa,
        }
        fila.guardar_resultado(tarefa_id, payload)
        fila.cliente().rpush(fila.FILA_TAREFAS, json.dumps({"id": tarefa_id, "texto": texto}))
        logger.warning("task_id=%s status=retrying input=%s tentativas=%s erro=%s", tarefa_id, texto, tentativa, mensagem)
        return payload


def main():
    print("[worker] carregando modelo...")
    modelo = carregar_modelo()
    print("[worker] pronto. aguardando tarefas (Ctrl+C para sair)")

    while True:
        tarefa = fila.proxima_tarefa(timeout=5)
        if tarefa is None:
            continue

        print(f"[worker] processando {tarefa['id']}")
        processar_tarefa(tarefa, modelo)


if __name__ == "__main__":
    main()