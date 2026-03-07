import json
import logging
import time
from datetime import datetime, date, timedelta
from typing import Dict, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_autorefresh import st_autorefresh

import database as db
import vapi_client as vapi
import ai_agent as agent
import scheduler as sched
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="InsureCall AI — Payment Collection",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styling ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500&family=Inter:wght@300;400;500&display=swap');

  :root {
    --bg:       #0A0E1A;
    --surface:  #111827;
    --surface2: #1A2236;
    --border:   #1E2D40;
    --accent:   #F59E0B;
    --accent2:  #3B82F6;
    --danger:   #EF4444;
    --success:  #10B981;
    --warning:  #F59E0B;
    --text:     #E2E8F0;
    --muted:    #64748B;
  }

  html, body, .stApp { background: var(--bg) !important; color: var(--text); font-family: 'Inter', sans-serif; }

  .main .block-container { padding: 1.5rem 2.5rem 3rem; max-width: 1600px; }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border); }
  section[data-testid="stSidebar"] * { color: var(--text) !important; }

  /* Typography */
  h1, h2, h3 { font-family: 'Syne', sans-serif !important; letter-spacing: -0.02em; }
  .brand-title { font-family: 'Syne', sans-serif; font-size: 1.6rem; font-weight: 800;
    background: linear-gradient(135deg, #F59E0B, #3B82F6); -webkit-background-clip: text;
    -webkit-text-fill-color: transparent; background-clip: text; line-height: 1.2; }
  .brand-sub { font-size: 0.7rem; color: var(--muted); font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.15em; text-transform: uppercase; }

  /* Metric Cards */
  .metric-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 1.2rem 1.4rem; position: relative; overflow: hidden; }
  .metric-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg, var(--accent), var(--accent2)); }
  .metric-val { font-family: 'Syne', sans-serif; font-size: 2rem; font-weight: 700; line-height: 1; }
  .metric-lbl { font-size: 0.72rem; color: var(--muted); text-transform: uppercase;
    letter-spacing: 0.12em; margin-top: 0.3rem; }
  .metric-delta { font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; margin-top: 0.2rem; }

  /* Tables */
  .stDataFrame { border: 1px solid var(--border) !important; border-radius: 10px; overflow: hidden; }
  .stDataFrame thead th { background: var(--surface2) !important; color: var(--muted) !important;
    font-family: 'IBM Plex Mono', monospace !important; font-size: 0.7rem !important;
    text-transform: uppercase !important; letter-spacing: 0.1em !important; }
  .stDataFrame tbody tr:hover { background: rgba(59,130,246,0.06) !important; }
  .stDataFrame tbody td { color: var(--text) !important; font-size: 0.85rem !important; }

  /* Buttons */
  .stButton > button { background: var(--surface2); color: var(--text); border: 1px solid var(--border);
    border-radius: 8px; font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem;
    letter-spacing: 0.05em; transition: all 0.2s; }
  .stButton > button:hover { background: var(--accent); color: #000; border-color: var(--accent); }

  /* Call button */
  .call-btn > button { background: linear-gradient(135deg, #10B981, #059669) !important;
    color: #fff !important; border: none !important; font-weight: 600 !important; font-size: 0.85rem !important;
    border-radius: 8px !important; padding: 0.5rem 1.5rem !important; }
  .call-btn > button:hover { opacity: 0.9 !important; transform: translateY(-1px); }

  /* Danger button */
  .danger-btn > button { background: rgba(239,68,68,0.15) !important;
    color: var(--danger) !important; border-color: var(--danger) !important; }

  /* Inputs */
  .stTextInput input, .stNumberInput input, .stSelectbox div, .stDateInput input,
  .stTextArea textarea { background: var(--surface2) !important; color: var(--text) !important;
    border-color: var(--border) !important; border-radius: 8px !important; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { background: var(--surface); border-radius: 12px;
    border: 1px solid var(--border); padding: 4px; gap: 2px; }
  .stTabs [data-baseweb="tab"] { border-radius: 8px; color: var(--muted) !important;
    font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem; letter-spacing: 0.05em;
    padding: 0.5rem 1.2rem; border: none; background: transparent; }
  .stTabs [aria-selected="true"] { background: var(--surface2) !important;
    color: var(--accent) !important; }

  /* Status pills */
  .pill { display: inline-block; padding: 0.15rem 0.7rem; border-radius: 999px;
    font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem; font-weight: 500; letter-spacing: 0.08em; }
  .pill-critical { background: rgba(239,68,68,0.15); color: #EF4444; border: 1px solid rgba(239,68,68,0.3); }
  .pill-high     { background: rgba(245,158,11,0.15); color: #F59E0B; border: 1px solid rgba(245,158,11,0.3); }
  .pill-medium   { background: rgba(234,179,8,0.12);  color: #EAB308; border: 1px solid rgba(234,179,8,0.25); }
  .pill-low      { background: rgba(16,185,129,0.12); color: #10B981; border: 1px solid rgba(16,185,129,0.3); }
  .pill-paid     { background: rgba(16,185,129,0.15); color: #10B981; border: 1px solid rgba(16,185,129,0.3); }
  .pill-escalated{ background: rgba(239,68,68,0.15);  color: #EF4444; border: 1px solid rgba(239,68,68,0.3); }
  .pill-promise  { background: rgba(59,130,246,0.12); color: #60A5FA; border: 1px solid rgba(59,130,246,0.3); }
  .pill-unknown  { background: rgba(100,116,139,0.15);color: #94A3B8; border: 1px solid rgba(100,116,139,0.3); }

  /* Expandable log card */
  .log-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 1rem 1.2rem; margin-bottom: 0.6rem; transition: border-color 0.2s; }
  .log-card:hover { border-color: var(--accent2); }
  .log-title { font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 600; }
  .log-meta { font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem; color: var(--muted); }

  /* Policy detail card */
  .policy-card { background: var(--surface); border-left: 4px solid var(--accent);
    border-radius: 0 10px 10px 0; padding: 1rem 1.2rem; margin-bottom: 0.6rem; }

  /* Section headers */
  .section-header { font-family: 'Syne', sans-serif; font-size: 1.1rem; font-weight: 700;
    color: var(--text); border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;
    margin-bottom: 1rem; }

  /* Alert boxes */
  .alert-info { background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.25);
    border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.83rem; color: #93C5FD; }
  .alert-warn { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25);
    border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.83rem; color: #FCD34D; }
  .alert-success { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.25);
    border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.83rem; color: #6EE7B7; }
  .alert-danger { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.25);
    border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.83rem; color: #FCA5A5; }

  /* Divider */
  hr { border-color: var(--border) !important; }

  /* Scrollbar */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: var(--bg); }
  ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: var(--muted); }
</style>
""", unsafe_allow_html=True)


# ─── Session State Init ────────────────────────────────────────────────────────
def init_session():
    defaults = {
        "db_ready": False,
        "scheduler_running": False,
        "selected_policy_id": None,
        "selected_log_id": None,
        "call_result_msg": None,
        "active_tab": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()


# ─── DB Init ──────────────────────────────────────────────────────────────────
@st.cache_resource
def setup_database():
    try:
        db.init_db()
        db.seed_demo_data()
        return True
    except Exception as e:
        return str(e)

db_status = setup_database()
if db_status is True:
    st.session_state.db_ready = True
else:
    st.error(f"⚠️ Database connection failed: {db_status}")
    st.info("Ensure PostgreSQL is running and DATABASE_URL is set in .env")
    st.stop()


# ─── Scheduler ────────────────────────────────────────────────────────────────
@st.cache_resource
def start_bg_scheduler():
    try:
        sched.start_scheduler()
        return True
    except Exception as e:
        logger.warning("Scheduler start failed: %s", e)
        return False

start_bg_scheduler()


# ─── Auto-refresh every 60s ───────────────────────────────────────────────────
st_autorefresh(interval=60_000, key="dashboard_refresh")


# ─── Helpers ──────────────────────────────────────────────────────────────────
def outcome_pill(outcome: str) -> str:
    m = {
        "paid":               ("pill-paid",     "✓ Paid"),
        "promise_to_pay":     ("pill-promise",  "⏰ Promise"),
        "callback_requested": ("pill-promise",  "📞 Callback"),
        "unreachable":        ("pill-unknown",  "○ Unreachable"),
        "voicemail":          ("pill-unknown",  "✉ Voicemail"),
        "escalated":          ("pill-escalated","↑ Escalated"),
        "disputed":           ("pill-escalated","⚠ Disputed"),
        "do_not_call":        ("pill-high",     "⊘ DNC"),
    }
    cls, label = m.get(outcome or "", ("pill-unknown", outcome or "—"))
    return f'<span class="pill {cls}">{label}</span>'

def priority_pill(label: str) -> str:
    cls = f"pill-{label}"
    icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "upcoming": "🔵"}
    return f'<span class="pill {cls}">{icons.get(label,"")} {label.upper()}</span>'

def fmt_currency_inr(val) -> str:
    try:
        return f"₹{float(val):,.2f}"
    except Exception:
        return "—"

def fmt_dt(val) -> str:
    if val is None:
        return "—"
    if isinstance(val, datetime):
        return val.strftime("%b %d, %Y %H:%M")
    if isinstance(val, date):
        return val.strftime("%b %d, %Y")
    return str(val)

def days_overdue_badge(days) -> str:
    try:
        d = int(days)
    except Exception:
        return "—"
    if d < 0:
        return f'<span style="color:#60A5FA">Due in {abs(d)}d</span>'
    elif d == 0:
        return '<span style="color:#F59E0B">Due today</span>'
    elif d <= 7:
        return f'<span style="color:#F59E0B">+{d}d overdue</span>'
    elif d <= 30:
        return f'<span style="color:#FB923C">+{d}d overdue</span>'
    else:
        return f'<span style="color:#EF4444">+{d}d overdue</span>'


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="brand-title">InsureCall AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">Payment Collection Agent</div>', unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### ⚙️ System Status")

    db_ok = st.session_state.db_ready
    sched_ok = sched.get_scheduler().running if sched._scheduler else False

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f'<div style="font-size:0.78rem; padding:0.4rem 0.7rem; border-radius:6px; '
            f'background:{"rgba(16,185,129,0.12)" if db_ok else "rgba(239,68,68,0.12)"}; '
            f'color:{"#10B981" if db_ok else "#EF4444"}; text-align:center;">DB {"● Live" if db_ok else "✕ Error"}</div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<div style="font-size:0.78rem; padding:0.4rem 0.7rem; border-radius:6px; '
            f'background:{"rgba(16,185,129,0.12)" if sched_ok else "rgba(100,116,139,0.12)"}; '
            f'color:{"#10B981" if sched_ok else "#94A3B8"}; text-align:center;">Sched {"● On" if sched_ok else "○ Off"}</div>',
            unsafe_allow_html=True
        )

    vapi_ok = bool(config.VAPI_API_KEY)
    ai_ok = bool(config.ANTHROPIC_API_KEY)
    col3, col4 = st.columns(2)
    with col3:
        st.markdown(
            f'<div style="font-size:0.78rem; padding:0.4rem 0.7rem; border-radius:6px; margin-top:4px;'
            f'background:{"rgba(16,185,129,0.12)" if vapi_ok else "rgba(245,158,11,0.12)"}; '
            f'color:{"#10B981" if vapi_ok else "#F59E0B"}; text-align:center;">VAPI {"● On" if vapi_ok else "⚠ Key?"}</div>',
            unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f'<div style="font-size:0.78rem; padding:0.4rem 0.7rem; border-radius:6px; margin-top:4px;'
            f'background:{"rgba(16,185,129,0.12)" if ai_ok else "rgba(245,158,11,0.12)"}; '
            f'color:{"#10B981" if ai_ok else "#F59E0B"}; text-align:center;">AI {"● On" if ai_ok else "⚠ Key?"}</div>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    st.markdown("### 🕐 Call Window")
    tz_label = config.APP_TIMEZONE
    st.markdown(
        f'<div class="alert-info">Calls allowed: {config.CALL_WINDOW_START}:00–{config.CALL_WINDOW_END}:00<br>'
        f'Zone: {tz_label}<br>'
        f'Max/day: {config.MAX_CALLS_PER_DAY} · Max/week: {config.MAX_CALLS_PER_WEEK}</div>',
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown("### 🚀 Manual Sweep")
    if st.button("▶ Run Call Sweep Now", width='stretch'):
        with st.spinner("Running sweep..."):
            try:
                sched.run_overdue_call_sweep()
                st.success("Sweep completed.")
            except Exception as e:
                st.error(f"Sweep error: {e}")

    if st.button("↺ Sync VAPI Statuses", width='stretch'):
        with st.spinner("Syncing..."):
            try:
                sched.sync_vapi_call_statuses()
                st.success("Synced.")
            except Exception as e:
                st.error(f"Sync error: {e}")

    st.markdown("---")
    st.markdown(
        f'<div style="font-size:0.68rem; color:#334155; text-align:center; font-family:IBM Plex Mono,monospace;">'
        f'{config.COMPANY_NAME}<br>{config.COMPANY_PHONE}</div>',
        unsafe_allow_html=True
    )


# ─── Main Header ──────────────────────────────────────────────────────────────
st.markdown(
    '<h1 style="font-family:Syne,sans-serif; font-size:2rem; font-weight:800; margin-bottom:0.2rem;">'
    '📞 InsureCall AI <span style="color:#F59E0B;">Payment Collection</span></h1>',
    unsafe_allow_html=True
)
st.markdown(
    '<p style="color:#64748B; font-family:IBM Plex Mono,monospace; font-size:0.75rem; '
    'letter-spacing:0.1em; margin-bottom:1.5rem;">AUTOMATED OUTBOUND VOICE AGENT · TRAI COMPLIANT · INDIA</p>',
    unsafe_allow_html=True
)


# ─── Dashboard Metrics ────────────────────────────────────────────────────────
metrics = db.get_dashboard_metrics()

mc1, mc2, mc3, mc4, mc5, mc6 = st.columns(6)
def metric_card(col, val, label, delta=None, delta_color="#10B981"):
    with col:
        st.markdown(
            f'<div class="metric-card">'
            f'<div class="metric-val">{val}</div>'
            f'<div class="metric-lbl">{label}</div>'
            f'{"" if delta is None else f"<div class=metric-delta style=color:{delta_color}>{delta}</div>"}'
            f'</div>',
            unsafe_allow_html=True
        )

metric_card(mc1, metrics.get("overdue_policies", 0), "Overdue Policies", "Needs attention", "#EF4444")
metric_card(mc2, fmt_currency_inr(metrics.get("overdue_amount", 0)), "Overdue Amount", "Total at risk", "#F59E0B")
metric_card(mc3, metrics.get("calls_today", 0), "Calls Today", "24h period")
metric_card(mc4, metrics.get("paid_calls", 0), "Paid Outcomes", "All-time")
metric_card(mc5, metrics.get("promises", 0), "Promise-to-Pay", "Pending")
metric_card(mc6, metrics.get("escalations", 0), "Escalations", "Human review", "#EF4444")

st.markdown("<br>", unsafe_allow_html=True)


# ─── Charts Row ───────────────────────────────────────────────────────────────
chart1, chart2 = st.columns([3, 2])

with chart1:
    daily = db.get_daily_call_volume(14)
    if daily:
        df_daily = pd.DataFrame(daily)
        df_daily["call_date"] = pd.to_datetime(df_daily["call_date"])
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=df_daily["call_date"], y=df_daily["total"],
            name="Total Calls", marker_color="rgba(59,130,246,0.6)",
        ))
        fig.add_trace(go.Bar(
            x=df_daily["call_date"], y=df_daily["paid_count"],
            name="Paid", marker_color="rgba(16,185,129,0.8)",
        ))
        fig.update_layout(
            title=dict(text="Call Volume (14 days)", font=dict(family="Syne", size=14, color="#E2E8F0")),
            paper_bgcolor="#111827", plot_bgcolor="#111827",
            barmode="overlay",
            xaxis=dict(gridcolor="#1E2D40", color="#64748B"),
            yaxis=dict(gridcolor="#1E2D40", color="#64748B"),
            legend=dict(font=dict(color="#94A3B8"), bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=0, r=0, t=40, b=0), height=220,
        )
        st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
    else:
        st.markdown('<div class="alert-info">No call volume data yet.</div>', unsafe_allow_html=True)

with chart2:
    dist = db.get_outcome_distribution()
    if dist:
        df_dist = pd.DataFrame(dist)
        color_map = {
            "paid": "#10B981", "promise_to_pay": "#60A5FA", "callback_requested": "#818CF8",
            "unreachable": "#94A3B8", "voicemail": "#64748B", "escalated": "#EF4444",
            "disputed": "#FB923C", "do_not_call": "#F43F5E",
        }
        colors = [color_map.get(o, "#64748B") for o in df_dist["outcome"]]
        fig2 = go.Figure(go.Pie(
            labels=df_dist["outcome"].str.replace("_", " ").str.title(),
            values=df_dist["count"],
            hole=0.55,
            marker=dict(colors=colors, line=dict(color="#0A0E1A", width=2)),
            textfont=dict(family="IBM Plex Mono", size=10, color="#E2E8F0"),
        ))
        fig2.update_layout(
            title=dict(text="Outcome Distribution", font=dict(family="Syne", size=14, color="#E2E8F0")),
            paper_bgcolor="#111827", plot_bgcolor="#111827",
            legend=dict(font=dict(color="#94A3B8", family="IBM Plex Mono", size=10), bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=0, r=0, t=40, b=0), height=220,
            showlegend=True,
        )
        st.plotly_chart(fig2, width='stretch', config={"displayModeBar": False})
    else:
        st.markdown('<div class="alert-info">No outcome data yet.</div>', unsafe_allow_html=True)

st.markdown("---")


# ─── Main Tabs ────────────────────────────────────────────────────────────────
tab_logs, tab_overdue, tab_customers, tab_policies, tab_settings = st.tabs([
    "📋  Call Logs",
    "⚠️  Overdue Policies",
    "👤  Customers",
    "📄  Policies",
    "⚙️  Settings",
])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1: CALL LOGS
# ════════════════════════════════════════════════════════════════════════════════
with tab_logs:
    st.markdown('<div class="section-header">📋 Outbound Call Logs</div>', unsafe_allow_html=True)

    fl1, fl2, fl3 = st.columns([2, 2, 1])
    with fl1:
        log_outcome_filter = st.selectbox(
            "Filter by Outcome",
            ["all"] + config.CALL_OUTCOMES,
            format_func=lambda x: "All Outcomes" if x == "all" else x.replace("_", " ").title(),
            key="log_outcome_filter",
        )
    with fl2:
        log_search = st.text_input("Search customer / policy", placeholder="Name or policy number…", key="log_search")
    with fl3:
        log_limit = st.selectbox("Show", [50, 100, 200, 500], key="log_limit")

    logs = db.get_call_logs(limit=log_limit, outcome_filter=log_outcome_filter)

    if log_search:
        logs = [l for l in logs if
                log_search.lower() in (l.get("full_name") or "").lower() or
                log_search.lower() in (l.get("policy_number") or "").lower()]

    st.markdown(f'<div class="alert-info">Showing <b>{len(logs)}</b> call records</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    if not logs:
        st.markdown('<div class="alert-warn">No call logs found matching the filter.</div>', unsafe_allow_html=True)
    else:
        # Table view
        df_logs = pd.DataFrame([{
            "ID":          l["id"],
            "Customer":    l.get("full_name", "—"),
            "Phone":       l.get("phone", "—"),
            "Policy":      l.get("policy_number", "—"),
            "Amount":      fmt_currency_inr(l.get("premium_amount")),
            "Initiated":   fmt_dt(l.get("initiated_at")),
            "Duration":    f"{l.get('duration_seconds') or 0}s",
            "Status":      (l.get("call_status") or "—").replace("_", " ").title(),
            "Outcome":     (l.get("outcome") or "—").replace("_", " ").title(),
            "Escalated":   "Yes" if l.get("escalation_flag") else "No",
            "Language":    (l.get("language_detected") or "en").upper(),
        } for l in logs])

        st.dataframe(
            df_logs,
            width='stretch',
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(width="small"),
                "Escalated": st.column_config.TextColumn(width="small"),
            }
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-header">🔍 Log Detail Viewer</div>', unsafe_allow_html=True)

        log_ids = [l["id"] for l in logs]
        selected_log_id = st.selectbox(
            "Select a call log to inspect",
            log_ids,
            format_func=lambda lid: next(
                (f"#{l['id']} · {l.get('full_name','?')} · {fmt_dt(l.get('initiated_at'))} · {(l.get('outcome') or 'pending').replace('_',' ').title()}"
                 for l in logs if l["id"] == lid), str(lid)
            ),
            key="log_detail_select"
        )

        if selected_log_id:
            log = next((l for l in logs if l["id"] == selected_log_id), None)
            if log:
                d1, d2, d3 = st.columns(3)
                with d1:
                    st.markdown(
                        f'<div class="metric-card">'
                        f'<div class="metric-val" style="font-size:1.2rem;">{log.get("full_name","—")}</div>'
                        f'<div class="metric-lbl">Customer</div>'
                        f'<div class="metric-delta" style="color:#94A3B8">{log.get("phone","—")}</div>'
                        f'</div>', unsafe_allow_html=True
                    )
                with d2:
                    st.markdown(
                        f'<div class="metric-card">'
                        f'<div class="metric-val" style="font-size:1.2rem;">{log.get("policy_number","—")}</div>'
                        f'<div class="metric-lbl">Policy Number</div>'
                        f'<div class="metric-delta" style="color:#94A3B8">{fmt_currency_inr(log.get("premium_amount"))}</div>'
                        f'</div>', unsafe_allow_html=True
                    )
                with d3:
                    st.markdown(
                        f'<div class="metric-card">'
                        f'<div class="metric-val" style="font-size:1.1rem;">{outcome_pill(log.get("outcome",""))}</div>'
                        f'<div class="metric-lbl">Outcome</div>'
                        f'<div class="metric-delta" style="color:#{"EF4444" if log.get("escalation_flag") else "94A3B8"}">{"🚨 Escalated" if log.get("escalation_flag") else "No escalation"}</div>'
                        f'</div>', unsafe_allow_html=True
                    )

                st.markdown("<br>", unsafe_allow_html=True)
                col_a, col_b = st.columns([1, 1])
                with col_a:
                    st.markdown("**📝 AI Summary**")
                    st.markdown(
                        f'<div style="background:#1A2236; border:1px solid #1E2D40; border-radius:8px; '
                        f'padding:1rem; font-size:0.85rem; line-height:1.6; color:#CBD5E1; min-height:80px;">'
                        f'{log.get("summary") or "<span style=color:#4B5563>No summary available yet.</span>"}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                with col_b:
                    st.markdown("**📞 Call Details**")
                    details = {
                        "VAPI Call ID": log.get("vapi_call_id") or "—",
                        "Initiated":    fmt_dt(log.get("initiated_at")),
                        "Ended":        fmt_dt(log.get("ended_at")),
                        "Duration":     f"{log.get('duration_seconds') or 0}s",
                        "Language":     (log.get("language_detected") or "en").upper(),
                        "Callback DT":  fmt_dt(log.get("callback_dt")),
                        "Promise Date": fmt_dt(log.get("promise_date")),
                        "Escalation":   log.get("escalation_reason") or "—",
                    }
                    for k, v in details.items():
                        st.markdown(
                            f'<div style="display:flex; justify-content:space-between; padding:0.25rem 0; '
                            f'border-bottom:1px solid #1E2D40; font-size:0.8rem;">'
                            f'<span style="color:#64748B; font-family:IBM Plex Mono,monospace">{k}</span>'
                            f'<span style="color:#CBD5E1">{v}</span></div>',
                            unsafe_allow_html=True
                        )

                if log.get("transcript"):
                    with st.expander("📃 Full Transcript"):
                        st.markdown(
                            f'<div style="background:#0D1117; border:1px solid #1E2D40; border-radius:8px; '
                            f'padding:1rem; font-family:IBM Plex Mono,monospace; font-size:0.78rem; '
                            f'white-space:pre-wrap; color:#94A3B8; max-height:300px; overflow-y:auto;">'
                            f'{log["transcript"]}</div>',
                            unsafe_allow_html=True
                        )

                if log.get("recording_url"):
                    st.markdown(f"🎵 [Listen to Recording]({log['recording_url']})")

                # ── Sync from VAPI button (always visible if vapi_call_id exists) ──
                vapi_call_id = log.get("vapi_call_id")
                if vapi_call_id:
                    sync_col1, sync_col2 = st.columns([1, 3])
                    with sync_col1:
                        if st.button("🔄 Sync from VAPI", key=f"sync_{log['id']}"):
                            with st.spinner("Fetching call data from VAPI..."):
                                try:
                                    import requests as req
                                    resp = req.get(
                                        f"https://api.vapi.ai/call/{vapi_call_id}",
                                        headers={"Authorization": f"Bearer {config.VAPI_API_KEY}"},
                                        timeout=10
                                    )
                                    if resp.status_code == 200:
                                        call_data = resp.json()
                                        transcript = call_data.get("transcript", "") or ""
                                        artifact = call_data.get("artifact", {}) or {}
                                        recording_url = artifact.get("recordingUrl", "") or call_data.get("recordingUrl", "")
                                        duration = call_data.get("endedAt") and call_data.get("startedAt") and None
                                        ended_at = call_data.get("endedAt")
                                        started_at = call_data.get("startedAt")
                                        ended_reason = call_data.get("endedReason", "")

                                        update_data = {
                                            "call_status": "completed",
                                            "transcript": transcript,
                                            "recording_url": recording_url,
                                        }
                                        if ended_at:
                                            update_data["ended_at"] = ended_at
                                        if recording_url:
                                            update_data["recording_url"] = recording_url

                                        # Calculate duration
                                        if started_at and ended_at:
                                            from datetime import datetime as dt
                                            try:
                                                s = dt.fromisoformat(started_at.replace("Z", "+00:00"))
                                                e = dt.fromisoformat(ended_at.replace("Z", "+00:00"))
                                                update_data["duration_seconds"] = int((e - s).total_seconds())
                                            except Exception:
                                                pass

                                        db.update_call_log(log["id"], update_data)

                                        # Auto-run AI classification if transcript available
                                        if transcript.strip() and config.ANTHROPIC_API_KEY:
                                            try:
                                                classification = agent.classify_outcome(transcript)
                                                db.update_call_log(log["id"], {
                                                    "summary": classification.get("summary", ""),
                                                    "outcome": classification.get("outcome") or log.get("outcome"),
                                                    "language_detected": classification.get("language", "en"),
                                                    "intent_tags": classification.get("intent_tags", []),
                                                })
                                                st.success("✅ Synced and AI summary generated!")
                                            except Exception:
                                                st.success("✅ Synced from VAPI! (Add Anthropic API key for AI summary)")
                                        else:
                                            st.success("✅ Synced from VAPI!")
                                    else:
                                        st.error(f"VAPI API returned {resp.status_code}: {resp.text[:200]}")
                                except Exception as e:
                                    st.error(f"Sync failed: {e}")
                            st.rerun()
                    with sync_col2:
                        st.caption(f"VAPI Call ID: `{vapi_call_id[:30]}...`")

                if not log.get("summary"):
                    transcript = log.get("transcript") or ""
                    if transcript.strip():
                        if not config.GEMINI_API_KEY:
                            st.warning("⚠️ GEMINI_API_KEY not set in .env — AI summary unavailable.")
                        else:
                            if st.button("🤖 Generate AI Summary", key=f"gen_sum_{log['id']}"):
                                with st.spinner("Analysing transcript with Claude AI..."):
                                    try:
                                        classification = agent.classify_outcome(transcript)
                                        db.update_call_log(log["id"], {
                                            "summary": classification.get("summary", ""),
                                            "outcome": classification.get("outcome") or log.get("outcome"),
                                            "language_detected": classification.get("language", "en"),
                                            "intent_tags": classification.get("intent_tags", []),
                                        })
                                        st.success("✅ AI Summary saved!")
                                    except Exception as e:
                                        st.error(f"AI summary failed: {str(e)}")
                                        st.caption("Check that your ANTHROPIC_API_KEY is valid and has credits.")
                                st.rerun()
                    else:
                        st.caption("⏳ Transcript not yet received. Click 🔄 Sync from VAPI above.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2: OVERDUE POLICIES
# ════════════════════════════════════════════════════════════════════════════════
with tab_overdue:
    st.markdown('<div class="section-header">⚠️ Overdue & Upcoming Policies</div>', unsafe_allow_html=True)

    op_col1, op_col2 = st.columns([3, 1])
    with op_col1:
        op_search = st.text_input("Search by name or policy number", key="op_search", placeholder="Search…")
    with op_col2:
        show_upcoming = st.checkbox("Include upcoming (7 days)", value=True, key="show_upcoming")

    overdue = db.get_overdue_policies()

    if not show_upcoming:
        overdue = [p for p in overdue if (p.get("days_overdue") or 0) >= 0]

    if op_search:
        overdue = [p for p in overdue if
                   op_search.lower() in (p.get("full_name") or "").lower() or
                   op_search.lower() in (p.get("policy_number") or "").lower()]

    scored = []
    for p in overdue:
        score, label = agent.calculate_priority_score(p)
        scored.append({**p, "priority_score": score, "priority_label": label})
    scored.sort(key=lambda x: x["priority_score"], reverse=True)

    critical_count = sum(1 for p in scored if p["priority_label"] == "critical")
    high_count = sum(1 for p in scored if p["priority_label"] == "high")

    if critical_count > 0:
        st.markdown(
            f'<div class="alert-danger">🚨 <b>{critical_count} critical</b> policies with 30+ days overdue require immediate attention.</div>',
            unsafe_allow_html=True
        )
    if high_count > 0:
        st.markdown(
            f'<div class="alert-warn" style="margin-top:6px;">⚠️ <b>{high_count} high-priority</b> policies are 15-30 days overdue.</div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    if not scored:
        st.markdown('<div class="alert-success">✅ No overdue policies found. All premiums are current!</div>', unsafe_allow_html=True)
    else:
        for policy in scored:
            pid = policy["id"]
            score, label = policy["priority_score"], policy["priority_label"]
            days_ov = policy.get("days_overdue", 0) or 0
            can_call, reason = db.can_call_customer(pid, manual_override=True)

            border_color = agent.get_priority_color(label)

            with st.container():
                st.markdown(
                    f'<div class="policy-card" style="border-left-color:{border_color};">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center;">'
                    f'<span class="log-title">{policy.get("full_name","—")} &nbsp;·&nbsp; '
                    f'<span style="font-family:IBM Plex Mono,monospace; font-size:0.8rem; color:#64748B">'
                    f'{policy.get("policy_number","—")}</span></span>'
                    f'{priority_pill(label)}</div>'
                    f'<div style="display:flex; gap:2rem; margin-top:0.5rem; flex-wrap:wrap;">'
                    f'<span style="font-size:0.8rem; color:#94A3B8">📋 {policy.get("policy_type","—")}</span>'
                    f'<span style="font-size:0.8rem; color:#F59E0B">💰 {fmt_currency_inr(policy.get("premium_amount"))}</span>'
                    f'<span style="font-size:0.8rem;">{days_overdue_badge(days_ov)}</span>'
                    f'<span style="font-size:0.8rem; color:#94A3B8">📞 {policy.get("phone","—")}</span>'
                    f'<span style="font-size:0.8rem; color:#94A3B8">🌐 {config.SUPPORTED_LANGUAGES.get(policy.get("language_pref","en"),"English")}</span>'
                    f'<span style="font-size:0.8rem; color:#64748B">Last called: {fmt_dt(policy.get("last_call_date"))}</span>'
                    f'</div></div>',
                    unsafe_allow_html=True
                )

                btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1.5, 1, 1, 3])

                with btn_col1:
                    if can_call:
                        st.markdown('<div class="call-btn">', unsafe_allow_html=True)
                        if st.button(f"📞 Call Now", key=f"call_{pid}"):
                            with st.spinner(f"Initiating call to {policy.get('full_name')}..."):
                                # manual_override=True allows agents to call outside window
                                can_call_now, reason_now = db.can_call_customer(pid, manual_override=True)
                                if not can_call_now:
                                    st.error(f"Cannot call: {reason_now}")
                                else:
                                    pass
                            with st.spinner(f"Initiating call to {policy.get('full_name')}..."):
                                customer = db.get_customer_by_id(policy["customer_id"])
                                result = vapi.initiate_call(customer, policy)
                                if result["success"]:
                                    log_id = db.create_call_log({
                                        "policy_id": pid,
                                        "customer_id": policy["customer_id"],
                                        "vapi_call_id": result["call_id"],
                                        "call_status": "initiated",
                                        "language_detected": customer.get("language_pref", "en"),
                                        "raw_vapi_payload": json.dumps(result.get("raw", {})) if result.get("raw") else None,
                                    })
                                    db.update_policy_call_info(pid, date.today())
                                    st.success(f"✅ Call initiated! VAPI ID: {result['call_id']}")
                                else:
                                    st.error(f"❌ Call failed: {result.get('error')}")
                        st.markdown('</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(
                            f'<div class="alert-warn" style="font-size:0.72rem; padding:0.4rem 0.6rem; margin:0;">'
                            f'⊘ {reason}</div>',
                            unsafe_allow_html=True
                        )

                with btn_col2:
                    if st.button("📜 Script", key=f"script_btn_{pid}"):
                        customer = db.get_customer_by_id(policy["customer_id"])
                        script = agent.generate_call_script(customer, policy)
                        st.session_state[f"script_data_{pid}"] = script

                with btn_col3:
                    with st.expander("📊 History"):
                        hist = db.get_call_logs(limit=5, policy_id=pid)
                        if hist:
                            for h in hist:
                                st.markdown(
                                    f'<div style="font-size:0.75rem; padding:0.2rem 0; border-bottom:1px solid #1E2D40;">'
                                    f'{fmt_dt(h.get("initiated_at"))} · {outcome_pill(h.get("outcome",""))}</div>',
                                    unsafe_allow_html=True
                                )
                        else:
                            st.markdown('<span style="font-size:0.75rem; color:#64748B">No calls yet</span>', unsafe_allow_html=True)

                if st.session_state.get(f"script_data_{pid}"):
                    with st.expander(f"📜 Call Script — {policy.get('policy_number')}", expanded=True):
                        st.markdown(
                            f'<div style="background:#0D1117; border:1px solid #1E2D40; border-radius:8px; '
                            f'padding:1rem; font-size:0.8rem; white-space:pre-wrap; color:#94A3B8;">'
                            f'{st.session_state[f"script_data_{pid}"]}</div>',
                            unsafe_allow_html=True
                        )

        # Bulk action
        st.markdown("---")
        st.markdown("**⚡ Bulk Actions**")
        bulk_col1, bulk_col2 = st.columns([2, 4])
        with bulk_col1:
            if st.button("📞 Initiate All Eligible Calls", width='stretch', key="bulk_call"):
                eligible = [p for p in scored if db.can_call_customer(p["id"])[0]]
                if not eligible:
                    st.warning("No eligible policies for calling right now.")
                else:
                    with st.spinner(f"Queuing {len(eligible)} calls..."):
                        sched.run_overdue_call_sweep()
                    st.success(f"Sweep queued {len(eligible)} calls.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3: CUSTOMERS
# ════════════════════════════════════════════════════════════════════════════════
with tab_customers:
    st.markdown('<div class="section-header">👤 Customer Management</div>', unsafe_allow_html=True)

    cust_action = st.radio(
        "Action",
        ["View / Search", "Add New Customer", "Edit Customer"],
        horizontal=True,
        key="cust_action"
    )

    if cust_action == "View / Search":
        cust_search = st.text_input("Search customers", placeholder="Name, phone, or email…", key="cust_search")
        customers = db.get_all_customers(search=cust_search)
        st.markdown(f'<div class="alert-info">Found <b>{len(customers)}</b> customers</div>', unsafe_allow_html=True)
        if customers:
            df_c = pd.DataFrame([{
                "ID":       c["id"],
                "Name":     c.get("full_name", "—"),
                "Phone":    c.get("phone", "—"),
                "Email":    c.get("email", "—"),
                "Language": config.SUPPORTED_LANGUAGES.get(c.get("language_pref","en"), "English"),
                "Consent":  "✓" if c.get("consent_given") else "✗",
                "DNC":      "🚫" if c.get("do_not_call") else "—",
                "City":     c.get("city", "—"),
                "State":    c.get("state", "—"),
                "Created":  fmt_dt(c.get("created_at")),
            } for c in customers])
            st.dataframe(df_c, width='stretch', hide_index=True)

    elif cust_action == "Add New Customer":
        st.markdown("##### ➕ Add New Customer")
        with st.form("add_customer_form"):
            fc1, fc2 = st.columns(2)
            with fc1:
                cn_name  = st.text_input("Full Name *", key="cn_name")
                cn_phone = st.text_input("Phone (Indian mobile) *", placeholder="+919876543210", key="cn_phone")
                cn_email = st.text_input("Email", key="cn_email")
                cn_lang  = st.selectbox("Language Preference", list(config.SUPPORTED_LANGUAGES.keys()),
                                         format_func=lambda x: config.SUPPORTED_LANGUAGES[x], key="cn_lang")
            with fc2:
                cn_address = st.text_input("Address", key="cn_address")
                cn_city    = st.text_input("City", key="cn_city")
                cn_state   = st.selectbox("State", config.INDIAN_STATES, key="cn_state")
                cn_pincode = st.text_input("Pincode", placeholder="400001", key="cn_pincode")
            fc3, fc4, fc5 = st.columns(3)
            with fc3:
                cn_consent = st.checkbox("Consent Given", value=True, key="cn_consent")
            with fc4:
                cn_dnc = st.checkbox("Do Not Call", value=False, key="cn_dnc")
            with fc5:
                cn_ndnc = st.checkbox("NDNC Registered", value=False, key="cn_ndnc")
            cn_notes = st.text_area("Notes", key="cn_notes", height=80)

            submitted = st.form_submit_button("💾 Save Customer", width='stretch')
            if submitted:
                if not cn_name or not cn_phone:
                    st.error("Name and phone are required.")
                elif not cn_phone.startswith("+91"):
                    st.error("Phone must be an Indian number starting with +91")
                else:
                    try:
                        new_id = db.create_customer({
                            "full_name": cn_name, "phone": cn_phone, "email": cn_email,
                            "language_pref": cn_lang, "consent_given": cn_consent,
                            "do_not_call": cn_dnc, "ndnc_registered": cn_ndnc,
                            "address": cn_address, "city": cn_city,
                            "state": cn_state, "pincode": cn_pincode,
                            "country": "India", "notes": cn_notes,
                        })
                        st.success(f"✅ Customer created with ID {new_id}")
                    except Exception as e:
                        st.error(f"Error: {e}")

    else:  # Edit Customer
        customers = db.get_all_customers()
        if not customers:
            st.info("No customers found.")
        else:
            sel_cust = st.selectbox(
                "Select Customer to Edit",
                [c["id"] for c in customers],
                format_func=lambda cid: next(
                    (f"#{c['id']} · {c['full_name']} · {c['phone']}" for c in customers if c["id"] == cid), str(cid)
                ),
                key="edit_cust_sel"
            )
            cust = db.get_customer_by_id(sel_cust)
            if cust:
                st.markdown(f"##### ✏️ Editing: {cust['full_name']}")
                with st.form("edit_customer_form"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        ec_name  = st.text_input("Full Name *", value=cust.get("full_name",""), key="ec_name")
                        ec_phone = st.text_input("Phone (Indian mobile) *", value=cust.get("phone",""), key="ec_phone")
                        ec_email = st.text_input("Email", value=cust.get("email") or "", key="ec_email")
                        lang_keys = list(config.SUPPORTED_LANGUAGES.keys())
                        lang_idx = lang_keys.index(cust.get("language_pref","hi")) if cust.get("language_pref","hi") in lang_keys else 0
                        ec_lang = st.selectbox("Language", lang_keys, index=lang_idx,
                                               format_func=lambda x: config.SUPPORTED_LANGUAGES[x], key="ec_lang")
                    with ec2:
                        ec_address = st.text_input("Address", value=cust.get("address") or "", key="ec_address")
                        ec_city    = st.text_input("City", value=cust.get("city") or "", key="ec_city")
                        ec_state   = st.selectbox("State", config.INDIAN_STATES,
                                        index=config.INDIAN_STATES.index(cust.get("state")) if cust.get("state") in config.INDIAN_STATES else 0,
                                        key="ec_state")
                        ec_pincode = st.text_input("Pincode", value=cust.get("pincode") or "", key="ec_pincode")
                    ec3, ec4, ec5 = st.columns(3)
                    with ec3:
                        ec_consent = st.checkbox("Consent Given", value=bool(cust.get("consent_given")), key="ec_consent")
                    with ec4:
                        ec_dnc = st.checkbox("Do Not Call", value=bool(cust.get("do_not_call")), key="ec_dnc")
                    with ec5:
                        ec_ndnc = st.checkbox("NDNC Registered", value=bool(cust.get("ndnc_registered")), key="ec_ndnc")
                    ec_notes = st.text_area("Notes", value=cust.get("notes") or "", key="ec_notes", height=80)

                    sc1, sc2 = st.columns([3, 1])
                    with sc1:
                        if st.form_submit_button("💾 Update Customer", width='stretch'):
                            ok = db.update_customer(sel_cust, {
                                "full_name": ec_name, "phone": ec_phone, "email": ec_email,
                                "language_pref": ec_lang, "consent_given": ec_consent,
                                "do_not_call": ec_dnc, "ndnc_registered": ec_ndnc,
                                "address": ec_address, "city": ec_city,
                                "state": ec_state, "pincode": ec_pincode,
                                "country": "India", "notes": ec_notes,
                            })
                            if ok:
                                st.success("✅ Customer updated.")
                            else:
                                st.error("Update failed.")
                    with sc2:
                        if st.form_submit_button("🗑 Delete", width='stretch'):
                            db.delete_customer(sel_cust)
                            st.warning("Customer deleted.")
                            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4: POLICIES
# ════════════════════════════════════════════════════════════════════════════════
with tab_policies:
    st.markdown('<div class="section-header">📄 Policy Management</div>', unsafe_allow_html=True)

    pol_action = st.radio(
        "Action",
        ["View / Search", "Add New Policy", "Edit Policy"],
        horizontal=True,
        key="pol_action"
    )

    if pol_action == "View / Search":
        pol_search = st.text_input("Search policies", placeholder="Policy number or customer name…", key="pol_search")
        policies = db.get_all_policies(search=pol_search)
        st.markdown(f'<div class="alert-info">Found <b>{len(policies)}</b> policies</div>', unsafe_allow_html=True)
        if policies:
            df_p = pd.DataFrame([{
                "ID":           p["id"],
                "Policy No.":   p.get("policy_number","—"),
                "Customer":     p.get("full_name","—"),
                "Type":         p.get("policy_type","—"),
                "Amount":       fmt_currency_inr(p.get("premium_amount")),
                "Due Date":     fmt_dt(p.get("due_date")),
                "Status":       (p.get("status") or "—").title(),
                "Lapse Risk":   (p.get("lapse_risk") or "—").title(),
                "Last Called":  fmt_dt(p.get("last_call_date")),
                "Agent":        p.get("agent_name") or "—",
            } for p in policies])
            st.dataframe(df_p, width='stretch', hide_index=True)

    elif pol_action == "Add New Policy":
        st.markdown("##### ➕ Add New Policy")
        customers = db.get_all_customers()
        if not customers:
            st.warning("No customers found. Add a customer first.")
        else:
            with st.form("add_policy_form"):
                pp1, pp2 = st.columns(2)
                with pp1:
                    ap_customer = st.selectbox(
                        "Customer *",
                        [c["id"] for c in customers],
                        format_func=lambda cid: next((f"{c['full_name']} ({c['phone']})" for c in customers if c["id"] == cid), str(cid)),
                        key="ap_customer"
                    )
                    ap_polnum  = st.text_input("Policy Number *", key="ap_polnum")
                    ap_type    = st.selectbox("Policy Type", config.POLICY_TYPES, key="ap_type")
                    ap_amount  = st.number_input("Premium Amount *", min_value=0.01, value=500.00, step=10.0, key="ap_amount")
                    ap_curr    = st.text_input("Currency", value="INR", key="ap_curr")
                with pp2:
                    ap_due     = st.date_input("Due Date *", value=date.today(), key="ap_due")
                    ap_grace   = st.number_input("Grace Period (days)", min_value=0, value=30, key="ap_grace")
                    ap_status  = st.selectbox("Status", ["active","overdue","paid","lapsed","cancelled"], key="ap_status")
                    ap_risk    = st.selectbox("Lapse Risk", ["low","medium","high","critical"], key="ap_risk")
                    ap_agent   = st.text_input("Agent Name", key="ap_agent")
                ap_notes = st.text_area("Notes", key="ap_notes", height=80)

                if st.form_submit_button("💾 Save Policy", width='stretch'):
                    if not ap_polnum:
                        st.error("Policy number is required.")
                    else:
                        try:
                            new_pid = db.create_policy({
                                "customer_id": ap_customer, "policy_number": ap_polnum,
                                "policy_type": ap_type, "premium_amount": ap_amount,
                                "currency": ap_curr, "due_date": ap_due,
                                "grace_period_days": ap_grace, "status": ap_status,
                                "lapse_risk": ap_risk, "agent_name": ap_agent, "notes": ap_notes,
                            })
                            st.success(f"✅ Policy created with ID {new_pid}")
                        except Exception as e:
                            st.error(f"Error: {e}")

    else:  # Edit Policy
        policies = db.get_all_policies()
        if not policies:
            st.info("No policies found.")
        else:
            sel_pol = st.selectbox(
                "Select Policy to Edit",
                [p["id"] for p in policies],
                format_func=lambda pid: next(
                    (f"#{p['id']} · {p['policy_number']} · {p.get('full_name','?')} · {fmt_currency_inr(p.get('premium_amount'))}" for p in policies if p["id"] == pid), str(pid)
                ),
                key="edit_pol_sel"
            )
            pol = db.get_policy_by_id(sel_pol)
            if pol:
                st.markdown(f"##### ✏️ Editing Policy: {pol['policy_number']}")
                with st.form("edit_policy_form"):
                    ep1, ep2 = st.columns(2)
                    with ep1:
                        ep_type    = st.selectbox("Policy Type", ["Life Insurance","Auto Insurance","Health Insurance","Home Insurance","Travel Insurance","Business Insurance"],
                                                   index=config.POLICY_TYPES.index(pol.get("policy_type")) if pol.get("policy_type") in config.POLICY_TYPES else 0, key="ep_type")
                        ep_amount  = st.number_input("Premium Amount", value=float(pol.get("premium_amount",0)), key="ep_amount")
                        ep_curr    = st.text_input("Currency", value=pol.get("currency","USD"), key="ep_curr")
                        ep_due     = st.date_input("Due Date", value=pol.get("due_date") or date.today(), key="ep_due")
                    with ep2:
                        ep_grace   = st.number_input("Grace Period (days)", value=int(pol.get("grace_period_days",30)), key="ep_grace")
                        ep_status  = st.selectbox("Status", ["active","overdue","paid","lapsed","cancelled"],
                                                   index=["active","overdue","paid","lapsed","cancelled"].index(pol.get("status","active")) if pol.get("status") in ["active","overdue","paid","lapsed","cancelled"] else 0, key="ep_status")
                        ep_risk    = st.selectbox("Lapse Risk", ["low","medium","high","critical"],
                                                   index=["low","medium","high","critical"].index(pol.get("lapse_risk","low")) if pol.get("lapse_risk") in ["low","medium","high","critical"] else 0, key="ep_risk")
                        ep_agent   = st.text_input("Agent Name", value=pol.get("agent_name") or "", key="ep_agent")
                    ep_notes = st.text_area("Notes", value=pol.get("notes") or "", key="ep_notes", height=80)

                    se1, se2 = st.columns([3, 1])
                    with se1:
                        if st.form_submit_button("💾 Update Policy", width='stretch'):
                            ok = db.update_policy(sel_pol, {
                                "policy_type": ep_type, "premium_amount": ep_amount,
                                "currency": ep_curr, "due_date": ep_due,
                                "grace_period_days": ep_grace, "status": ep_status,
                                "lapse_risk": ep_risk, "agent_name": ep_agent, "notes": ep_notes,
                            })
                            if ok:
                                st.success("✅ Policy updated.")
                            else:
                                st.error("Update failed.")
                    with se2:
                        if st.form_submit_button("🗑 Delete", width='stretch'):
                            db.delete_policy(sel_pol)
                            st.warning("Policy deleted.")
                            st.rerun()


# ════════════════════════════════════════════════════════════════════════════════
# TAB 5: SETTINGS
# ════════════════════════════════════════════════════════════════════════════════
with tab_settings:
    st.markdown('<div class="section-header">⚙️ Configuration & Settings</div>', unsafe_allow_html=True)

    s1, s2 = st.columns(2)

    with s1:
        st.markdown("**🔑 API Configuration**")
        st.markdown(
            f'<div class="alert-info" style="margin-bottom:0.5rem;">'
            f'VAPI Key: {"✅ Configured" if config.VAPI_API_KEY else "❌ Missing"}<br>'
            f'Anthropic Key: {"✅ Configured" if config.ANTHROPIC_API_KEY else "❌ Missing"}<br>'
            f'VAPI Phone ID: {"✅ Set" if config.VAPI_PHONE_NUMBER_ID else "❌ Missing"}<br>'
            f'VAPI Assistant ID: {"✅ Set" if config.VAPI_ASSISTANT_ID else "⚪ Optional"}'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown(
            '<div class="alert-warn">Update API keys in your <code>.env</code> file and restart the app.</div>',
            unsafe_allow_html=True
        )

        st.markdown("<br>**📞 Call Window & Frequency**")
        st.markdown(
            f'<div class="alert-info">'
            f'Allowed hours: {config.CALL_WINDOW_START}:00 – {config.CALL_WINDOW_END}:00<br>'
            f'Timezone: {config.APP_TIMEZONE}<br>'
            f'Max calls/day: {config.MAX_CALLS_PER_DAY}<br>'
            f'Max calls/week: {config.MAX_CALLS_PER_WEEK}<br>'
            f'Company: {config.COMPANY_NAME}'
            f'</div>',
            unsafe_allow_html=True
        )

        st.markdown("<br>**🌐 Supported Languages**")
        for code, name in config.SUPPORTED_LANGUAGES.items():
            st.markdown(
                f'<div style="display:flex; justify-content:space-between; padding:0.2rem 0; '
                f'border-bottom:1px solid #1E2D40; font-size:0.8rem;">'
                f'<span style="font-family:IBM Plex Mono,monospace; color:#64748B">{code}</span>'
                f'<span style="color:#CBD5E1">{name}</span></div>',
                unsafe_allow_html=True
            )

    with s2:
        st.markdown("**🤖 VAPI Assistant**")
        if st.button("🔄 Create / Update VAPI Assistant", width='stretch', key="create_asst"):
            with st.spinner("Connecting to VAPI..."):
                aid = vapi.create_or_update_assistant()
                if aid:
                    st.success(f"Assistant created/updated: `{aid}`")
                else:
                    st.error("Failed — check VAPI_API_KEY.")

        if st.button("📋 List VAPI Phone Numbers", width='stretch', key="list_phones"):
            with st.spinner("Fetching..."):
                numbers = vapi.get_phone_numbers()
                if numbers:
                    for n in numbers:
                        st.markdown(
                            f'<div style="font-family:IBM Plex Mono,monospace; font-size:0.78rem; '
                            f'padding:0.3rem; color:#94A3B8">ID: {n.get("id")} · {n.get("number","?")}</div>',
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No phone numbers found or VAPI key not set.")

        st.markdown("<br>**🗓️ Scheduler Status**")
        scheduler = sched.get_scheduler() if sched._scheduler else None
        if scheduler and scheduler.running:
            jobs = scheduler.get_jobs()
            for job in jobs:
                next_run = job.next_run_time
                st.markdown(
                    f'<div style="background:#1A2236; border:1px solid #1E2D40; border-radius:6px; '
                    f'padding:0.5rem 0.7rem; margin-bottom:0.3rem; font-size:0.78rem;">'
                    f'<div style="color:#E2E8F0; font-weight:500">{job.name}</div>'
                    f'<div style="color:#64748B; font-family:IBM Plex Mono,monospace">Next: {fmt_dt(next_run)}</div>'
                    f'</div>',
                    unsafe_allow_html=True
                )
        else:
            st.markdown('<div class="alert-warn">Scheduler is not running.</div>', unsafe_allow_html=True)

        st.markdown("<br>**📊 Compliance Summary**")
        st.markdown(
            '<div class="alert-success">'
            '✅ Automated call timing windows enforced<br>'
            '✅ Customer consent check before each call<br>'
            '✅ Do Not Call list respected<br>'
            '✅ Daily/weekly frequency caps active<br>'
            '✅ Escalation path to human agents available<br>'
            '✅ Call transcription & audit logging<br>'
            '✅ Multilingual support (8 languages)'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown("<br>**⚡ Manual DB Actions**")
        if st.button("♻️ Reset Daily Call Counts", width='stretch', key="reset_daily"):
            sched.reset_daily_call_counts()
            st.success("Daily counts reset.")
        if st.button("♻️ Reset Weekly Call Counts", width='stretch', key="reset_weekly"):
            sched.reset_weekly_call_counts()
            st.success("Weekly counts reset.")
        if st.button("🌱 Re-seed Demo Data", width='stretch', key="reseed"):
            db.seed_demo_data()
            st.success("Demo data checked/seeded.")