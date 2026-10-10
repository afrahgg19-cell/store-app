import re
import pandas as pd
import streamlit as st
from io import BytesIO

# ===== النصوص العربية بصيغة يونيكود حتى ما ينكسر اللصق =====
T = {
    "page": "\u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u062a\u0648\u0632\u064a\u0639",
    "title": "\u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u062a\u0648\u0632\u064a\u0639 \u062d\u0633\u0628 \u0627\u0644\u0645\u0643\u062a\u0628",
    "up_agents": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0648\u0643\u0644\u0627\u0621",
    "up_dist": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u062a\u0648\u0632\u064a\u0639",
    "sheet": "\u0634\u064a\u062a",
    "agents": "\u0627\u0644\u0648\u0643\u0644\u0627\u0621",
    "dist": "\u0627\u0644\u062a\u0648\u0632\u064a\u0639",
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


def pick_sheet(file, label):
    xls = pd.ExcelFile(file)
    if len(xls.sheet_names) == 1:
        return xls, xls.sheet_names[0]
    chosen = st.selectbox(T["sheet"] + " " + label, xls.sheet_names, key="sheet_" + label)
    return xls, chosen


c1, c2 = st.columns(2)
with c1:
    agents_file = st.file_uploader(T["up_agents"], type=["xlsx", "xls"], key="agents")
with c2:
    dist_file = st.file_uploader(T["up_dist"], type=["xlsx", "xls"], key="dist")

if agents_file is not None and dist_file is not None:
    with c1:
        xls_a, sheet_a = pick_sheet(agents_file, T["agents"])
    with c2:
        xls_d, sheet_d = pick_sheet(dist_file, T["dist"])

    if st.button(T["calc"]):
        agents = pd.read_excel(xls_a, sheet_name=sheet_a, dtype=str)
        dist = pd.read_excel(xls_d, sheet_name=sheet_d, dtype=str)

        # Agents: B = office number, A = office name
        agents_df = pd.DataFrame({
            "key": agents.iloc[:, 1].apply(last10),
            T["office_name"]: agents.iloc[:, 0],
        })
        agents_df = agents_df.dropna(subset=["key"]).drop_duplicates("key")

        # Distribution: A line, C item, E status, F office number, I date
        d = pd.DataFrame({
            "line": dist.iloc[:, 0].astype(str).str.strip(),
            "item": dist.iloc[:, 2].astype(str).str.strip().str.lower(),
            "status": dist.iloc[:, 4].astype(str).str.strip().str.lower(),
            "key": dist.iloc[:, 5].apply(last10),
            "date": pd.to_datetime(dist.iloc[:, 8], errors="coerce"),
        })

        total_rows = len(d)
        bad_dates = int(d["date"].isna().sum())

        # keep the latest record per line
        d = d.sort_values("date", kind="stable")
        d = d.drop_duplicates(subset="line", keep="last")
        after_dedup = len(d)

        # then keep only Distributed
        d = d[d["status"] == "distributed"].copy()
        d[T["item"]] = d["item"].map(item_map)
        d = d.dropna(subset=[T["item"]])

        if d.empty:
            st.error(T["empty"])
            st.stop()

        merged = d.merge(agents_df, on="key", how="left")
        unmatched = int(merged[T["office_name"]].isna().sum())

        result = pd.crosstab(
            [merged["key"], merged[T["office_name"]].fillna(T["unmatched"])],
            merged[T["item"]],
        )
        result[T["total"]] = result.sum(axis=1)
        result = result.sort_values(T["total"], ascending=False).reset_index()
        result = result.rename(columns={"key": T["office_no"]})

        st.success(T["done"] + ": " + str(len(result)) + " | " + T["unm_rows"] + ": " + str(unmatched))
        st.info(
            T["orig"] + ": " + str(total_rows)
            + " | " + T["dedup"] + ": " + str(after_dedup)
            + " | " + T["real"] + ": " + str(len(d))
            + " | " + T["bad_dates"] + ": " + str(bad_dates)
        )
        st.dataframe(result, use_container_width=True)

        buf = BytesIO()
        result.to_excel(buf, index=False)
        st.download_button(
            T["download"],
            data=buf.getvalue(),
            file_name=T["file_name"],
            mime=XLSX_MIME,
        )
