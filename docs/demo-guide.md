# AI-OpsLog Demo Guide

## 1. 启动服务

```bash
docker compose up -d --build
```

## 2. 检查服务状态

```bash
docker compose ps
```

```bash
curl -s http://127.0.0.1:8000/health | python -m json.tool
```

## 3. 检查通义千问连接

```bash
curl -s http://127.0.0.1:8000/qwen/test | python -m json.tool
```

## 4. 发送 Docker 故障日志

```bash
python scripts/send_log.py \
  --server http://127.0.0.1:8000 \
  --source docker-host-01 \
  --service-name redis-container \
  --env dev \
  --log-type docker_log \
  --file examples/docker_port_conflict.log
```

## 5. 发送 Nginx Error 日志

```bash
python scripts/send_log.py \
  --server http://127.0.0.1:8000 \
  --source nginx-web-01 \
  --service-name nginx \
  --env dev \
  --log-type nginx_error \
  --file examples/nginx_error_502.log
```

## 6. 查看报告

```bash
ls -lh reports/
```

```bash
cat reports/生成的报告文件名.md
```

## 7. 检查报告目录挂载

```bash
curl -s http://127.0.0.1:8000/reports/check | python -m json.tool
```

```bash
docker exec -it ai-opslog-backend ls -lh /app/reports
```
