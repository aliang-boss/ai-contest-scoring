"""
SQLite 数据库初始化和操作
"""
import sqlite3
import json
import os
from pathlib import Path

import os
# 数据目录：优先使用环境变量，否则相对于backend目录的上级
_data_root = os.environ.get("DATA_ROOT", str(Path(__file__).resolve().parent.parent))
DB_DIR = Path(_data_root) / "data"
DB_PATH = DB_DIR / "contest.db"

# 种子数据路径：尝试多个可能位置
_seed_candidates = [
    Path(__file__).resolve().parent.parent.parent.parent / "tmp" / "demo_data.json",
    Path(__file__).resolve().parent.parent / "tmp" / "demo_data.json",
    Path("/tmp/demo_data.json"),
]
DEMO_DATA_PATH = None
for _c in _seed_candidates:
    if _c.exists():
        DEMO_DATA_PATH = _c
        break


def get_db() -> sqlite3.Connection:
    """获取数据库连接"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS judges (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            avatar TEXT DEFAULT '',
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            applicant TEXT NOT NULL,
            members TEXT DEFAULT '',
            brief TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            judge_id TEXT NOT NULL,
            pain_point REAL DEFAULT 0,
            workflow_embed REAL DEFAULT 0,
            feasibility REAL DEFAULT 0,
            transferability REAL DEFAULT 0,
            novelty REAL DEFAULT 0,
            workflow_design REAL DEFAULT 0,
            experience_deposit REAL DEFAULT 0,
            quantitative REAL DEFAULT 0,
            quality REAL DEFAULT 0,
            sustainability REAL DEFAULT 0,
            end_to_end REAL DEFAULT 0,
            documentation REAL DEFAULT 0,
            demo_quality REAL DEFAULT 0,
            exception_handling REAL DEFAULT 0,
            penalty REAL DEFAULT 0,
            timestamp INTEGER DEFAULT 0,
            UNIQUE(project_id, judge_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (judge_id) REFERENCES judges(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS computed (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id TEXT NOT NULL,
            total REAL NOT NULL,
            judge_count INTEGER DEFAULT 0,
            grade TEXT NOT NULL,
            penalty REAL DEFAULT 0,
            timestamp INTEGER DEFAULT 0,
            UNIQUE(project_id),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        );
    """)

    # 设置默认管理员密码
    c.execute(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        ("adminPass", "admin123")
    )

    conn.commit()
    conn.close()


