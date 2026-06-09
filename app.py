"""
OakTree Req Readiness — Streamlit dashboard (brand-styled).

Reads data/req-scores.json (committed by the req-readiness pipeline on Phil's
machine) and renders it with OakTree's visual identity. Read-only; no AI or
Snowflake here.

Brand: Overpass + Noto Serif. Navy #0D2A39, Forest #004638, Coral #FF6F59,
Sky #36ADEC, Sage #C0D7BB, Cream #F0E5D5. Tagline: "Your branch to success."
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Brand palette

NAVY    = "#0D2A39"
FOREST  = "#004638"
CORAL   = "#FF6F59"
CORALDK = "#C0432E"
RED     = "#9E2B1A"
SKY     = "#36ADEC"
LIGHTBL = "#BEDCFE"
SAGE    = "#C0D7BB"
CREAM   = "#F0E5D5"
INK     = "#0D2A39"
MUTED   = "#5b6b73"

# Recruitability band → display config
BANDS = {
    "ready":    {"label": "Ready",           "emoji": "🟢", "text": FOREST,  "bg": "#E7F0E3", "accent": FOREST},
    "minor":    {"label": "Minor friction",  "emoji": "🔵", "text": "#1d6ea3","bg": "#E9F4FB", "accent": SKY},
    "needs":    {"label": "Needs fixing",    "emoji": "🟠", "text": CORALDK, "bg": "#FDEAE4", "accent": CORAL},
    "notready": {"label": "Not recruitable", "emoji": "🔴", "text": RED,     "bg": "#FBE1DB", "accent": RED},
}
SEV_ACCENT = {"high": CORALDK, "medium": "#9a6700", "low": FOREST, "critical": RED}


# ---------------------------------------------------------------------------
# Page config + brand styling

st.set_page_config(page_title="OakTree Req Readiness", page_icon="🌳",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown(f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Overpass:wght@400;500;600;700;800;900&family=Noto+Serif:wght@400;600;700&display=swap');

  /* Base typography */
  html, body, .stApp, [class*="css"], button, input, textarea, select,
  [data-testid="stMarkdownContainer"] {{ font-family:'Overpass', system-ui, sans-serif; }}
  h1,h2,h3,h4,h5 {{ font-family:'Overpass', sans-serif !important; font-weight:800 !important;
                    letter-spacing:-0.01em; color:{INK}; }}
  .serif {{ font-family:'Noto Serif', Georgia, serif; }}

  /* Hide Streamlit chrome for an app-like feel */
  header[data-testid="stHeader"] {{ display:none; }}
  #MainMenu, footer {{ visibility:hidden; }}
  .block-container {{ padding-top: 1.2rem; padding-bottom: 2.5rem; max-width: 1480px; }}

  /* ---- Header banner ---- */
  .otbar {{ background:{NAVY}; border-radius:14px; padding:18px 26px; margin-bottom:18px;
            display:flex; align-items:center; justify-content:space-between;
            box-shadow:0 1px 3px rgba(13,42,57,.18); }}
  .otbar .left {{ display:flex; align-items:center; gap:16px; }}
  .otbar .wm {{ line-height:0.92; }}
  .otbar .wm .o {{ font-family:'Overpass',sans-serif; font-weight:900; font-size:26px;
                   color:#fff; letter-spacing:-0.5px; }}
  .otbar .wm .s {{ font-family:'Overpass',sans-serif; font-weight:900; font-size:26px;
                   color:#fff; letter-spacing:-0.5px; display:block; }}
  .otbar .tag {{ color:{SAGE}; font-size:13.5px; font-weight:600; text-align:right; }}
  .otbar .tag .sub {{ color:#9fb7c4; font-weight:500; font-size:12px; display:block; margin-top:3px; }}
  .accentrule {{ height:4px; width:54px; background:{CORAL}; border-radius:2px; margin-top:6px; }}

  /* ---- Metric cards ---- */
  .cards {{ display:flex; gap:12px; flex-wrap:wrap; margin-bottom:8px; }}
  .card {{ flex:1; min-width:150px; background:#fff; border:1px solid #e6eaed;
           border-radius:12px; padding:14px 16px; border-top:4px solid var(--c);
           box-shadow:0 1px 2px rgba(13,42,57,.05); }}
  .card .n {{ font-size:30px; font-weight:800; color:var(--c); line-height:1; }}
  .card .l {{ font-size:12px; color:{MUTED}; text-transform:uppercase; letter-spacing:.04em;
              font-weight:600; margin-top:6px; }}

  /* ---- Pills + blocks ---- */
  .pill {{ display:inline-block; padding:3px 11px; border-radius:999px; font-size:12px;
           font-weight:700; white-space:nowrap; }}
  .act {{ border-left:3px solid #e1e4e8; padding:8px 0 8px 12px; margin-bottom:10px; }}
  .act .a {{ font-weight:700; color:{INK}; }}
  .act .m {{ color:{MUTED}; font-size:13px; margin-top:3px; }}
  .act .o {{ font-size:12px; color:{MUTED}; margin-top:3px; font-weight:600; }}
  .u {{ display:inline-block; font-size:10.5px; font-weight:800; text-transform:uppercase;
        padding:1px 7px; border-radius:5px; margin-left:7px; vertical-align:middle; }}
  .cat {{ display:inline-block; font-size:10px; font-weight:800; text-transform:uppercase;
          letter-spacing:.03em; background:{NAVY}; color:#fff; border-radius:4px;
          padding:1px 7px; margin-right:6px; }}
  .tag {{ font-size:11px; background:#eef1f4; color:#3d4651; border-radius:5px;
          padding:2px 7px; margin:0 4px 4px 0; display:inline-block; }}
  .sec {{ font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.05em;
          color:{CORAL}; margin:14px 0 6px; }}

  .disclaimer {{ background:{CREAM}; border-left:4px solid {CORAL}; border-radius:8px;
                 padding:9px 14px; margin-bottom:16px; font-size:12.5px; color:#6b4a3a; }}

  /* Sidebar branding */
  section[data-testid="stSidebar"] {{ background:{NAVY}; }}
  section[data-testid="stSidebar"] * {{ color:#eaf1f4; }}
  section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3, section[data-testid="stSidebar"] label {{ color:#ffffff !important; }}
  section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] [data-baseweb="select"] > div {{
      color:{INK}; }}
  section[data-testid="stSidebar"] .stCheckbox p {{ color:#eaf1f4 !important; }}
</style>
""", unsafe_allow_html=True)


