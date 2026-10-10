import re
import pandas as pd
import streamlit as st
from io import BytesIO, StringIO

# ===== النصوص العربية بصيغة يونيكود حتى ما ينكسر اللصق =====
T = {
    "page": "\u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u062a\u0648\u0632\u064a\u0639",
    "title": "\u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u062a\u0648\u0632\u064a\u0639 \u062d\u0633\u0628 \u0627\u0644\u0645\u0643\u062a\u0628",
    "up_agents": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
    "up_dist": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u062a\u0648\u0632\u064a\u0639",
    "up_quality": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0643\u0648\u0627\u0644\u062a\u064a",
    "sheet": "\u0634\u064a\u062a",
    "agents": "\u0627\u0644\u0648\u0643\u0644\u0627\u0621",
    "dist": "\u0627\u0644\u062a\u0648\u0632\u064a\u0639",
    "quality": "\u0627\u0644\u0643\u0648\u0627\u0644\u062a\u064a",
    "calc": "\u0627\u062d\u0633\u0628",
    "office_name": "\u0627\u0633\u0645 \u0627\u0644\u0645\u0643\u062a\u0628",
    "office_no": "\u0631\u0642\u0645 \u0627\u0644\u0645\u0643\u062a\u0628",
    "item": "\u0627\u0644\u0635\u0646\u0641",
    "total": "\u0627\u0644\u0645\u062c\u0645\u0648\u0639",
    "unmatched": "\u063a\u064a\u0631 \u0645\u0637\u0627\u0628\u0642",
    "empty": "\u0645\u0627 \u0628\u0642\u0649 \u0623\u064a \u0635\u0641 \u0628\u0639\u062f \u0627\u0644\u0641\u0644\u062a\u0631\u0629. \u062a\u0623\u0643\u062f \u0645\u0646 \u0639\u0645\u0648\u062f E \u0648\u0627\u0644\u0623\u0635\u0646\u0627\u0641.",
    "done": "\u062a\u0645. \u0639\u062f\u062f \u0627\u0644\u0645\u0643\u0627\u062a\u0628",
    "unm_rows": "\u0635\u0641\u0648\u0641 \u063a\u064a\u0631 \u0645\u0637\u0627\u0628\u0642\u0629",
    "orig": "\u0635\u0641\u0648\u0641 \u0627\u0644\u062a\u0648\u0632\u064a\u0639 \u0627\u0644\u0623\u0635\u0644\u064a\u0629",
    "dedup": "\u0628\u0639\u062f \u0625\u0632\u0627\u0644\u0629 \u0627\u0644\u0645\u0643\u0631\u0631 (\u0622\u062e\u0631 \u062a\u0627\u0631\u064a\u062e)",
    "real": "\u0627\u0644\u0645\u0648\u0632\u0651\u0639 \u0641\u0639\u0644\u064a\u0627\u064b",
    "bad_dates": "\u062a\u0648\u0627\u0631\u064a\u062e \u063a\u064a\u0631 \u0645\u0642\u0631\u0648\u0621\u0629",
    "download": "\u062a\u062d\u0645\u064a\u0644 \u0627\u0644\u0646\u062a\u064a\u062c\u0629 (\u0625\u0643\u0633\u0644)",
    "file_name": "distribution_result.xlsx",
    "act_red": "\u062a\u0641\u0639\u064a\u0644 \u0643\u0644\u064a \u0631\u064a\u062f",
    "act_use": "\u062a\u0641\u0639\u064a\u0644 \u0643\u0644\u064a \u064a\u0648\u0632",
    "act_net": "\u062a\u0641\u0639\u064a\u0644 \u0643\u0644\u064a \u0646\u062a",
    "last_ru": "\u062a\u0641\u0639\u064a\u0644 \u0622\u062e\u0631 \u064a\u0648\u0645 (\u0631\u064a\u062f + \u064a\u0648\u0632)",
    "last_net": "\u062a\u0641\u0639\u064a\u0644 \u0622\u062e\u0631 \u064a\u0648\u0645 (\u0646\u062a)",
    "q_info": "\u0627\u0644\u0643\u0648\u0627\u0644\u062a\u064a: \u0639\u062f\u062f \u0627\u0644\u0635\u0641\u0648\u0641",
    "q_last": "\u0622\u062e\u0631 \u064a\u0648\u0645",
    "q_ignored": "\u0635\u0641\u0648\u0641 \u0645\u062a\u062c\u0627\u0647\u0644\u0629 (\u0646\u0648\u0639 \u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641)",
    "q_baddate": "\u062a\u0648\u0627\u0631\u064a\u062e \u0643\u0648\u0627\u0644\u062a\u064a \u063a\u064a\u0631 \u0645\u0642\u0631\u0648\u0621\u0629",
    "read_fail": "\u062a\u0639\u0630\u0631 \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u0645\u0644\u0641",
}