def seed_demo_data():
    """从 demo_data.json 预置演示数据"""
    if not DEMO_DATA_PATH.exists():
        print(f"[WARN] demo_data.json not found at {DEMO_DATA_PATH}, skipping seed")
        return

    conn = get_db()
    c = conn.cursor()

    # 检查是否已有数据
    c.execute("SELECT COUNT(*) FROM judges")
    if c.fetchone()[0] > 0:
        conn.close()
        return

    with open(DEMO_DATA_PATH, "r", encoding="utf-8") as f:
        demo = json.load(f)

    # 插入评委
    for j in demo.get("judges", []):
        c.execute(
            "INSERT OR IGNORE INTO judges (id, name, avatar, username, password) VALUES (?,?,?,?,?)",
            (j["id"], j["name"], j.get("avatar", ""), j["username"], j["password"])
        )

    # 插入项目
    for p in demo.get("projects", []):
        c.execute(
            "INSERT OR IGNORE INTO projects (id, applicant, members, brief) VALUES (?,?,?,?)",
            (p["id"], p["applicant"], p.get("members", ""), p.get("brief", ""))
        )

    # 插入评分
    scores = demo.get("scores", {})
    for pid, judge_scores in scores.items():
        for jid, sdata in judge_scores.items():
            items = sdata.get("items", {})
            c.execute(
                """INSERT OR REPLACE INTO scores
                (project_id, judge_id, pain_point, workflow_embed, feasibility, transferability,
                 novelty, workflow_design, experience_deposit, quantitative, quality, sustainability,
                 end_to_end, documentation, demo_quality, exception_handling, penalty, timestamp)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    pid, jid,
                    items.get("pain_point", 0),
                    items.get("workflow_embed", 0),
                    items.get("feasibility", 0),
                    items.get("transferability", 0),
                    items.get("novelty", 0),
                    items.get("workflow_design", 0),
                    items.get("experience_deposit", 0),
                    items.get("quantitative", 0),
                    items.get("quality", 0),
                    items.get("sustainability", 0),
                    items.get("end_to_end", 0),
                    items.get("documentation", 0),
                    items.get("demo_quality", 0),
                    items.get("exception_handling", 0),
                    sdata.get("penalty", 0),
                    sdata.get("timestamp", 0)
                )
            )

    # 插入计算结果
    computed = demo.get("computed", {})
    for r in computed.get("results", []):
        c.execute(
            "INSERT OR REPLACE INTO computed (project_id, total, judge_count, grade, penalty, timestamp) VALUES (?,?,?,?,?,?)",
            (r["pid"], r["total"], r["judgeCount"], r["grade"], 0, computed.get("timestamp", 0))
        )

    # 设置管理员密码
    admin_pass = demo.get("adminPass", "admin123")
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('adminPass', ?)", (admin_pass,))

    conn.commit()
    conn.close()
    print(f"[OK] Seeded {len(demo.get('judges',[]))} judges, {len(demo.get('projects',[]))} projects")


# ========== 数据操作函数 ==========

def get_all_judges():
    conn = get_db()
    rows = conn.execute("SELECT * FROM judges").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_judge_by_username(username: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM judges WHERE username = ?", (username,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_judge(data: dict):
    conn = get_db()
    conn.execute(
        "INSERT INTO judges (id, name, avatar, username, password) VALUES (?,?,?,?,?)",
        (data["id"], data["name"], data.get("avatar", ""), data["username"], data["password"])
    )
    conn.commit()
    conn.close()


def delete_judge(jid: str):
    conn = get_db()
    conn.execute("DELETE FROM judges WHERE id = ?", (jid,))
    conn.commit()
    conn.close()


def get_all_projects():
    conn = get_db()
    rows = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_project(data: dict):
    conn = get_db()
    conn.execute(
        "INSERT INTO projects (id, applicant, members, brief) VALUES (?,?,?,?)",
        (data["id"], data["applicant"], data.get("members", ""), data.get("brief", ""))
    )
    conn.commit()
    conn.close()


def delete_project(pid: str):
    conn = get_db()
    conn.execute("DELETE FROM projects WHERE id = ?", (pid,))
    conn.commit()
    conn.close()


def get_project_scores(pid: str):
    conn = get_db()
    rows = conn.execute("SELECT * FROM scores WHERE project_id = ?", (pid,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_scores():
    conn = get_db()
    rows = conn.execute("SELECT * FROM scores").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_score(data: dict):
    conn = get_db()
    conn.execute(
        """INSERT OR REPLACE INTO scores
        (project_id, judge_id, pain_point, workflow_embed, feasibility, transferability,
         novelty, workflow_design, experience_deposit, quantitative, quality, sustainability,
         end_to_end, documentation, demo_quality, exception_handling, penalty, timestamp)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data["project_id"], data["judge_id"],
            data.get("pain_point", 0), data.get("workflow_embed", 0),
            data.get("feasibility", 0), data.get("transferability", 0),
            data.get("novelty", 0), data.get("workflow_design", 0),
            data.get("experience_deposit", 0), data.get("quantitative", 0),
            data.get("quality", 0), data.get("sustainability", 0),
            data.get("end_to_end", 0), data.get("documentation", 0),
            data.get("demo_quality", 0), data.get("exception_handling", 0),
            data.get("penalty", 0), data.get("timestamp", 0)
        )
    )
    conn.commit()
    conn.close()


