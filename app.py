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
    # turns 93.0 or " 93 " into "93"
    if pd.isna(val):
        return None
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def pick_sheet(file, label):
    xls = pd.ExcelFile(file)
    if len(xls.sheet_names) == 1:
        return xls, xls.sheet_names[0]
    chosen = st.selectbox(T["sheet"] + " " + label, xls.sheet_names, key="sheet_" + label)
    return xls, chosen


c1, c2, c3 = st.columns(3)
with c1:
    agents_file = st.file_uploader(T["up_agents"], type=["xlsx", "xls"], key="agents")
with c2:
    dist_file = st.file_uploader(T["up_dist"], type=["xlsx", "xls"], key="dist")
with c3:
    quality_file = st.file_uploader(T["up_quality"], type=["xlsx", "xls"], key="quality")

if agents_file is not None and dist_file is not None:
    with c1:
        xls_a, sheet_a = pick_sheet(agents_file, T["agents"])
    with c2:
        xls_d, sheet_d = pick_sheet(dist_file, T["dist"])
    if quality_file is not None:
        with c3:
            xls_q, sheet_q = pick_sheet(quality_file, T["quality"])

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

        # ===== Quality report (optional third upload) =====
        q_msg = None
        if quality_file is not None:
            q = pd.read_excel(xls_q, sheet_name=sheet_q, dtype=str)

            qd = pd.DataFrame({
                "group": q.iloc[:, Q_TYPE_COL].apply(clean_code).map(QUALITY_TYPE),
                "key": q.iloc[:, Q_OFFICE_COL].apply(last10),
                "date": pd.to_datetime(q.iloc[:, DATE_COL], errors="coerce"),
            })

            q_total = len(qd)
            q_ignored = int(qd["group"].isna().sum())
            q_baddate = int(qd["date"].isna().sum())

            qd = qd.dropna(subset=["group", "key"]).copy()

            # all-time activation per group
            tot = pd.crosstab(qd["key"], qd["group"])
            for g in ["red", "use", "net"]:
                if g not in tot.columns:
                    tot[g] = 0
            tot = tot[["red", "use", "net"]]
            tot.columns = [T["act_red"], T["act_use"], T["act_net"]]

            # last day activation
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

            # rename last-day columns to include the actual date
            if last_day is not None:
                day_txt = str(last_day.date())
                q_all = q_all.rename(columns={
                    T["last_ru"]: T["last_ru"] + " " + day_txt,
                    T["last_net"]: T["last_net"] + " " + day_txt,
                })

            result = result.merge(q_all, on=T["office_no"], how="outer")

            # fill office names for offices that only exist in quality
            name_map = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
            result[T["office_name"]] = result[T["office_name"]].fillna(
                result[T["office_no"]].map(name_map)
            ).fillna(T["unmatched"])

            num_cols = [c for c in result.columns if c not in (T["office_no"], T["office_name"])]
            result[num_cols] = result[num_cols].fillna(0).astype(int)

            q_msg = (
                T["q_info"] + ": " + str(q_total)
                + " | " + T["q_ignored"] + ": " + str(q_ignored)
                + " | " + T["q_baddate"] + ": " + str(q_baddate)
                + " | " + T["q_last"] + ": " + (str(last_day.date()) if last_day is not None else "-")
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
        st.dataframe(result, use_container_width=True)

        buf = BytesIO()
        result.to_excel(buf, index=False)
        st.download_button(
            T["download"],
            data=buf.getvalue(),
            file_name=T["file_name"],
            mime=XLSX_MIME,
        )
