"""Veritabanı katmanı. Danışanlar, seanslar ve ajan hafızası burada tutulur.

İki motor desteklenir; uygulamanın geri kalanı farkı bilmez:
  - SQLite (varsayılan): kurulum gerektirmez, tek kullanıcılı deneme ve sunum için.
  - PostgreSQL: DATABASE_URL=postgresql://... verilirse. Çok kullanıcılı, ölçeklenebilir kurulum
    (kurum geneli kullanım, yedekleme, eşzamanlı yazma). Sorgular SQLite sözdiziminde yazılır;
    _PgConnection bunları PostgreSQL'e çevirir (? -> %s, AUTOINCREMENT -> SERIAL, json_extract -> ->>).
"""
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .config import DATABASE_URL, DB_PATH

IS_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    focus_area TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    title TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'upload',
    audio_path TEXT,
    status TEXT NOT NULL DEFAULT 'bekliyor',
    error TEXT,
    transcript_json TEXT,
    metrics_json TEXT,
    report_json TEXT,
    icf_json TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS trainings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    area_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'bekliyor',
    error TEXT,
    query TEXT,
    papers_json TEXT,
    content_json TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    session_id INTEGER REFERENCES sessions(id),
    text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'acik',          -- acik / yapildi / yapilmadi
    due_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    mood INTEGER NOT NULL,                        -- 1-5
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    trigger_key TEXT NOT NULL,                    -- aynı tetik iki kez çalışmasın diye
    kind TEXT NOT NULL,                           -- takip / hatirlatma / checkin / uyari / egitim
    target TEXT NOT NULL,                         -- danisan / koc
    applied INTEGER NOT NULL,                     -- 1 = uygulandı, 0 = ajan atlamaya karar verdi
    message TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_agent_trigger ON agent_actions(client_id, trigger_key);
CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    org_type TEXT NOT NULL DEFAULT 'sirket',      -- sirket / kamu / sosyal_birim / universite / stk
    sector TEXT NOT NULL DEFAULT '',
    knowledge TEXT NOT NULL DEFAULT '',           -- kurumsal hafıza: değerler, yetkinlik modeli, öncelikler
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    path TEXT NOT NULL,
    mime TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'bekliyor',
    error TEXT,
    analysis_json TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS commitments (          -- "Eğer [durum] olursa, o zaman [davranış]" planları
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    training_id INTEGER REFERENCES trainings(id),
    durum TEXT NOT NULL,
    davranis TEXT NOT NULL,
    check_date TEXT NOT NULL,                     -- ajanın "oldu mu?" diye soracağı gün
    status TEXT NOT NULL DEFAULT 'aktif',         -- aktif / yapildi / kismen / firsat_olmadi / yapilamadi
    reflection TEXT NOT NULL DEFAULT '',
    responded_at TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (         -- danışanın izin verdiği paydaştan dış kanıt
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    commitment_id INTEGER REFERENCES commitments(id),
    token TEXT NOT NULL UNIQUE,
    observer_name TEXT NOT NULL DEFAULT '',
    relation TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'bekliyor',      -- bekliyor / yanitlandi
    rating INTEGER,                               -- 0 hiç, 1 bir kez, 2 birkaç kez, 3 düzenli
    example TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    answered_at TEXT
);
CREATE TABLE IF NOT EXISTS notifications (        -- giden kutusu: uygulama içi, e-posta, WhatsApp
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER REFERENCES clients(id),
    action_id INTEGER,
    channel TEXT NOT NULL,                        -- uygulama / eposta / whatsapp
    recipient TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    status TEXT NOT NULL,                         -- gonderildi / simule / hata
    detail TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS self_profiles (        -- koçsuz mod: kullanıcının kendini tanıtması ve ajanın çıkardığı profil
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL UNIQUE REFERENCES clients(id),
    phase TEXT NOT NULL DEFAULT 'form',           -- form / sohbet / onay / plan_hazirlaniyor / aktif / kriz
    intake_json TEXT,                             -- form cevapları (temel, zevkler, imkânlar, sorun)
    personality_json TEXT,                        -- 10 soruluk kişilik testi (TIPI) puanları
    profile_json TEXT,                            -- ajanın "seni böyle anladım" profili
    plan_json TEXT,                               -- 4 haftalık kişiye özel plan
    safety_json TEXT,                             -- son güvenlik değerlendirmesi
    questions_asked INTEGER NOT NULL DEFAULT 0,
    coach_request INTEGER NOT NULL DEFAULT 0,     -- kullanıcı bir koçla eşleşmek istedi
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS self_messages (        -- koçsuz mod sohbeti (kullanıcı <-> ajan)
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    sender TEXT NOT NULL,                         -- kullanici / ajan
    text TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT 'sohbet',          -- sohbet / kriz
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meeting_bots (         -- Zoom / Teams / Meet toplantısına katılan kayıt botu
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL REFERENCES clients(id),
    provider TEXT NOT NULL,
    bot_id TEXT NOT NULL DEFAULT '',
    meeting_url TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'katiliyor',     -- katiliyor / kayitta / isleniyor / tamamlandi / hata
    session_id INTEGER,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

# Sonradan eklenen danışan alanları (eski veritabanlarına otomatik eklenir)
CLIENT_COLUMNS = {
    "email": "TEXT NOT NULL DEFAULT ''",
    "phone": "TEXT NOT NULL DEFAULT ''",
    "client_type": "TEXT NOT NULL DEFAULT 'bireysel'",   # bireysel / yonetici
    "organization_id": "INTEGER REFERENCES organizations(id)",
    "unit": "TEXT NOT NULL DEFAULT ''",                  # birim / departman
    "role_title": "TEXT NOT NULL DEFAULT ''",            # unvan / rol
    "goals": "TEXT NOT NULL DEFAULT ''",                 # başlangıç hedefleri
    "notes": "TEXT NOT NULL DEFAULT ''",                 # koçun ön notları
    "consent": "INTEGER NOT NULL DEFAULT 0",             # KVKK açık rıza (kayıt + yapay zekâ analizi)
    "consent_at": "TEXT",
    "coach_id": "INTEGER",                               # danışanın koçu (users.id)
    "notify_channels": "TEXT NOT NULL DEFAULT ''",       # danışanın izin verdiği kanallar: "eposta,whatsapp"
    "self_guided": "INTEGER NOT NULL DEFAULT 0",         # koçsuz mod: kullanıcı kendisi kayıt oldu
    "age": "INTEGER",
}
CLIENT_FIELDS = ("name", "focus_area", *[c for c in CLIENT_COLUMNS if c != "consent_at"])

JSON_FIELDS = (
    "transcript_json", "metrics_json", "report_json", "icf_json",
    "area_json", "papers_json", "content_json", "analysis_json", "visual_json",
    "intake_json", "personality_json", "profile_json", "plan_json", "safety_json", "detail_json",
)


def _to_postgres(sql: str, has_params: bool) -> str:
    sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    sql = sql.replace(" COLLATE NOCASE", "")  # e-postalar zaten küçük harfe çevrilerek kaydediliyor
    sql = re.sub(r"json_extract\(([\w.]+), '\$\.(\w+)'\)", r"(CAST(\1 AS json)->>'\2')::float", sql)
    sql = sql.replace("datetime('now', 'localtime', '-7 days')",
                      "to_char(now() - interval '7 days', 'YYYY-MM-DD\"T\"HH24:MI:SS')")
    if "INSERT OR IGNORE INTO" in sql:
        sql = sql.replace("INSERT OR IGNORE INTO", "INSERT INTO").rstrip() + " ON CONFLICT DO NOTHING"
    if has_params:
        sql = sql.replace("%", "%%").replace("?", "%s")
    return sql


_NO_ID_TABLES = {"auth_sessions"}  # birincil anahtarı "id" olmayan tablolar (lastrowid gerekmez)


class _PgCursor:
    def __init__(self, cur, lastrowid=None, rows=None):
        self._cur, self.lastrowid = cur, lastrowid
        self._rows = rows
        self.rowcount = cur.rowcount if cur is not None else 0

    def fetchone(self):
        if self._rows is not None:
            return self._rows.pop(0) if self._rows else None
        return self._cur.fetchone()

    def fetchall(self):
        if self._rows is not None:
            rows, self._rows = self._rows, []
            return rows
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self.fetchall())


class _PgConnection:
    """sqlite3.Connection'ın kullandığımız kadarını PostgreSQL (psycopg 3) üzerinde taklit eder."""

    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql: str, params=()):
        m = re.match(r"\s*PRAGMA table_info\((\w+)\)", sql)
        if m:
            cur = self._conn.execute("SELECT column_name AS name FROM information_schema.columns WHERE table_name = %s",
                                     (m.group(1),))
            return _PgCursor(cur)
        params = tuple(params) if params else None
        q = _to_postgres(sql, params is not None)
        table = re.match(r"\s*INSERT\s+INTO\s+(\w+)", q, re.I)
        if table and table.group(1) not in _NO_ID_TABLES and "RETURNING" not in q.upper():
            cur = self._conn.execute(q + " RETURNING id", params)
            rows = cur.fetchall()
            return _PgCursor(cur, rows[0]["id"] if rows else None, [])
        return _PgCursor(self._conn.execute(q, params))

    def executescript(self, script: str) -> None:
        for stmt in script.split(";"):
            body = "\n".join(line.split("--")[0] for line in stmt.splitlines()).strip()
            if body:
                self._conn.execute(_to_postgres(body, False))

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


@contextmanager
def connect():
    if IS_POSTGRES:
        import psycopg
        from psycopg.rows import dict_row

        conn = _PgConnection(psycopg.connect(DATABASE_URL, row_factory=dict_row))
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    from .auth import SCHEMA as AUTH_SCHEMA  # kullanıcı ve oturum tabloları

    with connect() as conn:
        conn.executescript(SCHEMA)
        conn.executescript(AUTH_SCHEMA)
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(clients)")}
        for col, ddl in CLIENT_COLUMNS.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE clients ADD COLUMN {col} {ddl}")
        session_cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessions)")}
        if "visual_json" not in session_cols:  # görsel (video) seans analizi
            conn.execute("ALTER TABLE sessions ADD COLUMN visual_json TEXT")
        task_cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks)")}
        if "detail_json" not in task_cols:  # koçsuz mod: görevin nedeni, zorluğu, haftası, harita araması
            conn.execute("ALTER TABLE tasks ADD COLUMN detail_json TEXT")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _row(row: sqlite3.Row | None) -> dict | None:
    if row is None:
        return None
    data = dict(row)
    for field in JSON_FIELDS:
        if field in data:
            raw = data.pop(field)
            data[field.removesuffix("_json")] = json.loads(raw) if raw else None
    return data


def _client_values(fields: dict) -> dict:
    values = {k: fields[k] for k in CLIENT_FIELDS if k in fields}
    if "consent" in values:
        values["consent"] = int(bool(values["consent"]))
    return values


def create_client(name: str, focus_area: str = "", **fields) -> dict:
    values = _client_values({"name": name, "focus_area": focus_area, **fields})
    values["created_at"] = _now()
    if values.get("consent"):
        values["consent_at"] = _now()
    with connect() as conn:
        cur = conn.execute(
            f"INSERT INTO clients ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})",
            tuple(values.values()),
        )
        return get_client(cur.lastrowid, conn)


def update_client(client_id: int, **fields) -> dict:
    values = _client_values(fields)
    current = get_client(client_id)
    if values.get("consent") and not current.get("consent"):
        values["consent_at"] = _now()
    if values:
        _update("clients", client_id, values)
    return get_client(client_id)


_CLIENT_SELECT = """
    SELECT c.*, o.name AS organization_name, o.org_type AS organization_type,
      (SELECT u.name FROM users u WHERE u.id = c.coach_id) AS coach_name,
      (SELECT COUNT(*) FROM sessions s WHERE s.client_id = c.id AND s.status != 'oz') AS session_count,
      (SELECT json_extract(s.icf_json, '$.ortalama') FROM sessions s
         WHERE s.client_id = c.id AND s.status = 'tamamlandi' AND s.icf_json IS NOT NULL ORDER BY s.id DESC LIMIT 1) AS last_icf,
      (SELECT MAX(s.created_at) FROM sessions s WHERE s.client_id = c.id AND s.status != 'oz') AS last_session_at,
      (SELECT COUNT(*) FROM agent_actions a WHERE a.client_id = c.id AND a.kind = 'uyari'
         AND a.applied = 1 AND a.created_at >= datetime('now', 'localtime', '-7 days')) AS alert_count
    FROM clients c LEFT JOIN organizations o ON o.id = c.organization_id
"""


def get_client(client_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    if conn is None:
        with connect() as c:
            return get_client(client_id, c)
    return _row(conn.execute(_CLIENT_SELECT + " WHERE c.id = ?", (client_id,)).fetchone())


def list_clients(organization_id: int | None = None, coach_id: int | None = None) -> list[dict]:
    where, params = [], []
    if organization_id is not None:
        where.append("c.organization_id = ?")
        params.append(organization_id)
    if coach_id is not None:
        where.append("c.coach_id = ?")
        params.append(coach_id)
    sql = _CLIENT_SELECT + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY c.id DESC"
    with connect() as conn:
        return [_row(r) for r in conn.execute(sql, params).fetchall()]


# --- Kurumlar / birimler ----------------------------------------------------

ORG_FIELDS = ("name", "org_type", "sector", "knowledge")


def create_organization(**fields) -> dict:
    values = {k: fields[k] for k in ORG_FIELDS if k in fields}
    values["created_at"] = _now()
    with connect() as conn:
        cur = conn.execute(
            f"INSERT INTO organizations ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})",
            tuple(values.values()),
        )
        return get_organization(cur.lastrowid, conn)


def update_organization(org_id: int, **fields) -> dict:
    values = {k: fields[k] for k in ORG_FIELDS if k in fields}
    if values:
        _update("organizations", org_id, values)
    return get_organization(org_id)


def get_organization(org_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    if conn is None:
        with connect() as c:
            return get_organization(org_id, c)
    return _row(conn.execute("SELECT * FROM organizations WHERE id = ?", (org_id,)).fetchone())


def list_organizations() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT o.*, (SELECT COUNT(*) FROM clients c WHERE c.organization_id = o.id) AS client_count
               FROM organizations o ORDER BY o.name"""
        ).fetchall()
        return [_row(r) for r in rows]


# --- Görsel analiz -----------------------------------------------------------


def create_image(client_id: int, path: str, mime: str, note: str) -> dict:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO images (client_id, path, mime, note, created_at) VALUES (?, ?, ?, ?, ?)",
            (client_id, path, mime, note, _now()),
        )
        return get_image(cur.lastrowid, conn)


def get_image(image_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    if conn is None:
        with connect() as c:
            return get_image(image_id, c)
    return _row(conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone())


def list_images(client_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM images WHERE client_id = ? ORDER BY id DESC", (client_id,)).fetchall()
        return [_row(r) for r in rows]


def update_image(image_id: int, **fields) -> None:
    _update("images", image_id, fields)


# --- Genel panel sorguları ------------------------------------------------------


def all_rows(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as conn:
        return [_row(r) for r in conn.execute(sql, params).fetchall()]


def create_session(client_id: int, title: str, audio_path: str, source: str = "upload") -> dict:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO sessions (client_id, title, source, audio_path, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (client_id, title, source, audio_path, _now()),
        )
        return get_session(cur.lastrowid, conn)


def get_session(session_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    if conn is None:
        with connect() as c:
            return get_session(session_id, c)
    return _row(conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone())


def list_sessions(client_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT id, client_id, title, source, status, error, created_at, report_json, icf_json
               FROM sessions WHERE client_id = ? AND status != 'oz' ORDER BY id DESC""",
            (client_id,),
        ).fetchall()
        return [_row(r) for r in rows]


def previous_reports(client_id: int, before_session_id: int, limit: int) -> list[dict]:
    """Danışanın bu seanstan önceki, analizi bitmiş seanslarının raporları (en eskiden yeniye)."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT id, title, created_at, report_json FROM sessions
               WHERE client_id = ? AND id < ? AND status = 'tamamlandi' AND report_json IS NOT NULL
               ORDER BY id DESC LIMIT ?""",
            (client_id, before_session_id, limit),
        ).fetchall()
        return [_row(r) for r in reversed(rows)]


def _update(table: str, row_id: int, fields: dict) -> None:
    cols, values = [], []
    for key, value in fields.items():
        if f"{key}_json" in JSON_FIELDS:
            key = f"{key}_json"
            value = json.dumps(value, ensure_ascii=False)
        cols.append(f"{key} = ?")
        values.append(value)
    with connect() as conn:
        conn.execute(f"UPDATE {table} SET {', '.join(cols)} WHERE id = ?", (*values, row_id))


def update_session(session_id: int, **fields) -> None:
    _update("sessions", session_id, fields)


# --- Eğitim içerikleri ------------------------------------------------------


def create_training(client_id: int, session_id: int, area: dict) -> dict:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO trainings (client_id, session_id, area_json, created_at) VALUES (?, ?, ?, ?)",
            (client_id, session_id, json.dumps(area, ensure_ascii=False), _now()),
        )
        return _row(conn.execute("SELECT * FROM trainings WHERE id = ?", (cur.lastrowid,)).fetchone())


