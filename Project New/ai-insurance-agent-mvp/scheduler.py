import logging
from datetime import datetime, date
from typing import Optional

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from config import config
import database as db
import vapi_client as vapi
import ai_agent as agent

logger = logging.getLogger(__name__)

_scheduler: Optional[BackgroundScheduler] = None


def _is_within_call_window() -> bool:
    tz = pytz.timezone(config.APP_TIMEZONE)
    now_hour = datetime.now(tz).hour
    return config.CALL_WINDOW_START <= now_hour < config.CALL_WINDOW_END


def run_overdue_call_sweep():
    """Core job: identify overdue policies and initiate calls."""
    if not _is_within_call_window():
        logger.info("Outside calling window. Skipping sweep.")
        return

    if not config.VAPI_API_KEY:
        logger.warning("VAPI_API_KEY not set. Skipping sweep.")
        return

    overdue = db.get_overdue_policies()
    if not overdue:
        logger.info("No overdue policies eligible for calling.")
        return

    prioritized = []
    for policy in overdue:
        score, label = agent.calculate_priority_score(policy)
        prioritized.append({**policy, "priority_score": score, "priority_label": label})

    prioritized.sort(key=lambda x: x["priority_score"], reverse=True)
    logger.info("Sweep: %d eligible policies. Top priority: %s",
                len(prioritized),
                prioritized[0].get("policy_number") if prioritized else "none")

    MAX_PER_SWEEP = 10
    for policy in prioritized[:MAX_PER_SWEEP]:
        can_call, reason = db.can_call_customer(policy["id"])
        if not can_call:
            logger.debug("Skipping policy %s: %s", policy["policy_number"], reason)
            continue

        customer = db.get_customer_by_id(policy["customer_id"])
        if not customer:
            continue

        log_id = db.create_call_log({
            "policy_id": policy["id"],
            "customer_id": customer["id"],
            "vapi_call_id": None,
            "call_status": "initiating",
            "language_detected": customer.get("language_pref", "en"),
            "raw_vapi_payload": None,
        })

        result = vapi.initiate_call(customer, policy)

        if result["success"]:
            db.update_call_log(log_id, {
                "vapi_call_id": result["call_id"],
                "call_status": "initiated",
            })
            db.update_policy_call_info(policy["id"], date.today())
            logger.info("Call initiated for policy %s, VAPI ID: %s",
                        policy["policy_number"], result["call_id"])
        else:
            db.update_call_log(log_id, {
                "call_status": "failed",
                "error_message": result.get("error"),
            })
            logger.error("Call failed for policy %s: %s",
                         policy["policy_number"], result.get("error"))


def reset_daily_call_counts():
    """Reset per-day call counters at midnight."""
    with db.get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE policies SET call_count_today = 0;")
        conn.commit()
        cur.close()
    logger.info("Daily call counts reset.")


def reset_weekly_call_counts():
    """Reset per-week call counters every Monday."""
    with db.get_conn() as conn:
        cur = conn.cursor()
        cur.execute("UPDATE policies SET call_count_week = 0;")
        conn.commit()
        cur.close()
    logger.info("Weekly call counts reset.")


def sync_vapi_call_statuses():
    """Poll VAPI for pending call statuses and update DB."""
    if not config.VAPI_API_KEY:
        return
    try:
        recent = vapi.list_recent_calls(limit=20)
        for call in recent:
            cid = call.get("id")
            status = call.get("status", "")
            if cid:
                parsed = vapi.parse_webhook_payload(call)
                if parsed.get("call_status") == "completed" and parsed.get("transcript"):
                    import ai_agent as agent
                    classification = agent.classify_outcome(parsed["transcript"])
                    db.update_call_log_by_vapi_id(cid, {
                        "call_status": parsed["call_status"],
                        "outcome": parsed.get("outcome") or classification.get("outcome"),
                        "transcript": parsed.get("transcript"),
                        "summary": parsed.get("summary") or classification.get("summary"),
                        "duration_seconds": parsed.get("duration_seconds"),
                        "recording_url": parsed.get("recording_url"),
                        "escalation_flag": parsed.get("escalation_flag", False),
                        "language_detected": classification.get("language", "en"),
                        "intent_tags": classification.get("intent_tags", []),
                    })
    except Exception as e:
        logger.error("VAPI sync error: %s", e)


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler(timezone=pytz.timezone(config.APP_TIMEZONE))

        _scheduler.add_job(
            run_overdue_call_sweep,
            trigger=IntervalTrigger(minutes=30),
            id="overdue_sweep",
            name="Overdue Policy Call Sweep",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

        _scheduler.add_job(
            sync_vapi_call_statuses,
            trigger=IntervalTrigger(minutes=5),
            id="vapi_sync",
            name="VAPI Status Sync",
            replace_existing=True,
            max_instances=1,
        )

        _scheduler.add_job(
            reset_daily_call_counts,
            trigger=CronTrigger(hour=0, minute=1),
            id="daily_reset",
            name="Reset Daily Call Counts",
            replace_existing=True,
        )

        _scheduler.add_job(
            reset_weekly_call_counts,
            trigger=CronTrigger(day_of_week="mon", hour=0, minute=2),
            id="weekly_reset",
            name="Reset Weekly Call Counts",
            replace_existing=True,
        )

    return _scheduler


def start_scheduler():
    s = get_scheduler()
    if not s.running:
        s.start()
        logger.info("Scheduler started.")


def stop_scheduler():
    s = get_scheduler()
    if s.running:
        s.shutdown(wait=False)
        logger.info("Scheduler stopped.")
