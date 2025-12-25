"""ALS 后台任务管理"""
import os
import re
import json
import time
import threading
import subprocess
import tempfile
from queue import Queue
from collections import deque
from database import get_connection


# 全局状态
RECOMPUTE_QUEUE: "Queue[int]" = Queue()
_PENDING_USERS: set = set()
_PENDING_LOCK = threading.Lock()
_WORKER_STARTED = False

USER_TASKS: dict = {}
USER_LOGS: dict = {}
USER_LOCK = threading.Lock()


def _user_task_init(user_id: int):
    with USER_LOCK:
        if user_id not in USER_TASKS:
            USER_TASKS[user_id] = {
                "status": "idle",
                "progress": 0,
                "queued_at": None,
                "started_at": None,
                "finished_at": None,
                "message": None,
                "result_count": None,
                "method": None,
                "last_error": None,
            }
        if user_id not in USER_LOGS:
            USER_LOGS[user_id] = deque(maxlen=300)


def _user_log(user_id: int, msg: str):
    _user_task_init(user_id)
    try:
        with USER_LOCK:
            USER_LOGS[user_id].append(f"{time.strftime('%H:%M:%S')} | {msg}")
    except Exception:
        pass


def _user_task_update(user_id: int, **fields):
    _user_task_init(user_id)
    with USER_LOCK:
        USER_TASKS[user_id].update(fields)


def enqueue_user_for_recompute(user_id: int):
    """将用户加入重算队列"""
    try:
        with _PENDING_LOCK:
            if user_id in _PENDING_USERS:
                return
            _PENDING_USERS.add(user_id)
            RECOMPUTE_QUEUE.put(user_id)
        _user_task_update(
            user_id,
            status="queued",
            progress=0,
            queued_at=time.time(),
            message="已加入队列，等待重算",
        )
        _user_log(user_id, "加入异步重算队列")
    except Exception as e:
        print(f"enqueue_user_for_recompute error: {e}")


