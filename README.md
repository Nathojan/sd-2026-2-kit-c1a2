# Serviço de Inferência Distribuído

## Visão geral

Este projeto implementa um serviço distribuído para inferência de sentimento em texto usando um modelo de IA offline já fornecido no kit. A arquitetura foi organizada para separar responsabilidades entre:

- API REST em FastAPI
- API gRPC por contrato protobuf
- fila em Redis
- worker assíncrono
- armazenamento de resultados por task_id

O objetivo principal é permitir que o cliente envie uma mensagem, receba imediatamente um identificador e continue sem esperar a inferência terminar. O processamento ocorre em segundo plano no worker, com resultados consultáveis posteriormente.

---

## Arquitetura

A arquitetura do sistema segue o fluxo abaixo:

1. Cliente envia texto para a API REST ou gRPC.
2. A API valida a entrada e cria uma tarefa.
3. A tarefa é armazenada na fila Redis.
4. O worker consume a fila.
5. O worker executa a inferência usando o modelo carregado uma vez.
6. O resultado é salvo no Redis com o identificador da tarefa.
7. O cliente consulta o estado/finalização pelo task_id.

### Componentes

- REST API: recebe requisições HTTP e enfileira tarefas.
- gRPC API: oferece o mesmo serviço via protobuf.
- Queue: Redis como broker de mensagens.
- Worker: executa previsão e armazena os resultados.
- Modelo: carregado uma única vez no startup do worker.

---

## Tecnologias

- Python 3.12+
- FastAPI
- gRPC + protobuf
- Redis
- scikit-learn
- Docker / Docker Compose

---

## Estrutura do projeto

```text
sd-2026-2-kit-c1a2/
├── app/
│   ├── __init__.py
│   ├── api_rest.py
│   ├── fila.py
│   ├── modelo.py
│   ├── servidor_grpc.py
│   └── worker.py
├── examples/
│   ├── cliente_rest.py
│   └── cliente_grpc.py
├── proto/
│   └── inferencia.proto
├── tests/
│   ├── test_api_rest.py
│   ├── test_grpc.py
│   └── test_worker.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
└── TAREFAS.md
```

---

## Instalação

### 1. Clonar o repositório

```bash
git clone https://github.com/howardroatti/sd-2026-2-kit-c1a2.git
cd sd-2026-2-kit-c1a2
```

### 2. Criar ambiente virtual

#### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### Linux/macOS

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências

```bash
pip install -r requirements.txt
```

### 4. Subir o Redis

#### Opção local

```bash
docker compose up -d redis
```

#### Opção com todos os serviços

```bash
docker compose up --build
```

---

## Execução dos serviços

> Execute os comandos abaixo a partir da raiz do projeto, ou seja, da pasta que contém `app`, `proto` e `requirements.txt`.

```powershell
cd caminho\para\sd-2026-2-kit-c1a2
\.venv\Scripts\Activate.ps1
```

### REST API

Abra um **novo terminal**, mantenha-o nessa sessão e execute:

```bash
uvicorn app.api_rest:app --host 0.0.0.0 --port 8000 --reload
```

Acesse a documentação em:

- http://localhost:8000/docs
- http://localhost:8000/redoc

### Worker

Abra outro **novo terminal**, ative o ambiente virtual novamente e execute:

```bash
python -m app.worker
```

Deixe os dois terminais abertos: a API REST recebe e enfileira as tarefas, enquanto o
worker executa as inferências em segundo plano.

### gRPC

Com a REST e o worker em execução, abra um terceiro terminal para o gRPC. Gere os stubs
e inicie o servidor nessa nova sessão:

Antes de iniciar o servidor gRPC, gere os stubs:

```bash
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto
python -m app.servidor_grpc
```

---

## Testes REST