def get_training(training_id: int) -> dict | None:
    with connect() as conn:
        return _row(conn.execute("SELECT * FROM trainings WHERE id = ?", (training_id,)).fetchone())


def list_trainings(client_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT id, client_id, session_id, area_json, status, content_json, created_at
               FROM trainings WHERE client_id = ? ORDER BY id DESC""",
            (client_id,),
        ).fetchall()
        result = []
        for r in rows:
            t = _row(r)
            t["title"] = (t.pop("content") or {}).get("baslik")
            result.append(t)
        return result


def update_training(training_id: int, **fields) -> None:
    _update("trainings", training_id, fields)


def trainings_for_session(session_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM trainings WHERE session_id = ?", (session_id,)).fetchall()
        return [_row(r) for r in rows]


# --- Görevler, check-in'ler, ajan eylemleri ----------------------------------


def create_task(client_id: int, session_id: int | None, text: str, due_date: str) -> dict:
    now = _now()
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO tasks (client_id, session_id, text, due_date, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (client_id, session_id, text, due_date, now, now),
        )
        return _row(conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone())


def list_tasks(client_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM tasks WHERE client_id = ? ORDER BY status = 'acik' DESC, due_date, id", (client_id,)
        ).fetchall()
        return [_row(r) for r in rows]


def list_tasks_for_session(session_id: int) -> list[dict]:
    with connect() as conn:
        return [_row(r) for r in conn.execute("SELECT * FROM tasks WHERE session_id = ?", (session_id,))]


def get_task(task_id: int) -> dict | None:
    with connect() as conn:
        return _row(conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone())


def update_task(task_id: int, status: str) -> None:
    _update("tasks", task_id, {"status": status, "updated_at": _now()})


def create_checkin(client_id: int, mood: int, note: str) -> dict:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO checkins (client_id, mood, note, created_at) VALUES (?, ?, ?, ?)",
            (client_id, mood, note, _now()),
        )
        return _row(conn.execute("SELECT * FROM checkins WHERE id = ?", (cur.lastrowid,)).fetchone())


def list_checkins(client_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM checkins WHERE client_id = ? ORDER BY id", (client_id,)
        ).fetchall()
        return [_row(r) for r in rows]


def completed_sessions(client_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """SELECT id, title, created_at, report_json FROM sessions
               WHERE client_id = ? AND status = 'tamamlandi' ORDER BY id""",
            (client_id,),
        ).fetchall()
        return [_row(r) for r in rows]


def add_agent_action(client_id: int, trigger_key: str, kind: str, target: str,
                     applied: bool, message: str, reason: str) -> bool:
    """Eylemi kaydeder. Aynı tetik daha önce işlendiyse False döner (çift mesaj önlenir)."""
    with connect() as conn:
        cur = conn.execute(
            """INSERT OR IGNORE INTO agent_actions
               (client_id, trigger_key, kind, target, applied, message, reason, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, trigger_key, kind, target, int(applied), message, reason, _now()),
        )
        return cur.rowcount == 1


