import json
import math
import sqlite3
import threading
from pathlib import Path


class SQLiteResearchStore:
    def __init__(self, path='data/finsight.sqlite3'):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.connection = sqlite3.connect(str(self.path), check_same_thread=False, timeout=30.0)
        self.connection.row_factory = sqlite3.Row
        with self._lock, self.connection:
            self.connection.executescript('CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY,source_path TEXT,manifest TEXT);CREATE TABLE IF NOT EXISTS pages (document_id TEXT,page INTEGER,payload TEXT,PRIMARY KEY(document_id,page));CREATE TABLE IF NOT EXISTS sections (document_id TEXT,title TEXT,start_page INTEGER,end_page INTEGER,kind TEXT);CREATE TABLE IF NOT EXISTS tables_data (document_id TEXT,page INTEGER,table_index INTEGER,payload TEXT,PRIMARY KEY(document_id,page,table_index));CREATE TABLE IF NOT EXISTS visuals (document_id TEXT,page INTEGER,visual_index INTEGER,payload TEXT,PRIMARY KEY(document_id,page,visual_index));CREATE TABLE IF NOT EXISTS narratives (document_id TEXT,page INTEGER,block_index INTEGER,payload TEXT,PRIMARY KEY(document_id,page,block_index));CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY,document_id TEXT,page INTEGER,text TEXT,embedding TEXT);CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY,document_id TEXT,status TEXT,result TEXT);')
            if 'manifest' not in [row[1] for row in self.connection.execute('PRAGMA table_info(documents)')]:
                self.connection.execute(
                    'ALTER TABLE documents ADD COLUMN manifest TEXT')

    def save_analysis(self, manifest):
        doc = manifest['document_id']
        with self._lock, self.connection:
            self.connection.execute('INSERT OR REPLACE INTO documents(id,source_path,manifest) VALUES (?,?,?)', (
                doc, manifest['original_pdf_path'], json.dumps(manifest)))
            for table in ('pages', 'sections', 'tables_data', 'visuals', 'narratives'):
                self.connection.execute(
                    f'DELETE FROM {table} WHERE document_id=?', (doc,))
            for page in manifest['pages']:
                self.connection.execute(
                    'INSERT INTO pages VALUES (?,?,?)', (doc, page['page'], json.dumps(page)))
                for i, item in enumerate(page['tables']):
                    self.connection.execute(
                        'INSERT INTO tables_data VALUES (?,?,?,?)', (doc, page['page'], i, json.dumps(item)))
                for i, item in enumerate(page['visuals']):
                    self.connection.execute(
                        'INSERT INTO visuals VALUES (?,?,?,?)', (doc, page['page'], i, json.dumps(item)))
                for i, item in enumerate(page['narrative_blocks']):
                    self.connection.execute(
                        'INSERT INTO narratives VALUES (?,?,?,?)', (doc, page['page'], i, json.dumps(item)))
            self.connection.executemany('INSERT INTO sections VALUES (?,?,?,?,?)', [(
                doc, s['title'], s['start_page'], s['end_page'], s['kind']) for s in manifest['sections']])

    def index(self, doc, path, chunks, vectors):
        with self._lock, self.connection:
            self.connection.execute(
                'INSERT INTO documents(id,source_path) VALUES (?,?) ON CONFLICT(id) DO UPDATE SET source_path=excluded.source_path', (doc, path))
            self.connection.execute(
                'DELETE FROM chunks WHERE document_id=?', (doc,))
            self.connection.executemany('INSERT INTO chunks VALUES (?,?,?,?,?)', [(
                c['id'], doc, c['page'], c['text'], json.dumps(v)) for c, v in zip(chunks, vectors, strict=True)])

    def search(self, doc, vector, limit=4):
        with self._lock:
            rows = self.connection.execute(
                'SELECT id,page,text,embedding FROM chunks WHERE document_id=?', (doc,)).fetchall()

        def score(r):
            v = json.loads(r['embedding'])
            denom = math.sqrt(sum(x*x for x in vector)) * \
                math.sqrt(sum(x*x for x in v))
            return sum(x*y for x, y in zip(vector, v, strict=True))/denom if denom else 0
        return [{'chunk_id': r['id'], 'page': r['page'], 'text': r['text'], 'score': round(score(r), 5)} for r in sorted(rows, key=score, reverse=True)[:limit]]

    def save_run(self, run, doc, status, result):
        """Save run for document. Overwrites previous runs so only the single latest report is retained."""
        with self._lock, self.connection:
            self.connection.execute('DELETE FROM runs WHERE document_id=?', (doc,))
            self.connection.execute(
                'INSERT INTO runs VALUES (?,?,?,?)', (run, doc, status, json.dumps(result)))

    def update_run_status(self, run, status):
        """Manually update the verification status of a run (e.g. human-in-the-loop review)."""
        with self._lock, self.connection:
            row = self.connection.execute('SELECT result FROM runs WHERE id=?', (run,)).fetchone()
            if row and row['result']:
                try:
                    res = json.loads(row['result'])
                    res['status'] = status
                    self.connection.execute(
                        'UPDATE runs SET status=?, result=? WHERE id=?', (status, json.dumps(res), run))
                except Exception:
                    self.connection.execute('UPDATE runs SET status=? WHERE id=?', (status, run))
            else:
                self.connection.execute('UPDATE runs SET status=? WHERE id=?', (status, run))

    def delete_document(self, doc):
        """Completely remove all database entries associated with a document."""
        with self._lock, self.connection:
            for table in ('pages', 'sections', 'tables_data', 'visuals', 'narratives', 'chunks', 'runs'):
                self.connection.execute(f'DELETE FROM {table} WHERE document_id=?', (doc,))
            self.connection.execute('DELETE FROM documents WHERE id=?', (doc,))

    def clear_all(self):
        """Clear all records from all tables."""
        with self._lock, self.connection:
            for table in ('documents', 'pages', 'sections', 'tables_data', 'visuals', 'narratives', 'chunks', 'runs'):
                self.connection.execute(f'DELETE FROM {table}')
            self.connection.execute('VACUUM')
