"""
OakTree Req Readiness — Streamlit dashboard.

Reads data/req-scores.json (committed daily by the req-readiness pipeline on
Phil's machine) and renders it as a sortable, filterable, click-to-expand
dashboard.

Deploy: Streamlit Community Cloud, pointed at the GitHub repo containing this
file. The pipeline does not run here; this app is a read-only renderer.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Page config + global styles

st.set_page_config(
    page_title="OakTree Req Readiness",
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  /* Tighter spacing */
  .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 1400px; }
  /* Status pills */
  .pill { display:inline-block; padding:2px 9px; border-radius:999px; font-size:11.5px; font-weight:640; white-space:nowrap; }
  .b-ready    { color:#1a7f37; background:#e9f6ee; }
  .b-minor    { color:#9a6700; background:#fbf3e0; }
  .b-needs    { color:#bc4c00; background:#fdeee2; }
  .b-notready { color:#b91c1c; background:#fdeaea; }
  /* Action / blocker boxes */
  .act { border-left:3px solid #e1e4e8; padding:7px 0 7px 11px; margin-bottom:9px; }
  .act.critical { border-color:#b91c1c; } .act.high { border-color:#bc4c00; }
  .act.medium   { border-color:#9a6700; } .act.low  { border-color:#1a7f37; }
  .act .a { font-weight:620; }
  .act .m { color:#636c76; font-size:12.5px; margin-top:2px; }
  .act .o { font-size:11.5px; color:#636c76; margin-top:3px; }
  .u { display:inline-block; font-size:10.5px; font-weight:700; text-transform:uppercase; padding:1px 6px; border-radius:5px; margin-left:6px; }
  .u.critical { background:#fdeaea; color:#b91c1c; } .u.high { background:#fdeee2; color:#bc4c00; }
  .u.medium   { background:#fbf3e0; color:#9a6700; } .u.low  { background:#e9f6ee; color:#1a7f37; }
  .cat { display:inline-block; font-size:10px; font-weight:700; text-transform:uppercase;
         letter-spacing:.03em; background:#3d4651; color:#fff; border-radius:4px;
         padding:1px 6px; margin-right:5px; }
  .tag { font-size:11px; background:#eef1f4; color:#3d4651; border-radius:5px;
         padding:1px 6px; margin:0 4px 4px 0; display:inline-block; }
  /* Disclaimer banner */
  .disclaimer { background:#fef3c7; border:1px solid #f59e0b; border-radius:8px;
                padding:10px 14px; margin-bottom:14px; font-size:13px; color:#78350f; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data loader (cached so Streamlit doesn't re-read on every interaction)

DATA_PATH = Path(__file__).parent / "data" / "req-scores.json"


@st.cache_data(ttl=60)  # short TTL — file may be updated mid-day
def load_data() -> tuple[dict, list[dict]]:
    if not DATA_PATH.exists():
        st.error(f"Data file missing: {DATA_PATH}. The pipeline writes this file; "
                 f"check the daily push job.")
        st.stop()
    d = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    return d.get("meta", {}), d.get("reqs", [])


meta, reqs = load_data()


# ---------------------------------------------------------------------------
# Header

st.markdown('<div class="disclaimer">⚠️ <b>OakTree internal — sensitive content.</b> '
            'This dashboard contains candidate names, resume excerpts, and client '
            'manager feedback. Do not share the URL externally.</div>',
            unsafe_allow_html=True)

st.title("🌳 OakTree Req Readiness")
generated = meta.get("generated_at_local") or meta.get("generated_at", "")[:16]
src_label = meta.get("source_file", "?")
st.caption(f"**{meta.get('req_count', len(reqs))} active reqs** · source `{src_label}` · "
           f"generated **{generated}**")


# ---------------------------------------------------------------------------
# Summary cards

bands = meta.get("bands", {})
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Not recruitable",  bands.get("notready", 0))
c2.metric("Needs fixing",     bands.get("needs", 0))
c3.metric("Minor friction",   bands.get("minor", 0))
c4.metric("Ready",            bands.get("ready", 0))
c5.metric("New / changed",    meta.get("new_or_changed", 0))


# ---------------------------------------------------------------------------
# Sidebar filters

with st.sidebar:
    st.header("Filters")
    q = st.text_input("Search title, company, AM, RM, job ID", value="").strip().lower()
    band_choices = ["All", "ready", "minor", "needs", "notready"]
    band_labels = {"All": "All",
                   "ready": "Ready",
                   "minor": "Minor friction",
                   "needs": "Needs fixing",
                   "notready": "Not recruitable"}
    band_filter = st.selectbox("Recruitability", band_choices,
                               format_func=lambda x: band_labels[x])
    priorities = sorted({r["priority"] for r in reqs if r.get("priority")})
    pri_filter = st.selectbox("Priority", ["All"] + priorities)
    ams = sorted({r["salesperson"] for r in reqs if r.get("salesperson")})
    am_filter = st.selectbox("AM", ["All"] + ams)
    rms = sorted({r["recruiting_manager"] for r in reqs if r.get("recruiting_manager")})
    rm_filter = st.selectbox("RM", ["All"] + rms)
    only_changed = st.checkbox("New / changed only", value=False)
    has_subs_only = st.checkbox("Has submittals only", value=False)


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
# Reqs table

st.markdown(f"### {len(filtered)} reqs")

if not filtered:
    st.info("No reqs match the current filters.")
    st.stop()

# Build DataFrame for st.dataframe with row selection
df_rows = []
for r in filtered:
    df_rows.append({
        "Recruit":  int(r.get("readiness_score") or 0),
        "Status":   r.get("band_label", ""),
        "Intake":   int(r.get("intake_quality_score") or 0),
        "Job ID":   r.get("job_id"),
        "Title":    r.get("title", ""),
        "Company":  r.get("company", ""),
        "Priority": r.get("priority", ""),
        "AM":       r.get("salesperson", ""),
        "RM":       r.get("recruiting_manager", ""),
        "Days":     r.get("days_open", 0),
        "Subs":     r.get("submittals", 0),
        "Fixes":    r.get("action_count", 0),
        "State":    r.get("change_status", ""),
    })

df = pd.DataFrame(df_rows)

# Sort: not-recruitable + lowest score first
band_order = {"Not recruitable": 0, "Needs fixing": 1, "Minor friction": 2, "Ready": 3}
df["_b"] = df["Status"].map(band_order).fillna(9)
df = df.sort_values(["_b", "Recruit"]).drop(columns=["_b"]).reset_index(drop=True)

# Streamlit dataframe with single-row selection
event = st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    height=420,
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Recruit":  st.column_config.NumberColumn(format="%d", width="small"),
        "Status":   st.column_config.TextColumn(width="small"),
        "Intake":   st.column_config.NumberColumn(format="%d", width="small"),
        "Job ID":   st.column_config.NumberColumn(format="%d", width="small"),
        "Title":    st.column_config.TextColumn(width="medium"),
        "Company":  st.column_config.TextColumn(width="medium"),
        "Priority": st.column_config.TextColumn(width="small"),
        "AM":       st.column_config.TextColumn(width="small"),
        "RM":       st.column_config.TextColumn(width="small"),
        "Days":     st.column_config.NumberColumn(format="%d", width="small"),
        "Subs":     st.column_config.NumberColumn(format="%d", width="small"),
        "Fixes":    st.column_config.NumberColumn(format="%d", width="small"),
        "State":    st.column_config.TextColumn(width="small"),
    },
)


# ---------------------------------------------------------------------------
# Detail panel for the selected req

def esc(s) -> str:
    if s is None:
        return ""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                  .replace(">", "&gt;").replace('"', "&quot;"))


def render_detail(req: dict) -> None:
    band_class_map = {"ready": "b-ready", "minor": "b-minor",
                      "needs": "b-needs", "notready": "b-notready"}
    band_class = band_class_map.get(req.get("band"), "")

    bullhorn_url = req.get("bullhorn_url", "")
    st.markdown(
        f"## [{req.get('job_id')}]({bullhorn_url}) · {esc(req.get('title',''))} "
        f"@ {esc(req.get('company',''))}"
    )
    st.markdown(
        f"<span class='pill {band_class}'>{esc(req.get('band_label',''))} · "
        f"{req.get('readiness_score',0)}/100</span> &nbsp; "
        f"<b>AM:</b> {esc(req.get('salesperson',''))} &nbsp; "
        f"<b>RM:</b> {esc(req.get('recruiting_manager',''))} &nbsp; "
        f"<b>Priority:</b> {esc(req.get('priority',''))} &nbsp; "
        f"<b>Days open:</b> {req.get('days_open',0)} &nbsp; "
        f"<b>Submittals:</b> {req.get('submittals',0)}",
        unsafe_allow_html=True
    )

    col_left, col_right = st.columns([1.2, 1])

    # ---- Left: recruitability + blockers + actions ----
    with col_left:
        if req.get("recruitability_rationale"):
            st.markdown(f"_{esc(req['recruitability_rationale'])}_")

        st.markdown("##### Blockers")
        blockers = req.get("blockers") or []
        if not blockers:
            st.markdown("_No recruitability blockers — sourceable as-is._")
        else:
            sev_class = {"high": "critical", "medium": "high", "low": "medium"}
            for b in blockers:
                u = sev_class.get(b.get("severity", "medium"), "medium")
                html = (f"<div class='act {u}'>"
                        f"<div class='a'><span class='cat'>{esc(b.get('category',''))}</span>"
                        f"{esc(b.get('detail',''))}"
                        f"<span class='u {u}'>{esc(b.get('severity',''))}</span></div>")
                if b.get("fix"):
                    html += f"<div class='m'>Fix: {esc(b['fix'])}</div>"
                html += "</div>"
                st.markdown(html, unsafe_allow_html=True)

        st.markdown("##### What needs to happen")
        actions = req.get("actions") or []
        if not actions:
            st.markdown("_No outstanding actions._")
        else:
            for a in actions:
                u = a.get("urgency", "medium")
                html = (f"<div class='act {esc(u)}'>"
                        f"<div class='a'>{esc(a.get('action',''))}"
                        f"<span class='u {esc(u)}'>{esc(u)}</span></div>"
                        f"<div class='m'>{esc(a.get('why_it_matters',''))}</div>"
                        f"<div class='o'>Owner: {esc(a.get('owner',''))}</div></div>")
                st.markdown(html, unsafe_allow_html=True)

    # ---- Right: read, coaching, intake quality ----
    with col_right:
        st.markdown("##### Read")
        if req.get("role_summary"):
            st.markdown(f"**{esc(req['role_summary'])}**")
        if req.get("realistic_candidate_profile"):
            st.markdown(f"_Realistic candidate:_ {esc(req['realistic_candidate_profile'])}")
        if req.get("peer_coaching_note") and req["peer_coaching_note"] != "No coaching note — clean intake.":
            st.markdown(f"_Coaching:_ {esc(req['peer_coaching_note'])}")
        if req.get("no_client_access"):
            st.markdown("_No client access (CC/VMS)_")

        st.markdown("##### Intake quality (coaching only)")
        st.markdown(f"JQF completeness: **{req.get('intake_quality_score',0)}/100** "
                    "· does not affect recruitability")
        gaps = req.get("intake_gaps") or []
        if gaps:
            tags = " ".join(f"<span class='tag'>{esc(g)}</span>" for g in gaps)
            st.markdown(f"<small>Missing / weak:</small><br>{tags}", unsafe_allow_html=True)
        st.markdown(f"<small>Scored {esc((req.get('first_scored_at','') or '')[:10])} · "
                    f"{esc(req.get('change_status',''))}"
                    f"{' · ' + esc(req.get('role_family','')) if req.get('role_family') else ''}</small>",
                    unsafe_allow_html=True)

    # ---- Submittal Intelligence (full width below) ----
    si = req.get("submittal_intel")
    if si:
        st.markdown("---")
        cands = si.get("candidates", [])
        st.markdown(f"### Submittal Intelligence · {len(cands)} submittal{'s' if len(cands)!=1 else ''}")
        if si.get("pipeline_summary"):
            st.markdown(f"**{esc(si['pipeline_summary'])}**")

        col_p, col_c = st.columns([1.2, 1])
        with col_p:
            st.markdown("##### Rejection patterns → what to source for next")
            patterns = si.get("rejection_patterns") or []
            if not patterns:
                st.markdown("_No rejection patterns inferable from current submittal notes._")
            else:
                conf_class = {"high": "critical", "medium": "high", "low": "medium"}
                for p in patterns:
                    u = conf_class.get(p.get("confidence", "medium"), "medium")
                    affects = ", ".join(p.get("candidates_affected", []) or [])
                    html = (f"<div class='act {u}'>"
                            f"<div class='a'>{esc(p.get('pattern',''))}"
                            f"<span class='u {u}'>{esc(p.get('confidence',''))}</span></div>")
                    if affects:
                        html += f"<div class='o'>Candidates: {esc(affects)}</div>"
                    if p.get("evidence_quote"):
                        html += f"<div class='m'><i>Evidence:</i> {esc(p['evidence_quote'])}</div>"
                    if p.get("sourcing_correction"):
                        html += f"<div class='m'><b>Next time:</b> {esc(p['sourcing_correction'])}</div>"
                    html += "</div>"
                    st.markdown(html, unsafe_allow_html=True)

        with col_c:
            st.markdown("##### Where each candidate is")
            inflight = [c for c in cands if not (c.get("current_status","").startswith("Reject")
                                                  or c.get("current_status","").startswith("Withdrew"))]
            closed = [c for c in cands if c.get("current_status","").startswith("Reject")
                                       or c.get("current_status","").startswith("Withdrew")]
            if not inflight:
                st.markdown("_No candidates currently in-flight._")
            else:
                _render_candidate_blocks(inflight)
            if closed:
                with st.expander(f"{len(closed)} closed (rejected/withdrew)"):
                    _render_candidate_blocks(closed)


def _render_candidate_blocks(cands):
    """Render a list of CandidateState records as styled blocks."""
    fit_class = {"strong": "low", "viable": "medium", "at_risk": "high",
                 "weak": "critical", "insufficient_data": "medium", "n/a": "low"}
    fit_label = {"strong": "Strong fit", "viable": "Viable",
                 "at_risk": "At risk", "weak": "Weak fit",
                 "insufficient_data": "Insufficient data", "n/a": ""}
    for c in cands:
        band = c.get("placement_likelihood_band", "n/a")
        stall = ""
        if c.get("is_stalled"):
            stall = f"<span class='u critical'>STALLED {c.get('days_since_last_activity',0)}d</span>"
        badge = ""
        if band != "n/a":
            score = c.get("placement_likelihood")
            score_str = f" {score}" if score is not None else ""
            badge = f"<span class='u {fit_class.get(band,'medium')}'>{fit_label.get(band, band)}{score_str}</span>"
        block_cls = "critical" if c.get("is_stalled") else fit_class.get(band, "low")

        html = (f"<div class='act {block_cls}'>"
                f"<div class='a'>{esc(c.get('candidate_name',''))} "
                f"<span class='o' style='font-weight:400'>· {esc(c.get('current_status',''))}</span> "
                f"{badge} {stall}</div>"
                f"<div class='m'>{esc(c.get('where_they_are',''))}</div>")

        # Fit details if assessed
        if band in ("strong", "viable", "at_risk", "weak"):
            if c.get("fit_rationale"):
                html += f"<div class='m' style='margin-top:5px'><i>{esc(c['fit_rationale'])}</i></div>"
            if c.get("fit_strengths"):
                items = "".join(f"<li>{esc(s)}</li>" for s in c["fit_strengths"])
                html += f"<div style='margin-top:4px'><b style='color:#1a7f37'>+ Strengths:</b>" \
                        f"<ul style='margin:2px 0 4px 18px;padding:0'>{items}</ul></div>"
            if c.get("fit_risks"):
                items = "".join(f"<li>{esc(s)}</li>" for s in c["fit_risks"])
                html += f"<div><b style='color:#b91c1c'>! Risks:</b>" \
                        f"<ul style='margin:2px 0 0 18px;padding:0'>{items}</ul></div>"
        html += "</div>"
        st.markdown(html, unsafe_allow_html=True)


# Show detail panel for selected row, if any
sel = (event.selection.rows if hasattr(event, "selection") else []) or []
if sel:
    selected_index = sel[0]
    # df was reset_index'd above, so iloc by position
    selected_job_id = int(df.iloc[selected_index]["Job ID"])
    selected_req = next((r for r in filtered if r.get("job_id") == selected_job_id), None)
    if selected_req:
        st.markdown("---")
        render_detail(selected_req)
else:
    st.caption("Select a row above to see the full readiness analysis, "
               "blockers, actions, and submittal intelligence.")
