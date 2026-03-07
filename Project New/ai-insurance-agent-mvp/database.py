import os
import json
import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

from config import config

logger = logging.getLogger(__name__)

_pool: Optional[ThreadedConnectionPool] = None

def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=config.DATABASE_URL
        )
    return _pool

@contextmanager
def get_conn():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)

@contextmanager
def get_cursor(dict_cursor: bool = True):
    with get_conn() as conn:
        cursor_factory = psycopg2.extras.RealDictCursor if dict_cursor else None
        cur = conn.cursor(cursor_factory=cursor_factory)
        try:
            yield cur
        finally:
            cur.close()


def init_db():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id               SERIAL PRIMARY KEY,
                full_name        VARCHAR(200) NOT NULL,
                phone            VARCHAR(30)  NOT NULL UNIQUE,
                email            VARCHAR(200),
                language_pref    VARCHAR(10)  NOT NULL DEFAULT 'hi',
                consent_given    BOOLEAN      NOT NULL DEFAULT TRUE,
                do_not_call      BOOLEAN      NOT NULL DEFAULT FALSE,
                ndnc_registered  BOOLEAN      NOT NULL DEFAULT FALSE,
                address          TEXT,
                city             VARCHAR(100),
                state            VARCHAR(100),
                pincode          VARCHAR(10),
                country          VARCHAR(100) DEFAULT 'India',
                aadhaar_last4    VARCHAR(4),
                pan_number       VARCHAR(10),
                notes            TEXT,
                created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS policies (
                id               SERIAL PRIMARY KEY,
                customer_id      INTEGER      NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
                policy_number    VARCHAR(100) NOT NULL UNIQUE,
                policy_type      VARCHAR(100) NOT NULL DEFAULT 'Term Life Insurance',
                premium_amount   NUMERIC(12,2) NOT NULL,
                currency         VARCHAR(10)  NOT NULL DEFAULT 'INR',
                due_date         DATE         NOT NULL,
                grace_period_days INTEGER     NOT NULL DEFAULT 30,
                status           VARCHAR(50)  NOT NULL DEFAULT 'active',
                lapse_risk       VARCHAR(20)  NOT NULL DEFAULT 'low',
                agent_id         VARCHAR(100),
                agent_name       VARCHAR(200),
                last_call_date   DATE,
                call_count_today INTEGER      NOT NULL DEFAULT 0,
                call_count_week  INTEGER      NOT NULL DEFAULT 0,
                notes            TEXT,
                created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS call_logs (
                id               SERIAL PRIMARY KEY,
                policy_id        INTEGER      REFERENCES policies(id),
                customer_id      INTEGER      NOT NULL REFERENCES customers(id),
                vapi_call_id     VARCHAR(200) UNIQUE,
                initiated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                answered_at      TIMESTAMPTZ,
                ended_at         TIMESTAMPTZ,
                duration_seconds INTEGER,
                call_status      VARCHAR(50)  NOT NULL DEFAULT 'initiated',
                outcome          VARCHAR(50),
                transcript       TEXT,
                summary          TEXT,
                language_detected VARCHAR(10),
                intent_tags      TEXT[],
                escalation_flag  BOOLEAN      NOT NULL DEFAULT FALSE,
                escalation_reason TEXT,
                callback_dt      TIMESTAMPTZ,
                promise_amount   NUMERIC(12,2),
                promise_date     DATE,
                recording_url    VARCHAR(500),
                error_message    TEXT,
                raw_vapi_payload JSONB,
                created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS call_schedules (
                id               SERIAL PRIMARY KEY,
                policy_id        INTEGER      NOT NULL REFERENCES policies(id),
                customer_id      INTEGER      NOT NULL REFERENCES customers(id),
                scheduled_at     TIMESTAMPTZ  NOT NULL,
                priority_score   INTEGER      NOT NULL DEFAULT 50,
                priority_label   VARCHAR(20)  NOT NULL DEFAULT 'medium',
                status           VARCHAR(30)  NOT NULL DEFAULT 'pending',
                attempt_number   INTEGER      NOT NULL DEFAULT 1,
                created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
            );

            CREATE INDEX IF NOT EXISTS idx_policies_due_date ON policies(due_date);
            CREATE INDEX IF NOT EXISTS idx_policies_status ON policies(status);
            CREATE INDEX IF NOT EXISTS idx_call_logs_policy ON call_logs(policy_id);
            CREATE INDEX IF NOT EXISTS idx_call_logs_customer ON call_logs(customer_id);
            CREATE INDEX IF NOT EXISTS idx_call_logs_initiated ON call_logs(initiated_at);
            CREATE INDEX IF NOT EXISTS idx_call_schedules_scheduled ON call_schedules(scheduled_at);
        """)
        conn.commit()
        cur.close()
    logger.info("Database initialized successfully.")


def seed_demo_data():
    """Demo seeding disabled — add data manually via the UI."""
    logger.info("Demo seeding skipped. Add customers and policies via the UI.")
    pass


# ─── Customer CRUD ────────────────────────────────────────────────────────────

def get_all_customers(search: str = "") -> List[Dict]:
    with get_cursor() as cur:
        if search:
            cur.execute(
                """SELECT * FROM customers
                   WHERE full_name ILIKE %s OR phone ILIKE %s OR email ILIKE %s
                   ORDER BY created_at DESC""",
                (f"%{search}%", f"%{search}%", f"%{search}%")
            )
        else:
            cur.execute("SELECT * FROM customers ORDER BY created_at DESC;")
        return [dict(r) for r in cur.fetchall()]

def get_customer_by_id(cid: int) -> Optional[Dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM customers WHERE id = %s;", (cid,))
        row = cur.fetchone()
        return dict(row) if row else None

def create_customer(data: Dict) -> int:
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO customers
               (full_name, phone, email, language_pref, consent_given, do_not_call,
                ndnc_registered, address, city, state, pincode, country, notes)
               VALUES (%(full_name)s, %(phone)s, %(email)s, %(language_pref)s,
                       %(consent_given)s, %(do_not_call)s, %(ndnc_registered)s,
                       %(address)s, %(city)s, %(state)s, %(pincode)s,
                       %(country)s, %(notes)s)
               RETURNING id""",
            data
        )
        return cur.fetchone()["id"]

def update_customer(cid: int, data: Dict) -> bool:
    with get_cursor() as cur:
        cur.execute(
            """UPDATE customers SET
               full_name=%(full_name)s, phone=%(phone)s, email=%(email)s,
               language_pref=%(language_pref)s, consent_given=%(consent_given)s,
               do_not_call=%(do_not_call)s, ndnc_registered=%(ndnc_registered)s,
               address=%(address)s, city=%(city)s, state=%(state)s,
               pincode=%(pincode)s, country=%(country)s, notes=%(notes)s,
               updated_at=NOW()
               WHERE id=%(id)s""",
            {**data, "id": cid}
        )
        return cur.rowcount == 1

def delete_customer(cid: int) -> bool:
    with get_cursor() as cur:
        cur.execute("DELETE FROM customers WHERE id = %s;", (cid,))
        return cur.rowcount == 1


# ─── Policy CRUD ──────────────────────────────────────────────────────────────

def get_all_policies(search: str = "") -> List[Dict]:
    with get_cursor() as cur:
        if search:
            cur.execute(
                """SELECT p.*, c.full_name, c.phone, c.language_pref
                   FROM policies p
                   JOIN customers c ON c.id = p.customer_id
                   WHERE p.policy_number ILIKE %s OR c.full_name ILIKE %s
                   ORDER BY p.due_date ASC""",
                (f"%{search}%", f"%{search}%")
            )
        else:
            cur.execute(
                """SELECT p.*, c.full_name, c.phone, c.language_pref
                   FROM policies p
                   JOIN customers c ON c.id = p.customer_id
                   ORDER BY p.due_date ASC"""
            )
        return [dict(r) for r in cur.fetchall()]

def get_overdue_policies() -> List[Dict]:
    with get_cursor() as cur:
        cur.execute(
            """SELECT p.*, c.full_name, c.phone, c.language_pref,
                      c.do_not_call, c.consent_given, c.ndnc_registered,
                      c.city, c.state,
                      (CURRENT_DATE - p.due_date) AS days_overdue
               FROM policies p
               JOIN customers c ON c.id = p.customer_id
               WHERE p.due_date <= (CURRENT_DATE + INTERVAL '7 days')
                 AND p.status NOT IN ('lapsed', 'cancelled', 'paid')
                 AND c.do_not_call = FALSE
                 AND c.consent_given = TRUE
                 AND c.ndnc_registered = FALSE
               ORDER BY p.due_date ASC"""
        )
        return [dict(r) for r in cur.fetchall()]

def get_policy_by_id(pid: int) -> Optional[Dict]:
    with get_cursor() as cur:
        cur.execute(
            """SELECT p.*, c.full_name, c.phone, c.do_not_call,
                      c.consent_given, c.ndnc_registered
               FROM policies p
               JOIN customers c ON c.id = p.customer_id WHERE p.id = %s""",
            (pid,)
        )
        row = cur.fetchone()
        return dict(row) if row else None

def create_policy(data: Dict) -> int:
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO policies
               (customer_id, policy_number, policy_type, premium_amount, currency,
                due_date, grace_period_days, status, lapse_risk, agent_name, notes)
               VALUES (%(customer_id)s, %(policy_number)s, %(policy_type)s,
                       %(premium_amount)s, %(currency)s, %(due_date)s,
                       %(grace_period_days)s, %(status)s, %(lapse_risk)s,
                       %(agent_name)s, %(notes)s)
               RETURNING id""",
            data
        )
        return cur.fetchone()["id"]

def update_policy(pid: int, data: Dict) -> bool:
    with get_cursor() as cur:
        cur.execute(
            """UPDATE policies SET
               policy_type=%(policy_type)s, premium_amount=%(premium_amount)s,
               currency=%(currency)s, due_date=%(due_date)s,
               grace_period_days=%(grace_period_days)s, status=%(status)s,
               lapse_risk=%(lapse_risk)s, agent_name=%(agent_name)s,
               notes=%(notes)s, updated_at=NOW()
               WHERE id=%(id)s""",
            {**data, "id": pid}
        )
        return cur.rowcount == 1

def update_policy_call_info(pid: int, call_date: date):
    with get_cursor() as cur:
        cur.execute(
            """UPDATE policies SET last_call_date=%s,
               call_count_today=call_count_today+1,
               call_count_week=call_count_week+1,
               updated_at=NOW() WHERE id=%s""",
            (call_date, pid)
        )

def delete_policy(pid: int) -> bool:
    with get_cursor() as cur:
        cur.execute("DELETE FROM policies WHERE id = %s;", (pid,))
        return cur.rowcount == 1


# ─── Call Log CRUD ────────────────────────────────────────────────────────────

def create_call_log(data: Dict) -> int:
    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO call_logs
               (policy_id, customer_id, vapi_call_id, call_status,
                language_detected, raw_vapi_payload)
               VALUES (%(policy_id)s, %(customer_id)s, %(vapi_call_id)s,
                       %(call_status)s, %(language_detected)s,
                       %(raw_vapi_payload)s)
               RETURNING id""",
            data
        )
        return cur.fetchone()["id"]

