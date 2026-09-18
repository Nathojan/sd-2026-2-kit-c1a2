FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000 50051

CMD ["bash", "-lc", "python -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/inferencia.proto && uvicorn app.api_rest:app --host 0.0.0.0 --port 8000"]