# Three-coral-slash brand emblem (the recurring OakTree mark)
OT_EMBLEM = f"""
<svg width="30" height="40" viewBox="0 0 32 42" style="flex:none">
  <g fill="{CORAL}" transform="rotate(-24 16 21)">
    <rect x="3" y="4"  width="26" height="7" rx="3.5"/>
    <rect x="3" y="17" width="26" height="7" rx="3.5"/>
    <rect x="3" y="30" width="26" height="7" rx="3.5"/>
  </g>
</svg>"""


# ---------------------------------------------------------------------------
# Data

DATA_PATH = Path(__file__).parent / "data" / "req-scores.json"


@st.cache_data(ttl=60)
def load_data() -> tuple[dict, list[dict]]:
    if not DATA_PATH.exists():
        st.error(f"Data file missing: {DATA_PATH}. The pipeline writes this file.")
        st.stop()
    d = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return d.get("meta", {}), d.get("reqs", [])


meta, reqs = load_data()


# ---------------------------------------------------------------------------
# Header

generated = meta.get("generated_at_local") or (meta.get("generated_at", "")[:16])
src_label = meta.get("source_file", "?")
# Trim the verbose snowflake-pull label to something tidy
if "snowflake" in str(src_label).lower():
    src_short = "Snowflake (live Bullhorn mirror)"
elif "299" in str(src_label):
    src_short = "Bullhorn export"
else:
    src_short = str(src_label)