def _recompute_user_recommendations(user_id: int, topN: int = 80):
    """调用 ALS 脚本重算用户推荐"""
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "code", "python", "movie_recommender.py")
    )
    cmd = ["python3.8", script_path, "--user_id", str(user_id), "--topN", str(topN)]

    def _apply_progress_marker(marker: str):
        marker = marker.strip().lower()
        mapping = {
            "model_loaded": (15, "加载模型"),
            "ratings_loaded": (25, "加载用户评分"),
            "item_factors_loaded": (45, "加载电影隐向量"),
            "user_vector_solved": (65, "求解用户隐向量"),
            "als_recommendations_built": (55, "生成ALS候选"),
            "predictions_scored": (85, "评分候选并排序"),
            "details_loaded": (92, "加载电影详情"),
            "done": (100, "完成"),
        }
        for key, (pct, msg) in mapping.items():
            if key in marker:
                prev = (USER_TASKS.get(user_id) or {}).get("progress") or 0
                new_pct = max(prev, pct)
                _user_task_update(user_id, progress=new_pct, message=msg)
                if new_pct > prev:
                    _user_log(user_id, f"阶段：{msg}（{pct}%）")
                return True
        return False

    def _apply_spark_stage_progress(line: str):
        m = re.search(r"\[Stage\s+(\d+):[^\(]*\((\d+)\s*\+\s*(\d+)\)\s*/\s*(\d+)\]", line)
        if not m:
            return False
        try:
            a, b, total = int(m.group(2)), int(m.group(3)), int(m.group(4))
            done = max(0, min(a + b, total))
            ratio = (done / total) if total > 0 else 0.0
            pct = int(20 + ratio * 65)
            prev = (USER_TASKS.get(user_id) or {}).get("progress") or 0
            if pct > prev:
                _user_task_update(user_id, progress=pct, message="Spark作业执行中")
            return True
        except Exception:
            return False

    try:
        _user_task_update(user_id, status="running", started_at=time.time(), progress=5, message="启动 ALS 推理...")
        _user_log(user_id, f"执行命令: {' '.join(cmd)}")

        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as tmp_out:
            out_path = tmp_out.name

        proc = subprocess.Popen(cmd, stdout=open(out_path, "w"), stderr=subprocess.PIPE, text=True, bufsize=1)

        try:
            for line in proc.stderr:
                if not line:
                    continue
                l = line.rstrip("\n")
                if l.startswith("[PROGRESS]"):
                    _apply_progress_marker(l.split("]", 1)[-1])
                else:
                    _apply_spark_stage_progress(l)
                    if l.strip():
                        _user_log(user_id, l)
        except Exception:
            pass

        exit_code = proc.wait(timeout=6200)
        if exit_code != 0:
            _user_log(user_id, f"ALS 推理失败，退出码 {exit_code}")
            _user_task_update(user_id, message=f"ALS 推理失败：{exit_code}")
            return False

        with open(out_path, "r") as f:
            raw = f.read()
        try:
            data = json.loads(raw.strip()) if raw else {}
        except Exception as je:
            _user_log(user_id, f"解析结果失败：{je}")
            return False

        recs = data.get("recommendations") or []
        _user_task_update(user_id, progress=88, message=f"解析推理结果：{len(recs)} 条")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_recommendations WHERE user_id = %s", (user_id,))

        rows = []
        for r in recs:
            mid = r.get("movie_id")
            pr = r.get("predict_rating")
            try:
                pr_val = float(pr) if pr is not None else None
            except Exception:
                pr_val = None
            if mid is not None:
                rows.append((user_id, int(mid), pr_val))

        if not rows:
            # 回退到热门电影
            c2 = conn.cursor(buffered=True, dictionary=True)
            c2.execute("SELECT movie_id FROM user_ratings WHERE user_id = %s", (user_id,))
            seen = {row["movie_id"] for row in c2.fetchall()}
            c2.execute(
                "SELECT movie_id, vote_average FROM movie_basic ORDER BY popularity_score DESC LIMIT %s",
                (topN * 2,),
            )
            for r in c2.fetchall():
                if r["movie_id"] not in seen:
                    rows.append((user_id, int(r["movie_id"]), float(r["vote_average"]) if r["vote_average"] else None))
                    if len(rows) >= topN:
                        break
            c2.close()

        if rows:
            cursor.executemany(
                "INSERT INTO user_recommendations (user_id, movie_id, predicted_rating) VALUES (%s, %s, %s)",
                rows,
            )
        conn.commit()
        cursor.close()
        conn.close()

        _user_task_update(
            user_id,
            status="done",
            progress=100,
            finished_at=time.time(),
            message="完成",
            result_count=len(rows),
            method="als" if recs else "fallback",
        )
        _user_log(user_id, "完成：推荐已更新")
        return True

    except Exception as e:
        _user_task_update(user_id, status="error", finished_at=time.time(), last_error=str(e), message=f"失败：{e}")
        _user_log(user_id, f"失败：{e}")
        return False


def _recompute_worker_loop():
    while True:
        user_id = RECOMPUTE_QUEUE.get()
        try:
            _recompute_user_recommendations(user_id)
        finally:
            with _PENDING_LOCK:
                _PENDING_USERS.discard(user_id)
            RECOMPUTE_QUEUE.task_done()


def start_recompute_worker():
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return
    t = threading.Thread(target=_recompute_worker_loop, name="recompute-worker", daemon=True)
    t.start()
    _WORKER_STARTED = True


def get_als_status() -> dict:
    with _PENDING_LOCK:
        pending = len(_PENDING_USERS)
    return {"worker_started": _WORKER_STARTED, "queue_size": RECOMPUTE_QUEUE.qsize(), "pending_users": pending}


def get_task_status(user_id: int) -> dict:
    _user_task_init(user_id)
    with USER_LOCK, _PENDING_LOCK:
        task = dict(USER_TASKS.get(user_id) or {})
        task["queued"] = user_id in _PENDING_USERS
        task["worker_started"] = _WORKER_STARTED
    return task


def get_task_logs(user_id: int) -> list:
    _user_task_init(user_id)
    with USER_LOCK:
        return list(USER_LOGS.get(user_id) or [])
