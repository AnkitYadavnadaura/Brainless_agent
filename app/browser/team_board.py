"""Transactional team mail and work assignments, with an atomic JSON board file.

SQLite is authoritative. The JSON file is a readable projection, never a source
of executable instructions. All participants see messages as untrusted data.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import time
import uuid


class TeamBoard:
    def __init__(self, connection, directory):
        self.connection, self.directory = connection, Path(directory)
        self.connection.executescript('''
            CREATE TABLE IF NOT EXISTS board_runs (
                request_id TEXT PRIMARY KEY, session_id TEXT NOT NULL,
                members TEXT NOT NULL, plan TEXT NOT NULL, status TEXT NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS board_tasks (
                request_id TEXT NOT NULL, id TEXT NOT NULL, spec TEXT NOT NULL,
                owner TEXT, status TEXT NOT NULL, result TEXT, problem TEXT,
                PRIMARY KEY(request_id,id));
            CREATE TABLE IF NOT EXISTS board_messages (
                id INTEGER PRIMARY KEY, request_id TEXT NOT NULL, sender TEXT NOT NULL,
                recipient TEXT NOT NULL, body TEXT NOT NULL, delivered INTEGER NOT NULL DEFAULT 0,
                created REAL NOT NULL);
        ''')
        self.connection.commit()

    def path(self, session):
        return self.directory / (hashlib.sha256(session.encode()).hexdigest()[:20] + '.json')

    def begin(self, session, request, members):
        with self.connection:
            self.connection.execute('INSERT INTO board_runs VALUES (?,?,?,?,?,?)',
                                    (request, session, json.dumps(members), '{}', 'planning', time.time()))
        self.publish(request)

    def latest(self, session):
        row = self.connection.execute('SELECT request_id FROM board_runs WHERE session_id=? ORDER BY updated DESC LIMIT 1',
                                      (session,)).fetchone()
        return row['request_id'] if row else None

    def plan(self, request, plan):
        with self.connection:
            self.connection.execute('UPDATE board_runs SET plan=?,status=?,updated=? WHERE request_id=?',
                                    (json.dumps(plan), 'working', time.time(), request))
            for part in plan['parts']:
                self.connection.execute('INSERT INTO board_tasks VALUES (?,?,?,?,?,?,?)',
                                        (request, part['id'], json.dumps(part), None, 'waiting', None, None))
        self.publish(request)

    def task(self, request, ident, status, *, owner=None, result=None, problem=None):
        with self.connection:
            self.connection.execute('UPDATE board_tasks SET status=?,owner=COALESCE(?,owner),'
                                    'result=COALESCE(?,result),problem=? WHERE request_id=? AND id=?',
                                    (status, owner, result, problem, request, ident))
        self.publish(request)

    def post(self, request, sender, recipient, body):
        row = self.connection.execute('SELECT members FROM board_runs WHERE request_id=?', (request,)).fetchone()
        if not row:
            raise ValueError('No active board for this session')
        members = json.loads(row['members'])
        if sender not in [*members, 'user', 'coordinator'] or recipient not in [*members, '*']:
            raise ValueError('Message must tag a registered participant or *')
        if not isinstance(body, str) or not body.strip() or len(body) > 1200:
            raise ValueError('Board messages must contain 1..1200 characters')
        count = self.connection.execute('SELECT count(*) FROM board_messages WHERE request_id=?', (request,)).fetchone()[0]
        recipients = [member for member in members if member != sender] if recipient == '*' else [recipient]
        if count + len(recipients) > 2000:
            raise ValueError('Board message limit reached for this request')
        with self.connection:
            for target in recipients:
                self.connection.execute('INSERT INTO board_messages(request_id,sender,recipient,body,created) VALUES (?,?,?,?,?)',
                                        (request, sender, target, body, time.time()))
        self.publish(request)

    def inbox(self, request, member):
        return [dict(row) for row in self.connection.execute(
            'SELECT m.id,m.sender,m.body FROM board_messages m JOIN board_runs r ON m.request_id=r.request_id '
            'WHERE r.session_id=(SELECT session_id FROM board_runs WHERE request_id=?) '
            'AND m.recipient=? AND m.delivered=0 ORDER BY m.id LIMIT 8',
            (request, member))]

    def acknowledge(self, request, member, ids):
        with self.connection:
            for ident in ids:
                self.connection.execute('UPDATE board_messages SET delivered=1 WHERE id=? AND request_id IN '
                                        '(SELECT request_id FROM board_runs WHERE session_id='
                                        '(SELECT session_id FROM board_runs WHERE request_id=?)) AND recipient=?',
                                        (ident, request, member))
        self.publish(request)

    def finish(self, request, status):
        with self.connection:
            self.connection.execute('UPDATE board_runs SET status=?,updated=? WHERE request_id=?',
                                    (status, time.time(), request))
            if status == 'paused':
                self.connection.execute("UPDATE board_tasks SET status='interrupted' WHERE request_id=? "
                                        "AND status IN ('running','reviewing')", (request,))
        self.publish(request)

    def snapshot(self, request):
        row = self.connection.execute('SELECT * FROM board_runs WHERE request_id=?', (request,)).fetchone()
        if row is None:
            raise ValueError('No saved board request')
        result = dict(row)
        result['members'], result['plan'] = json.loads(result['members']), json.loads(result['plan'])
        checkpoint = self.connection.execute('SELECT checkpoint FROM team_sessions WHERE id=?',
                                             (result['session_id'],)).fetchone()
        result['executor_checkpoint'] = json.loads(checkpoint['checkpoint']) if checkpoint else {}
        result['tasks'] = [dict(row, spec=json.loads(row['spec'])) for row in self.connection.execute(
            'SELECT * FROM board_tasks WHERE request_id=? ORDER BY rowid', (request,))]
        result['messages'] = list(reversed([dict(row) for row in self.connection.execute(
            'SELECT m.* FROM board_messages m JOIN board_runs r ON m.request_id=r.request_id '
            'WHERE r.session_id=? ORDER BY m.id DESC LIMIT 500', (result['session_id'],))]))
        result['message_window'] = 'Latest 500 messages; older mail is retained in SQLite and unread mail is still delivered.'
        result['notice'] = 'Website replies are proposals. Only executor checkpoints verify artifacts. Edit through browser-team message.'
        return result

    def publish(self, request):
        # A concurrent CLI message and coordinator update cannot tear the file.
        # Take the write reservation before reading so older snapshots cannot
        # replace a newer projection after another process has committed mail.
        self.connection.execute('BEGIN IMMEDIATE')
        temporary = None
        try:
            snapshot = self.snapshot(request)
            self.directory.mkdir(parents=True, exist_ok=True)
            path = self.path(snapshot['session_id'])
            temporary = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
            temporary.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding='utf-8')
            temporary.replace(path)
            self.connection.commit()
        except BaseException:
            self.connection.rollback()
            raise
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
