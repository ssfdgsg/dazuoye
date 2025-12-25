import os
import re
import json
import base64
import random
import threading
import time
from collections import deque
from pathlib import Path
import shlex
import threading
import time
from collections import deque
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import mysql.connector
import numpy as np
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import threading
from queue import Queue

app = Flask(__name__, static_folder='static')
CORS(app)  # 允许跨域请求
app.secret_key = os.getenv('SECRET_KEY', 'movie-recommendation-secret-key-2024')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Database configuration (use environment variables with sensible defaults)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'root')
DB_PASS = os.getenv('DB_PASS', 'root123')
DB_NAME = os.getenv('DB_NAME', 'movie_db')

# ===== 背景任务：评分后异步重算用户推荐 =====
RECOMPUTE_QUEUE: "Queue[int]" = Queue()
_PENDING_USERS = set()
_PENDING_LOCK = threading.Lock()
_WORKER_STARTED = False

# ===== 每用户任务状态与日志（仅内存，重启清空） =====
USER_TASKS = {}
USER_LOGS = {}
USER_LOCK = threading.Lock()

def _user_task_init(user_id: int):
    with USER_LOCK:
        if user_id not in USER_TASKS:
            USER_TASKS[user_id] = {
                'status': 'idle',  # idle|queued|running|done|error
                'progress': 0,
                'queued_at': None,
                'started_at': None,
                'finished_at': None,
                'message': None,
                'result_count': None,
                'method': None,
                'last_error': None,
            }
        if user_id not in USER_LOGS:
            # 只保留最近 300 行日志
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

