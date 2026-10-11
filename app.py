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
    "last_ru": "\u062a\u0641\u0639\u064a\u0644 \u0627\u0644\u062e\u0637 \u0627\u0644\u064a\u0648\u0645\u064a (\u064a\u0648\u0632 \u0648\u0631\u064a\u062f)",
    "last_net": "\u062a\u0641\u0639\u064a\u0644 \u0627\u0644\u0646\u062a \u0627\u0644\u064a\u0648\u0645\u064a",
    "q_info": "\u0627\u0644\u0643\u0648\u0627\u0644\u062a\u064a: \u0639\u062f\u062f \u0627\u0644\u0635\u0641\u0648\u0641",
    "q_last": "\u0622\u062e\u0631 \u064a\u0648\u0645",
    "q_ignored": "\u0635\u0641\u0648\u0641 \u0645\u062a\u062c\u0627\u0647\u0644\u0629 (\u0646\u0648\u0639 \u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641)",
    "q_baddate": "\u062a\u0648\u0627\u0631\u064a\u062e \u0643\u0648\u0627\u0644\u062a\u064a \u063a\u064a\u0631 \u0645\u0642\u0631\u0648\u0621\u0629",
    "pts_word": "\u0646\u0642\u0627\u0637",
    "pts_ru": "\u0646\u0642\u0627\u0637 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0627\u0644\u0643\u0644\u064a\u0629",
    "pts_net": "\u0646\u0642\u0627\u0637 \u0627\u0644\u0646\u062a \u0627\u0644\u0643\u0644\u064a\u0629",
    "pts_last_ru": "\u0646\u0642\u0627\u0637 \u0627\u0644\u0627\u062a\u0635\u0627\u0644 \u0627\u0644\u064a\u0648\u0645\u064a\u0629",
    "pts_last_net": "\u0646\u0642\u0627\u0637 \u0627\u0644\u0646\u062a \u0627\u0644\u064a\u0648\u0645\u064a\u0629",
    "up_inc": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u062d\u0627\u0641\u0632",
    "inc": "\u062d\u0627\u0641\u0632",
    "inc_info": "\u0627\u0644\u062d\u0627\u0641\u0632: \u0639\u062f\u062f \u0627\u0644\u0635\u0641\u0648\u0641",
    "inc_after": "\u0628\u0639\u062f \u0625\u0632\u0627\u0644\u0629 \u0627\u0644\u0635\u0641\u0631",
    "inc_offices": "\u0645\u0643\u0627\u062a\u0628 \u0628\u0627\u0644\u062d\u0627\u0641\u0632",
    "up_wal": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0645\u062d\u0627\u0641\u0638",
    "wal": "\u0645\u062d\u0641\u0638\u0629",
    "wal_info": "\u0627\u0644\u0645\u062d\u0627\u0641\u0638: \u0639\u062f\u062f \u0627\u0644\u0635\u0641\u0648\u0641",
    "wal_after": "\u0628\u0639\u062f \u0641\u0644\u062a\u0631 Y",
    "wal_offices": "\u0645\u0643\u0627\u062a\u0628 \u0628\u0627\u0644\u0645\u062d\u0627\u0641\u0638",
    "up_bnd": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0628\u0627\u0642\u0627\u062a",
    "bnd": "\u0627\u0644\u0628\u0627\u0642\u0627\u062a",
    "bnd_info": "\u0627\u0644\u0628\u0627\u0642\u0627\u062a: \u0639\u062f\u062f \u0627\u0644\u0635\u0641\u0648\u0641",
    "bnd_unknown": "\u0628\u0627\u0642\u0627\u062a \u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629",
    "bnd_nodist": "\u062e\u0637\u0648\u0637 \u063a\u064a\u0631 \u0645\u0648\u0632\u0639\u0629",
    "bnd_mm": "\u0628\u0627\u0642\u0627\u062a \u0645\u062e\u0627\u0644\u0641\u0629",
    "bnd_col": "\u0639\u0645\u0648\u062f \u0627\u0633\u0645 \u0627\u0644\u0628\u0627\u0642\u0629",
    "bnd_noname": "\u0645\u0627 \u0644\u0642\u064a\u062a \u0639\u0645\u0648\u062f \u0627\u0633\u0645 \u0627\u0644\u0628\u0627\u0642\u0629 \u0628\u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0628\u0627\u0642\u0627\u062a",
    "bnd_unames": "\u0623\u0633\u0645\u0627\u0621 \u0628\u0627\u0642\u0627\u062a \u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629",
    "mm_ru": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0639\u0644\u0649 \u062e\u0637 \u0631\u064a\u062f",
    "mm_ur": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0639\u0644\u0649 \u062e\u0637 \u064a\u0648\u0632",
    "mm_title": "\u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0627\u0644\u0645\u062e\u0627\u0644\u0641\u0629 (\u0645\u0641\u0631\u0648\u0632\u0629 \u0644\u062d\u0627\u0644\u0647\u0627)",
    "line_lbl": "\u0631\u0642\u0645 \u0627\u0644\u062e\u0637",
    "dist_type": "\u0646\u0648\u0639 \u0627\u0644\u062a\u0648\u0632\u064a\u0639",
    "bundle_lbl": "\u0627\u0644\u0628\u0627\u0642\u0629",
    "mm_sheet": "\u0628\u0627\u0642\u0627\u062a \u0645\u062e\u0627\u0644\u0641\u0629",
    "bnd_empty": "\u0645\u0627 \u0644\u0642\u064a\u062a \u0628\u0627\u0642\u0627\u062a \u0645\u0637\u0627\u0628\u0642\u0629 \u0644\u062e\u0637\u0648\u0637 \u0645\u0648\u0632\u0639\u0629",
    "read_fail": "\u062a\u0639\u0630\u0631 \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u0645\u0644\u0641",
    "preview": "\u0645\u0639\u0627\u064a\u0646\u0629 \u0623\u0648\u0644 5 \u0635\u0641\u0648\u0641",
    "err": "\u062d\u062f\u062b \u062e\u0637\u0623",
}