def compute_rankings(penalties: dict = None):
    """计算所有项目总分和排名"""
    import time
    conn = get_db()
    judges = conn.execute("SELECT id FROM judges").fetchall()
    projects = conn.execute("SELECT * FROM projects").fetchall()
    all_scores = conn.execute("SELECT * FROM scores").fetchall()
    conn.close()

    if penalties is None:
        penalties = {}

    jids = [j["id"] for j in judges]
    results = []

    # 评分维度最大值
    dim_max = {
        "pain_point": 15, "workflow_embed": 10, "feasibility": 10, "transferability": 5,
        "novelty": 12, "workflow_design": 10, "experience_deposit": 8,
        "quantitative": 10, "quality": 5, "sustainability": 5,
        "end_to_end": 4, "documentation": 2, "demo_quality": 2, "exception_handling": 2
    }

    for proj in projects:
        pid = proj["id"]
        proj_scores = [s for s in all_scores if s["project_id"] == pid]
        if not proj_scores:
            continue

        # 每个评委的总分
        judge_totals = {}
        for s in proj_scores:
            total = sum(s[k] for k in dim_max)
            judge_totals[s["judge_id"]] = total

        # 平均分
        avg = sum(judge_totals.values()) / len(judge_totals) if judge_totals else 0
        penalty = float(penalties.get(pid, 0))
        final = round(avg - penalty, 2)

        if final >= 90:
            grade = "一等奖"
        elif final >= 75:
            grade = "二/三等奖"
        elif final >= 60:
            grade = "入围"
        else:
            grade = "陪跑"

        results.append({
            "project_id": pid,
            "total": final,
            "judge_count": len(judge_totals),
            "grade": grade,
            "penalty": penalty
        })

    # 排序
    results.sort(key=lambda x: x["total"], reverse=True)

    # 存入数据库
    conn = get_db()
    ts = int(time.time() * 1000)
    conn.execute("DELETE FROM computed")
    for i, r in enumerate(results):
        conn.execute(
            "INSERT INTO computed (project_id, total, judge_count, grade, penalty, timestamp) VALUES (?,?,?,?,?,?)",
            (r["project_id"], r["total"], r["judge_count"], r["grade"], r["penalty"], ts)
        )
    conn.commit()
    conn.close()

    return {"timestamp": ts, "results": results}


def get_rankings():
    conn = get_db()
    rows = conn.execute("SELECT * FROM computed ORDER BY total DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_setting(key: str, default=None):
    conn = get_db()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_db()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, value))
    conn.commit()
    conn.close()


def get_full_data():
    """获取完整数据JSON（用于导出/发布）"""
    judges = get_all_judges()
    projects = get_all_projects()
    all_scores = get_all_scores()
    rankings = get_rankings()
    admin_pass = get_setting("adminPass", "admin123")

    # 重组scores结构
    scores_dict = {}
    for s in all_scores:
        pid = s["project_id"]
        if pid not in scores_dict:
            scores_dict[pid] = {}
        scores_dict[pid][s["judge_id"]] = {
            "items": {
                "pain_point": s["pain_point"],
                "workflow_embed": s["workflow_embed"],
                "feasibility": s["feasibility"],
                "transferability": s["transferability"],
                "novelty": s["novelty"],
                "workflow_design": s["workflow_design"],
                "experience_deposit": s["experience_deposit"],
                "quantitative": s["quantitative"],
                "quality": s["quality"],
                "sustainability": s["sustainability"],
                "end_to_end": s["end_to_end"],
                "documentation": s["documentation"],
                "demo_quality": s["demo_quality"],
                "exception_handling": s["exception_handling"]
            },
            "penalty": s["penalty"],
            "timestamp": s["timestamp"]
        }

    computed = None
    if rankings:
        computed = {
            "timestamp": rankings[0].get("timestamp", 0),
            "results": [
                {
                    "pid": r["project_id"],
                    "total": r["total"],
                    "judgeCount": r["judge_count"],
                    "grade": r["grade"]
                } for r in rankings
            ]
        }

    return {
        "judges": judges,
        "projects": projects,
        "scores": scores_dict,
        "computed": computed,
        "projectPenalties": {},
        "adminPass": admin_pass
    }