def ensure_user_recommendations_table(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_recommendations (
            user_id INT NOT NULL,
            movie_id INT NOT NULL,
            predicted_rating FLOAT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, movie_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )

def enqueue_user_for_recompute(user_id: int):
    try:
        with _PENDING_LOCK:
            if user_id in _PENDING_USERS:
                return
            _PENDING_USERS.add(user_id)
            RECOMPUTE_QUEUE.put(user_id)
        _user_task_update(user_id,
                          status='queued',
                          progress=0,
                          queued_at=time.time(),
                          message='已加入队列，等待重算')
        _user_log(user_id, '加入异步重算队列')
    except Exception as e:
        print(f"enqueue_user_for_recompute error: {e}")

def _recompute_user_recommendations(user_id: int, topN: int = 80):
    """调用现有 ALS 脚本（流式捕获进度），生成个性化推荐，并写入 user_recommendations 表"""
    import tempfile
    script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'code', 'python', 'movie_recommender.py'))
    cmd = ['python3.8', script_path, '--user_id', str(user_id), '--topN', str(topN)]

    def _apply_progress_marker(marker: str):
        marker = marker.strip().lower()
        # 将脚本阶段映射到进度
        mapping = {
            'model_loaded': (15, '加载模型'),
            'ratings_loaded': (25, '加载用户评分'),
            'item_factors_loaded': (45, '加载电影隐向量'),
            'user_vector_solved': (65, '求解用户隐向量'),
            'als_recommendations_built': (55, '生成ALS候选'),
            'predictions_scored': (85, '评分候选并排序'),
            'details_loaded': (92, '加载电影详情'),
            'done': (100, '完成'),
        }
        for key, (pct, msg) in mapping.items():
            if key in marker:
                prev = (USER_TASKS.get(user_id) or {}).get('progress') or 0
                new_pct = max(prev, pct)
                _user_task_update(user_id, progress=new_pct, message=msg)
                if new_pct > prev:
                    _user_log(user_id, f"阶段：{msg}（{pct}%）")
                return True
        return False

    def _apply_progress_keyword(line: str):
        """根据常见 Spark 启动日志，平滑提升早期进度，避免长时间停留在 5%。"""
        kw_map = [
            (['SLF4J:', 'binding'], 7, '初始化日志模块'),
            (['hostname', 'loopback'], 9, '初始化网络'),
            (['NativeCodeLoader'], 12, '加载 Hadoop 本地库'),
            (['Setting default log level'], 16, '初始化 Spark'),
            (['setLogLevel'], 18, '配置日志级别'),
        ]
        low = (USER_TASKS.get(user_id) or {}).get('progress') or 0
        for kws, pct, msg in kw_map:
            if all(k.lower() in line.lower() for k in kws):
                if pct > low:
                    _user_task_update(user_id, progress=pct, message=msg)
                    _user_log(user_id, f"阶段：{msg}（{pct}%）")
                return True
        return False

    def _apply_spark_stage_progress(line: str):
        """解析 Spark 的 [Stage x: ... (a + b) / total] 日志，映射为 20%-85% 的平滑进度。"""
        m = re.search(r"\[Stage\s+(\d+):[^\(]*\((\d+)\s*\+\s*(\d+)\)\s*/\s*(\d+)\]", line)
        if not m:
            return False
        try:
            a = int(m.group(2))
            b = int(m.group(3))
            total = int(m.group(4))
            done = max(0, min(a + b, total))
            ratio = (done / total) if total > 0 else 0.0
            base = 20  # 下限：Spark 作业阶段开始
            cap = 85   # 上限：进入打分/详情前
            pct = int(base + ratio * (cap - base))
            prev = (USER_TASKS.get(user_id) or {}).get('progress') or 0
            if pct > prev:
                _user_task_update(user_id, progress=pct, message='Spark作业执行中')
            return True
        except Exception:
            return False

    try:
        _user_task_update(user_id, status='running', started_at=time.time(), progress=5, message='启动 ALS 推理...')
        _user_log(user_id, f"执行命令: {' '.join(cmd)}")

        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_out:
            out_path = tmp_out.name
        # 以流式方式读取stderr作为进度/日志通道，stdout写入临时文件供完成后解析
        proc = subprocess.Popen(
            cmd,
            stdout=open(out_path, 'w'),
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # 持续读取stderr以更新日志与进度
        try:
            for line in proc.stderr:
                if not line:
                    continue
                l = line.rstrip('\n')
                if l.startswith('[PROGRESS]'):
                    marker = l.split(']', 1)[-1]
                    _apply_progress_marker(marker)
                else:
                    # 尝试解析 Spark 阶段进度与关键字，再记录日志（跳过空行）
                    progressed = _apply_progress_keyword(l)
                    progressed = _apply_spark_stage_progress(l) or progressed
                    if l.strip():
                        _user_log(user_id, l)
        except Exception:
            pass

        exit_code = proc.wait(timeout=6200)
        if exit_code != 0:
            _user_log(user_id, f"ALS 推理失败，退出码 {exit_code}")
            _user_task_update(user_id, message=f"ALS 推理失败：{exit_code}")
            return False

        # 读取JSON结果
        with open(out_path, 'r') as f:
            raw = f.read()
        try:
            data = json.loads(raw.strip()) if raw else {}
        except Exception as je:
            _user_log(user_id, f"解析结果失败：{je}")
            _user_task_update(user_id, message='解析结果失败')
            return False
        recs = data.get('recommendations') or []
        _user_task_update(user_id, progress=max(USER_TASKS[user_id].get('progress') or 0, 88), message=f'解析推理结果：{len(recs)} 条')
        _user_log(user_id, f"推理返回 {len(recs)} 条候选")

        conn = get_mysql_conn()
        cursor = conn.cursor()
        ensure_user_recommendations_table(cursor)

        cursor.execute("DELETE FROM user_recommendations WHERE user_id = %s", (user_id,))
        rows = []
        if recs:
            for r in recs:
                mid = r.get('movie_id')
                pr = r.get('predict_rating')
                try:
                    pr_val = float(pr) if pr is not None else None
                except Exception:
                    pr_val = None
                if mid is not None:
                    rows.append((user_id, int(mid), pr_val))
        else:
            # ALS 无结果时，使用热门回退并排除用户已评分
            try:
                c2 = conn.cursor(buffered=True, dictionary=True)
                c2.execute("SELECT movie_id FROM user_ratings WHERE user_id = %s", (user_id,))
                rated_rows = c2.fetchall()
                seen = {row['movie_id'] for row in rated_rows} if rated_rows else set()

                c2.execute(
                    "SELECT movie_id, vote_average FROM movie_basic ORDER BY popularity_score DESC, vote_average DESC LIMIT %s",
                    (topN * 2,),
                )
                pop_rows = c2.fetchall()
                for r in pop_rows:
                    mid = r.get('movie_id')
                    if mid in seen:
                        continue
                    pr_val = float(r.get('vote_average')) if r.get('vote_average') is not None else None
                    rows.append((user_id, int(mid), pr_val))
                    if len(rows) >= topN:
                        break
                _user_log(user_id, f"ALS 无结果，采用热门回退，生成 {len(rows)} 条")
            except Exception as e:
                print(f"回退推荐失败 user_id={user_id}: {e}")
                _user_log(user_id, f"回退生成失败：{e}")
            finally:
                try:
                    c2.close()
                except Exception:
                    pass

        if rows:
            cursor.executemany(
                "INSERT INTO user_recommendations (user_id, movie_id, predicted_rating) VALUES (%s, %s, %s)",
                rows,
            )
        _user_task_update(user_id, progress=max(USER_TASKS[user_id].get('progress') or 0, 96), message=f'写入推荐表 {len(rows)} 条')
        _user_log(user_id, f"写入 user_recommendations 行数：{len(rows)}")
        conn.commit()
        cursor.close()
        conn.close()
        print(f"已重算并更新用户 {user_id} 的推荐，共 {len(recs)} 条")
        print(f"已重算并更新用户 {user_id} 的推荐，共 {len(rows)} 条（ALS 返回 {len(recs)} 条）")
        _user_task_update(user_id, status='done', progress=100, finished_at=time.time(), message='完成', result_count=len(rows), method='als' if recs else 'fallback')
        _user_log(user_id, '完成：推荐已更新')
    except Exception as e:
        print(f"重算用户 {user_id} 推荐失败: {e}")
        _user_task_update(user_id, status='error', finished_at=time.time(), last_error=str(e), message=f'失败：{e}')
        _user_log(user_id, f"失败：{e}")
        return False

def _recompute_worker_loop():
    while True:
        user_id = RECOMPUTE_QUEUE.get()
        try:
            _user_task_update(user_id, status='running', started_at=time.time(), message='开始重算推荐')
            _user_log(user_id, '开始重算推荐')
            _recompute_user_recommendations(user_id)
        finally:
            with _PENDING_LOCK:
                _PENDING_USERS.discard(user_id)
            RECOMPUTE_QUEUE.task_done()

def start_recompute_worker():
    global _WORKER_STARTED
    if _WORKER_STARTED:
        return
    t = threading.Thread(target=_recompute_worker_loop, name='recompute-worker', daemon=True)
    t.start()
    _WORKER_STARTED = True


def get_mysql_conn():
    try:
        return mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASS,
            database=DB_NAME,
            charset='utf8mb4'
        )
    except mysql.connector.Error as e:
        # Re-raise so callers can return a JSON error
        raise