# الاصناف: Red, Use, Monthly, Daily net, Big router, Small mifi, 1M use
RED = "\u0631\u064a\u062f"
USE = "\u064a\u0648\u0632"
MONTHLY = "\u062e\u0637 \u0634\u0647\u0631\u064a"
DAILY = "\u062e\u0637 \u0646\u062a \u064a\u0648\u0645\u064a"
BIG_ROUTER = "\u0631\u0627\u0648\u062a\u0631 \u0643\u0628\u064a\u0631"
SMALL_MIFI = "\u0645\u0627\u064a \u0641\u0627\u064a \u0635\u063a\u064a\u0631"
USE_1M = "\u062e\u0637 \u064a\u0648\u0632 \u0645\u0644\u064a\u0648\u0646\u064a"

item_map = {
    "pre-paid sim card - type2": RED,
    "pre-paid sim card": RED,
    "youth line sim card": USE,
    "white list usim preloaded with iqd 40000": MONTHLY,
    "gprs sim card with package": DAILY,
    "gprs sim card with tozed cpe cat6": BIG_ROUTER,
    "gprs sim card with mifi huawei cat4": SMALL_MIFI,
    "nms-1 million coin silver": USE_1M,
}

# Quality report: column B code -> group
QUALITY_TYPE = {
    "2": "net",
    "93": "red",
    "4": "red",
    "32": "use",
}

# Quality report columns by position (A=0, B=1, C=2, D=3, ...)
Q_TYPE_COL = 1      # B = line type code
Q_OFFICE_COL = 2    # C = office number
DATE_COL = 3        # D = activation date (CHANGE THIS if the date is in another column)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

st.set_page_config(page_title=T["page"], layout="wide")
st.title(T["title"])


def last10(num):
    if pd.isna(num):
        return None
    s = re.sub(r"\D", "", str(num))
    if s:
        return s[-10:]
    return None


def clean_code(val):
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def detect_kind(raw):
    head = raw[:2048]
    if head[:4] == b"PK\x03\x04":
        return "xlsx"
    if head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return "xls"
    low = head.lower()
    if b"<html" in low or b"<table" in low or b"<!doctype" in low:
        return "html"
    return "csv"


def decode_text(raw):
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig", errors="ignore")
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1256", errors="ignore")


def read_any(raw, kind):
    if kind == "xlsx":
        return pd.read_excel(BytesIO(raw), sheet_name=None, dtype=str, engine="openpyxl")
    if kind == "xls":
        return pd.read_excel(BytesIO(raw), sheet_name=None, dtype=str, engine="xlrd")
    text = decode_text(raw)
    if kind == "html":
        tables = pd.read_html(StringIO(text), flavor="lxml")
        return {"sheet1": tables[0].astype(str).replace("nan", pd.NA)}
    head = text[:4096]
    sep = ","
    if head.count("\t") > head.count(","):
        sep = "\t"
    return {"sheet1": pd.read_csv(StringIO(text), sep=sep, dtype=str)}


def load_report(file, label):
    raw = file.getvalue()
    kind = detect_kind(raw)
    try:
        return read_any(raw, kind)
    except Exception as e:
        st.error(T["read_fail"] + " (" + label + "): " + str(e))
        st.stop()


def pick_sheet(sheets, label):
    names = list(sheets.keys())
    if len(names) == 1:
        return sheets[names[0]]
    chosen = st.selectbox(T["sheet"] + " " + label, names, key="sheet_" + label)
    return sheets[chosen]


c1, c2, c3 = st.columns(3)
with c1:
    agents_file = st.file_uploader(T["up_agents"], key="agents")
with c2:
    dist_file = st.file_uploader(T["up_dist"], key="dist")
with c3:
    quality_file = st.file_uploader(T["up_quality"], key="quality")

if agents_file is not None and dist_file is not None:
    with c1:
        agents = pick_sheet(load_report(agents_file, T["agents"]), T["agents"])
    with c2:
        dist = pick_sheet(load_report(dist_file, T["dist"]), T["dist"])
    q = None
    if quality_file is not None:
        with c3:
            q = pick_sheet(load_report(quality_file, T["quality"]), T["quality"])

    if st.button(T["calc"]):
        # Agents: B = office number, A = office name
        agents_df = pd.DataFrame({
            "key": agents.iloc[:, 1].apply(last10),
            T["office_name"]: agents.iloc[:, 0],
        })
        agents_df = agents_df.dropna(subset=["key"]).drop_duplicates("key")
