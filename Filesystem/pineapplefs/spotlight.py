"""Fast local metadata/content index for Pineapple volumes."""
import os
import sqlite3
from pathlib import Path

from .constants import SYSTEM_NAMES, is_hidden_name, is_sidecar


class SpotlightIndex:
    """SQLite FTS5 index with incremental filesystem scanning."""

    def __init__(self, root):
        self.root = Path(root)
        self.db_path = self.root / ".Spotlight-V100" / "index.sqlite3"

    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.db_path)
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=NORMAL")
        db.execute(
            "CREATE TABLE IF NOT EXISTS files "
            "(path TEXT PRIMARY KEY, mtime_ns INTEGER, size INTEGER)"
        )
        db.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS content USING fts5 "
            "(path UNINDEXED, name, text)"
        )
        return db

    def _visible(self, name):
        return (
            name not in SYSTEM_NAMES
            and not is_hidden_name(name)
            and not is_sidecar(name)
        )

    def _read_text(self, path, size):
        if size > 2 * 1024 * 1024:
            return ""
        try:
            with path.open("rb") as stream:
                data = stream.read(2 * 1024 * 1024 + 1)
            if b"\0" in data:
                return ""
            return data.decode("utf-8", errors="ignore")
        except (OSError, UnicodeError):
            return ""

    def rebuild(self):
        """Incrementally index visible files and remove deleted entries."""
        db = self._connect()
        seen = set()
        pending = []
        stack = [self.root]
        while stack:
            directory = stack.pop()
            try:
                entries = os.scandir(directory)
            except OSError:
                continue
            with entries:
                for entry in entries:
                    if not self._visible(entry.name):
                        continue
                    try:
                        stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        continue
                    relative = os.path.relpath(entry.path, self.root).replace(os.sep, "/")
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(Path(entry.path))
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        continue
                    seen.add(relative)
                    old = db.execute(
                        "SELECT mtime_ns, size FROM files WHERE path = ?", (relative,)
                    ).fetchone()
                    if old == (stat.st_mtime_ns, stat.st_size):
                        continue
                    pending.append((relative, stat.st_mtime_ns, stat.st_size))
                    db.execute("DELETE FROM content WHERE path = ?", (relative,))
                    db.execute(
                        "INSERT INTO content(path, name, text) VALUES (?, ?, ?)",
                        (relative, entry.name, self._read_text(Path(entry.path), stat.st_size)),
                    )
                    db.execute(
                        "INSERT OR REPLACE INTO files(path, mtime_ns, size) VALUES (?, ?, ?)",
                        (relative, stat.st_mtime_ns, stat.st_size),
                    )
        if seen:
            placeholders = ",".join("?" for _ in seen)
            db.execute(f"DELETE FROM files WHERE path NOT IN ({placeholders})", tuple(seen))
            db.execute(f"DELETE FROM content WHERE path NOT IN ({placeholders})", tuple(seen))
        else:
            db.execute("DELETE FROM files")
            db.execute("DELETE FROM content")
        db.commit()
        count = db.execute("SELECT count(*) FROM files").fetchone()[0]
        db.close()
        return count, len(pending)

    def search(self, query, limit=100):
        db = self._connect()
        rows = db.execute(
            "SELECT path FROM content WHERE content MATCH ? LIMIT ?", (query, limit)
        ).fetchall()
        db.close()
        return [row[0] for row in rows]
