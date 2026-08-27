"""
艺术升AI应用大赛 · 评委打分系统 - FastAPI 后端
"""
import time
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from database import (
    init_db, seed_demo_data,
    get_all_judges, get_judge_by_username, add_judge, delete_judge,
    get_all_projects, add_project, delete_project,
    get_project_scores, get_all_scores, save_score,
    get_rankings, compute_rankings,
    get_setting, set_setting, get_full_data
)
from models import (
    LoginRequest, SubmitScoreRequest, ComputeRequest,
    JudgeCreate, ProjectCreate
)

app = FastAPI(title="艺术升AI应用大赛评委打分系统", version="3.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 评分维度配置
RULES = [
    {"id": "practicality", "name": "一、实用性", "max": 40, "color": "#4f46e5", "items": [
        {"id": "pain_point", "label": "痛点真实性", "max": 15},
        {"id": "workflow_embed", "label": "工作流嵌入度", "max": 10},
        {"id": "feasibility", "label": "可落地性", "max": 10},
        {"id": "transferability", "label": "可迁移性", "max": 5}
    ]},
    {"id": "innovation", "name": "二、创新性", "max": 30, "color": "#ef4444", "items": [
        {"id": "novelty", "label": "思路新颖度", "max": 12},
        {"id": "workflow_design", "label": "工作流设计", "max": 10},
        {"id": "experience_deposit", "label": "个人经验沉淀", "max": 8}
    ]},
    {"id": "efficiency", "name": "三、效率提升", "max": 20, "color": "#10b981", "items": [
        {"id": "quantitative", "label": "量化提升幅度", "max": 10},
        {"id": "quality", "label": "质量提升", "max": 5},
        {"id": "sustainability", "label": "可持续性", "max": 5}
    ]},
    {"id": "completeness", "name": "四、作品完整性", "max": 10, "color": "#f59e0b", "items": [
        {"id": "end_to_end", "label": "端到端可用性", "max": 4},
        {"id": "documentation", "label": "文档与说明", "max": 2},
        {"id": "demo_quality", "label": "演示完成度", "max": 2},
        {"id": "exception_handling", "label": "边界与异常处理", "max": 2}
    ]}
]


@app.on_event("startup")
async def startup():
    init_db()
    seed_demo_data()


# ==================== 认证 ====================

@app.post("/api/login")
def login(req: LoginRequest):
    admin_user = get_setting("adminUser", "admin")
    admin_pass = get_setting("adminPass", "admin123")
    if (req.username == "admin" and req.password == admin_pass) or (req.username == admin_user and req.password == admin_pass):
        return {"type": "admin", "name": "管理员", "avatar": "🛡️"}

    judge = get_judge_by_username(req.username)
    if judge and judge["password"] == req.password:
        return {"type": "judge", "judgeId": judge["id"], "name": judge["name"], "avatar": judge.get("avatar", "")}

    raise HTTPException(401, "账号或密码错误")


# ==================== 评委管理 ====================

@app.get("/api/judges")
def list_judges():
    return get_all_judges()


@app.post("/api/judges")
def create_judge(data: JudgeCreate):
    existing = get_judge_by_username(data.username)
    if existing:
        raise HTTPException(400, "该账号已存在")
    add_judge(data.model_dump())
    return {"ok": True}


@app.delete("/api/judges/{jid}")
def remove_judge(jid: str):
    delete_judge(jid)
    return {"ok": True}


# ==================== 项目管理 ====================

@app.get("/api/projects")
def list_projects():
    return get_all_projects()


@app.post("/api/projects")
def create_project(data: ProjectCreate):
    add_project(data.model_dump())
    return {"ok": True}


@app.delete("/api/projects/{pid}")
def remove_project(pid: str):
    delete_project(pid)
    return {"ok": True}


# ==================== 评分 ====================

@app.get("/api/scores/{pid}")
def get_scores(pid: str):
    return get_project_scores(pid)


@app.get("/api/scores")
def get_all_scores_api():
    return get_all_scores()


@app.post("/api/scores")
def submit_score(data: SubmitScoreRequest):
    ts = int(time.time() * 1000)
    score_data = {
        "project_id": data.project_id,
        "judge_id": data.judge_id,
        "pain_point": data.items.pain_point,
        "workflow_embed": data.items.workflow_embed,
        "feasibility": data.items.feasibility,
        "transferability": data.items.transferability,
        "novelty": data.items.novelty,
        "workflow_design": data.items.workflow_design,
        "experience_deposit": data.items.experience_deposit,
        "quantitative": data.items.quantitative,
        "quality": data.items.quality,
        "sustainability": data.items.sustainability,
        "end_to_end": data.items.end_to_end,
        "documentation": data.items.documentation,
        "demo_quality": data.items.demo_quality,
        "exception_handling": data.items.exception_handling,
        "penalty": data.penalty,
        "timestamp": data.timestamp or ts
    }
    save_score(score_data)

    # 自动重新计算排名
    try:
        compute_rankings()
    except:
        pass

    return {"ok": True, "timestamp": ts}


# ==================== 排名计算 ====================

@app.get("/api/rankings")
def get_rankings_api():
    return get_rankings()


@app.post("/api/compute")
def compute(req: ComputeRequest):
    result = compute_rankings(req.penalties)
    return result


# ==================== 数据同步 ====================

@app.get("/api/data")
def get_data():
    return get_full_data()


@app.get("/api/rules")
def get_rules():
    return RULES


# ==================== 设置 ====================

@app.get("/api/settings/{key}")
def get_setting_api(key: str):
    return {"value": get_setting(key, "")}


@app.post("/api/settings/{key}")
async def set_setting_api(key: str):
    from fastapi import Request
    body = await Request.json()
    set_setting(key, str(body.get("value", "")))
    return {"ok": True}


# ==================== 静态文件 ====================

import os
# Render上从backend目录启动，frontend在../frontend；本地启动在项目根
_frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if not os.path.isdir(_frontend_dir):
    _frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
if os.path.isdir(_frontend_dir):
    app.mount("/", StaticFiles(directory=_frontend_dir, html=True), name="frontend")