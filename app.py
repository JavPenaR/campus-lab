"""Campus Lab: intentionally vulnerable, local-only teaching application."""
import json
import os
import secrets
import sqlite3
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("DATA_DIR", ROOT / "data"))
DB = DATA / "campus.db"
STUDENT = "lucia"
PRICES = {"atlas": 80, "orion": 80}


def connect():
    db = sqlite3.connect(DB, timeout=10)
    db.row_factory = sqlite3.Row
    return db


def flag():
    return "CAMPUS{" + secrets.token_hex(12) + "}"


def initialize():
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "reports").mkdir(exist_ok=True)
    (DATA / "private").mkdir(exist_ok=True)
    db = connect()
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS resources (id INTEGER PRIMARY KEY, title TEXT, summary TEXT, visible INTEGER);
      CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY, owner TEXT, item TEXT, detail TEXT);
      CREATE TABLE IF NOT EXISTS wallets (owner TEXT PRIMARY KEY, balance INTEGER);
      CREATE TABLE IF NOT EXISTS passes (owner TEXT, name TEXT, PRIMARY KEY(owner,name));
      CREATE TABLE IF NOT EXISTS flags (challenge TEXT PRIMARY KEY, value TEXT);
    """)
    if not db.execute("SELECT 1 FROM flags LIMIT 1").fetchone():
        values = {key: flag() for key in ("search", "receipt", "export", "vault")}
        db.executemany("INSERT INTO flags VALUES (?,?)", values.items())
        db.executemany("INSERT INTO resources VALUES (?,?,?,?)", [
            (1, "Introducción a redes", "Guía de laboratorio y topologías básicas.", 1),
            (2, "Biblioteca digital", "Lecturas recomendadas de arquitectura web.", 1),
            (3, "Taller de bases de datos", "Ejercicios de consultas y relaciones.", 1),
            (4, "Índice reservado", "Registro interno: " + values["search"], 0),
        ])
        db.executemany("INSERT INTO receipts VALUES (?,?,?,?)", [
            (1041, STUDENT, "Kit de bienvenida", "Comprobante de Lucía. Sin información reservada."),
            (1042, "marco", "Archivo de investigación", "Referencia privada: " + values["receipt"]),
            (1043, STUDENT, "Cuaderno de campo", "Comprobante de Lucía, segundo semestre."),
        ])
        db.execute("INSERT INTO wallets VALUES (?,?)", (STUDENT, 100))
        (DATA / "reports" / "resumen.txt").write_text(
            "Resumen semestral público\nLos documentos internos se guardan en ../private/ y usan nombres de plan.\n", encoding="utf-8")
        (DATA / "private" / "plan-semestral.txt").write_text(
            "Plan semestral interno\nCódigo de revisión: " + values["export"] + "\n", encoding="utf-8")
        db.commit()
    db.close()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args), flush=True)

    def reply(self, status, data, content_type="application/json; charset=utf-8"):
        body = json.dumps(data, ensure_ascii=False).encode() if isinstance(data, (dict, list)) else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def params(self):
        return parse_qs(urlparse(self.path).query, keep_blank_values=True)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self.reply(200, (ROOT / "static" / "index.html").read_bytes(), "text/html; charset=utf-8")
        if path in ("/app.css", "/app.js"):
            kind = "text/css" if path.endswith("css") else "text/javascript"
            return self.reply(200, (ROOT / "static" / path[1:]).read_bytes(), kind + "; charset=utf-8")
        if path == "/api/health":
            return self.reply(200, {"status": "ok"})
        if path == "/api/resources":
            q = self.params().get("q", [""])[0]
            # Challenge 1: untrusted search text is interpolated into SQL.
            sql = "SELECT id,title,summary FROM resources WHERE visible=1 AND (title LIKE '%" + q + "%' OR summary LIKE '%" + q + "%')"
            try:
                with connect() as db:
                    rows = [dict(x) for x in db.execute(sql).fetchall()]
                return self.reply(200, {"resources": rows})
            except sqlite3.Error:
                return self.reply(400, {"error": "No se pudo completar la búsqueda."})
        if path == "/api/receipts":
            with connect() as db:
                rows = [dict(x) for x in db.execute("SELECT id,item FROM receipts WHERE owner=?", (STUDENT,))]
            return self.reply(200, {"receipts": rows})
        if path.startswith("/api/receipts/"):
            try:
                number = int(path.rsplit("/", 1)[1])
            except ValueError:
                return self.reply(404, {"error": "No existe."})
            # Challenge 2: a valid receipt ID is enough; ownership is never checked.
            with connect() as db:
                row = db.execute("SELECT id,owner,item,detail FROM receipts WHERE id=?", (number,)).fetchone()
            return self.reply(200, dict(row)) if row else self.reply(404, {"error": "No existe."})
        if path == "/api/exports":
            return self.reply(200, {"reports": ["resumen.txt"]})
        if path == "/api/exports/preview":
            name = self.params().get("name", [""])[0]
            # Challenge 3: validation occurs before a second URL decoding pass.
            if "../" in name or "..\\" in name or not name.endswith(".txt"):
                return self.reply(400, {"error": "Nombre de informe inválido."})
            report = DATA / "reports" / unquote(name)
            try:
                content = report.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                return self.reply(404, {"error": "Informe no disponible."})
            return self.reply(200, {"name": name, "content": content})
        if path == "/api/wallet":
            with connect() as db:
                balance = db.execute("SELECT balance FROM wallets WHERE owner=?", (STUDENT,)).fetchone()[0]
                owned = [x[0] for x in db.execute("SELECT name FROM passes WHERE owner=?", (STUDENT,))]
            return self.reply(200, {"balance": balance, "passes": owned, "prices": PRICES})
        if path == "/api/vault":
            with connect() as db:
                owned = {x[0] for x in db.execute("SELECT name FROM passes WHERE owner=?", (STUDENT,))}
                value = db.execute("SELECT value FROM flags WHERE challenge='vault'").fetchone()[0]
            if set(PRICES) <= owned:
                return self.reply(200, {"message": "Archivo desbloqueado", "code": value})
            return self.reply(403, {"error": "Se requieren los pases Atlas y Orión."})
        return self.reply(404, {"error": "Ruta no encontrada."})

    def do_POST(self):
        if urlparse(self.path).path != "/api/passes/buy":
            return self.reply(404, {"error": "Ruta no encontrada."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size > 4096:
                return self.reply(413, {"error": "Solicitud demasiado grande."})
            body = json.loads(self.rfile.read(size))
            name = body.get("pass")
        except (ValueError, TypeError, AttributeError):
            return self.reply(400, {"error": "JSON inválido."})
        if name not in PRICES:
            return self.reply(400, {"error": "Pase desconocido."})
        with connect() as db:
            balance = db.execute("SELECT balance FROM wallets WHERE owner=?", (STUDENT,)).fetchone()[0]
            owned = db.execute("SELECT 1 FROM passes WHERE owner=? AND name=?", (STUDENT, name)).fetchone()
        if owned:
            return self.reply(409, {"error": "Ya tienes este pase."})
        if balance < PRICES[name]:
            return self.reply(402, {"error": "Saldo insuficiente."})
        # Challenge 4: balance is checked outside the write transaction.
        time.sleep(0.4)
        try:
            with connect() as db:
                db.execute("UPDATE wallets SET balance=balance-? WHERE owner=?", (PRICES[name], STUDENT))
                db.execute("INSERT INTO passes VALUES (?,?)", (STUDENT, name))
            return self.reply(200, {"message": "Pase adquirido", "pass": name})
        except sqlite3.IntegrityError:
            return self.reply(409, {"error": "Ya tienes este pase."})


if __name__ == "__main__":
    initialize()
    server = ThreadingHTTPServer((os.environ.get("HOST", "127.0.0.1"), int(os.environ.get("PORT", "8080"))), Handler)
    print("Campus Lab listening on :%s" % server.server_port, flush=True)
    server.serve_forever()