RED = "\u0631\u064a\u062f"
USE = "\u064a\u0648\u0632"
MONTHLY = "\u0646\u062a \u0634\u0647\u0631\u064a"
DAILY = "\u0646\u062a \u064a\u0648\u0645\u064a"
BIG_ROUTER = "\u0631\u0627\u0648\u062a\u0631 \u0643\u0628\u064a\u0631"
SMALL_MIFI = "\u0631\u0627\u0648\u062a\u0631 \u0635\u063a\u064a\u0631"
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
Q_POINTS_COL = 17   # R = points
INC_OFFICE_COL = 0  # incentive: A = office number
INC_VALUE_COL = 7   # incentive: H = value (zeros removed)
WAL_OFFICE_COL = 1  # wallets: B = office number
WAL_FLAG_COL = 2    # wallets: C = flag (keep rows with Y)

# ===== Bundles report (A = line number, H = sub-type) =====
BND_LINE_COL = 0
BND_SUB_COL = 7

BUNDLE_DIRECT = {
    "red 15 4 weeks": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 3 \u0623\u0634\u0647\u0631",
    "red 30 4 weeks": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0634\u0647\u0631\u064a 30",
    "monthly10gb": "\u0628\u0627\u0642\u0629 \u0625\u0646\u062a\u0631\u0646\u062a \u0634\u0647\u0631\u064a\u0629 \u0628\u0644\u0627 \u062d\u062f\u0648\u062f",
    "yooz 15-extra voice for 12 weeks": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "yooz 15 extra voice": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "yooz 15 mix": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "yooz 15-extra data for 12 weeks": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "yooz 15 extra data": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "yooz 30 extra data": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 30",
    "yooz 25 extra data": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 25",
    "yooz 25 mix": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 25",
    "yooz 5 extra voice": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0627\u0645 5",
    "yooz 5 extra data": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0627\u0645 5",
    "red 5,000 weekly package": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 5",
    "red 10,000 for 20 days": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 10",
    "red 25 4 weeks": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 25",
}