st.markdown(f"""
<div class="otbar">
  <div class="left">
    {OT_EMBLEM}
    <div class="wm"><span class="o">OakTree</span><span class="s">Staffing</span>
      <div class="accentrule"></div></div>
    <div style="margin-left:14px;">
      <div style="color:#fff;font-weight:800;font-size:19px;letter-spacing:-.01em;">Req Readiness</div>
      <div style="color:#9fb7c4;font-size:12.5px;">Recruitability &amp; submittal intelligence</div>
    </div>
  </div>
  <div class="tag">Your branch to success
    <span class="sub">{meta.get('req_count', len(reqs))} active reqs &middot; {src_short} &middot; {generated}</span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="disclaimer">⚠️ <b>OakTree internal — sensitive content.</b> '
            'Contains candidate names, resume excerpts, and client manager feedback. '
            'Please don\'t share this URL externally.</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Metric cards

b = meta.get("bands", {})
st.markdown(f"""
<div class="cards">
  <div class="card" style="--c:{RED}">    <div class="n">{b.get('notready',0)}</div><div class="l">Not recruitable</div></div>
  <div class="card" style="--c:{CORAL}">  <div class="n">{b.get('needs',0)}</div>   <div class="l">Needs fixing</div></div>
  <div class="card" style="--c:{SKY}">    <div class="n">{b.get('minor',0)}</div>   <div class="l">Minor friction</div></div>
  <div class="card" style="--c:{FOREST}"> <div class="n">{b.get('ready',0)}</div>   <div class="l">Ready</div></div>
  <div class="card" style="--c:{NAVY}">   <div class="n">{meta.get('new_or_changed',0)}</div><div class="l">New / changed</div></div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar filters

with st.sidebar:
    st.markdown(f"{OT_EMBLEM}", unsafe_allow_html=True)
    st.header("Filters")
    q = st.text_input("Search", placeholder="title, company, AM, RM, job ID").strip().lower()
    band_choices = ["All", "notready", "needs", "minor", "ready"]
    band_filter = st.selectbox("Recruitability", band_choices,
                               format_func=lambda x: "All" if x == "All" else BANDS[x]["label"])
    priorities = sorted({r["priority"] for r in reqs if r.get("priority")})
    pri_filter = st.selectbox("Priority", ["All"] + priorities)
    ams = sorted({r["salesperson"] for r in reqs if r.get("salesperson")})
    am_filter = st.selectbox("Account Manager", ["All"] + ams)
    rms = sorted({r["recruiting_manager"] for r in reqs if r.get("recruiting_manager")})
    rm_filter = st.selectbox("Recruiting Manager", ["All"] + rms)
    only_changed = st.checkbox("New / changed only")
    has_subs_only = st.checkbox("Has submittals only")


def keep(r: dict) -> bool:
    if band_filter != "All" and r.get("band") != band_filter:
        return False
    if pri_filter != "All" and r.get("priority") != pri_filter:
        return False
    if am_filter != "All" and r.get("salesperson") != am_filter:
        return False
    if rm_filter != "All" and r.get("recruiting_manager") != rm_filter:
        return False
    if only_changed and r.get("change_status") == "stable":
        return False
    if has_subs_only and (r.get("submittals") or 0) == 0:
        return False
    if q:
        hay = f"{r.get('job_id')} {r.get('title','')} {r.get('company','')} " \
              f"{r.get('salesperson','')} {r.get('recruiting_manager','')}".lower()
        if q not in hay:
            return False
    return True


filtered = [r for r in reqs if keep(r)]


# ---------------------------------------------------------------------------
# Reqs table — trimmed columns, progress bar score, emoji status (no cutoff)

st.markdown(f"<div style='font-weight:800;font-size:18px;color:{INK};margin:6px 0 2px'>"
            f"{len(filtered)} reqs</div>", unsafe_allow_html=True)

if not filtered:
    st.info("No reqs match the current filters.")
    st.stop()

rows = []
for r in filtered:
    band = r.get("band", "")
    bc = BANDS.get(band, {"emoji": "", "label": r.get("band_label", "")})
    rows.append({
        "Recruit":  int(r.get("readiness_score") or 0),
        "Status":   f"{bc['emoji']} {bc['label']}",
        "Title":    r.get("title", ""),
        "Company":  r.get("company", ""),
        "AM":       r.get("salesperson", ""),
        "Subs":     r.get("submittals", 0),
        "Fixes":    r.get("action_count", 0),
        "ID":       r.get("job_id"),
    })

df = pd.DataFrame(rows)
order = {"🔴": 0, "🟠": 1, "🔵": 2, "🟢": 3}
df["_o"] = df["Status"].str[0].map(order).fillna(9)
df = df.sort_values(["_o", "Recruit"]).drop(columns="_o").reset_index(drop=True)

event = st.dataframe(
    df, use_container_width=True, hide_index=True, height=440,
    on_select="rerun", selection_mode="single-row",
    column_config={
        "Recruit": st.column_config.ProgressColumn(
            "Recruit", help="AI recruitability score (0–100)",
            min_value=0, max_value=100, format="%d", width="medium"),
        "Status":  st.column_config.TextColumn("Status", width="medium"),
        "Title":   st.column_config.TextColumn("Title", width="large"),
        "Company": st.column_config.TextColumn("Company", width="medium"),
        "AM":      st.column_config.TextColumn("AM", width="small"),
        "Subs":    st.column_config.NumberColumn("Subs", format="%d", width="small",
                                                 help="Real submittals (excludes pre-sub workflow)"),
        "Fixes":   st.column_config.NumberColumn("Fixes", format="%d", width="small"),
        "ID":      st.column_config.NumberColumn("Job ID", format="%d", width="small"),
    },
)


# ---------------------------------------------------------------------------
# Detail panel

def esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                  .replace(">", "&gt;").replace('"', "&quot;"))


