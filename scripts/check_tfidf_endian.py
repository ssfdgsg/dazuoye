import mysql.connector
import base64
import numpy as np

conn = mysql.connector.connect(host='localhost', user='root', password='root123', database='movie_db')
cur = conn.cursor(dictionary=True)
cur.execute("SELECT m.movie_id, m.title, f.tfidf_features FROM movie_basic m JOIN movie_features f ON m.movie_id=f.movie_id LIMIT 10")
rows = cur.fetchall()

for r in rows:
    mid = r['movie_id']
    title = r['title']
    enc = r['tfidf_features']
    if not enc:
        print(mid, title, 'NULL')
        continue
    b = base64.b64decode(enc)
    try:
        arr_le = np.frombuffer(b, dtype=np.float64).astype(np.float64)
        arr_be = np.frombuffer(b, dtype='>f8').astype(np.float64)
    except Exception as e:
        print(mid, title, 'decode error', e)
        continue
    def stats(a):
        return {'len': a.size, 'nnz': int(np.count_nonzero(a)), 'norm': float(np.linalg.norm(a)), 'min': float(np.nanmin(a)), 'max': float(np.nanmax(a))}
    print('---', mid, title)
    print('LE:', stats(arr_le))
    print('BE:', stats(arr_be))

cur.close()
conn.close()