BUNDLE_SPLIT = {
    "unlimited weekly 4g": {
        "base": "\u0628\u0627\u0642\u0629 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000 \u0628\u0644\u0627 \u062d\u062f\u0648\u062f",
        "sub": [
            ("usim-gprs-pkg", "\u0628\u0627\u0642\u0629 \u0646\u062a \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000"),
            ("usim-prp2", "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 12000 \u0623\u0633\u0628\u0648\u0639\u064a\u0629"),
            ("usim-yout", "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000"),
        ],
    },
    "unlimited 4g bundle": {
        "base": "\u0628\u0627\u0642\u0629 \u0623\u0631\u0628\u0639\u064a\u0646",
        "sub": [
            ("usim-gprs-pkg", "\u0628\u0627\u0642\u0629 \u0646\u062a \u0623\u0633\u0628\u0648\u0639\u064a\u0629 40"),
            ("usim-prp2", "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 40 \u0623\u0633\u0628\u0648\u0639\u064a\u0629"),
            ("usim-yout", "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 40"),
            ("usim-40kv", "\u0628\u0627\u0642\u0629 \u0646\u062a \u0634\u0647\u0631\u064a 40"),
        ],
    },
    "unlimited premium package fup": {
        "base": "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645",
        "sub": [
            ("usim-gprs-rtr2", "\u0628\u0627\u0642\u0629 \u0631\u0627\u0648\u062a\u0631 110"),
            ("usim-40kv", "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0646\u062a \u0623\u0628\u0648 40 \u0628\u062a\u0639\u0628\u0626\u0629 50"),
            ("usim-prp2", "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645 \u0631\u064a\u062f"),
            ("usim-prp", "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645 \u0631\u064a\u062f"),
        ],
    },
}

BUNDLE_ORDER = [
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 3 \u0623\u0634\u0647\u0631",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0634\u0647\u0631\u064a 30",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 5",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 10",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 25",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0627\u0645 5",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 25",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 30",
    "\u0628\u0627\u0642\u0629 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000 \u0628\u0644\u0627 \u062d\u062f\u0648\u062f",
    "\u0628\u0627\u0642\u0629 \u0646\u062a \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 12000 \u0623\u0633\u0628\u0648\u0639\u064a\u0629",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000",
    "\u0628\u0627\u0642\u0629 \u0623\u0631\u0628\u0639\u064a\u0646",
    "\u0628\u0627\u0642\u0629 \u0646\u062a \u0623\u0633\u0628\u0648\u0639\u064a\u0629 40",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 40 \u0623\u0633\u0628\u0648\u0639\u064a\u0629",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 40",
    "\u0628\u0627\u0642\u0629 \u0646\u062a \u0634\u0647\u0631\u064a 40",
    "\u0628\u0627\u0642\u0629 \u0625\u0646\u062a\u0631\u0646\u062a \u0634\u0647\u0631\u064a\u0629 \u0628\u0644\u0627 \u062d\u062f\u0648\u062f",
    "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645",
    "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645 \u0631\u064a\u062f",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0646\u062a \u0623\u0628\u0648 40 \u0628\u062a\u0639\u0628\u0626\u0629 50",
    "\u0628\u0627\u0642\u0629 \u0631\u0627\u0648\u062a\u0631 110",
]

BUNDLE_FAMILY = {}
for _lbl in [
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 3 \u0623\u0634\u0647\u0631",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0634\u0647\u0631\u064a 30",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 5",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 10",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 25",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 12000 \u0623\u0633\u0628\u0648\u0639\u064a\u0629",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 40 \u0623\u0633\u0628\u0648\u0639\u064a\u0629",
    "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645 \u0631\u064a\u062f",
]:
    BUNDLE_FAMILY[_lbl] = "red"
for _lbl in [
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0627\u0645 5",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 25",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 30",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 40",
]:
    BUNDLE_FAMILY[_lbl] = "use"