def serif(s) -> str:
    return f"<span class='serif'>{esc(s)}</span>"


def _candidate_blocks(cands):
    fit_class = {"strong": "low", "viable": "medium", "at_risk": "high",
                 "weak": "critical", "insufficient_data": "medium", "n/a": "low"}
    fit_label = {"strong": "Strong fit", "viable": "Viable", "at_risk": "At risk",
                 "weak": "Weak fit", "insufficient_data": "Insufficient data", "n/a": ""}
    for c in cands:
        band = c.get("placement_likelihood_band", "n/a")
        accent = SEV_ACCENT.get(fit_class.get(band, "low"), FOREST)
        stall = (f"<span class='u' style='background:{RED};color:#fff'>STALLED "
                 f"{c.get('days_since_last_activity',0)}d</span>") if c.get("is_stalled") else ""
        badge = ""
        if band != "n/a":
            score = c.get("placement_likelihood")
            ss = f" {score}" if score is not None else ""
            badge = (f"<span class='u' style='background:{accent};color:#fff'>"
                     f"{fit_label.get(band, band)}{ss}</span>")
        html = (f"<div class='act' style='border-color:{accent}'>"
                f"<div class='a'>{esc(c.get('candidate_name',''))} "
                f"<span class='o' style='font-weight:500'>· {esc(c.get('current_status',''))}</span> "
                f"{badge} {stall}</div>"
                f"<div class='m'>{serif(c.get('where_they_are',''))}</div>")
        if band in ("strong", "viable", "at_risk", "weak"):
            if c.get("fit_rationale"):
                html += f"<div class='m' style='margin-top:5px'>{serif(c['fit_rationale'])}</div>"
            if c.get("fit_strengths"):
                items = "".join(f"<li>{esc(s)}</li>" for s in c["fit_strengths"])
                html += f"<div style='margin-top:4px'><b style='color:{FOREST}'>+ Strengths</b>" \
                        f"<ul style='margin:2px 0 4px 18px;padding:0;color:{MUTED};font-size:13px'>{items}</ul></div>"
            if c.get("fit_risks"):
                items = "".join(f"<li>{esc(s)}</li>" for s in c["fit_risks"])
                html += f"<div><b style='color:{CORALDK}'>! Risks</b>" \
                        f"<ul style='margin:2px 0 0 18px;padding:0;color:{MUTED};font-size:13px'>{items}</ul></div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)


