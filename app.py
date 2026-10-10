import re
import traceback
import pandas as pd
import streamlit as st
from io import BytesIO, StringIO

st.set_page_config(page_title="Distribution", layout="wide")

T = {
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
    "preview": "\u0645\u0639\u0627\u064a\u0646\u0629 \u0623\u0648\u0644 5 \u0635\u0641\u0648\u0641",
    "err": "\u062d\u062f\u062b \u062e\u0637\u0623",
}

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

QUALITY_TYPE = {"2": "net", "93": "red", "4": "red", "32": "use"}

Q_TYPE_COL = 1
Q_OFFICE_COL = 2
DATE_COL = 3

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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
        tables = pd.read_html(StringIO(text))
        return {"sheet1": tables[0].astype(str)}
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
        st.error(T["read_fail"] + " (" + label + ", " + kind + "): " + str(e))
        return None


def pick_sheet(sheets, label):
    names = list(sheets.keys())
    if len(names) == 1:
        return sheets[names[0]]
    chosen = st.selectbox(T["sheet"] + " " + label, names, key="sheet_" + label)
    return sheets[chosen]


def compute(agents, dist, q):
    agents_df = pd.DataFrame({
        "key": agents.iloc[:, 1].apply(last10),
        T["office_name"]: agents.iloc[:, 0],
    })
    agents_df = agents_df.dropna(subset=["key"]).drop_duplicates("key")

    d = pd.DataFrame({
        "line": dist.iloc[:, 0].astype(str).str.strip(),
        "item": dist.iloc[:, 2].astype(str).str.strip().str.lower(),
        "status": dist.iloc[:, 4].astype(str).str.strip().str.lower(),
        "key": dist.iloc[:, 5].apply(last10),
        "date": pd.to_datetime(dist.iloc[:, 8], errors="coerce"),
    })

    total_rows = len(d)
    bad_dates = int(d["date"].isna().sum())

    d = d.sort_values("date", kind="stable")
    d = d.drop_duplicates(subset="line", keep="last")
    after_dedup = len(d)

    d = d[d["status"] == "distributed"].copy()
    d[T["item"]] = d["item"].map(item_map)
    d = d.dropna(subset=[T["item"]])

    if d.empty:
        st.error(T["empty"])
        return None

    merged = d.merge(agents_df, on="key", how="left")
    unmatched = int(merged[T["office_name"]].isna().sum())

    result = pd.crosstab(
        [merged["key"], merged[T["office_name"]].fillna(T["unmatched"])],
        merged[T["item"]],
    )
    result[T["total"]] = result.sum(axis=1)
    result = result.sort_values(T["total"], ascending=False).reset_index()
    result = result.rename(columns={"key": T["office_no"]})

    q_msg = None
    if q is not None:
        qd = pd.DataFrame({
            "group": q.iloc[:, Q_TYPE_COL].apply(clean_code).map(QUALITY_TYPE),
            "key": q.iloc[:, Q_OFFICE_COL].apply(last10),
            "date": pd.to_datetime(q.iloc[:, DATE_COL], errors="coerce"),
        })

        q_total = len(qd)
        q_ignored = int(qd["group"].isna().sum())
        q_baddate = int(qd["date"].isna().sum())

        qd = qd.dropna(subset=["group", "key"]).copy()

        tot = pd.crosstab(qd["key"], qd["group"])
        for g in ["red", "use", "net"]:
            if g not in tot.columns:
                tot[g] = 0
        tot = tot[["red", "use", "net"]]
        tot.columns = [T["act_red"], T["act_use"], T["act_net"]]

        qdd = qd.dropna(subset=["date"]).copy()
        if qdd.empty:
            last_day = None
            last_tbl = pd.DataFrame(columns=[T["last_ru"], T["last_net"]])
        else:
            qdd["day"] = qdd["date"].dt.normalize()
            last_day = qdd["day"].max()
            ld = qdd[qdd["day"] == last_day]
            ru = ld[ld["group"].isin(["red", "use"])].groupby("key").size()
            nt = ld[ld["group"] == "net"].groupby("key").size()
            last_tbl = pd.DataFrame({T["last_ru"]: ru, T["last_net"]: nt})

        q_all = tot.join(last_tbl, how="outer").fillna(0).astype(int)
        q_all.index.name = T["office_no"]
        q_all = q_all.reset_index()

        if last_day is not None:
            day_txt = str(last_day.date())
            q_all = q_all.rename(columns={
                T["last_ru"]: T["last_ru"] + " " + day_txt,
                T["last_net"]: T["last_net"] + " " + day_txt,
            })

        result = result.merge(q_all, on=T["office_no"], how="outer")

        name_map = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
        result[T["office_name"]] = result[T["office_name"]].fillna(
            result[T["office_no"]].map(name_map)
        ).fillna(T["unmatched"])

        num_cols = [c for c in result.columns if c not in (T["office_no"], T["office_name"])]
        result[num_cols] = result[num_cols].fillna(0).astype(int)

        last_txt = "-"
        if last_day is not None:
            last_txt = str(last_day.date())
        q_msg = (
            T["q_info"] + ": " + str(q_total)
            + " | " + T["q_ignored"] + ": " + str(q_ignored)
            + " | " + T["q_baddate"] + ": " + str(q_baddate)
            + " | " + T["q_last"] + ": " + last_txt
        )

    st.success(T["done"] + ": " + str(len(result)) + " | " + T["unm_rows"] + ": " + str(unmatched))
    st.info(
        T["orig"] + ": " + str(total_rows)
        + " | " + T["dedup"] + ": " + str(after_dedup)
        + " | " + T["real"] + ": " + str(len(d))
        + " | " + T["bad_dates"] + ": " + str(bad_dates)
    )
    if q_msg is not None:
        st.info(q_msg)
    return result


st.title(T["title"])

c1, c2, c3 = st.columns(3)
with c1:
    agents_file = st.file_uploader(T["up_agents"], key="agents")
with c2:
    dist_file = st.file_uploader(T["up_dist"], key="dist")
with c3:
    quality_file = st.file_uploader(T["up_quality"], key="quality")

if agents_file is not None and dist_file is not None:
    agents = None
    dist = None
    q = None

    with c1:
        sh = load_report(agents_file, T["agents"])
        if sh is not None:
            agents = pick_sheet(sh, T["agents"])
    with c2:
        sh = load_report(dist_file, T["dist"])
        if sh is not None:
            dist = pick_sheet(sh, T["dist"])
    if quality_file is not None:
        with c3:
            sh = load_report(quality_file, T["quality"])
            if sh is not None:
                q = pick_sheet(sh, T["quality"])

    if agents is not None and dist is not None:
        with st.expander(T["preview"]):
            st.write(T["agents"])
            st.dataframe(agents.head(5))
            st.write(T["dist"])
            st.dataframe(dist.head(5))
            if q is not None:
                st.write(T["quality"])
                st.dataframe(q.head(5))

        if st.button(T["calc"]):
            try:
                result = compute(agents, dist, q)
                if result is not None:
                    st.dataframe(result, use_container_width=True)
                    buf = BytesIO()
                    result.to_excel(buf, index=False)
                    st.download_button(
                        T["download"],
                        data=buf.getvalue(),
                        file_name=T["file_name"],
                        mime=XLSX_MIME,
                    )
            except Exception:
                st.error(T["err"])
                st.code(traceback.format_exc())