def ensure_users_table(cursor):
    """Create a minimal users table when missing so login/registration works."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def ensure_user_ratings_table(cursor):
    """Create user_ratings table if missing to avoid runtime failures."""
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user_ratings (
            user_id INT COMMENT '用户ID',
            movie_id INT COMMENT '电影ID',
            rating DECIMAL(2,1) COMMENT '评分（1-5分）',
            rating_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '评分时间',
            PRIMARY KEY (user_id, movie_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def ensure_rating_time_column(cursor):
    """Add rating_time column if legacy table is missing it."""
    cursor.execute(
        """
        SELECT 1 FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'user_ratings' AND COLUMN_NAME = 'rating_time'
        """,
        (DB_NAME,),
    )
    exists = cursor.fetchone()
    if not exists:
        cursor.execute(
            """
            ALTER TABLE user_ratings
            ADD COLUMN rating_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '评分时间'
            """
        )


def decode_tfidf(encoded_str):
    """解码 Base64 编码的 TF-IDF 向量（小端序）"""
    if not encoded_str:
        return None
    try:
        b = base64.b64decode(encoded_str)
        # Scala 使用 LITTLE_ENDIAN 写入，因此使用 '<f8' 解码
        vec = np.frombuffer(b, dtype='<f8')
        return vec.astype(np.float64)
    except Exception as e:
        print(f"TF-IDF 解码失败: {e}")
        return None


@app.route('/api/movie/<int:movie_id>/similar')
def similar_movies(movie_id):
    topN = int(request.args.get('topN', 5))
    try:
        conn = get_mysql_conn()
    except Exception as e:
        return jsonify({'error': 'database connection failed', 'detail': str(e)}), 500
    cursor = conn.cursor(buffered=True, dictionary=True)

    # Get target movie
    cursor.execute(
        """
        SELECT m.movie_id, m.title, m.genres, f.tfidf_features
        FROM movie_basic m
        JOIN movie_features f ON m.movie_id = f.movie_id
        WHERE m.movie_id = %s
        """,
        (movie_id,)
    )
    target = cursor.fetchone()
    if not target:
        cursor.close()
        conn.close()
        return jsonify({'error': f'movie_id {movie_id} not found'}), 404

    target_vec = decode_tfidf(target.get('tfidf_features'))
    if target_vec is None or np.linalg.norm(target_vec) == 0:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Target movie has no valid tfidf_features'}), 400

    # Fetch other movies with features
    cursor.execute(
        """
        SELECT m.movie_id, m.title, m.genres, f.tfidf_features
        FROM movie_basic m
        JOIN movie_features f ON m.movie_id = f.movie_id
        WHERE m.movie_id != %s AND f.tfidf_features IS NOT NULL
        """,
        (movie_id,)
    )

    candidates = cursor.fetchall()
    results = []
    for row in candidates:
        try:
            vec = decode_tfidf(row.get('tfidf_features'))
            if vec is None:
                continue
            denom = np.linalg.norm(target_vec) * np.linalg.norm(vec)
            if denom == 0:
                sim = 0.0
            else:
                sim = float(np.dot(target_vec, vec) / denom)

            results.append({
                'movie_id': row['movie_id'],
                'title': row['title'],
                'genres': row.get('genres'),
                'similarity': round(sim, 4)
            })
        except Exception:
            continue

    cursor.close()
    conn.close()

    results.sort(key=lambda x: x['similarity'], reverse=True)
    return jsonify({
        'movie_id': movie_id,
        'title': target.get('title'),
        'recommendations': results[:topN]
    })


@app.route('/api/user/<int:user_id>/recommend')
def recommend_by_user(user_id):
    # 优先使用预计算表 user_recommendations（与首页“猜你喜欢”一致），失败则回退热门排除已评分
    topN = int(request.args.get('topN', 10))

    try:
        try:
            conn = get_mysql_conn()
        except Exception as e:
            return jsonify({'error': 'database connection failed', 'detail': str(e)}), 500
        cursor = conn.cursor(buffered=True, dictionary=True)

        # 尝试读取预计算的 ALS 推荐
        cursor.execute(
            """
            SELECT r.movie_id, m.title, m.genres, m.vote_average, m.release_date, r.predicted_rating
            FROM user_recommendations r
            JOIN movie_basic m ON r.movie_id = m.movie_id
            WHERE r.user_id = %s
            ORDER BY r.predicted_rating DESC
            LIMIT %s
            """,
            (user_id, topN),
        )
        als_rows = cursor.fetchall()
        if als_rows:
            mapped = []
            for rec in als_rows:
                genres_list = rec['genres'].split('|') if rec['genres'] else []
                mapped.append({
                    'movie_id': rec['movie_id'],
                    'title': rec['title'],
                    'genres': genres_list,
                    'release_date': str(rec['release_date']) if rec['release_date'] else None,
                    'vote_average': float(rec['vote_average']) if rec['vote_average'] is not None else None,
                    'predicted_rating': float(rec['predicted_rating']) if rec['predicted_rating'] is not None else None
                })
            cursor.close()
            conn.close()
            return jsonify({'user_id': user_id, 'recommendations': mapped, 'method': 'als_model'})

        # 回退策略：热门电影，排除该用户已评分
        cursor.execute("SELECT movie_id FROM user_ratings WHERE user_id = %s", (user_id,))
        rated_rows = cursor.fetchall()
        seen = {row['movie_id'] for row in rated_rows} if rated_rows else set()

        cursor.execute(
            "SELECT movie_id, title, genres, release_date, vote_average, popularity_score FROM movie_basic ORDER BY popularity_score DESC, vote_average DESC LIMIT 80"
        )
        all_rows = cursor.fetchall()
        candidates = [r for r in all_rows if r['movie_id'] not in seen]

        recommendations = []
        for r in candidates[:topN]:
            recommendations.append({
                'movie_id': r['movie_id'],
                'title': r['title'],
                'genres': r.get('genres'),
                'release_date': str(r.get('release_date')) if r.get('release_date') else None,
                'vote_average': float(r.get('vote_average')) if r.get('vote_average') is not None else None
            })

        cursor.close()
        conn.close()
        return jsonify({'user_id': user_id, 'recommendations': recommendations, 'method': 'fallback'})

    except Exception as e:
        try:
            cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'error': 'database query failed', 'detail': str(e)}), 500


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/img/<path:filename>')
def serve_image(filename):
    """提供电影海报图片"""
    return send_from_directory('static/img', filename)


@app.route('/api/movie/<int:movie_id>')
def get_movie_detail(movie_id):
    """获取单个电影的详细信息"""
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # 获取电影基本信息和特征
        cursor.execute("""
            SELECT 
                b.movie_id,
                b.title,
                b.genres,
                b.release_date,
                b.runtime,
                b.vote_average,
                b.vote_count,
                b.popularity_score,
                b.budget_million,
                b.revenue,
                b.keywords as basic_keywords,
                b.production_companies as basic_companies,
                f.keywords as feature_keywords,
                f.production_companies as feature_companies
            FROM movie_basic b
            LEFT JOIN movie_features f ON b.movie_id = f.movie_id
            WHERE b.movie_id = %s
        """, (movie_id,))
        
        movie = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not movie:
            return jsonify({'error': f'Movie ID {movie_id} not found'}), 404
        
        # 合并 keywords 和 production_companies（优先使用 basic 表）
        keywords_str = movie['basic_keywords'] or movie['feature_keywords'] or ''
        companies_str = movie['basic_companies'] or movie['feature_companies'] or ''
        
        # 格式化数据
        result = {
            'id': movie['movie_id'],
            'title': movie['title'],
            'genres': movie['genres'].split(',') if movie['genres'] else [],
            'release_date': str(movie['release_date']) if movie['release_date'] else None,
            'runtime': movie['runtime'],
            'rating': float(movie['vote_average']) if movie['vote_average'] else 0.0,
            'vote_count': movie['vote_count'],
            'popularity': float(movie['popularity_score']) if movie['popularity_score'] else 0.0,
            'budget': float(movie['budget_million']) if movie['budget_million'] else 0.0,
            'revenue': movie['revenue'] or '0',
            'overview': f"{movie['title']} 是一部 {movie['genres']} 类型的电影。" if movie['genres'] else '暂无简介',
            'keywords': [k.strip() for k in keywords_str.split(',') if k.strip()] if keywords_str else [],
            'production_companies': [c.strip() for c in companies_str.split(',') if c.strip()] if companies_str else [],
            'language': 'en',
            'poster': f"img/{movie['movie_id']}.webp"
        }
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch movie details', 'detail': str(e)}), 500


@app.route('/api/similar-movies/<int:movie_id>')
def get_similar_movies(movie_id):
    """获取相似电影列表（基于 TF-IDF 相似度）"""
    try:
        limit = int(request.args.get('limit', 12))
        
        conn = get_mysql_conn()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # 获取目标电影的 TF-IDF 特征
        cursor.execute("""
            SELECT m.movie_id, f.tfidf_features
            FROM movie_basic m
            JOIN movie_features f ON m.movie_id = f.movie_id
            WHERE m.movie_id = %s
        """, (movie_id,))
        
        target = cursor.fetchone()
        if not target:
            cursor.close()
            conn.close()
            return jsonify({'error': f'Movie ID {movie_id} not found'}), 404
        
        target_vec = decode_tfidf(target.get('tfidf_features'))
        if target_vec is None or np.linalg.norm(target_vec) == 0:
            cursor.close()
            conn.close()
            return jsonify({'error': 'Target movie has no valid TF-IDF features'}), 400
        
        # 获取其他电影
        cursor.execute("""
            SELECT 
                m.movie_id,
                m.title,
                m.genres,
                m.vote_average,
                m.vote_count,
                f.tfidf_features
            FROM movie_basic m
            JOIN movie_features f ON m.movie_id = f.movie_id
            WHERE m.movie_id != %s AND f.tfidf_features IS NOT NULL
            LIMIT 500
        """, (movie_id,))
        
        candidates = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 计算相似度
        results = []
        for row in candidates:
            try:
                vec = decode_tfidf(row.get('tfidf_features'))
                if vec is None:
                    continue
                
                denom = np.linalg.norm(target_vec) * np.linalg.norm(vec)
                if denom == 0:
                    sim = 0.0
                else:
                    sim = float(np.dot(target_vec, vec) / denom)
                
                results.append({
                    'id': row['movie_id'],
                    'title': row['title'],
                    'genres': row['genres'].split(',') if row['genres'] else [],
                    'rating': float(row['vote_average']) if row['vote_average'] else 0.0,
                    'vote_count': row['vote_count'],
                    'similarity': round(sim, 4),
                    'poster': f"img/{row['movie_id']}.webp"
                })
            except Exception as e:
                continue
        
        # 按相似度排序并返回前 N 个
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return jsonify(results[:limit])
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch similar movies', 'detail': str(e)}), 500


@app.route('/api/movie/<int:movie_id>/rate', methods=['POST'])
def rate_movie(movie_id):
    """用户评分电影"""
    if 'user_id' not in session:
        return jsonify({'error': 'Please login first'}), 401
    
    try:
        data = request.get_json()
        rating = data.get('rating')
        comment = data.get('comment', '')
        
        # 支持 1 到 10 分的评分（允许整数或小数），前端以 1-10 的整数传入
        try:
            rating_val = float(rating)
        except Exception:
            return jsonify({'error': 'Invalid rating value'}), 400

        if not (1.0 <= rating_val <= 10.0):
            return jsonify({'error': 'Rating must be between 1 and 10'}), 400
        
        user_id = session['user_id']
        
        conn = get_mysql_conn()
        cursor = conn.cursor(buffered=True)
        ensure_user_ratings_table(cursor)
        ensure_rating_time_column(cursor)

        # 检查是否已评分（表里没有 rating_id，使用 EXISTS 检测）
        cursor.execute(
            """
            SELECT 1 FROM user_ratings 
            WHERE user_id = %s AND movie_id = %s
            """,
            (user_id, movie_id),
        )

        existing = cursor.fetchone()

        if existing:
            # 更新评分
            cursor.execute(
                """
                UPDATE user_ratings 
                SET rating = %s, rating_time = NOW()
                WHERE user_id = %s AND movie_id = %s
                """,
                (rating_val, user_id, movie_id),
            )
        else:
            # 插入新评分
            cursor.execute(
                """
                INSERT INTO user_ratings (user_id, movie_id, rating, rating_time)
                VALUES (%s, %s, %s, NOW())
                """,
                (user_id, movie_id, rating_val),
            )
        
        conn.commit()
        cursor.close()
        conn.close()

        # 评分成功后，异步重算该用户的个性化推荐
        try:
            enqueue_user_for_recompute(user_id)
        except Exception as _:
            pass
        
        return jsonify({'success': True, 'message': 'Rating submitted successfully'})
        
    except mysql.connector.Error as e:
        # Return DB error details to help diagnose (frontend will show detail)
        return jsonify({'error': 'Failed to submit rating', 'detail': str(e)}), 500
    except Exception as e:
        return jsonify({'error': 'Failed to submit rating', 'detail': str(e)}), 500


@app.route('/api/rankings')
def get_rankings():
    """获取电影排行榜
    参数：
    - type: rating(评分榜), popularity(热度榜), new(新片榜), boxoffice(票房榜)
    - genre: 类型筛选，默认为 all
    - year_from: 起始年份（可选）
    - year_to: 结束年份（可选）
    - limit: 返回数量，默认为 50
    """
    try:
        rank_type = request.args.get('type', 'rating')
        genre_filter = request.args.get('genre', 'all')
        year_from = request.args.get('year_from', '')
        year_to = request.args.get('year_to', '')
        limit = int(request.args.get('limit', 50))
        
        conn = get_mysql_conn()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # 构建基础 SQL
        base_sql = """
            SELECT 
                movie_id,
                title,
                genres,
                release_date,
                runtime,
                vote_average,
                vote_count,
                popularity_score,
                revenue
            FROM movie_basic
            WHERE 1=1
        """
        
        params = []
        
        # 添加类型筛选
        if genre_filter != 'all':
            # 将前端的类型映射转换为数据库中的类型
            genre_map = {
                'action': 'Action',
                'comedy': 'Comedy',
                'drama': 'Drama',
                'sci-fi': 'Science Fiction',
                'romance': 'Romance',
                'thriller': 'Thriller'
            }
            db_genre = genre_map.get(genre_filter.lower(), genre_filter.title())
            base_sql += " AND genres LIKE %s"
            params.append(f"%{db_genre}%")
        
        # 添加年份范围筛选
        if year_from:
            base_sql += " AND YEAR(release_date) >= %s"
            params.append(int(year_from))
        
        if year_to:
            base_sql += " AND YEAR(release_date) <= %s"
            params.append(int(year_to))
        
        # 根据排行榜类型选择排序字段和条件
        if rank_type == 'rating':
            # 评分榜：按评分排序，至少要有一定数量的评分
            base_sql += " AND vote_count >= 100 AND vote_average > 0"
            order_by = " ORDER BY vote_average DESC, vote_count DESC"
        elif rank_type == 'popularity':
            # 热度榜：按热度分数排序
            base_sql += " AND popularity_score IS NOT NULL"
            order_by = " ORDER BY popularity_score DESC"
        elif rank_type == 'new':
            # 新片榜：按上映日期排序（最新的）
            base_sql += " AND release_date IS NOT NULL"
            order_by = " ORDER BY release_date DESC"
        elif rank_type == 'boxoffice':
            # 票房榜：按票房排序
            base_sql += " AND revenue IS NOT NULL AND revenue != '' AND CAST(revenue AS UNSIGNED) > 0"
            order_by = " ORDER BY CAST(revenue AS UNSIGNED) DESC"
        else:
            return jsonify({'error': 'Invalid rank type'}), 400
        
        # 组合完整 SQL
        full_sql = base_sql + order_by + f" LIMIT {limit}"
        
        cursor.execute(full_sql, params)
        movies = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 格式化结果
        result = []
        for idx, movie in enumerate(movies, 1):
            result.append({
                'rank': idx,
                'id': movie['movie_id'],
                'title': movie['title'],
                'genres': movie['genres'].split(',') if movie['genres'] else [],
                'release_date': str(movie['release_date']) if movie['release_date'] else None,
                'runtime': movie['runtime'],
                'rating': float(movie['vote_average']) if movie['vote_average'] else 0.0,
                'vote_count': movie['vote_count'],
                'popularity': float(movie['popularity_score']) if movie['popularity_score'] else 0.0,
                'revenue': movie['revenue'] or '0',
                'poster': f"img/{movie['movie_id']}.webp"
            })
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch rankings', 'detail': str(e)}), 500


@app.route('/api/search')
def search_movies():
    """搜索电影
    参数：
    - q: 搜索关键词（标题、类型、关键词）
    - limit: 返回数量，默认为 20
    """
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 20))
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        conn = get_mysql_conn()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # 搜索电影（标题、类型、关键词）
        search_pattern = f"%{query}%"
        cursor.execute("""
            SELECT 
                movie_id,
                title,
                genres,
                release_date,
                runtime,
                vote_average,
                vote_count,
                popularity_score
            FROM movie_basic
            WHERE title LIKE %s 
               OR genres LIKE %s 
               OR keywords LIKE %s
            ORDER BY popularity_score DESC, vote_average DESC
            LIMIT %s
        """, (search_pattern, search_pattern, search_pattern, limit))
        
        movies = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 格式化结果
        result = []
        for movie in movies:
            result.append({
                'id': movie['movie_id'],
                'title': movie['title'],
                'genres': movie['genres'].split(',') if movie['genres'] else [],
                'release_date': str(movie['release_date']) if movie['release_date'] else None,
                'runtime': movie['runtime'],
                'rating': float(movie['vote_average']) if movie['vote_average'] else 0.0,
                'vote_count': movie['vote_count'],
                'popularity': float(movie['popularity_score']) if movie['popularity_score'] else 0.0,
                'poster': f"img/{movie['movie_id']}.webp"
            })
        
        return jsonify({
            'query': query,
            'total': len(result),
            'results': result
        })
        
    except Exception as e:
        return jsonify({'error': 'Search failed', 'detail': str(e)}), 500


@app.route('/api/genres')
def get_genres():
    """获取所有电影类型"""
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        # 获取所有不同的类型
        cursor.execute("""
            SELECT DISTINCT genres FROM movie_basic 
            WHERE genres IS NOT NULL AND genres != ''
        """)
        
        genres_set = set()
        for row in cursor.fetchall():
            if row['genres']:
                # 分割多个类型（如 "Action, Adventure, Sci-Fi"）
                for genre in row['genres'].split(','):
                    genre = genre.strip()
                    if genre:
                        genres_set.add(genre)
        
        cursor.close()
        conn.close()
        
        genres_list = sorted(list(genres_set))
        return jsonify({'genres': genres_list})
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch genres', 'detail': str(e)}), 500


@app.route('/api/movies/by-genre')
def get_movies_by_genre():
    """按类型获取电影列表（随机排序）"""
    genre = request.args.get('genre', 'all')
    limit = int(request.args.get('limit', 12))
    
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(buffered=True, dictionary=True)
        
        if genre == 'all' or genre == '':
            # 获取所有电影，按评分和流行度排序
            cursor.execute("""
                SELECT movie_id, title, genres, release_date, vote_average, popularity_score
                FROM movie_basic
                WHERE vote_average IS NOT NULL
                ORDER BY popularity_score DESC, vote_average DESC
                LIMIT %s
            """, (limit * 3,))  # 获取更多以便随机
        else:
            # 按类型筛选
            cursor.execute("""
                SELECT movie_id, title, genres, release_date, vote_average, popularity_score
                FROM movie_basic
                WHERE genres LIKE %s AND vote_average IS NOT NULL
                ORDER BY popularity_score DESC, vote_average DESC
                LIMIT %s
            """, (f'%{genre}%', limit * 3))
        
        movies = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not movies:
            return jsonify({'movies': [], 'genre': genre})
        
        # 随机打乱并取指定数量
        random.shuffle(movies)
        selected_movies = movies[:limit]
        
        # 格式化数据
        result = []
        for movie in selected_movies:
            result.append({
                'id': movie['movie_id'],
                'title': movie['title'],
                'genre': movie['genres'].split(',') if movie['genres'] else [],
                'rating': float(movie['vote_average']) if movie['vote_average'] else 0.0,
                'poster': f"img/{movie['movie_id']}.webp"
            })
        
        return jsonify({'movies': result, 'genre': genre})
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch movies', 'detail': str(e)}), 500


# （移除手动训练 API；统一使用评分后的异步重算流程）



@app.route('/api/movies/recommendations')
def get_recommendations():
    """获取个性化推荐（登录用户使用 ALS 模型，未登录用户随机推荐）"""
    topN = int(request.args.get('topN', 10))
    user_id = session.get('user_id')  # 从会话中获取用户ID
    force_refresh = str(request.args.get('force', '0')) == '1'
    
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(buffered=True, dictionary=True)

        # 强制刷新：直接调用 ALS 模型脚本实时计算
        if user_id and force_refresh:
            try:
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'code', 'python', 'movie_recommender.py'))
                cmd = ['python3.8', script_path, '--user_id', str(user_id), '--topN', str(topN)]
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode == 0 and proc.stdout:
                    data = json.loads(proc.stdout.strip())
                    recs = data.get('recommendations') or []
                    result = []
                    for rec in recs:
                        genres_str = rec.get('genre') or ''
                        if '|' in genres_str:
                            genres_list = genres_str.split('|')
                        else:
                            genres_list = genres_str.split(',') if genres_str else []
                        release = rec.get('release_date')
                        release_year = None
                        try:
                            if release and str(release)[:4].isdigit():
                                release_year = int(str(release)[:4])
                        except Exception:
                            release_year = None
                        result.append({
                            'id': rec.get('movie_id'),
                            'title': rec.get('title'),
                            'genre': genres_list,
                            'rating': float(rec.get('vote_average')) if rec.get('vote_average') is not None else 0.0,
                            'poster': f"/img/{rec.get('movie_id')}.webp",
                            'prediction': float(rec.get('predict_rating')) if rec.get('predict_rating') is not None else 0.0,
                            'release_date': release_year
                        })
                    if result:
                        try:
                            cursor.close()
                        except Exception:
                            pass
                        try:
                            conn.close()
                        except Exception:
                            pass
                        print(f"为用户 {user_id} 强制刷新返回 ALS 个性化推荐: {len(result)} 部电影")
                        return jsonify({'movies': result, 'user_id': user_id, 'method': 'als_model'})
                else:
                    print(f"ALS 脚本执行失败，returncode={proc.returncode}, stderr={proc.stderr}")
            except Exception as e:
                print(f"强制刷新调用 ALS 失败: {e}")

        if user_id and not force_refresh:
            # 已登录用户 - 尝试使用 ALS 模型推荐
            try:
                # 首先检查是否有预计算的推荐
                cursor.execute("""
                    SELECT r.movie_id, m.title, m.genres, m.vote_average, 
                           m.release_date, m.popularity_score,
                           r.predicted_rating as prediction
                    FROM user_recommendations r
                    JOIN movie_basic m ON r.movie_id = m.movie_id
                    WHERE r.user_id = %s
                    ORDER BY r.predicted_rating DESC
                    LIMIT %s
                """, (user_id, topN))
                
                recommendations = cursor.fetchall()
                
                if recommendations and len(recommendations) > 0:
                    # 有预计算的推荐
                    result = []
                    for rec in recommendations:
                        genres_list = rec['genres'].split('|') if rec['genres'] else []
                        result.append({
                            'id': rec['movie_id'],
                            'title': rec['title'],
                            'genre': genres_list,
                            'rating': float(rec['vote_average']) if rec['vote_average'] else 0.0,
                            'poster': f"/img/{rec['movie_id']}.webp",
                            'prediction': float(rec['prediction']) if rec['prediction'] else 0.0,
                            'release_date': rec['release_date'].year if rec['release_date'] else None
                        })
                    
                    cursor.close()
                    conn.close()
                    print(f"为用户 {user_id} 返回 ALS 个性化推荐: {len(result)} 部电影")
                    return jsonify({
                        'movies': result,
                        'user_id': user_id,
                        'method': 'als_model'
                    })
                else:
                    print(f"用户 {user_id} 没有 ALS 推荐数据，使用回退策略")
            except Exception as e:
                print(f"ALS 推荐失败: {e}")
                import traceback
                traceback.print_exc()
                # 继续使用回退策略
        
        # 未登录、强制刷新或 ALS 推荐失败 - 使用回退策略（热门电影）
        if user_id:
            # 已登录用户 - 排除已评分的电影
            cursor.execute("""
                SELECT m.movie_id, m.title, m.genres, m.vote_average, m.popularity_score
                FROM movie_basic m
                WHERE m.movie_id NOT IN (
                    SELECT movie_id FROM user_ratings WHERE user_id = %s
                ) AND m.vote_average IS NOT NULL
                ORDER BY m.popularity_score DESC, m.vote_average DESC
                LIMIT %s
            """, (user_id, topN * 2))
        else:
            # 未登录用户 - 随机热门电影
            cursor.execute("""
                SELECT movie_id, title, genres, vote_average, popularity_score
                FROM movie_basic
                WHERE vote_average IS NOT NULL
                ORDER BY popularity_score DESC, vote_average DESC
                LIMIT %s
            """, (topN * 2,))
        
        movies = cursor.fetchall()
        cursor.close()
        conn.close()
        
        if not movies:
            return jsonify({'movies': [], 'method': 'fallback'})
        
        # 随机打乱
        random.shuffle(movies)
        selected_movies = movies[:topN]
        
        result = []
        for movie in selected_movies:
            result.append({
                'id': movie['movie_id'],
                'title': movie['title'],
                'genre': movie['genres'].split(',') if movie['genres'] else [],
                'rating': float(movie['vote_average']) if movie['vote_average'] else 0.0,
                'poster': f"img/{movie['movie_id']}.webp"
            })
        
        return jsonify({
            'movies': result,
            'user_id': user_id,
            'method': 'fallback'
        })
        
    except Exception as e:
        return jsonify({'error': 'Failed to fetch recommendations', 'detail': str(e)}), 500


@app.route('/api/register', methods=['POST'])
def register():
    """用户注册，使用用户名+密码并将用户信息保存到 users 表"""
    data = request.get_json() or {}
    username = str(data.get('username', '')).strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': '用户名和密码均为必填项'}), 400
    if len(username) < 3 or len(username) > 20:
        return jsonify({'error': '用户名长度需在 3-20 个字符之间'}), 400
    if len(password) < 6:
        return jsonify({'error': '密码长度至少 6 位'}), 400

    conn = None
    cursor = None
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(buffered=True, dictionary=True)
        ensure_users_table(cursor)

        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return jsonify({'error': '用户名已被注册'}), 409

        password_hash = generate_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (%s, %s)",
            (username, password_hash),
        )
        conn.commit()
        user_id = cursor.lastrowid

        session['user_id'] = user_id
        session['username'] = username
        session.permanent = True

        return jsonify({'success': True, 'user_id': user_id, 'username': username})
    except Exception as e:
        return jsonify({'error': '注册失败', 'detail': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@app.route('/api/login', methods=['POST'])
def login():
    """用户登录，支持用户名+密码，兼容旧的 user_id 方式"""
    data = request.get_json() or {}
    username = str(data.get('username', '')).strip()
    password = data.get('password')
    legacy_user_id = data.get('user_id')

    # 优先使用用户名/密码登录
    if username:
        conn = None
        cursor = None
        try:
            conn = get_mysql_conn()
            cursor = conn.cursor(buffered=True, dictionary=True)
            ensure_users_table(cursor)

            cursor.execute(
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username,),
            )
            user = cursor.fetchone()
            if not user:
                return jsonify({'error': '用户不存在'}), 404
            if not password or not check_password_hash(user['password_hash'], password):
                return jsonify({'error': '用户名或密码错误'}), 401

            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True
            return jsonify({'success': True, 'user_id': user['id'], 'username': user['username']})
        except Exception as e:
            return jsonify({'error': '登录失败', 'detail': str(e)}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # 兼容：仅传 user_id 的旧逻辑（无密码，基于已有评分数据）
    if legacy_user_id:
        conn = None
        cursor = None
        try:
            conn = get_mysql_conn()
            cursor = conn.cursor(buffered=True, dictionary=True)
            cursor.execute(
                "SELECT DISTINCT user_id FROM user_ratings WHERE user_id = %s LIMIT 1",
                (legacy_user_id,),
            )
            user = cursor.fetchone()
            if user:
                session['user_id'] = legacy_user_id
                session.pop('username', None)
                session.permanent = True
                return jsonify({'success': True, 'user_id': legacy_user_id})
            return jsonify({'error': 'User not found'}), 404
        except Exception as e:
            return jsonify({'error': 'Login failed', 'detail': str(e)}), 500
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return jsonify({'error': '请提供用户名/密码或 user_id'}), 400


@app.route('/api/logout', methods=['POST'])
def logout():
    """用户登出"""
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({'success': True})


@app.route('/api/session')
def get_session():
    """获取当前会话信息"""
    user_id = session.get('user_id')
    return jsonify({
        'logged_in': user_id is not None,
        'user_id': user_id,
        'username': session.get('username')
    })


@app.route('/api/als/status')
def als_status():
    """返回后台 ALS 重算线程与队列状态"""
    try:
        with _PENDING_LOCK:
            pending = len(_PENDING_USERS)
        return jsonify({
            'worker_started': bool(_WORKER_STARTED),
            'queue_size': int(RECOMPUTE_QUEUE.qsize()),
            'pending_users': int(pending)
        })
    except Exception as e:
        return jsonify({'error': 'Failed to fetch ALS status', 'detail': str(e)}), 500


@app.route('/api/als/task/<int:user_id>')
def als_task_status(user_id: int):
    """查询指定用户的异步重算任务状态"""
    try:
        _user_task_init(user_id)
        with USER_LOCK, _PENDING_LOCK:
            task = dict(USER_TASKS.get(user_id) or {})
            task['queued'] = user_id in _PENDING_USERS
            task['worker_started'] = bool(_WORKER_STARTED)
        return jsonify(task)
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user task', 'detail': str(e)}), 500


@app.route('/api/als/logs/<int:user_id>')
def als_task_logs(user_id: int):
    """获取指定用户的推理日志（最近 300 行）"""
    try:
        _user_task_init(user_id)
        with USER_LOCK:
            logs = list(USER_LOGS.get(user_id) or [])
        return jsonify({'user_id': user_id, 'logs': logs, 'count': len(logs)})
    except Exception as e:
        return jsonify({'error': 'Failed to fetch user logs', 'detail': str(e)}), 500


@app.route('/api/user/<int:user_id>/ratings')
def get_user_ratings(user_id):
    """
    获取指定用户的所有评分记录
    返回用户评分历史，包括电影信息和评分详情
    """
    conn = None
    try:
        conn = get_mysql_conn()
        cursor = conn.cursor(dictionary=True)
        
        # 确保 user_ratings 表存在
        ensure_user_ratings_table(cursor)
        
        # 查询用户的所有评分记录，关联电影基本信息
        query = """
            SELECT 
                ur.movie_id,
                ur.rating,
                ur.rating_time,
                mb.title,
                mb.release_date,
                mb.genres,
                mb.vote_average,
                mb.popularity_score
            FROM user_ratings ur
            LEFT JOIN movie_basic mb ON ur.movie_id = mb.movie_id
            WHERE ur.user_id = %s
            ORDER BY ur.rating_time DESC
        """
        
        cursor.execute(query, (user_id,))
        ratings = cursor.fetchall()
        
        # 计算统计信息
        total_ratings = len(ratings)
        avg_rating = 0
        if total_ratings > 0:
            avg_rating = sum(r['rating'] for r in ratings) / total_ratings
        
        # 获取用户名（如果是当前登录用户）
        username = None
        if session.get('user_id') == user_id:
            username = session.get('username')
        
        # 格式化评分数据
        formatted_ratings = []
        for r in ratings:
            formatted_ratings.append({
                'movie_id': r['movie_id'],
                'title': r['title'] or f'电影 {r["movie_id"]}',
                'rating': float(r['rating']),
                'rating_time': r['rating_time'].isoformat() if r['rating_time'] else None,
                'release_date': r['release_date'].isoformat() if r['release_date'] else None,
                'genres': r['genres'].split('|') if r['genres'] else [],
                'vote_average': float(r['vote_average']) if r['vote_average'] else 0,
                'popularity': float(r['popularity_score']) if r['popularity_score'] else 0,
                'poster': f'/img/{r["movie_id"]}.webp'
            })
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'username': username,
            'total_ratings': total_ratings,
            'avg_rating': round(avg_rating, 2),
            'ratings': formatted_ratings
        })
        
    except Exception as e:
        print(f"获取用户评分失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'获取评分记录失败: {str(e)}'
        }), 500
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    # 在实际运行进程中启动后台重算线程：
    # - Flask 自带 reloader 会设置 WERKZEUG_RUN_MAIN='true' 在子进程
    # - 无 reloader（None），或生产模式也应启动
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or os.environ.get('WERKZEUG_RUN_MAIN') is None:
        start_recompute_worker()
    app.run(host='0.0.0.0', port=port, debug=True)