def render_detail(r: dict) -> None:
    band = r.get("band", "")
    bc = BANDS.get(band, {"bg": "#eee", "text": INK, "label": r.get("band_label", "")})
    st.markdown(
        f"## [{r.get('job_id')}]({r.get('bullhorn_url','')}) · "
        f"{esc(r.get('title',''))} <span style='color:{MUTED};font-weight:600'>@ "
        f"{esc(r.get('company',''))}</span>", unsafe_allow_html=True)
    st.markdown(
        f"<span class='pill' style='background:{bc['bg']};color:{bc['text']}'>"
        f"{esc(bc['label'])} · {r.get('readiness_score',0)}/100</span> &nbsp; "
        f"<b>AM:</b> {esc(r.get('salesperson',''))} &nbsp; "
        f"<b>RM:</b> {esc(r.get('recruiting_manager','') or '—')} &nbsp; "
        f"<b>Priority:</b> {esc(r.get('priority',''))} &nbsp; "
        f"<b>Branch:</b> {esc(r.get('branch','') or '—')} &nbsp; "
        f"<b>Days open:</b> {r.get('days_open',0)} &nbsp; "
        f"<b>Submittals:</b> {r.get('submittals',0)} &nbsp; "
        f"<b>State:</b> {esc(r.get('change_status',''))}", unsafe_allow_html=True)

    left, right = st.columns([1.25, 1])
    with left:
        if r.get("recruitability_rationale"):
            st.markdown(f"<div class='m' style='margin:8px 0'>{serif(r['recruitability_rationale'])}</div>",
                        unsafe_allow_html=True)
        st.markdown("<div class='sec'>Blockers</div>", unsafe_allow_html=True)
        blockers = r.get("blockers") or []
        if not blockers:
            st.markdown("<div class='m'>No recruitability blockers — sourceable as-is.</div>",
                        unsafe_allow_html=True)
        else:
            sev = {"high": "critical", "medium": "high", "low": "medium"}
            for bl in blockers:
                u = sev.get(bl.get("severity", "medium"), "medium")
                acc = SEV_ACCENT.get(u, CORAL)
                html = (f"<div class='act' style='border-color:{acc}'>"
                        f"<div class='a'><span class='cat'>{esc(bl.get('category',''))}</span>"
                        f"{esc(bl.get('detail',''))}"
                        f"<span class='u' style='background:{acc};color:#fff'>{esc(bl.get('severity',''))}</span></div>")
                if bl.get("fix"):
                    html += f"<div class='m'>Fix: {serif(bl['fix'])}</div>"
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)

        st.markdown("<div class='sec'>What needs to happen</div>", unsafe_allow_html=True)
        actions = r.get("actions") or []
        if not actions:
            st.markdown("<div class='m'>No outstanding actions.</div>", unsafe_allow_html=True)
        for a in actions:
            u = a.get("urgency", "medium")
            acc = SEV_ACCENT.get(u, CORAL)
            st.markdown(
                f"<div class='act' style='border-color:{acc}'>"
                f"<div class='a'>{esc(a.get('action',''))}"
                f"<span class='u' style='background:{acc};color:#fff'>{esc(u)}</span></div>"
                f"<div class='m'>{serif(a.get('why_it_matters',''))}</div>"
                f"<div class='o'>Owner: {esc(a.get('owner',''))}</div></div>", unsafe_allow_html=True)

    with right:
        st.markdown("<div class='sec'>Read</div>", unsafe_allow_html=True)
        if r.get("role_summary"):
            st.markdown(f"<b>{esc(r['role_summary'])}</b>", unsafe_allow_html=True)
        if r.get("realistic_candidate_profile"):
            st.markdown(f"<div class='m'>Realistic candidate: {serif(r['realistic_candidate_profile'])}</div>",
                        unsafe_allow_html=True)
        if r.get("peer_coaching_note") and r["peer_coaching_note"] != "No coaching note — clean intake.":
            st.markdown(f"<div class='m'>Coaching: {serif(r['peer_coaching_note'])}</div>",
                        unsafe_allow_html=True)
        if r.get("no_client_access"):
            st.markdown("<div class='m'><i>No client access (CC/VMS)</i></div>", unsafe_allow_html=True)

        st.markdown("<div class='sec'>Intake quality (coaching)</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='m'>JQF completeness <b>{r.get('intake_quality_score',0)}/100</b> "
                    f"· does not affect recruitability</div>", unsafe_allow_html=True)
        gaps = r.get("intake_gaps") or []
        if gaps:
            st.markdown("".join(f"<span class='tag'>{esc(g)}</span>" for g in gaps),
                        unsafe_allow_html=True)

    # Submittal intelligence
    si = r.get("submittal_intel")
    if si:
        st.markdown("<hr style='margin:18px 0 10px;border:none;border-top:1px solid #e6eaed'>",
                    unsafe_allow_html=True)
        cands = si.get("candidates", [])
        st.markdown(f"### Submittal Intelligence "
                    f"<span style='color:{MUTED};font-weight:600;font-size:15px'>· "
                    f"{len(cands)} submittal{'s' if len(cands)!=1 else ''}</span>", unsafe_allow_html=True)
        if si.get("pipeline_summary"):
            st.markdown(f"<b>{serif(si['pipeline_summary'])}</b>", unsafe_allow_html=True)
        cp, cc = st.columns([1.25, 1])
        with cp:
            st.markdown("<div class='sec'>Rejection patterns → what to source for next</div>",
                        unsafe_allow_html=True)
            patterns = si.get("rejection_patterns") or []
            if not patterns:
                st.markdown("<div class='m'>No rejection patterns inferable from current notes.</div>",
                            unsafe_allow_html=True)
            for p in patterns:
                conf = {"high": "critical", "medium": "high", "low": "medium"}.get(p.get("confidence", "medium"), "high")
                acc = SEV_ACCENT.get(conf, CORAL)
                affects = ", ".join(p.get("candidates_affected", []) or [])
                html = (f"<div class='act' style='border-color:{acc}'>"
                        f"<div class='a'>{esc(p.get('pattern',''))}"
                        f"<span class='u' style='background:{acc};color:#fff'>{esc(p.get('confidence',''))}</span></div>")
                if affects:
                    html += f"<div class='o'>Candidates: {esc(affects)}</div>"
                if p.get("evidence_quote"):
                    html += f"<div class='m'><i>Evidence:</i> {serif(p['evidence_quote'])}</div>"
                if p.get("sourcing_correction"):
                    html += f"<div class='m'><b>Next time:</b> {serif(p['sourcing_correction'])}</div>"
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)
        with cc:
            st.markdown("<div class='sec'>Where each candidate is</div>", unsafe_allow_html=True)
            inflight = [c for c in cands if not (c.get("current_status", "").startswith("Reject")
                                                 or c.get("current_status", "").startswith("Withdrew"))]
            closed = [c for c in cands if c.get("current_status", "").startswith("Reject")
                                       or c.get("current_status", "").startswith("Withdrew")]
            if inflight:
                _candidate_blocks(inflight)
            else:
                st.markdown("<div class='m'>No candidates currently in-flight.</div>", unsafe_allow_html=True)
            if closed:
                with st.expander(f"{len(closed)} closed (rejected / withdrew)"):
                    _candidate_blocks(closed)


sel = (event.selection.rows if hasattr(event, "selection") else []) or []
if sel:
    jid = int(df.iloc[sel[0]]["ID"])
    req = next((r for r in filtered if r.get("job_id") == jid), None)
    if req:
        st.markdown("<hr style='margin:14px 0;border:none;border-top:2px solid #e6eaed'>",
                    unsafe_allow_html=True)
        render_detail(req)
else:
    st.caption("Select a row to see the full readiness analysis, blockers, actions, and submittal intelligence.")
