# -*- coding: utf-8 -*-
"""
SQLite 数据库管理器 — 建表、连接管理。
"""

import sqlite3
import os


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL UNIQUE,
    description     TEXT    DEFAULT '',
    chroma_collection_name TEXT NOT NULL UNIQUE,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kb_id         INTEGER NOT NULL,
    filename      TEXT    NOT NULL,
    file_path     TEXT    NOT NULL,
    file_type     TEXT    NOT NULL CHECK(file_type IN ('pdf', 'docx', 'md')),
    file_size     INTEGER DEFAULT 0,
    chunk_count   INTEGER DEFAULT 0,
    chunk_size    INTEGER DEFAULT 0,
    chunk_overlap INTEGER DEFAULT 0,
    status        TEXT    NOT NULL DEFAULT 'pending'
                          CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    error_message TEXT    DEFAULT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    updated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chunks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id   INTEGER NOT NULL,
    chunk_index   INTEGER NOT NULL,
    chroma_id     TEXT    NOT NULL UNIQUE,
    char_count    INTEGER DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_documents_kb_id    ON documents(kb_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_chroma_id   ON chunks(chroma_id);
"""


class DatabaseManager:
    """SQLite 连接管理 + schema 初始化。"""

    def __init__(self, db_path: str = "data/database.db"):
        self._db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self.initialize()

    # ------------------------------------------------------------------ #
    #  Connection management
    # ------------------------------------------------------------------ #

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(
                self._db_path,
                check_same_thread=False,  # 允许跨线程使用（QThread worker 需要）
            )
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA foreign_keys = ON")
            self._conn.execute("PRAGMA journal_mode = WAL")   # WAL 模式支持并发读写
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def initialize(self) -> None:
        """执行建表 DDL（幂等）。"""
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()