def update_call_log(log_id: int, data: Dict):
    fields = ", ".join(f"{k}=%({k})s" for k in data.keys())
    with get_cursor() as cur:
        cur.execute(
            f"UPDATE call_logs SET {fields} WHERE id=%(id)s",
            {**data, "id": log_id}
        )

def update_call_log_by_vapi_id(vapi_call_id: str, data: Dict):
    fields = ", ".join(f"{k}=%({k})s" for k in data.keys())
    with get_cursor() as cur:
        cur.execute(
            f"UPDATE call_logs SET {fields} WHERE vapi_call_id=%(vapi_call_id)s",
            {**data, "vapi_call_id": vapi_call_id}
        )

def get_call_logs(limit: int = 200, outcome_filter: str = None,
                  policy_id: int = None) -> List[Dict]:
    with get_cursor() as cur:
        conditions = ["1=1"]
        params = []
        if outcome_filter and outcome_filter != "all":
            conditions.append("cl.outcome = %s")
            params.append(outcome_filter)
        if policy_id:
            conditions.append("cl.policy_id = %s")
            params.append(policy_id)
        where = " AND ".join(conditions)
        cur.execute(
            f"""SELECT cl.*, c.full_name, c.phone, p.policy_number,
                       p.premium_amount, p.currency
                FROM call_logs cl
                JOIN customers c ON c.id = cl.customer_id
                LEFT JOIN policies p ON p.id = cl.policy_id
                WHERE {where}
                ORDER BY cl.initiated_at DESC
                LIMIT %s""",
            params + [limit]
        )
        return [dict(r) for r in cur.fetchall()]

