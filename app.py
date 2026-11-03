"""Greek AI Job Market Analyzer - Streamlit εκδοχή για Community Cloud."""
import os
import re
from html import escape
from io import BytesIO
from urllib.parse import quote_plus

import pandas as pd
import plotly.graph_objects as go
import PyPDF2
import streamlit as st
from openai import OpenAI
from supabase import create_client

from docx_utils import create_docx
from matching import match_jobs_to_cv
from skills_config import TECH_SKILLS, aggregate_skill_demand, match_cv_skills

st.set_page_config(page_title="AI Job Market Analyzer | Greece", page_icon="🚀", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------------
# Styling: το styles.css του frontend + προσαρμογές για τα widgets του Streamlit
# ------------------------------------------------------------------
EXTRA_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');
html, body, [class*="st-"], .stApp { font-family: 'Inter', sans-serif; }
span[data-testid="stIconMaterial"], .material-symbols-rounded, [class*="material-symbols"] { font-family: "Material Symbols Rounded" !important; }
.stApp { background: radial-gradient(circle at 15% 0%, #161B27 0%, #0B0E14 45%) fixed; }
#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 80rem; padding-top: 1.5rem; padding-bottom: 4rem; }

.brand { font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.15rem; color: #E2E8F0; padding-top: 0.4rem; }
.brand span.accent { color: #3B82F6; }
.hero { text-align: center; padding: 2.2rem 0 1.6rem 0; }
.hero h1 { font-family: 'Sora', sans-serif; font-weight: 800; font-size: 2.8rem; margin: 0 0 0.6rem 0; padding: 0; display: inline-block; }
.hero p { color: #8B96AC; margin: 0; }
.status-warn { display: inline-block; margin-top: 1.2rem; font-size: 0.85rem; padding: 0.5rem 1rem; border-radius: 8px;
  background: rgba(245,158,11,0.1); color: #FCD34D; border: 1px solid rgba(245,158,11,0.3); }

/* Tabs -> pill navigation */
.stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 4px; background: #12151F; border: 1px solid #232838;
  border-radius: 999px; padding: 4px; width: fit-content; margin: 0 auto 1.6rem auto; }
.stTabs button[data-baseweb="tab"] { border-radius: 999px; padding: 0.4rem 1.2rem; height: auto; color: #8B96AC; font-weight: 500; font-size: 0.875rem; }
.stTabs button[data-baseweb="tab"]:hover { color: #E2E8F0; }
.stTabs button[data-baseweb="tab"][aria-selected="true"] { background: linear-gradient(90deg, #3B82F6, #8B5CF6); color: white; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

/* Panels (st.container(key="panel_...")) */
[class*="st-key-panel"] { background: #12151F; border: 1px solid #232838; border-radius: 16px; padding: 1.5rem; }

/* Buttons */
.stButton > button[kind="primary"] { background: linear-gradient(90deg, #3B82F6, #8B5CF6); color: white; border: none;
  border-radius: 8px; font-weight: 600; font-size: 0.875rem; }
.stButton > button[kind="primary"]:hover { opacity: 0.85; color: white; }
.stButton > button[kind="secondary"], .stDownloadButton > button { background: #1B2030; color: #93C5FD; border: 1px solid #2E384D;
  border-radius: 8px; font-size: 0.82rem; font-weight: 600; }
.stButton > button[kind="secondary"]:hover, .stDownloadButton > button:hover { border-color: #3B82F6; color: #93C5FD; }

/* Uploader -> upload-zone */
[data-testid="stFileUploaderDropzone"] { background: transparent; border: 1.5px dashed #2E384D; border-radius: 12px; color: #8B96AC; }
[data-testid="stFileUploaderDropzone"]:hover { border-color: #3B82F6; }

/* Inputs */
div[data-baseweb="select"] > div, .stTextArea textarea, .stTextInput input { background: #0D0F17; border-color: #232838; color: #E2E8F0; }

/* Job / match cards */
.job-list { display: flex; flex-direction: column; gap: 1rem; }
.job-card h4 { font-family: 'Sora', sans-serif; font-weight: 600; font-size: 1.1rem; margin: 0; color: #E2E8F0; }
.job-card .meta { color: #94A3B8; font-size: 0.85rem; margin-top: 0.3rem; }
.job-card .meta strong { color: #CBD5E1; }
.job-card .desc { color: #CBD5E1; font-size: 0.88rem; line-height: 1.6; margin-top: 0.5rem; }
.link-btn { display: inline-block; margin-top: 0.7rem; font-size: 0.75rem; padding: 0.35rem 0.75rem; border-radius: 8px;
  background: #12151F; border: 1px solid #232838; color: #E2E8F0 !important; text-decoration: none !important; transition: border-color 0.15s ease; }
.link-btn:hover { border-color: #3B82F6; }
a.match-card { display: block; text-decoration: none !important; color: inherit !important; margin-bottom: 0.7rem; transition: border-color 0.15s ease; }
a.match-card:hover { border-color: #3B82F6; }
.match-top { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
.match-top h5 { margin: 0; font-size: 0.9rem; font-weight: 600; color: #E2E8F0; }
.match-top .skill-pill { white-space: nowrap; }
.subhead { font-size: 0.9rem; font-weight: 600; color: #CBD5E1; margin: 1rem 0 0.5rem 0; }
.small-note { font-size: 0.75rem; color: #64748B; margin-top: 0.4rem; }
.pills { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 1rem; }
.footer { text-align: center; font-size: 0.75rem; color: #475569; padding: 2.5rem 0 0.5rem 0; }
"""


def load_css() -> str:
    try:
        with open(os.path.join(BASE_DIR, "styles.css"), encoding="utf-8") as f:
            base = f.read()
    except OSError:
        base = ""
    css = EXTRA_CSS + "\n" + base
    return re.sub(r"\n\s*\n", "\n", css)  # καμία κενή γραμμή μέσα στο <style> (markdown-safe)


st.markdown(f"<style>{load_css()}</style>", unsafe_allow_html=True)


def esc(text) -> str:
    """HTML-escape + προστασία από markdown/LaTeX ($) όταν ενσωματώνουμε κείμενο σε HTML."""
    return escape(str(text or "")).replace("$", "&#36;")


def safe_url(url: str) -> str:
    url = (url or "").strip()
    return escape(url, quote=True) if url.startswith(("http://", "https://")) else "#"


def panel_title(text: str):
    st.markdown(f'<div class="panel-title">{esc(text)}</div>', unsafe_allow_html=True)


# ------------------------------------------------------------------
# Secrets / clients
# ------------------------------------------------------------------
def get_secret(name: str) -> str:
    """Πρώτα st.secrets (Cloud), μετά μεταβλητές περιβάλλοντος (τοπικά/.env)."""
    try:
        if name in st.secrets:
            return str(st.secrets[name]).strip()
    except Exception:
        pass
    return (os.environ.get(name) or "").strip()


@st.cache_resource
def get_supabase():
    url, key = get_secret("SUPABASE_URL"), get_secret("SUPABASE_KEY")
    if not (url and key):
        return None
    try:
        return create_client(url, key)
    except Exception as e:
        st.error(f"Αποτυχία σύνδεσης Supabase: {e}")
        return None


@st.cache_resource
def get_openai():
    key = get_secret("OPENAI_API_KEY")
    return OpenAI(api_key=key) if key else None


supabase = get_supabase()
openai_client = get_openai()


# ------------------------------------------------------------------
# Προαιρετικός κωδικός πρόσβασης (προστατεύει το OpenAI budget σου)
# ------------------------------------------------------------------
APP_PASSWORD = get_secret("APP_PASSWORD")
if APP_PASSWORD and not st.session_state.get("authed"):
    st.markdown('<div class="hero"><h1 class="gradient-text">AI Job Market Analyzer</h1></div>', unsafe_allow_html=True)
    pwd = st.text_input("Κωδικός πρόσβασης", type="password")
    if pwd:
        if pwd == APP_PASSWORD:
            st.session_state["authed"] = True
            st.rerun()
        else:
            st.error("Λάθος κωδικός.")
    st.stop()


# ------------------------------------------------------------------
# Δεδομένα
# ------------------------------------------------------------------
@st.cache_data(ttl=600, show_spinner="Φόρτωση αγγελιών...")
def fetch_jobs() -> list[dict]:
    if not supabase:
        return []
    res = supabase.table("job_postings").select("*").execute()
    return res.data or []


def count_by(jobs: list[dict], field: str, default: str, mapping: dict | None = None) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for j in jobs:
        val = (j.get(field) or default).strip() or default
        if mapping:
            val = mapping.get(val, val)
        counts[val] = counts.get(val, 0) + 1
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)


def skills_demand(jobs: list[dict]) -> list[tuple[str, int]]:
    counts = aggregate_skill_demand([j.get("description") or "" for j in jobs], TECH_SKILLS)
    return sorted(counts.items(), key=lambda kv: kv[1], reverse=True)


def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PyPDF2.PdfReader(BytesIO(file_bytes))
    return "\n".join((page.extract_text() or "") for page in reader.pages).strip()


def ask_openai(prompt: str, temperature: float) -> str:
    res = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
    )
    return res.choices[0].message.content


# ------------------------------------------------------------------
# Charts (ίδια χρώματα με το Chart.js frontend)
# ------------------------------------------------------------------
def style_fig(fig: go.Figure, height: int = 320, legend: bool = False) -> go.Figure:
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#C7D2E5", family="Inter, sans-serif"),
        margin=dict(l=10, r=10, t=10, b=10), height=height, showlegend=legend,
        legend=dict(orientation="h", y=-0.1, font=dict(color="#C7D2E5")),
    )
    fig.update_xaxes(gridcolor="#1E2432", zeroline=False, tickfont=dict(color="#8B96AC"))
    fig.update_yaxes(gridcolor="#1E2432", zeroline=False, tickfont=dict(color="#C7D2E5"))
    return fig


def hbar(labels, values, fill: str, line: str, height: int = 320, hover: str = "%{x}") -> go.Figure:
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h",
        marker=dict(color=fill, line=dict(color=line, width=1)),
        hovertemplate="%{y}: " + hover + "<extra></extra>",
    ))
    style_fig(fig, height)
    fig.update_xaxes(rangemode="tozero")
    fig.update_yaxes(showgrid=False)
    return fig


REMOTE_LABELS = {
    "FULL": "Πλήρες Remote", "REMOTE": "Πλήρες Remote",
    "HYBRID": "Υβριδικό", "DISABLED": "On-site", "ONSITE": "On-site",
    "Άγνωστο": "Άγνωστο",
}

# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------
jobs = fetch_jobs()

top_l, top_r = st.columns([4, 1])
top_l.markdown('<div class="brand">🚀 Job<span class="accent">Market</span>AI</div>', unsafe_allow_html=True)
if top_r.button("🔄 Ανανέωση", use_container_width=True):
    fetch_jobs.clear()
    st.rerun()

issues = []
if not supabase:
    issues.append("Supabase δεν έχει ρυθμιστεί")
if not openai_client:
    issues.append("OpenAI key λείπει (CV feedback ανενεργό)")
banner = f'<div class="status-warn">⚠️ {esc(" · ".join(issues))}</div>' if issues else ""

st.markdown(
    '<div class="hero"><h1 class="gradient-text">Tech &amp; AI Job Trends (Greece)</h1>'
    '<p>Ζήτηση δεξιοτήτων στην ελληνική αγορά data &amp; AI, σε πραγματικό χρόνο.</p>'
    f"{banner}</div>",
    unsafe_allow_html=True,
)

if not supabase:
    st.stop()
if not jobs:
    st.warning("Ο πίνακας `job_postings` είναι άδειος. Τρέξε πρώτα το `scraper.py`.")
    st.stop()

tab_dash, tab_market, tab_jobs = st.tabs(["Dashboard", "Αγορά", "Αγγελίες"])

# ==================================================================
# DASHBOARD
# ==================================================================
with tab_dash:
    skills = skills_demand(jobs)
    top_skill, top_demand = skills[0]
    total = len(jobs)
    m_top = top_skill if top_demand > 0 else "-"
    m_cov = f"{round(100 * top_demand / total)}%" if top_demand > 0 and total else "-"

    m1, m2, m3 = st.columns(3)
    for col, label, value in [(m1, "Συνολικές Αγγελίες", total), (m2, "Κορυφαία Τεχνολογία", m_top),
                              (m3, "Κάλυψη Top Skill", m_cov)]:
        col.markdown(
            f'<div class="metric-card"><div class="metric-label">{esc(label)}</div>'
            f'<div class="metric-value">{esc(value)}</div></div>',
            unsafe_allow_html=True,
        )
    st.write("")

    # Κατανομή ανά κλάδο
    with st.container(key="panel_categories"):
        panel_title("🏢 Κατανομή Αγγελιών ανά Επαγγελματικό Κλάδο")
        cats = count_by(jobs, "category", "Χωρίς κατηγορία")[:12][::-1]
        st.plotly_chart(
            hbar([c for c, _ in cats], [n for _, n in cats], "rgba(167,139,250,0.55)", "#A78BFA", 320),
            use_container_width=True, config={"displayModeBar": False},
        )
    st.write("")

    left, right = st.columns([3, 2])

    # Skills chart + pills
    with left:
        with st.container(key="panel_skills"):
            panel_title("📊 Κατανομή Ζήτησης Tech Δεξιοτήτων")
            asc = sorted(skills, key=lambda kv: kv[1])
            st.plotly_chart(
                hbar([s for s, _ in asc], [n for _, n in asc], "rgba(59,130,246,0.55)", "#3B82F6", 320),
                use_container_width=True, config={"displayModeBar": False},
            )
            demands = sorted(n for _, n in skills)
            median = demands[len(demands) // 2] if demands else 0
            pills = "".join(
                f'<span class="skill-pill {"pill-high" if n >= median else "pill-low"}">{esc(s)} · {n}</span>'
                for s, n in skills if n > 0
            )
            st.markdown(f'<div class="pills">{pills}</div>', unsafe_allow_html=True)

    # CV matcher
    with right:
        with st.container(key="panel_cv"):
            panel_title("📄 AI CV Matcher & Cover Letter")
            uploaded = st.file_uploader("📎 Ανέβασε Βιογραφικό (PDF)", type=["pdf"], label_visibility="collapsed")

            if uploaded is not None:
                sig = (uploaded.name, uploaded.size)
                if st.session_state.get("cv_sig") != sig:
                    try:
                        text = extract_pdf_text(uploaded.getvalue())
                    except Exception as e:
                        text = ""
                        st.error(f"Σφάλμα ανάγνωσης PDF: {e}")
                    if not text:
                        st.error("Δεν βρέθηκε επιλέξιμο κείμενο (πιθανώς σαρωμένη εικόνα).")
                    else:
                        st.session_state["cv_sig"] = sig
                        st.session_state["cv_text"] = text
                        for k in ("matches", "feedback", "cover_letter_text"):
                            st.session_state.pop(k, None)

            cv_text = st.session_state.get("cv_text", "") if uploaded is not None else ""

            if cv_text:
                demand = dict(skills)
                max_demand = max(demand.values(), default=0) or 1
                user_skills = match_cv_skills(cv_text, TECH_SKILLS)
                market_vals = [round(demand.get(s, 0) / max_demand, 3) for s in TECH_SKILLS]
                cv_vals = [user_skills[s] for s in TECH_SKILLS]
                theta = TECH_SKILLS + TECH_SKILLS[:1]

                radar = go.Figure()
                radar.add_trace(go.Scatterpolar(r=market_vals + market_vals[:1], theta=theta, fill="toself", name="Αγορά",
                                                line=dict(color="#3B82F6"), fillcolor="rgba(59,130,246,0.2)"))
                radar.add_trace(go.Scatterpolar(r=cv_vals + cv_vals[:1], theta=theta, fill="toself", name="CV σου",
                                                line=dict(color="#34D399"), fillcolor="rgba(52,211,153,0.2)"))
                radar.update_layout(
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(range=[0, 1], showticklabels=False, gridcolor="#1E2432", linecolor="#1E2432"),
                        angularaxis=dict(gridcolor="#1E2432", linecolor="#1E2432", tickfont=dict(size=10, color="#C7D2E5")),
                    ),
                    paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#C7D2E5"),
                    margin=dict(l=30, r=30, t=20, b=10), height=300,
                    legend=dict(orientation="h", y=-0.05, font=dict(color="#C7D2E5")),
                )
                st.plotly_chart(radar, use_container_width=True, config={"displayModeBar": False})

                if not openai_client:
                    st.info("Για αξιολόγηση, cover letter και αντιστοίχιση αγγελιών χρειάζεται OPENAI_API_KEY στα Secrets.")
                else:
                    b1, b2 = st.columns(2)
                    if b1.button("🔍 Αξιολόγηση", type="primary", use_container_width=True):
                        prompt = (
                            f"Ανάλυσε το CV: {cv_text[:2500]}. "
                            f"Ζητούμενα skills: {', '.join(TECH_SKILLS)}. "
                            "Δώσε: 1. Match Score (%) 2. Δυνατά σημεία (2-3 bullets) "
                            "3. Τι λείπει (2-3 bullets). Σύντομα, στα Ελληνικά."
                        )
                        with st.spinner("⏳ Ανάλυση..."):
                            try:
                                st.session_state["feedback"] = ask_openai(prompt, 0.3)
                            except Exception as e:
                                st.error(f"Σφάλμα OpenAI: {e}")

                    if b2.button("✉️ Cover Letter", type="primary", use_container_width=True):
                        prompt = (
                            "Γράψε επαγγελματικό Cover Letter στα Ελληνικά για θέση Data/AI, "
                            f"βασισμένο στο εξής CV: {cv_text[:2500]}"
                        )
                        with st.spinner("⏳ Σύνταξη..."):
                            try:
                                st.session_state["cover_letter_text"] = ask_openai(prompt, 0.4)
                            except Exception as e:
                                st.error(f"Σφάλμα OpenAI: {e}")

                    if st.button("🎯 Βρες Ταιριαστές Αγγελίες", type="primary", use_container_width=True):
                        with st.spinner("⏳ Ψάχνει ταιριαστές αγγελίες..."):
                            try:
                                st.session_state["matches"] = match_jobs_to_cv(openai_client, cv_text, jobs, top_n=5)
                            except Exception as e:
                                st.error(f"Σφάλμα OpenAI embeddings: {e}")

                if "matches" in st.session_state:
                    st.markdown('<div class="subhead">🎯 Καλύτερες Αγγελίες για Εσένα</div>', unsafe_allow_html=True)
                    if not st.session_state["matches"]:
                        st.markdown('<div class="small-note">Δεν βρέθηκαν αγγελίες προς σύγκριση.</div>', unsafe_allow_html=True)
                    else:
                        cards = "".join(
                            f'<a class="job-card match-card" href="{safe_url(m.get("url"))}" target="_blank" rel="noopener">'
                            f'<div class="match-top"><h5>{esc(m.get("title") or "Θέση")}</h5>'
                            f'<span class="skill-pill pill-high">{round(m["score"] * 100)}% σχετική ταύτιση</span></div>'
                            f'<div class="meta">{esc(m.get("company") or "Εταιρεία")}'
                            f'{" · " + esc(m["category"]) if m.get("category") else ""}</div></a>'
                            for m in st.session_state["matches"]
                        )
                        st.markdown(cards, unsafe_allow_html=True)
                        st.markdown(
                            '<div class="small-note">* Ποσοστό σε σχέση με τις υπόλοιπες διαθέσιμες αγγελίες '
                            "αυτή τη στιγμή, όχι απόλυτη βαθμολογία.</div>",
                            unsafe_allow_html=True,
                        )

                if st.session_state.get("feedback"):
                    st.markdown('<div class="subhead">📋 AI Recruiter Feedback</div>', unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="info-box">{esc(st.session_state["feedback"]).replace(chr(10), "<br>")}</div>',
                        unsafe_allow_html=True,
                    )
                    st.download_button(
                        "📥 Λήψη Αναφοράς (.docx)",
                        create_docx("Τεχνική Αξιολόγηση Βιογραφικού", st.session_state["feedback"], "Evaluation Report"),
                        file_name="CV_Market_Evaluation.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="dl_feedback",
                    )

                if "cover_letter_text" in st.session_state:
                    st.markdown('<div class="subhead">✉️ Cover Letter</div>', unsafe_allow_html=True)
                    st.text_area("Cover Letter", key="cover_letter_text", height=220, label_visibility="collapsed")
                    st.download_button(
                        "📥 Λήψη (.docx)",
                        create_docx("Συνοδευτική Επιστολή Υποψηφιότητας", st.session_state["cover_letter_text"], "Cover Letter"),
                        file_name="Cover_Letter.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key="dl_cover",
                    )

# ==================================================================
# ΑΓΟΡΑ (insights)
# ==================================================================
with tab_market:
    c1, c2 = st.columns(2)

    with c1:
        with st.container(key="panel_remote"):
            panel_title("🏠 Remote / Hybrid / On-site")
            remote = count_by(jobs, "remote", "Άγνωστο", REMOTE_LABELS)
            palette = ["#3B82F6", "#A78BFA", "#F472B6", "#34D399", "#94A3B8"]
            fig = go.Figure(go.Pie(
                labels=[r for r, _ in remote], values=[n for _, n in remote], hole=0.55,
                marker=dict(colors=[palette[i % len(palette)] for i in range(len(remote))],
                            line=dict(color="#0B0E14", width=2)),
                textfont=dict(color="#0B0E14"),
            ))
            style_fig(fig, 300, legend=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        with st.container(key="panel_salary"):
            panel_title("💰 Μέσος Μισθός ανά Κλάδο")
            buckets: dict[str, list[float]] = {}
            for j in jobs:
                smin, smax = j.get("salary_min"), j.get("salary_max")
                if smin is None and smax is None:
                    continue
                try:
                    mid = (float(smin if smin is not None else smax) +
                           float(smax if smax is not None else smin)) / 2
                except (TypeError, ValueError):
                    continue
                cat = (j.get("category") or "Χωρίς κατηγορία").strip() or "Χωρίς κατηγορία"
                buckets.setdefault(cat, []).append(mid)

            if buckets:
                sal = sorted(((c, round(sum(v) / len(v))) for c, v in buckets.items()), key=lambda kv: kv[1])[-12:]
                st.plotly_chart(
                    hbar([c for c, _ in sal], [v for _, v in sal], "rgba(52,211,153,0.55)", "#34D399", 300, "~€%{x:,.0f}"),
                    use_container_width=True, config={"displayModeBar": False},
                )
            else:
                st.markdown(
                    '<div class="small-note">Δεν βρέθηκαν αρκετά δεδομένα μισθού στις τρέχουσες αγγελίες.</div>',
                    unsafe_allow_html=True,
                )

    st.write("")
    with st.container(key="panel_locations"):
        panel_title("📍 Κατανομή ανά Τοποθεσία")
        locs = count_by(jobs, "location", "Άγνωστο")[:15][::-1]
        st.plotly_chart(
            hbar([l for l, _ in locs], [n for _, n in locs], "rgba(244,114,182,0.5)", "#F472B6", 360),
            use_container_width=True, config={"displayModeBar": False},
        )

# ==================================================================
# ΑΓΓΕΛΙΕΣ
# ==================================================================
with tab_jobs:
    h1, h2 = st.columns([3, 1])
    with h1:
        panel_title("📋 Ελληνικές Θέσεις Εργασίας")
    with h2:
        choice = st.selectbox("Τεχνολογία", ["Όλες οι τεχνολογίες"] + TECH_SKILLS, label_visibility="collapsed")

    shown = jobs
    if choice != "Όλες οι τεχνολογίες":
        pattern = re.compile(rf"\b{re.escape(choice)}\b", re.IGNORECASE)
        shown = [j for j in jobs if pattern.search(j.get("description") or "")]

    st.markdown(f'<div class="meta" style="color:#94A3B8;font-size:0.85rem;margin-bottom:1rem">Εμφάνιση {len(shown)} αγγελιών</div>',
                unsafe_allow_html=True)

    if not shown:
        st.markdown('<div class="panel" style="text-align:center;color:#94A3B8">Δεν βρέθηκαν αγγελίες.</div>',
                    unsafe_allow_html=True)
    else:
        limit = st.session_state.get("jobs_limit", 40)
        cards = []
        for job in shown[:limit]:
            title = job.get("title") or "Θέση"
            company = job.get("company") or "Εταιρεία"
            posted = (job.get("posted_at") or "")[:10] or "N/A"
            desc = re.sub(r"\s+", " ", job.get("description") or "").strip()
            link = job.get("url") or (
                "https://www.google.com/search?q=" + quote_plus(f"{title} {company} Athens Greece")
            )
            cards.append(
                '<div class="job-card">'
                f"<h4>💼 {esc(title)}</h4>"
                f'<div class="meta"><strong>{esc(company)}</strong> &nbsp;·&nbsp; {esc(posted)}</div>'
                f'<a class="link-btn" href="{safe_url(link)}" target="_blank" rel="noopener">🔗 Αναζήτηση Θέσης</a>'
                f"<details><summary>Περιγραφή Θέσης</summary><p class=\"desc\">{esc(desc)}</p></details>"
                "</div>"
            )
        st.markdown(f'<div class="job-list">{"".join(cards)}</div>', unsafe_allow_html=True)

        if len(shown) > limit:
            st.write("")
            if st.button(f"Φόρτωσε περισσότερες ({len(shown) - limit} ακόμα)"):
                st.session_state["jobs_limit"] = limit + 40
                st.rerun()

st.markdown('<div class="footer">AI Job Market Analyzer · kariera.gr δεδομένα</div>', unsafe_allow_html=True)