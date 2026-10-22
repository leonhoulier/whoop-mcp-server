FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:e32be0e55814a08977501ca863271d9bd02443710db8f2afaf8372e2c4508530
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WHOOP_DATA_DIR=/data
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock && useradd --uid 1000 --create-home whoop
COPY src/shared_server.py src/shared_whoop.py ./
USER whoop
EXPOSE 8003
CMD ["python", "shared_server.py"]