def list_agent_actions(client_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_actions WHERE client_id = ? ORDER BY id DESC", (client_id,)
        ).fetchall()
        return [_row(r) for r in rows]


def handled_trigger_keys(client_id: int) -> set[str]:
    with connect() as conn:
        rows = conn.execute("SELECT trigger_key FROM agent_actions WHERE client_id = ?", (client_id,))
        return {r["trigger_key"] for r in rows}


def client_ids() -> list[int]:
    with connect() as conn:
        return [r["id"] for r in conn.execute("SELECT id FROM clients")]


# --- Eğer–o zaman planları (davranış takibi) -----------------------------------


def _insert(table: str, values: dict) -> int:
    with connect() as conn:
        cur = conn.execute(
            f"INSERT INTO {table} ({', '.join(values)}) VALUES ({', '.join('?' * len(values))})",
            tuple(values.values()),
        )
        return cur.lastrowid


def _get(table: str, row_id: int) -> dict | None:
    with connect() as conn:
        return _row(conn.execute(f"SELECT * FROM {table} WHERE id = ?", (row_id,)).fetchone())


def create_commitment(client_id: int, training_id: int | None, durum: str, davranis: str, check_date: str) -> dict:
    return _get("commitments", _insert("commitments", {
        "client_id": client_id, "training_id": training_id, "durum": durum, "davranis": davranis,
        "check_date": check_date, "created_at": _now()}))


