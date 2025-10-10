"""
Gunicorn配置文件
用于生产环境部署
"""

import multiprocessing
import os

# 服务器配置
bind = "0.0.0.0:8000"
backlog = 2048

# Worker配置
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000  # 处理N个请求后重启worker（防止内存泄漏）
max_requests_jitter = 50

# 超时配置
timeout = 120  # 请求超时（秒）
graceful_timeout = 30  # 优雅关闭超时
keepalive = 5  # Keep-Alive超时

# 日志配置
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "/var/log/image-classifier/access.log")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "/var/log/image-classifier/error.log")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "image-classifier"

# 其他配置
daemon = False  # 是否后台运行（建议用systemd管理）
pidfile = "/var/run/image-classifier.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# 环境变量
raw_env = [
    "ENV=production",
]

print(f"""
========================================
Gunicorn配置
========================================
Bind: {bind}
Workers: {workers}
Worker Class: {worker_class}
Timeout: {timeout}s
Log Level: {loglevel}
========================================
""")

