"""
Interface REST do servico de inferencia.

O QUE JA ESTA PRONTO:
  - carregamento do modelo UMA vez, na subida (nao a cada requisicao)
  - rota sincrona /predict-sync, usada no laboratorio da Aula 6

O QUE VOCE PRECISA FAZER (TAREFAS.md, itens 1 e 2):
  - POST /predict  -> colocar na fila e devolver o id
  - GET  /resultado/{id} -> devolver o resultado quando estiver pronto

Rodar:  uvicorn app.api_rest:app --reload --port 8000
Docs:   http://localhost:8000/docs
"""
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel

from app import fila
from app.modelo import carregar_modelo

app = FastAPI(title="Servico de Inferencia - C1.A2", version="0.1.0")
logger = logging.getLogger("app.api_rest")
if not logger.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

modelo = None


class Entrada(BaseModel):
    texto: str


def _log_requisicao(request_id: str, entrada: str, status_processamento: str, erro: str | None = None):
    timestamp = datetime.now(timezone.utc).isoformat()
    payload = {
        "request_id": request_id,
        "timestamp": timestamp,
        "entrada": entrada,
        "status": status_processamento,
    }
    if erro:
        payload["erro"] = erro
    logger.info("requisicao=%s", payload)


@app.on_event("startup")
def _subir():
    """Carrega o modelo UMA vez. Este e o ponto-chave da Aula 6."""
    global modelo
    inicio = time.time()
    modelo = carregar_modelo()
    print(f"[startup] modelo carregado em {time.time() - inicio:.3f}s")


@app.get("/saude")
def saude():
    return {"status": "ok", "modelo_carregado": modelo is not None}


@app.post("/predict-sync")
def predict_sync(entrada: Entrada):
    """Inferencia SINCRONA: o cliente espera a resposta. Lab da Aula 6."""
    if not entrada.texto.strip():
        raise HTTPException(status_code=400, detail="texto vazio")
    inicio = time.time()
    resultado = modelo.prever(entrada.texto)
    resultado["tempo_ms"] = round((time.time() - inicio) * 1000, 2)
    return resultado


@app.post("/predict", status_code=status.HTTP_202_ACCEPTED)
def predict(entrada: Entrada, request: Request):
    """Enfileira a tarefa e devolve um identificador para consulta posterior."""
    request_id = str(uuid.uuid4())
    texto = entrada.texto.strip()

    if not texto:
        erro = "texto vazio"
        _log_requisicao(request_id, entrada.texto, "invalid_input", erro)
        raise HTTPException(status_code=400, detail=erro)

    if len(texto) > 5000:
        erro = "texto excede o limite de 5000 caracteres"
        _log_requisicao(request_id, texto, "invalid_input", erro)
        raise HTTPException(status_code=400, detail=erro)

    try:
        task_id = fila.enfileirar(texto)
        _log_requisicao(request_id, texto, "queued")
        return {
            "task_id": task_id,
            "id": task_id,
            "status": "queued",
            "request_id": request_id,
        }
    except Exception as exc:  # pragma: no cover - resiliencia
        erro = str(exc)
        _log_requisicao(request_id, texto, "queue_error", erro)
        raise HTTPException(status_code=503, detail="falha ao enfileirar tarefa") from exc


@app.get("/resultado/{tarefa_id}")
def resultado(tarefa_id: str):
    """Consulta do resultado associado ao identificador da tarefa."""
    request_id = str(uuid.uuid4())
    try:
        dados = fila.buscar_resultado(tarefa_id)
        if dados is None:
            _log_requisicao(request_id, tarefa_id, "not_found", "tarefa inexistente")
            raise HTTPException(status_code=404, detail="tarefa inexistente")

        _log_requisicao(request_id, tarefa_id, dados.get("status", "unknown"))
        return dados
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - resiliencia
        _log_requisicao(request_id, tarefa_id, "result_error", str(exc))
        raise HTTPException(status_code=503, detail="falha na consulta do resultado") from exc