def get_call_log_by_id(log_id: int) -> Optional[Dict]:
    with get_cursor() as cur:
        cur.execute(
            """SELECT cl.*, c.full_name, c.phone, p.policy_number
               FROM call_logs cl
               JOIN customers c ON c.id = cl.customer_id
               LEFT JOIN policies p ON p.id = cl.policy_id
               WHERE cl.id = %s""",
            (log_id,)
        )
        row = cur.fetchone()
        return dict(row) if row else None


# ─── Analytics ────────────────────────────────────────────────────────────────

def get_dashboard_metrics() -> Dict:
    with get_cursor() as cur:
        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM customers) AS total_customers,
                (SELECT COUNT(*) FROM policies WHERE status = 'overdue') AS overdue_policies,
                (SELECT COUNT(*) FROM policies
                    WHERE due_date BETWEEN CURRENT_DATE AND CURRENT_DATE + 7
                    AND status = 'active') AS upcoming_due,
                (SELECT COUNT(*) FROM call_logs
                    WHERE DATE(initiated_at) = CURRENT_DATE) AS calls_today,
                (SELECT COUNT(*) FROM call_logs
                    WHERE outcome = 'paid') AS paid_calls,
                (SELECT COUNT(*) FROM call_logs
                    WHERE escalation_flag = TRUE) AS escalations,
                (SELECT COALESCE(SUM(premium_amount), 0)
                    FROM policies WHERE status = 'overdue') AS overdue_amount,
                (SELECT COUNT(*) FROM call_logs
                    WHERE outcome = 'promise_to_pay') AS promises
        """)
        row = cur.fetchone()
        return dict(row) if row else {}

def get_outcome_distribution() -> List[Dict]:
    with get_cursor() as cur:
        cur.execute(
            """SELECT outcome, COUNT(*) AS count
               FROM call_logs
               WHERE outcome IS NOT NULL
               GROUP BY outcome ORDER BY count DESC"""
        )
        return [dict(r) for r in cur.fetchall()]

def get_daily_call_volume(days: int = 14) -> List[Dict]:
    with get_cursor() as cur:
        cur.execute(
            f"""SELECT DATE(initiated_at) AS call_date,
                      COUNT(*) AS total,
                      SUM(CASE WHEN outcome='paid' THEN 1 ELSE 0 END) AS paid_count
               FROM call_logs
               WHERE initiated_at >= NOW() - INTERVAL '{days} days'
               GROUP BY call_date ORDER BY call_date"""
        )
        return [dict(r) for r in cur.fetchall()]

def can_call_customer(policy_id: int, manual_override: bool = False) -> tuple[bool, str]:
    policy = get_policy_by_id(policy_id)
    if not policy:
        return False, "Policy not found"
    if policy.get("do_not_call"):
        return False, "Customer is on Do Not Call list"
    if policy.get("ndnc_registered"):
        return False, "Customer is registered on NDNC (National Do Not Call)"
    if not policy.get("consent_given"):
        return False, "Customer has not given consent"
    if policy.get("call_count_today", 0) >= config.MAX_CALLS_PER_DAY:
        return False, f"Daily call limit ({config.MAX_CALLS_PER_DAY}) reached"
    if policy.get("call_count_week", 0) >= config.MAX_CALLS_PER_WEEK:
        return False, f"Weekly call limit ({config.MAX_CALLS_PER_WEEK}) reached"
    # Skip time window check if manually triggered by an agent
    if not manual_override:
        import pytz
        tz = pytz.timezone(config.APP_TIMEZONE)
        now_hour = datetime.now(tz).hour
        if not (config.CALL_WINDOW_START <= now_hour < config.CALL_WINDOW_END):
            return False, f"Outside TRAI calling window ({config.CALL_WINDOW_START}:00–{config.CALL_WINDOW_END}:00 IST)"
    return True, "OK"