### 1. Enviar tarefa assíncrona

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"texto":"atendimento excelente e muito rapido"}'
```

Resposta esperada:

```json
{
  "task_id": "<uuid>",
  "id": "<uuid>",
  "status": "queued",
  "request_id": "<uuid>"
}
```

### 2. Consultar resultado

```bash
curl "http://localhost:8000/resultado/<task_id>"
```

Resposta esperada:

```json
{
  "status": "completed",
  "task_id": "<uuid>",
  "resultado": {
    "texto": "atendimento excelente e muito rapido",
    "sentimento": "positivo",
    "confianca": 0.97
  },
  "tempo_ms": 12.34,
  "tentativas": 1
}
```

---

## Como testar o gRPC

O gRPC precisa de três passos: gerar os stubs, iniciar o servidor e executar um cliente.

### 1. Gerar os stubs

Os stubs são arquivos Python gerados automaticamente a partir do contrato
`proto/inferencia.proto`. Execute este comando uma única vez, a partir da raiz do projeto:

```bash
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto
```

### 2. Iniciar o servidor gRPC

Abra um novo terminal, ative o ambiente virtual, entre na raiz do projeto e execute:

```powershell
python -m app.servidor_grpc
```

Mantenha esse terminal aberto. O servidor ficará escutando na porta `50051`.

### 3. Executar o cliente

Abra outro terminal, também na raiz do projeto, com o ambiente virtual ativado, e execute:

```powershell
python -m exemplos.cliente_grpc
```

O arquivo `exemplos/cliente_grpc.py` envia duas frases ao método `PreverLote`.

Use `python -m exemplos.cliente_grpc` em vez de executar o arquivo diretamente. Dessa
forma, a raiz do projeto permanece no caminho de importação e os arquivos
`inferencia_pb2.py` e `inferencia_pb2_grpc.py` são encontrados corretamente.

> O bloco `python - <<'PY'` é uma forma de executar código diretamente no Bash.
> Ele não é necessário no Windows PowerShell; por isso o projeto fornece o cliente
> Python pronto acima.

Se aparecer um erro informando que a porta `50051` já está em uso, o servidor gRPC já
está executando em outro terminal. Nesse caso, não inicie uma segunda instância; execute
o cliente no terminal indicado acima. Para localizar e encerrar o processo no Windows:

```powershell
Get-NetTCPConnection -LocalPort 50051 -State Listen
Stop-Process -Id <PID> -Force
```

Exemplo de resposta:

```text
resultados {
  texto: "otimo atendimento"
  sentimento: "positivo"
  confianca: 0.9912
}
resultados {
  texto: "pessimo servico"
  sentimento: "negativo"
  confianca: 0.9823
}
```

---

## Fluxo completo

### Caso de uso real

1. O cliente envia uma requisição ao REST.
2. A API valida a entrada e registra logs.
3. A tarefa é adicionada à fila Redis.
4. O worker recebe a tarefa.
5. O modelo de inferência é executado uma vez e reutilizado.
6. O resultado é salvo no Redis.
7. O cliente consulta o seu task_id na rota de resultado.

### Exemplo

```bash
curl -X POST "http://localhost:8000/predict" \
  -H "Content-Type: application/json" \
  -d '{"texto":"o atendimento foi perfeito"}'
```

Resposta:

```json
{"task_id":"abc123","id":"abc123","status":"queued"}
```

Consulta:

```bash
curl "http://localhost:8000/resultado/abc123"
```

Resposta:

```json
{"status":"completed","resultado":{"texto":"o atendimento foi perfeito","sentimento":"positivo","confianca":0.96}}
```

---

## Observações importantes

- O modelo de IA não deve ser carregado em cada requisição.
- O worker é o responsável por fazer a inferência real.
- A fila desacopla as requisições da execução e melhora a resiliência.
- Em caso de falhas, o sistema tenta novamente e, após 3 tentativas, envia para dead-letter.
- Os logs registram request_id, timestamp, entrada, status e erro quando houver.

---

## Simulação de entrega

Para verificar o sistema do zero:

```bash
# 1. criar ambiente
python -m venv .venv
source .venv/bin/activate  # ou .\.venv\Scripts\Activate.ps1 no Windows
pip install -r requirements.txt

# 2. subir redis
docker compose up -d redis

# 3. iniciar worker
python -m app.worker

# 4. iniciar REST
uvicorn app.api_rest:app --host 0.0.0.0 --port 8000

# 5. iniciar gRPC
python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto
python -m app.servidor_grpc
```

Em seguida, valide:

- REST em /predict e /resultado/{id}
- gRPC em Prever e PreverLote
- fila Redis com mensagens pendentes
- worker processando corretamente e gravando resultados

---

## Licença

Este projeto é distribuído sob a licença do repositório original.
