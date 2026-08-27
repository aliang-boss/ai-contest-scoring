"""
艺术升AI应用大赛评委打分系统 - 一键启动
"""
import sys
import os
import subprocess

# 确保在正确目录
os.chdir(os.path.dirname(os.path.abspath(__file__)))

backend_dir = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_dir)

# 初始化数据库
from database import init_db, seed_demo_data
init_db()
seed_demo_data()

# 启动 uvicorn
import uvicorn
from main import app

print("=" * 60)
print("  艺术升AI应用大赛 · 评委打分系统 v3.0")
print("  后端: FastAPI + SQLite")
print("  数据: 持久化存储，任何人访问同一份数据")
print("=" * 60)
print()
print("  访问地址: http://localhost:8080")
print("  管理员: admin / admin123")
print("  评委1: judge1 / 123456")
print("  ...")
print("  评委5: judge5 / 123456")
print()
print("  按 Ctrl+C 停止服务")
print("=" * 60)

uvicorn.run(app, host="0.0.0.0", port=8080)