import mysql.connector
import base64
import numpy as np
import sys

conn = mysql.connector.connect(host='localhost', user='root', password='root123', database='movie_db')
cur = conn.cursor(dictionary=True)

# Try fetch sample from movie_features join
cur.execute("SELECT m.movie_id, m.title, f.tfidf_features FROM movie_basic m JOIN movie_features f ON m.movie_id=f.movie_id LIMIT 30")
rows = cur.fetchall()

if not rows:
    print('No rows found in movie_features join')
    sys.exit(0)

print('{:<8} {:<40} {:>8} {:>8} {:>8}'.format('movie_id','title','len','nnz','norm'))
for r in rows:
    mid = r['movie_id']
    title = (r['title'] or '')[:38]
    enc = r['tfidf_features']
    if not enc:
        print('{:<8} {:<40} {:>8} {:>8} {:>8}'.format(mid, title, 'NULL', '-', '-'))
        continue
    try:
        b = base64.b64decode(enc)
        arr = np.frombuffer(b, dtype=np.float64)
        length = arr.size
        nnz = int(np.count_nonzero(arr))
        norm = float(np.linalg.norm(arr))
        print('{:<8} {:<40} {:>8} {:>8} {:>8.4f}'.format(mid, title, length, nnz, norm))
    except Exception as e:
        print('{:<8} {:<40} ERROR decoding: {}'.format(mid, title, e))

# Also check if movie_basic has tfidf_features column
cur.execute("SHOW COLUMNS FROM movie_basic LIKE 'tfidf_features'")
if cur.fetchone():
    cur.execute("SELECT movie_id, title, tfidf_features FROM movie_basic LIMIT 20")
    rows2 = cur.fetchall()
    print('\nmovie_basic tfidf_features samples:')
    print('{:<8} {:<40} {:>8} {:>8} {:>8}'.format('movie_id','title','len','nnz','norm'))
    for r in rows2:
        mid = r['movie_id']
        title = (r['title'] or '')[:38]
        enc = r['tfidf_features']
        if not enc:
            print('{:<8} {:<40} {:>8} {:>8} {:>8}'.format(mid, title, 'NULL', '-', '-'))
            continue
        try:
            b = base64.b64decode(enc)
            arr = np.frombuffer(b, dtype=np.float64)
            length = arr.size
            nnz = int(np.count_nonzero(arr))
            norm = float(np.linalg.norm(arr))
            print('{:<8} {:<40} {:>8} {:>8} {:>8.4f}'.format(mid, title, length, nnz, norm))
        except Exception as e:
            print('{:<8} {:<40} ERROR decoding: {}'.format(mid, title, e))

cur.close()
conn.close()