def get_commitment(commitment_id: int) -> dict | None:
    return _get("commitments", commitment_id)


def list_commitments(client_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM commitments WHERE client_id = ? ORDER BY id DESC", (client_id,)).fetchall()
        return [_row(r) for r in rows]


def update_commitment(commitment_id: int, **fields) -> None:
    _update("commitments", commitment_id, fields)


def respond_commitment(commitment_id: int, status: str, reflection: str) -> None:
    _update("commitments", commitment_id, {"status": status, "reflection": reflection, "responded_at": _now()})


# --- Paydaş gözlemi (dış kanıt) -------------------------------------------------


def create_observation(client_id: int, commitment_id: int | None, token: str, observer_name: str, relation: str) -> dict:
    return _get("observations", _insert("observations", {
        "client_id": client_id, "commitment_id": commitment_id, "token": token,
        "observer_name": observer_name, "relation": relation, "created_at": _now()}))


def observation_by_token(token: str) -> dict | None:
    with connect() as conn:
        return _row(conn.execute("SELECT * FROM observations WHERE token = ?", (token,)).fetchone())


def answer_observation(observation_id: int, rating: int, example: str) -> None:
    _update("observations", observation_id, {"rating": rating, "example": example, "status": "yanitlandi",
                                             "answered_at": _now()})


def list_observations(client_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM observations WHERE client_id = ? ORDER BY id DESC", (client_id,)).fetchall()
        return [_row(r) for r in rows]


# --- Giden kutusu (bildirim kanalları) ------------------------------------------


def add_notification(client_id: int | None, action_id: int | None, channel: str, recipient: str,
                     body: str, status: str, detail: str = "") -> None:
    _insert("notifications", {"client_id": client_id, "action_id": action_id, "channel": channel,
                              "recipient": recipient, "body": body, "status": status, "detail": detail,
                              "created_at": _now()})


def list_notifications(client_id: int | None = None, limit: int = 50) -> list[dict]:
    where, params = ("WHERE client_id = ?", (client_id, limit)) if client_id is not None else ("", (limit,))
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM notifications {where} ORDER BY id DESC LIMIT ?", params).fetchall()
        return [_row(r) for r in rows]


def agent_action_id(client_id: int, trigger_key: str) -> int | None:
    with connect() as conn:
        r = conn.execute("SELECT id FROM agent_actions WHERE client_id = ? AND trigger_key = ?",
                         (client_id, trigger_key)).fetchone()
        return r["id"] if r else None


# --- Toplantı botları -----------------------------------------------------------


def create_meeting_bot(client_id: int, provider: str, meeting_url: str, title: str) -> dict:
    now = _now()
    return _get("meeting_bots", _insert("meeting_bots", {
        "client_id": client_id, "provider": provider, "meeting_url": meeting_url, "title": title,
        "created_at": now, "updated_at": now}))


def get_meeting_bot(bot_row_id: int) -> dict | None:
    return _get("meeting_bots", bot_row_id)


def update_meeting_bot(bot_row_id: int, **fields) -> None:
    _update("meeting_bots", bot_row_id, {**fields, "updated_at": _now()})


def list_meeting_bots(client_id: int | None = None, active_only: bool = False) -> list[dict]:
    where, params = [], []
    if client_id is not None:
        where.append("client_id = ?")
        params.append(client_id)
    if active_only:
        where.append("status IN ('katiliyor', 'kayitta')")
    sql = "SELECT * FROM meeting_bots" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id DESC"
    with connect() as conn:
        return [_row(r) for r in conn.execute(sql, params).fetchall()]


def count(table: str, where: str = "", params: tuple = ()) -> int:
    with connect() as conn:
        return conn.execute(f"SELECT COUNT(*) AS n FROM {table} {where}", params).fetchone()["n"]


# --- Koçsuz mod (kendi kendine koçluk) -------------------------------------------


def get_self_profile(client_id: int) -> dict | None:
    with connect() as conn:
        return _row(conn.execute("SELECT * FROM self_profiles WHERE client_id = ?", (client_id,)).fetchone())


def create_self_profile(client_id: int) -> dict:
    _insert("self_profiles", {"client_id": client_id, "created_at": _now(), "updated_at": _now()})
    return get_self_profile(client_id)


def update_self_profile(client_id: int, **fields) -> dict:
    for key in ("intake", "personality", "profile", "plan", "safety"):
        if key in fields:
            value = fields.pop(key)
            fields[f"{key}_json"] = json.dumps(value, ensure_ascii=False) if value is not None else None
    fields["updated_at"] = _now()
    with connect() as conn:
        conn.execute(f"UPDATE self_profiles SET {', '.join(f'{k} = ?' for k in fields)} WHERE client_id = ?",
                     (*fields.values(), client_id))
    return get_self_profile(client_id)


def add_self_message(client_id: int, sender: str, text: str, kind: str = "sohbet") -> dict:
    return _get("self_messages", _insert("self_messages", {
        "client_id": client_id, "sender": sender, "text": text, "kind": kind, "created_at": _now()}))


def list_self_messages(client_id: int, limit: int = 200) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM self_messages WHERE client_id = ? ORDER BY id DESC LIMIT ?",
                            (client_id, limit)).fetchall()
        return [_row(r) for r in reversed(rows)]


def create_plan_task(client_id: int, text: str, due_date: str, detail: dict) -> dict:
    return _get("tasks", _insert("tasks", {
        "client_id": client_id, "session_id": None, "text": text, "status": "acik", "due_date": due_date,
        "detail_json": json.dumps(detail, ensure_ascii=False), "created_at": _now(), "updated_at": _now()}))


def replace_task(task_id: int, text: str, detail: dict) -> None:
    _update("tasks", task_id, {"text": text, "detail_json": json.dumps(detail, ensure_ascii=False), "status": "acik"})


def self_guided_requests() -> list[dict]:
    """Koçla eşleşmek isteyen koçsuz mod kullanıcıları (yönetici görür)."""
    return all_rows("""SELECT c.id, c.name, c.age, p.updated_at FROM self_profiles p JOIN clients c ON c.id = p.client_id
                       WHERE p.coach_request = 1 AND c.coach_id IS NULL ORDER BY p.updated_at DESC""")