LINE_FAMILY = {RED: "red", USE: "use", USE_1M: "use"}

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


def norm_name(x):
    if pd.isna(x):
        return ""
    return re.sub(r"\s+", " ", str(x)).strip().lower()


def classify_bundle(name_n, sub_n):
    if name_n in BUNDLE_SPLIT:
        spec = BUNDLE_SPLIT[name_n]
        for key, label in spec["sub"]:
            if key in sub_n:
                return label
        return spec["base"]
    return BUNDLE_DIRECT.get(name_n)


def detect_bundle_col(b):
    known = set(BUNDLE_DIRECT) | set(BUNDLE_SPLIT)
    best = None
    best_score = 0
    for i in range(b.shape[1]):
        score = int(b.iloc[:, i].map(norm_name).isin(known).sum())
        if score > best_score:
            best = i
            best_score = score
    return best, best_score


def pick_sheet(sheets, label):
    names = list(sheets.keys())
    if len(names) == 1:
        return sheets[names[0]]
    chosen = st.selectbox(T["sheet"] + " " + label, names, key="sheet_" + label)
    return sheets[chosen]


def compute(agents, dist, q, inc=None, wal=None, bnd=None):
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
    for col in [RED, USE, DAILY, MONTHLY, BIG_ROUTER, SMALL_MIFI]:
        if col not in result.columns:
            result[col] = 0
    result[T["total"]] = result[RED] + result[USE]
    result = result.sort_values(T["total"], ascending=False).reset_index()
    result = result.rename(columns={"key": T["office_no"]})

    q_msg = None
    if q is not None:
        qd = pd.DataFrame({
            "group": q.iloc[:, Q_TYPE_COL].apply(clean_code).map(QUALITY_TYPE),
            "key": q.iloc[:, Q_OFFICE_COL].apply(last10),
            "date": pd.to_datetime(q.iloc[:, DATE_COL], errors="coerce"),
        })

        if q.shape[1] > Q_POINTS_COL:
            pts_raw = q.iloc[:, Q_POINTS_COL].astype(str).str.replace(",", "", regex=False)
            qd["pts"] = pd.to_numeric(pts_raw, errors="coerce")
        else:
            qd["pts"] = 0.0
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

        ru_mask = qd["group"].isin(["red", "use"])
        pts_ru = qd[ru_mask].groupby("key")["pts"].sum()
        pts_net = qd[qd["group"] == "net"].groupby("key")["pts"].sum()
        pts_tbl = pd.DataFrame({T["pts_ru"]: pts_ru, T["pts_net"]: pts_net})
        tot = tot.join(pts_tbl, how="outer")

        qdd = qd.dropna(subset=["date"]).copy()
        if qdd.empty:
            last_day = None
            last_tbl = pd.DataFrame(columns=[T["last_ru"], T["last_net"], T["pts_last_ru"], T["pts_last_net"]])
        else:
            qdd["day"] = qdd["date"].dt.normalize()
            last_day = qdd["day"].max()
            ld = qdd[qdd["day"] == last_day]
            ru = ld[ld["group"].isin(["red", "use"])].groupby("key").size()
            nt = ld[ld["group"] == "net"].groupby("key").size()
            pr = ld[ld["group"].isin(["red", "use"])].groupby("key")["pts"].sum()
            pn = ld[ld["group"] == "net"].groupby("key")["pts"].sum()
            last_tbl = pd.DataFrame({
                T["last_ru"]: ru,
                T["last_net"]: nt,
                T["pts_last_ru"]: pr,
                T["pts_last_net"]: pn,
            })

        q_all = tot.join(last_tbl, how="outer").fillna(0)
        q_all.index.name = T["office_no"]
        q_all = q_all.reset_index()

        if last_day is not None:
            day_txt = str(last_day.date())
            q_all = q_all.rename(columns={
                T["last_ru"]: T["last_ru"] + " " + day_txt,
                T["last_net"]: T["last_net"] + " " + day_txt,
                T["pts_last_ru"]: T["pts_last_ru"] + " " + day_txt,
                T["pts_last_net"]: T["pts_last_net"] + " " + day_txt,
            })

        result = result.merge(q_all, on=T["office_no"], how="outer")

        name_map = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
        result[T["office_name"]] = result[T["office_name"]].fillna(
            result[T["office_no"]].map(name_map)
        ).fillna(T["unmatched"])

        num_cols = [c for c in result.columns if c not in (T["office_no"], T["office_name"])]
        for c in num_cols:
            result[c] = result[c].fillna(0)
            if c.startswith(T["pts_word"]):
                result[c] = result[c].round(2)
            else:
                result[c] = result[c].astype(int)

        last_txt = "-"
        if last_day is not None:
            last_txt = str(last_day.date())
        q_msg = (
            T["q_info"] + ": " + str(q_total)
            + " | " + T["q_ignored"] + ": " + str(q_ignored)
            + " | " + T["q_baddate"] + ": " + str(q_baddate)
            + " | " + T["q_last"] + ": " + last_txt
        )

    inc_msg = None
    if inc is not None:
        inc_df = pd.DataFrame({
            "key": inc.iloc[:, INC_OFFICE_COL].apply(last10),
            "val": pd.to_numeric(
                inc.iloc[:, INC_VALUE_COL].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ),
        })
        inc_total = len(inc_df)
        inc_df = inc_df.dropna(subset=["key", "val"])
        inc_df = inc_df[inc_df["val"] != 0]
        inc_after = len(inc_df)
        inc_keys = inc_df["key"].drop_duplicates()
        inc_tbl = pd.DataFrame({T["office_no"]: inc_keys, T["inc"]: "done"})

        result = result.merge(inc_tbl, on=T["office_no"], how="outer")

        name_map2 = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
        result[T["office_name"]] = result[T["office_name"]].fillna(
            result[T["office_no"]].map(name_map2)
        ).fillna(T["unmatched"])
        result[T["inc"]] = result[T["inc"]].fillna("")

        skip_cols = (T["office_no"], T["office_name"], T["inc"])
        num_cols2 = [c for c in result.columns if c not in skip_cols]
        for c in num_cols2:
            result[c] = result[c].fillna(0)
            if c.startswith(T["pts_word"]):
                result[c] = result[c].round(2)
            else:
                result[c] = result[c].astype(int)

        inc_msg = (
            T["inc_info"] + ": " + str(inc_total)
            + " | " + T["inc_after"] + ": " + str(inc_after)
            + " | " + T["inc_offices"] + ": " + str(len(inc_keys))
        )

    wal_msg = None
    if wal is not None:
        wal_df = pd.DataFrame({
            "key": wal.iloc[:, WAL_OFFICE_COL].apply(last10),
            "flag": wal.iloc[:, WAL_FLAG_COL].astype(str).str.strip().str.lower(),
        })
        wal_total = len(wal_df)
        wal_df = wal_df.dropna(subset=["key"])
        wal_df = wal_df[wal_df["flag"] == "y"]
        wal_after = len(wal_df)
        wal_keys = wal_df["key"].drop_duplicates()
        wal_tbl = pd.DataFrame({T["office_no"]: wal_keys, T["wal"]: "done"})

        result = result.merge(wal_tbl, on=T["office_no"], how="outer")

        name_map3 = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
        result[T["office_name"]] = result[T["office_name"]].fillna(
            result[T["office_no"]].map(name_map3)
        ).fillna(T["unmatched"])

        text_cols = [T["inc"], T["wal"]]
        for c in text_cols:
            if c in result.columns:
                result[c] = result[c].fillna("")

        skip_cols3 = [T["office_no"], T["office_name"]] + text_cols
        num_cols3 = [c for c in result.columns if c not in skip_cols3]
        for c in num_cols3:
            result[c] = result[c].fillna(0)
            if c.startswith(T["pts_word"]):
                result[c] = result[c].round(2)
            else:
                result[c] = result[c].astype(int)

        wal_msg = (
            T["wal_info"] + ": " + str(wal_total)
            + " | " + T["wal_after"] + ": " + str(wal_after)
            + " | " + T["wal_offices"] + ": " + str(len(wal_keys))
        )

    bnd_msg = None
    bnd_warn = None
    bundle_df = None
    mismatch_df = None
    if bnd is not None:
        name_idx, hits = detect_bundle_col(bnd)
        if name_idx is None:
            st.error(T["bnd_noname"])
        else:
            if bnd.shape[1] > BND_SUB_COL:
                sub_vals = bnd.iloc[:, BND_SUB_COL].map(norm_name)
            else:
                sub_vals = ""
            b = pd.DataFrame({
                "line10": bnd.iloc[:, BND_LINE_COL].apply(last10),
                "name": bnd.iloc[:, name_idx].map(norm_name),
                "sub": sub_vals,
            })
            b_total = len(b)
            b["label"] = [classify_bundle(n, s2) for n, s2 in zip(b["name"], b["sub"])]
            unknown = b.loc[b["label"].isna() & (b["name"] != ""), "name"].value_counts().head(8)
            b_unknown = int(b["label"].isna().sum())
            b = b.dropna(subset=["label", "line10"])

            dl = d[["line", "key", T["item"]]].copy()
            dl["fam"] = dl[T["item"]].map(LINE_FAMILY)
            dl["line10"] = dl["line"].apply(last10)
            dl = dl.dropna(subset=["line10"]).drop_duplicates("line10")

            bm = b.merge(dl, on="line10", how="inner")
            b_nodist = len(b) - len(bm)
            bm["bfam"] = bm["label"].map(BUNDLE_FAMILY)
            bad_ru = (bm["fam"] == "red") & (bm["bfam"] == "use")
            bad_ur = (bm["fam"] == "use") & (bm["bfam"] == "red")
            bad = bad_ru | bad_ur

            ok = bm[~bad]
            if len(ok) > 0:
                tbl = ok.groupby(["key", "label"]).size().unstack(fill_value=0)
            else:
                tbl = pd.DataFrame()
            mm = pd.DataFrame({
                T["mm_ru"]: bm[bad_ru].groupby("key").size(),
                T["mm_ur"]: bm[bad_ur].groupby("key").size(),
            })
            tbl = tbl.join(mm, how="outer").fillna(0).astype(int)
            tbl.index.name = T["office_no"]
            tbl = tbl.reset_index()
            name_map5 = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
            tbl.insert(0, T["office_name"], tbl[T["office_no"]].map(name_map5).fillna(T["unmatched"]))
            wanted = BUNDLE_ORDER + [T["mm_ru"], T["mm_ur"]]
            ordered_b = [c for c in wanted if c in tbl.columns]
            tbl = tbl[[T["office_name"], T["office_no"]] + ordered_b]
            if len(ordered_b) > 0:
                tot_b = tbl[ordered_b].sum(axis=1)
                tbl = tbl.assign(_t=tot_b).sort_values("_t", ascending=False).drop(columns="_t")
            bundle_df = tbl.reset_index(drop=True)

            name_map4 = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
            mm_rows = bm[bad]
            mismatch_df = pd.DataFrame({
                T["office_no"]: mm_rows["key"],
                T["office_name"]: mm_rows["key"].map(name_map4).fillna(T["unmatched"]),
                T["line_lbl"]: mm_rows["line"],
                T["dist_type"]: mm_rows[T["item"]],
                T["bundle_lbl"]: mm_rows["label"],
            }).sort_values(T["office_no"])

            if hits == 0:
                bnd_warn = T["bnd_noname"]
            if len(unknown) > 0:
                names_txt = " ; ".join(str(k) + " (" + str(v) + ")" for k, v in unknown.items())
                bnd_warn = T["bnd_unames"] + ": " + names_txt
            col_letter = chr(65 + name_idx) if name_idx < 26 else str(name_idx)
            bnd_msg = (
                T["bnd_info"] + ": " + str(b_total)
                + " | " + T["bnd_unknown"] + ": " + str(b_unknown)
                + " | " + T["bnd_nodist"] + ": " + str(b_nodist)
                + " | " + T["bnd_mm"] + ": " + str(len(mm_rows))
                + " | " + T["bnd_col"] + ": " + col_letter
            )

    order_base = [
        T["office_name"], T["office_no"],
        RED, USE, DAILY, MONTHLY, BIG_ROUTER, SMALL_MIFI,
        T["total"],
        T["act_red"], T["act_use"], T["act_net"],
        T["last_ru"], T["last_net"],
        T["pts_ru"], T["pts_net"], T["pts_last_ru"], T["pts_last_net"],
        T["inc"], T["wal"],
    ]
    ordered = []
    for base in order_base:
        for c in result.columns:
            if c == base or str(c).startswith(base + " "):
                if c not in ordered:
                    ordered.append(c)
    rest = [c for c in result.columns if c not in ordered]
    result = result[ordered + rest]

    st.success(T["done"] + ": " + str(len(result)) + " | " + T["unm_rows"] + ": " + str(unmatched))
    st.info(
        T["orig"] + ": " + str(total_rows)
        + " | " + T["dedup"] + ": " + str(after_dedup)
        + " | " + T["real"] + ": " + str(len(d))
        + " | " + T["bad_dates"] + ": " + str(bad_dates)
    )
    if q_msg is not None:
        st.info(q_msg)
    if inc_msg is not None:
        st.info(inc_msg)
    if wal_msg is not None:
        st.info(wal_msg)
    if bnd_msg is not None:
        st.info(bnd_msg)
    if bnd_warn is not None:
        st.warning(bnd_warn)
    result.attrs["mismatch"] = mismatch_df
    result.attrs["bundles"] = bundle_df
    return result


# ===== formatting settings (change here) =====
FONT_SIZE = 14
COL_WIDTH = 24
GRAY_BODY = "D9D9D9"
GRAY_HEADER = "A6A6A6"
YELLOW = "FFFF00"


def format_excel(df, extras=None):
    # writes df (and optional extra sheet) to xlsx bytes: gray cells, yellow first column,
    # borders, centered text, equal column widths, font size 14
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    thin = Side(style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    gray_body = PatternFill("solid", start_color=GRAY_BODY, end_color=GRAY_BODY)
    gray_head = PatternFill("solid", start_color=GRAY_HEADER, end_color=GRAY_HEADER)
    yellow = PatternFill("solid", start_color=YELLOW, end_color=YELLOW)

    def style_sheet(ws):
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                is_header = cell.row == 1
                cell.font = Font(size=FONT_SIZE, bold=is_header)
                cell.alignment = center
                cell.border = border
                if cell.column == 1:
                    cell.fill = yellow
                elif is_header:
                    cell.fill = gray_head
                else:
                    cell.fill = gray_body
        for i in range(1, ws.max_column + 1):
            ws.column_dimensions[get_column_letter(i)].width = COL_WIDTH
        ws.row_dimensions[1].height = 70
        ws.freeze_panes = "B2"

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        style_sheet(writer.sheets["Sheet1"])
        if extras is not None:
            for sheet_name, sheet_df in extras:
                sheet_df.to_excel(writer, index=False, sheet_name=sheet_name)
                style_sheet(writer.sheets[sheet_name])
    return buf.getvalue()


def style_screen(df):
    # on-screen version of the same look (colors + centered text)
    first = df.columns[0]
    sty = df.style.set_properties(**{
        "background-color": "#D9D9D9",
        "color": "black",
        "text-align": "center",
        "font-size": "14px",
        "border": "1px solid black",
    })
    sty = sty.set_properties(subset=[first], **{"background-color": "#FFFF00"})
    return sty


def show_table(df):
    # shows the table on screen with the same look as the Excel file:
    # gray cells, yellow first column, borders, centered, equal widths, font 14
    if len(df) > 3000:
        st.dataframe(df, use_container_width=True)
        return
    try:
        def fmt(v):
            if isinstance(v, float) and v == v and v == int(v):
                return str(int(v))
            return v

        sty = style_screen(df)
        sty = sty.hide(axis="index")
        sty = sty.format(fmt)
        total_w = 160 * len(df.columns)
        sty = sty.set_table_styles([
            {"selector": "table", "props": [
                ("border-collapse", "collapse"),
                ("table-layout", "fixed"),
                ("width", str(total_w) + "px"),
            ]},
            {"selector": "th", "props": [
                ("background-color", "#A6A6A6"),
                ("color", "black"),
                ("border", "1px solid black"),
                ("text-align", "center"),
                ("font-size", "14px"),
                ("padding", "6px"),
                ("word-wrap", "break-word"),
            ]},
            {"selector": "th.col_heading.col0", "props": [("background-color", "#FFFF00")]},
            {"selector": "td", "props": [("padding", "6px"), ("word-wrap", "break-word")]},
        ])
        html = sty.to_html()
        st.markdown('<div style="overflow-x:auto">' + html + "</div>", unsafe_allow_html=True)
    except Exception:
        st.dataframe(df, use_container_width=True)


st.title(T["title"])

c1, c2, c3 = st.columns(3)
c4, c5, c6 = st.columns(3)
with c1:
    agents_file = st.file_uploader(T["up_agents"], key="agents")
with c2:
    dist_file = st.file_uploader(T["up_dist"], key="dist")
with c3:
    quality_file = st.file_uploader(T["up_quality"], key="quality")
with c4:
    inc_file = st.file_uploader(T["up_inc"], key="inc")
with c5:
    wal_file = st.file_uploader(T["up_wal"], key="wal")
with c6:
    bnd_file = st.file_uploader(T["up_bnd"], key="bnd")

if agents_file is not None and dist_file is not None:
    agents = None
    dist = None
    q = None
    inc = None
    wal = None
    bnd = None

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
    if inc_file is not None:
        with c4:
            sh = load_report(inc_file, T["inc"])
            if sh is not None:
                inc = pick_sheet(sh, T["inc"])
    if wal_file is not None:
        with c5:
            sh = load_report(wal_file, T["wal"])
            if sh is not None:
                wal = pick_sheet(sh, T["wal"])
    if bnd_file is not None:
        with c6:
            sh = load_report(bnd_file, T["bnd"])
            if sh is not None:
                bnd = pick_sheet(sh, T["bnd"])

    if agents is not None and dist is not None:
        with st.expander(T["preview"]):
            st.write(T["agents"])
            st.dataframe(agents.head(5))
            st.write(T["dist"])
            st.dataframe(dist.head(5))
            if q is not None:
                st.write(T["quality"])
                st.dataframe(q.head(5))
            if inc is not None:
                st.write(T["inc"])
                st.dataframe(inc.head(5))
            if wal is not None:
                st.write(T["wal"])
                st.dataframe(wal.head(5))
            if bnd is not None:
                st.write(T["bnd"])
                st.dataframe(bnd.head(5))

        if st.button(T["calc"]):
            try:
                result = compute(agents, dist, q, inc, wal, bnd)
                if result is not None:
                    show_table(result)
                    bundle_df = result.attrs.get("bundles")
                    mm_df = result.attrs.get("mismatch")
                    extras = []
                    if bundle_df is not None:
                        st.write(T["bnd"])
                        if len(bundle_df) > 0:
                            show_table(bundle_df)
                        else:
                            st.info(T["bnd_empty"])
                        extras.append((T["bnd"], bundle_df))
                    if mm_df is not None and len(mm_df) > 0:
                        st.write(T["mm_title"])
                        show_table(mm_df)
                        extras.append((T["mm_sheet"], mm_df))
                    xlsx_bytes = format_excel(result, extras)
                    st.download_button(
                        T["download"],
                        data=xlsx_bytes,
                        file_name=T["file_name"],
                        mime=XLSX_MIME,
                    )
            except Exception:
                st.error(T["err"])
                st.code(traceback.format_exc())
