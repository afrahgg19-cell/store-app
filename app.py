import re
import textwrap
import calendar
import json
import os
from datetime import datetime, timedelta, timezone
import traceback
import pandas as pd
import streamlit as st
from io import BytesIO, StringIO

st.set_page_config(page_title="Distribution", layout="wide")

# ===== login lock: username + password + 6-digit code from the authenticator app =====
# Streamlit secrets (Settings -> Secrets):
#   [users]
#   admin = "password"            (or "sha256:<hash>" instead of the plain password)
#   [totp]
#   admin = "BASE32SECRET"        (the key you add to the authenticator app)
# if the secrets are missing the app stays locked.
import base64
import hashlib
import hmac
import struct
import time


def _totp_at(secret_b32, t, step=30, digits=6):
    s = secret_b32.replace(" ", "").replace("-", "").upper()
    key = base64.b32decode(s + "=" * (-len(s) % 8))
    counter = int(t // step)
    h = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    num = (struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF) % (10 ** digits)
    return str(num).zfill(digits)


def _totp_ok(secret_b32, code):
    code = "".join(ch for ch in str(code) if ch.isdigit())
    if len(code) != 6:
        return False
    now = time.time()
    ok = False
    for off in (-60, -30, 0, 30):   # a code stays accepted for about 90 seconds
        if hmac.compare_digest(_totp_at(secret_b32, now + off), code):
            ok = True
    return ok


def _pass_ok(stored, given):
    stored = str(stored)
    if stored.lower().startswith("sha256:"):
        h = hashlib.sha256(given.encode("utf-8")).hexdigest()
        return hmac.compare_digest(h, stored[7:].strip().lower())
    return hmac.compare_digest(given.encode("utf-8"), stored.encode("utf-8"))


def _ti(label, **kw):
    # autocomplete lets the browser save/fill the username and password (not the code)
    try:
        return st.text_input(label, **kw)
    except TypeError:
        kw.pop("autocomplete", None)
        return st.text_input(label, **kw)


def require_login():
    if st.session_state.get("auth_ok"):
        return
    try:
        users = {str(k): str(v) for k, v in dict(st.secrets["users"]).items()}
        totp = {str(k): str(v) for k, v in dict(st.secrets["totp"]).items()}
    except Exception:
        st.error("ما لقيت إعدادات الدخول (secrets)، الكود مقفول")
        st.stop()
    if st.session_state.get("login_fails", 0) >= 5:
        st.error("محاولات كثيرة غلط، أعد تحميل الصفحة وجرب مرة ثانية")
        st.stop()
    st.title("تسجيل الدخول")
    with st.form("login_form"):
        u = _ti("اسم المستخدم", key="login_user", autocomplete="username")
        p = _ti("كلمة السر", type="password", key="login_pass", autocomplete="current-password")
        c = _ti("الرمز من تطبيق المصادقة (6 أرقام)", key="login_code", autocomplete="one-time-code")
        go = st.form_submit_button("دخول")
    if go:
        name = u.strip()
        good = False
        if name in users and name in totp:
            try:
                good = _pass_ok(users[name], p) and _totp_ok(totp[name], c)
            except Exception:
                good = False
        if good:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.session_state["login_fails"] = st.session_state.get("login_fails", 0) + 1
            st.error("اسم المستخدم أو كلمة السر أو الرمز غلط")
    st.stop()


require_login()

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
    "wal_after": "\u0628\u0639\u062f \u0641\u0644\u062a\u0631 5000 \u0648\u0641\u0648\u0642",
    "wal_offices": "\u0645\u0643\u0627\u062a\u0628 \u0628\u0627\u0644\u0645\u062d\u0627\u0641\u0638",
    "up_bnd": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0628\u0627\u0642\u0627\u062a",
    "bnd": "\u0627\u0644\u0628\u0627\u0642\u0627\u062a",
    "bnd_info": "\u0627\u0644\u0628\u0627\u0642\u0627\u062a: \u0639\u062f\u062f \u0627\u0644\u0635\u0641\u0648\u0641",
    "bnd_unknown": "\u0628\u0627\u0642\u0627\u062a \u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629",
    "bnd_nodist": "\u062e\u0637\u0648\u0637 \u063a\u064a\u0631 \u0645\u0648\u0632\u0639\u0629",
    "bnd_mm": "\u0628\u0627\u0642\u0627\u062a \u0645\u062e\u0627\u0644\u0641\u0629",
    "bnd_col": "\u0639\u0645\u0648\u062f \u0627\u0633\u0645 \u0627\u0644\u0628\u0627\u0642\u0629",
    "bnd_noname": "\u0645\u0627 \u0644\u0642\u064a\u062a \u0639\u0645\u0648\u062f \u0627\u0633\u0645 \u0627\u0644\u0628\u0627\u0642\u0629 \u0628\u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0628\u0627\u0642\u0627\u062a",
    "bnd_unames": "\u0628\u0627\u0642\u0627\u062a \u063a\u064a\u0631 \u0645\u0639\u0631\u0648\u0641\u0629 \u0627\u0646\u0636\u0627\u0641\u062a \u0628\u0623\u0633\u0645\u0627\u0626\u0647\u0627",
    "mm_ru": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0639\u0644\u0649 \u062e\u0637 \u0631\u064a\u062f",
    "mm_ur": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0639\u0644\u0649 \u062e\u0637 \u064a\u0648\u0632",
    "mm_title": "\u0627\u0644\u0628\u0627\u0642\u0627\u062a \u0627\u0644\u0645\u062e\u0627\u0644\u0641\u0629 (\u0645\u0641\u0631\u0648\u0632\u0629 \u0644\u062d\u0627\u0644\u0647\u0627)",
    "line_lbl": "\u0631\u0642\u0645 \u0627\u0644\u062e\u0637",
    "dist_type": "\u0646\u0648\u0639 \u0627\u0644\u062a\u0648\u0632\u064a\u0639",
    "bundle_lbl": "\u0627\u0644\u0628\u0627\u0642\u0629",
    "mm_sheet": "\u0628\u0627\u0642\u0627\u062a \u0645\u062e\u0627\u0644\u0641\u0629",
    "bnd_empty": "\u0645\u0627 \u0644\u0642\u064a\u062a \u0628\u0627\u0642\u0627\u062a \u0645\u0637\u0627\u0628\u0642\u0629 \u0644\u062e\u0637\u0648\u0637 \u0645\u0648\u0632\u0639\u0629",
    "bnd_nomatch": "\u063a\u064a\u0631 \u0645\u0637\u0627\u0628\u0642\u0629 \u0644\u0644\u0648\u0643\u0644\u0627\u0621",
    "remain": "\u0628\u0627\u0642\u064a",
    "brand": "\u0628\u0631\u064a\u0642 \u0627\u0644\u0627\u0646\u0648\u0627\u0631",
    "rep": "\u0627\u0633\u0645 \u0627\u0644\u0645\u0646\u062f\u0648\u0628",
    "loading": "\u062c\u0627\u0631\u064a \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u0645\u0644\u0641 (\u0645\u0631\u0629 \u0648\u062d\u062f\u0629 \u0628\u0633)",
    "pts_sheet": "\u0627\u0644\u0646\u0642\u0627\u0637 \u0627\u0644\u0643\u0644\u064a\u0629",
    "pts_title": "\u062c\u062f\u0648\u0644 \u0645\u062a\u0627\u0628\u0639\u0629 \u0627\u0644\u0646\u0642\u0627\u0637 \u0648\u0627\u0644\u062e\u0637\u0648\u0637 - \u0634\u0647\u0631",
    "col_date": "\u0627\u0644\u062a\u0627\u0631\u064a\u062e",
    "h_net_pts": "\u062e\u0637 \u0646\u062a \u0646\u0642\u0627\u0637",
    "h_red_pts": "\u062e\u0637 \u0631\u064a\u062f \u0646\u0642\u0627\u0637",
    "h_use_pts": "\u062e\u0637 \u064a\u0648\u0632 \u0646\u0642\u0627\u0637",
    "h_net_cnt": "\u0639\u062f\u062f \u062e\u0637 \u0646\u062a",
    "h_red_cnt": "\u0639\u062f\u062f \u062e\u0637 \u0631\u064a\u062f",
    "h_use_cnt": "\u0639\u062f\u062f \u062e\u0637 \u064a\u0648\u0632",
    "f_daily": "\u0645\u062c\u0645\u0648\u0639 \u0627\u0644\u064a\u0648\u0645\u064a",
    "f_total": "\u0627\u0644\u0645\u062c\u0645\u0648\u0639 \u0627\u0644\u0643\u0644\u064a",
    "f_target": "\u0627\u0644\u062a\u0627\u0631\u0643\u062a",
    "f_ratio": "\u0627\u0644\u0646\u0633\u0628\u0629",
    "tgt_title": "\u0627\u0644\u062a\u0627\u0631\u0643\u062a \u0627\u0644\u0634\u0647\u0631\u064a (\u0646\u0642\u0627\u0637)",
    "tgt_net": "\u062a\u0627\u0631\u0643\u062a \u0646\u062a",
    "tgt_red": "\u062a\u0627\u0631\u0643\u062a \u0631\u064a\u062f",
    "tgt_use": "\u062a\u0627\u0631\u0643\u062a \u064a\u0648\u0632",
    "tgt_nosave": "\u0645\u0627 \u0643\u062f\u0631\u062a \u0623\u062d\u0641\u0638 \u0627\u0644\u062a\u0627\u0631\u0643\u062a \u0639\u0644\u0649 \u0627\u0644\u0633\u064a\u0631\u0641\u0631\u060c \u064a\u0628\u0642\u0649 \u0644\u0644\u062c\u0644\u0633\u0629 \u0627\u0644\u062d\u0627\u0644\u064a\u0629 \u0628\u0633",
    "key_detect": "\u062a\u0645 \u0627\u0643\u062a\u0634\u0627\u0641 \u0623\u0639\u0645\u062f\u0629 \u0631\u0642\u0645 \u0627\u0644\u0645\u0643\u062a\u0628 \u062a\u0644\u0642\u0627\u0626\u064a\u0627\u064b \u0644\u0623\u0646 B \u0648 F \u0645\u0627 \u062a\u0637\u0627\u0628\u0642\u0648\u0627",
    "key_none": "\u0645\u0627 \u0641\u064a \u0623\u064a \u0631\u0642\u0645 \u0645\u0643\u062a\u0628 \u0645\u0634\u062a\u0631\u0643 \u0628\u064a\u0646 \u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0648\u0627\u0644\u062a\u0648\u0632\u064a\u0639",
    "source": "\u0627\u0644\u0645\u0635\u062f\u0631",
    "um_title": "\u0645\u0643\u0627\u062a\u0628 \u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f\u0629 \u0628\u0645\u0644\u0641 \u0627\u0644\u0648\u0643\u0644\u0627\u0621 (\u0628\u0634\u064a\u062a \u0645\u0646\u0641\u0635\u0644)",
    "um_msg": "\u0645\u0643\u0627\u062a\u0628 \u063a\u064a\u0631 \u0645\u0637\u0627\u0628\u0642\u0629 \u0627\u0646\u0646\u0642\u0644\u062a \u0644\u0634\u064a\u062a \u0645\u0646\u0641\u0635\u0644",
    "um_warn": "\u0623\u0631\u0642\u0627\u0645 \u0645\u0643\u0627\u062a\u0628 \u0628\u0627\u0644\u062a\u0648\u0632\u064a\u0639 (\u0639\u0645\u0648\u062f F) \u0645\u0627 \u0644\u0642\u064a\u062a\u0647\u0627 \u0628\u0639\u0645\u0648\u062f B \u0628\u0627\u0644\u0648\u0643\u0644\u0627\u0621\u060c \u0645\u0627 \u0637\u0644\u0639\u062a \u0628\u0627\u0644\u062c\u062f\u0648\u0644",
    "up_live": "\u0627\u0631\u0641\u0639 \u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0627\u064a\u0641 \u0633\u062a\u0648\u0643",
    "live": "\u0627\u0644\u0627\u064a\u0641 \u0633\u062a\u0648\u0643",
    "live_info": "\u0627\u0644\u0627\u064a\u0641 \u0633\u062a\u0648\u0643: \u0639\u062f\u062f \u0627\u0644\u0623\u0631\u0642\u0627\u0645",
    "live_main": "\u0627\u0646\u0634\u0627\u0644\u062a \u0645\u0646 \u0627\u0644\u0628\u0627\u0642\u064a (\u0627\u0644\u0634\u064a\u062a \u0627\u0644\u0623\u0648\u0644)",
    "live_month": "\u0627\u0646\u0634\u0627\u0644\u062a \u0645\u0646 \u0627\u0644\u0634\u064a\u062a \u0627\u0644\u0634\u0647\u0631\u064a",
    "live_none": "\u0645\u0627 \u0644\u0642\u064a\u062a \u0623\u064a \u0631\u0642\u0645 \u0645\u0634\u062a\u0631\u0643 \u0628\u064a\u0646 \u0627\u0644\u062a\u0648\u0632\u064a\u0639 \u0648\u0627\u0644\u0627\u064a\u0641 \u0633\u062a\u0648\u0643",
    "bnd_typed": "\u0635\u0641\u0648\u0641 \u0646\u0648\u0639 \u062e\u0637\u0647\u0627 \u0645\u0639\u0631\u0648\u0641 (\u0645\u0646 \u0639\u0645\u0648\u062f H)",
    "bnd_drop": "\u0628\u0627\u0642\u0627\u062a \u0627\u0646\u0641\u0635\u0644\u062a \u0644\u062d\u0642\u0644 \u0645\u0646\u0641\u0635\u0644 (\u062e\u0637 \u0631\u064a\u062f \u0645\u0633\u0648\u064a \u064a\u0648\u0632 / \u062e\u0637 \u064a\u0648\u0632 \u0645\u0633\u0648\u064a \u0631\u064a\u062f)",
    "mm_red_use": "\u062e\u0637 \u0631\u064a\u062f \u0645\u0633\u0648\u064a \u064a\u0648\u0632",
    "mm_use_red": "\u062e\u0637 \u064a\u0648\u0632 \u0645\u0633\u0648\u064a \u0631\u064a\u062f",
    "read_fail": "\u062a\u0639\u0630\u0631 \u0642\u0631\u0627\u0621\u0629 \u0627\u0644\u0645\u0644\u0641",
    "preview": "\u0645\u0639\u0627\u064a\u0646\u0629 \u0623\u0648\u0644 5 \u0635\u0641\u0648\u0641",
    "err": "\u062d\u062f\u062b \u062e\u0637\u0623",
    "q_required": "\u062a\u0642\u0631\u064a\u0631 \u0627\u0644\u0648\u0643\u0644\u0627\u0621 \u0625\u062c\u0628\u0627\u0631\u064a\u060c \u0627\u0631\u0641\u0639\u0647 \u062d\u062a\u0649 \u064a\u0634\u062a\u063a\u0644 \u0627\u0644\u062d\u0633\u0627\u0628 (\u0628\u0627\u0642\u064a \u0627\u0644\u062a\u0642\u0627\u0631\u064a\u0631 \u0627\u062e\u062a\u064a\u0627\u0631\u064a\u0629)",
    "monthly_sheet": "\u0634\u064a\u062a \u0627\u0644\u062a\u0648\u0632\u064a\u0639 \u0627\u0644\u0634\u0647\u0631\u064a",
}

RED = "\u0631\u064a\u062f"
USE = "\u064a\u0648\u0632"
MONTHLY = "\u0646\u062a \u0634\u0647\u0631\u064a"
DAILY = "\u0646\u062a \u064a\u0648\u0645\u064a"
BIG_ROUTER = "\u0631\u0627\u0648\u062a\u0631 \u0643\u0628\u064a\u0631"
SMALL_MIFI = "\u0631\u0627\u0648\u062a\u0631 \u0635\u063a\u064a\u0631"
USE_1M = "\u062e\u0637 \u064a\u0648\u0632 \u0645\u0644\u064a\u0648\u0646\u064a"
BLANK_LBL = "\u0628\u0644\u0627\u0646\u0643"

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

# ===== monthly distribution sheet settings =====
M_ITEMS = [RED, USE, USE_1M, DAILY, MONTHLY, BIG_ROUTER, SMALL_MIFI]
M_STATUSES = ["distributed", "activated", "active"]

QUALITY_TYPE = {"2": "net", "93": "red", "4": "red", "32": "use"}

Q_TYPE_COL = 1
Q_OFFICE_COL = 2
DATE_COL = 3
Q_POINTS_COL = 17   # R = points
INC_OFFICE_COL = 0  # incentive: A = office number
INC_VALUE_COL = 7   # incentive: H = value (zeros removed)
WAL_OFFICE_COL = 3  # wallets: D = office number (matched with agents B)
WAL_VALUE_COL = 5   # wallets: F = value
WAL_MIN = 5000      # wallets: keep only values >= 5000 (5000 itself counts)

# ===== Bundles report (A = office number, H = sub-type) =====
BND_OFFICE_COL = 0   # bundles: A = office number (matched with agents B)
BND_SUB_COL = 7

# line type is read from column H (SIM type): red line = usim-prp / usim-prp2, use line = usim-yout
LINE_RED_KEYS = ("usim-prp",)
LINE_USE_KEYS = ("usim-yout",)

# one label for: tesla new data bundle daily / daily300mb / weekly3gb
BUNDLE_300_TESLA = "\u0628\u0627\u0642\u0629 300 \u0648\u062a\u0633\u0644\u0627 \u06483\u0643\u064a\u0643\u0627"
BUNDLE_IRAN = "\u0628\u0627\u0642\u0629 \u0627\u064a\u0631\u0627\u0646"
BUNDLE_MISC = "\u0628\u0627\u0642\u0627\u062a \u0645\u062a\u0641\u0631\u0642\u0629"
BUNDLE_PUBG = "\u0628\u0648\u0628\u062c\u064a"
BUNDLE_RED20 = "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 20"
BUNDLE_YOOZ20 = "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 20"

BUNDLE_DIRECT = {
    "red 15,000 monthly package": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 15",
    "red 15 4 weeks": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 15",
    "red 15 for 12 weeks": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 15",
    "red 15 for 3 months": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 15",
    "red 30 4 weeks": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0634\u0647\u0631\u064a 30",
    "red 30 for 12 weeks": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0634\u0647\u0631\u064a 30",
    "red 30,000 monthly package": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0634\u0647\u0631\u064a 30",
    "yooz 30 mix": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 30",
    "yooz 30 extra voice": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 30",
    "red 25 for 12 weeks": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 25",
    "red 25,000 monthly package": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 25",
    "yooz 5 mix": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0627\u0645 5",
    "yooz 10 mix": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 10",
    "yooz 15 extra data-3 months": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "yooz 15 extra voice-3 months": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "red 30 for 3 months": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0634\u0647\u0631\u064a 30",
    "yooz 40 extra data": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 40",
    "yooz 10 extra voice": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 10",
    "yooz 10 extra data": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 10",
    "yooz 20 extra data": BUNDLE_YOOZ20,
    "yooz 25 extra voice": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 25",
    "yooz 25 extra data-3 months": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 25",
    "yooz 25 extra voice-3 months": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 25",
    "yooz 30 extra data-3 months": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 30",
    "red 20 for 3 months": BUNDLE_RED20,
    "red 20,000 monthly package": BUNDLE_RED20,
    "red 25 for 3 months": "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 25",
    "monthly5gb": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0645\u064a\u0629",
    "weekly iran & uae package": BUNDLE_IRAN,
    "tesla new data bundle weekly": BUNDLE_MISC,
    "passport package 10gb": BUNDLE_MISC,
    "daily iran & uae package": BUNDLE_MISC,
    "pubg": BUNDLE_PUBG,
    "tesla new data bundle daily": BUNDLE_300_TESLA,
    "daily300mb": BUNDLE_300_TESLA,
    "weekly3gb": BUNDLE_300_TESLA,
    "daily300mb weekly3gb": BUNDLE_300_TESLA,
    "unlimited daily 4g": "\u0628\u0627\u0642\u0629 \u064a\u0648\u0645\u064a\u0629",
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
        "base": None,   # premium with unknown sub-type: dropped
        "sub": [
            ("usim-gprs-rtr2", "\u0628\u0627\u0642\u0629 \u0631\u0627\u0648\u062a\u0631 110"),
            ("usim-40kv", "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0646\u062a \u0623\u0628\u0648 40 \u0628\u062a\u0639\u0628\u0626\u0629 50"),
            ("usim-prp2", "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645 \u0631\u064a\u062f"),
            ("usim-prp", "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645 \u0631\u064a\u062f"),
        ],
    },
}

BUNDLE_ORDER = [
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 5",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 10",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 12000 \u0623\u0633\u0628\u0648\u0639\u064a\u0629",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 15",
    BUNDLE_RED20,
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 25",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0634\u0647\u0631\u064a 30",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 40 \u0623\u0633\u0628\u0648\u0639\u064a\u0629",
    "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645 \u0631\u064a\u062f",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0627\u0645 5",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 10",
    BUNDLE_YOOZ20,
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 25",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 30",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 40",
    "\u0628\u0627\u0642\u0629 \u0646\u062a \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000",
    "\u0628\u0627\u0642\u0629 \u0646\u062a \u0623\u0633\u0628\u0648\u0639\u064a\u0629 40",
    "\u0628\u0627\u0642\u0629 \u0646\u062a \u0634\u0647\u0631\u064a 40",
    "\u0628\u0627\u0642\u0629 \u0625\u0646\u062a\u0631\u0646\u062a \u0634\u0647\u0631\u064a\u0629 \u0628\u0644\u0627 \u062d\u062f\u0648\u062f",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0646\u062a \u0623\u0628\u0648 40 \u0628\u062a\u0639\u0628\u0626\u0629 50",
    "\u0628\u0627\u0642\u0629 \u0631\u0627\u0648\u062a\u0631 110",
    "\u0628\u0627\u0642\u0629 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000 \u0628\u0644\u0627 \u062d\u062f\u0648\u062f",
    "\u0628\u0627\u0642\u0629 \u0623\u0631\u0628\u0639\u064a\u0646",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0645\u064a\u0629",
    BUNDLE_300_TESLA,
    BUNDLE_IRAN,
    BUNDLE_PUBG,
    BUNDLE_MISC,
]

BUNDLE_FAMILY = {}
for _lbl in [
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f \u0634\u0647\u0631\u064a 30",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 5",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 10",
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 15",
    BUNDLE_RED20,
    "\u0628\u0627\u0642\u0629 \u0631\u064a\u062f 25",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 12000 \u0623\u0633\u0628\u0648\u0639\u064a\u0629",
    "\u0628\u0627\u0642\u0629 \u062e\u0637 \u0631\u064a\u062f 40 \u0623\u0633\u0628\u0648\u0639\u064a\u0629",
    "\u0628\u0627\u0642\u0629 \u0628\u0631\u064a\u0645\u064a\u0648\u0645 \u0631\u064a\u062f",
]:
    BUNDLE_FAMILY[_lbl] = "red"
for _lbl in [
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0627\u0645 5",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 10",
    BUNDLE_YOOZ20,
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 15000",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 25",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 30",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 12000",
    "\u0628\u0627\u0642\u0629 \u064a\u0648\u0632 \u0623\u0633\u0628\u0648\u0639\u064a\u0629 40",
]:
    BUNDLE_FAMILY[_lbl] = "use"

LINE_FAMILY = {RED: "red", USE: "use", USE_1M: "use"}

SKIP_BUNDLE = "__skip__"   # bundle rows that are intentionally dropped

MONTHS = [
    "\u0643\u0627\u0646\u0648\u0646 \u0627\u0644\u062b\u0627\u0646\u064a",
    "\u0634\u0628\u0627\u0637",
    "\u0622\u0630\u0627\u0631",
    "\u0646\u064a\u0633\u0627\u0646",
    "\u0623\u064a\u0627\u0631",
    "\u062d\u0632\u064a\u0631\u0627\u0646",
    "\u062a\u0645\u0648\u0632",
    "\u0622\u0628",
    "\u0623\u064a\u0644\u0648\u0644",
    "\u062a\u0634\u0631\u064a\u0646 \u0627\u0644\u0623\u0648\u0644",
    "\u062a\u0634\u0631\u064a\u0646 \u0627\u0644\u062b\u0627\u0646\u064a",
    "\u0643\u0627\u0646\u0648\u0646 \u0627\u0644\u0623\u0648\u0644",
]

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def last10(num):
    if pd.isna(num):
        return None
    s = str(num).strip()
    if re.fullmatch(r"\d+\.0+", s):
        s = s.split(".")[0]
    elif re.fullmatch(r"\d+(\.\d+)?[eE]\+?\d+", s):
        try:
            s = str(int(float(s)))
        except Exception:
            pass
    s = re.sub(r"\D", "", s)
    if s:
        return s[-10:]
    return None


def letter_of(i):
    if i < 26:
        return chr(65 + i)
    return str(i)


def text_columns(df, key_idx):
    # columns (among the first 8) that mostly hold names (contain letters), without the key column
    found = []
    for i in range(min(df.shape[1], 8)):
        if i == key_idx:
            continue
        vals = df.iloc[:, i].dropna().astype(str).head(50)
        if len(vals) == 0:
            continue
        with_letters = vals.str.contains(r"[A-Za-z\u0600-\u06FF]", regex=True).sum()
        if with_letters >= 0.6 * len(vals):
            found.append(i)
    return found


def find_key_columns(agents, dist):
    # fallback when B (agents) and F (distribution) share no numbers:
    # find the two columns that share the most office numbers
    a_sets = {}
    for i in range(min(agents.shape[1], 10)):
        a_sets[i] = set(agents.iloc[:, i].apply(last10).dropna())
    d_sets = {}
    for j in range(min(dist.shape[1], 12)):
        d_sets[j] = set(dist.iloc[:, j].apply(last10).dropna())
    best = (0, 1, 5)
    for i, a_set in a_sets.items():
        if len(a_set) == 0:
            continue
        for j, d_set in d_sets.items():
            n = len(a_set & d_set)
            if n > best[0]:
                best = (n, i, j)
    return best


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


@st.cache_data(show_spinner=T["loading"], max_entries=16)
def read_cached(raw, kind):
    # each file is parsed once; reruns of the page reuse the saved result
    return read_any(raw, kind)


def load_report(file, label):
    raw = file.getvalue()
    kind = detect_kind(raw)
    try:
        return read_cached(raw, kind)
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
        if spec["base"] is None:
            return SKIP_BUNDLE
        return spec["base"]
    hit = BUNDLE_DIRECT.get(name_n)
    if hit is not None:
        return hit
    return classify_by_pattern(name_n)


# Pattern fallback: any "yooz N ..." / "red N ..." variant (extra data / extra voice / mix,
# with or without "-3 months", "for 12 weeks", ...) goes to the existing bundle of the same N.
# If there is no existing bundle for that N, the name stays under its own name.
YOOZ_N_LABEL = {
    "5": "باقة يوز ام 5",
    "10": "باقة يوز 10",
    "15": "باقة يوز 15000",
    "20": BUNDLE_YOOZ20,
    "25": "باقة يوز 25",
    "30": "باقة يوز 30",
    "40": "باقة يوز أسبوعية 40",
}
RED_N_LABEL = {
    "5": "باقة ريد 5",
    "10": "باقة ريد 10",
    "15": "باقة ريد 15",
    "20": BUNDLE_RED20,
    "25": "باقة ريد 25",
    "30": "باقة ريد شهري 30",
}
YOOZ_PATTERN = re.compile(
    r"^yooz (\d+)[ -]?(?:extra (?:voice|data)|mix)(?:[ -]*(?:for )?\d+ (?:months?|weeks?|days?))?$"
)
RED_PATTERN = re.compile(
    r"^red (\d+)(?:,000)? (?:monthly package|weekly package|\d+ weeks?|for \d+ (?:months?|weeks?|days?))$"
)


def classify_by_pattern(name_n):
    m = YOOZ_PATTERN.match(name_n)
    if m:
        return YOOZ_N_LABEL.get(m.group(1))
    m = RED_PATTERN.match(name_n)
    if m:
        return RED_N_LABEL.get(m.group(1))
    return None


def line_family_of(sub_n):
    # type of the line from column H: red / use / None (unknown)
    for k in LINE_RED_KEYS:
        if k in sub_n:
            return "red"
    for k in LINE_USE_KEYS:
        if k in sub_n:
            return "use"
    return None


def bundle_family_of(label, name_n):
    # family of the bundle: red / use / None (net and others)
    fam = BUNDLE_FAMILY.get(label)
    if fam is not None:
        return fam
    if name_n.startswith("red"):
        return "red"
    if name_n.startswith("yooz"):
        return "use"
    return None


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


def add_missing_keys(result, keys, name_map):
    # adds offices that are not in the table yet (all numbers 0, text empty).
    # used so every office of the agents file appears even with no distribution,
    # and so numbers found in other reports are not lost (they go to the unmatched sheet).
    have = set(result[T["office_no"]])
    miss = []
    for k in keys:
        if k is not None and not pd.isna(k) and k not in have and k not in miss:
            miss.append(k)
    if not miss:
        return result
    add = pd.DataFrame({T["office_no"]: miss})
    for c in result.columns:
        if c == T["office_no"]:
            continue
        if pd.api.types.is_numeric_dtype(result[c]):
            add[c] = 0
        else:
            add[c] = ""
    add[T["office_name"]] = add[T["office_no"]].map(name_map).fillna(T["unmatched"])
    return pd.concat([result, add[list(result.columns)]], ignore_index=True)


def compute(agents, dist, q, inc=None, wal=None, bnd=None, live=None):
    a_idx = 1   # agents: B = office number
    d_idx = 5   # distribution: F = office number
    have_agents = agents is not None
    have_dist = dist is not None
    if not have_agents:
        agents = pd.DataFrame({i: pd.Series(dtype=str) for i in range(3)})
    if not have_dist:
        dist = pd.DataFrame({i: pd.Series(dtype=str) for i in range(9)})
    a_keys = agents.iloc[:, a_idx].apply(last10)
    d_keys = dist.iloc[:, d_idx].apply(last10)
    if have_agents and have_dist and len(set(a_keys.dropna()) & set(d_keys.dropna())) == 0:
        n_best, bi, bj = find_key_columns(agents, dist)
        if n_best > 0:
            a_idx = bi
            d_idx = bj
            a_keys = agents.iloc[:, a_idx].apply(last10)
            st.warning(
                T["key_detect"] + ": " + T["agents"] + " = " + letter_of(a_idx)
                + " | " + T["dist"] + " = " + letter_of(d_idx)
            )
        else:
            st.warning(
                T["key_none"]
                + " | " + T["agents"] + " (B): " + str(agents.iloc[:3, 1].tolist()) + " -> " + str(a_keys.head(3).tolist())
                + " | " + T["dist"] + " (F): " + str(dist.iloc[:3, 5].tolist()) + " -> " + str(d_keys.head(3).tolist())
            )

    if a_idx == 1:
        name_idx = 0
        rep_idx = 2
    else:
        txt = text_columns(agents, a_idx)
        if len(txt) > 0:
            name_idx = txt[0]
        else:
            name_idx = 0 if a_idx != 0 else 1
        if len(txt) > 1:
            rep_idx = txt[1]
        else:
            rep_idx = None
    if rep_idx is not None and agents.shape[1] > rep_idx:
        rep_vals = agents.iloc[:, rep_idx]
    else:
        rep_vals = ""
    agents_df = pd.DataFrame({
        "key": a_keys,
        T["office_name"]: agents.iloc[:, name_idx],
        T["rep"]: rep_vals,
    })
    agents_df = agents_df.dropna(subset=["key"]).drop_duplicates("key")

    d = pd.DataFrame({
        "line": dist.iloc[:, 0].astype(str).str.strip(),
        "item": dist.iloc[:, 2].astype(str).str.strip().str.lower(),
        "status": dist.iloc[:, 4].astype(str).str.strip().str.lower(),
        "key": dist.iloc[:, d_idx].apply(last10),
        "date": pd.to_datetime(dist.iloc[:, 8], errors="coerce"),
    })

    src_sets = {}
    d_raw = d.copy()  # raw rows, used by the monthly sheet (its own de-duplication)
    total_rows = len(d)
    bad_dates = int(d["date"].isna().sum())

    d = d.sort_values("date", kind="stable")
    d = d.drop_duplicates(subset="line", keep="last")
    after_dedup = len(d)

    d = d[d["status"] == "distributed"].copy()
    d[T["item"]] = d["item"].map(item_map)
    d = d.dropna(subset=[T["item"]])

    live_set = set()
    live_removed_main = 0
    live_removed_m = 0
    if live is not None:
        live_set = set(live.iloc[:, 0].apply(last10).dropna())
        d["lkey"] = d["line"].apply(last10)
        in_live = d["lkey"].isin(live_set)
        live_removed_main = int(in_live.sum())
        d = d[~in_live].copy()

    if d.empty and have_dist:
        st.error(T["empty"])
        return None

    if have_dist:
        merged = d.merge(agents_df, on="key", how="left")
        unmatched = int(merged[T["office_name"]].isna().sum())
        src_sets[T["dist"]] = set(merged["key"].dropna())

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
    else:
        # no distribution report: the table is built from the offices found in quality
        unmatched = 0
        base_keys = []
        if q is not None:
            qg0 = q.iloc[:, Q_TYPE_COL].apply(clean_code).map(QUALITY_TYPE)
            qk0 = q.iloc[:, Q_OFFICE_COL].apply(last10)
            base_keys = list(qk0[qg0.notna()].dropna().drop_duplicates())
        name_map0 = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
        result = pd.DataFrame({T["office_no"]: base_keys})
        result[T["office_name"]] = result[T["office_no"]].map(name_map0).fillna(T["unmatched"])

    # every office of the agents file is in the first sheet, even with no distribution (all zeros)
    name_map_all = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
    result = add_missing_keys(result, list(agents_df["key"]), name_map_all)

    q_msg = None
    points_src = None
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

        points_src = qd.dropna(subset=["group"])[["group", "date", "pts"]].copy()
        qd = qd.dropna(subset=["group", "key"]).copy()
        src_sets[T["quality"]] = set(qd["key"])

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

        result = add_missing_keys(result, list(q_all[T["office_no"]]), name_map_all)
        result = result.merge(q_all, on=T["office_no"], how="left")

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
        src_sets[T["inc"]] = set(inc_keys)
        inc_tbl = pd.DataFrame({T["office_no"]: inc_keys, T["inc"]: "done"})

        result = add_missing_keys(result, list(inc_keys), name_map_all)
        result = result.merge(inc_tbl, on=T["office_no"], how="left")

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
        # wallets: D = office number (matched with agents B), F = value, keep only >= 10000
        wal_df = pd.DataFrame({
            "key": wal.iloc[:, WAL_OFFICE_COL].apply(last10),
            "val": pd.to_numeric(
                wal.iloc[:, WAL_VALUE_COL].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ),
        })
        wal_total = len(wal_df)
        wal_df = wal_df.dropna(subset=["key", "val"])
        wal_df = wal_df[wal_df["val"] >= WAL_MIN]
        wal_after = len(wal_df)
        wal_keys = wal_df["key"].drop_duplicates()
        src_sets[T["wal"]] = set(wal_keys)
        wal_tbl = pd.DataFrame({T["office_no"]: wal_keys, T["wal"]: "done"})

        result = add_missing_keys(result, list(wal_keys), name_map_all)
        result = result.merge(wal_tbl, on=T["office_no"], how="left")

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
                "key": bnd.iloc[:, BND_OFFICE_COL].apply(last10),
                "name": bnd.iloc[:, name_idx].map(norm_name),
                "sub": sub_vals,
            })
            b_total = len(b)
            b["label"] = [classify_bundle(n, s2) for n, s2 in zip(b["name"], b["sub"])]
            # names that are not in the lists keep their own (original) name as a column
            raw_names = bnd.iloc[:, name_idx].map(
                lambda x: "" if pd.isna(x) else re.sub(r"\s+", " ", str(x)).strip()
            )
            first_seen = {}
            for nm_n, nm_raw in zip(b["name"], raw_names):
                if nm_n and nm_n not in first_seen:
                    first_seen[nm_n] = nm_raw
            is_unknown = b["label"].isna() & (b["name"] != "")
            b.loc[is_unknown, "label"] = b.loc[is_unknown, "name"].map(first_seen)
            unknown = b.loc[is_unknown, "label"].value_counts().head(8)
            b_unknown = int(is_unknown.sum())
            b = b.dropna(subset=["label", "key"])
            b = b[b["label"] != SKIP_BUNDLE]

            # red line with any non-red bundle -> separate field "red line did use";
            # use line with any non-use bundle -> separate field "use line did red".
            # these rows are taken out of the normal bundle columns and counted per office
            b["lfam"] = b["sub"].map(line_family_of)
            b["bfam"] = [bundle_family_of(lb, nm) for lb, nm in zip(b["label"], b["name"])]
            bad_ru = (b["lfam"] == "red") & (b["bfam"] != "red")
            bad_ur = (b["lfam"] == "use") & (b["bfam"] != "use")
            b_typed = int(b["lfam"].notna().sum())
            b_drop_ru = int(bad_ru.sum())
            b_drop_ur = int(bad_ur.sum())
            mm_ru_cnt = b.loc[bad_ru].groupby("key").size()
            mm_ur_cnt = b.loc[bad_ur].groupby("key").size()
            b = b[~(bad_ru | bad_ur)].copy()
            src_sets[T["bnd"]] = set(b["key"]) | set(mm_ru_cnt.index) | set(mm_ur_cnt.index)

            agent_keys = set(agents_df["key"])
            if have_agents:
                b_nomatch = int((~b["key"].isin(agent_keys)).sum())
            else:
                b_nomatch = 0

            if len(b) > 0:
                tbl = b.groupby(["key", "label"]).size().unstack(fill_value=0)
            else:
                tbl = pd.DataFrame()
            # offices that only have separated rows must still appear in the sheet
            all_keys = tbl.index.union(mm_ru_cnt.index).union(mm_ur_cnt.index)
            tbl = tbl.reindex(all_keys, fill_value=0)
            tbl[T["mm_red_use"]] = mm_ru_cnt.reindex(all_keys).fillna(0).astype(int)
            tbl[T["mm_use_red"]] = mm_ur_cnt.reindex(all_keys).fillna(0).astype(int)
            mm_cols = [T["mm_red_use"], T["mm_use_red"]]
            tbl.index.name = T["office_no"]
            tbl.columns.name = None
            tbl = tbl.reset_index()
            name_map5 = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
            tbl.insert(0, T["office_name"], tbl[T["office_no"]].map(name_map5).fillna(T["unmatched"]))
            rep_map5 = dict(zip(agents_df["key"], agents_df[T["rep"]]))
            tbl.insert(2, T["rep"], tbl[T["office_no"]].map(rep_map5).fillna(""))
            ordered_b = [c for c in BUNDLE_ORDER if c in tbl.columns]
            # unknown names go after the known ones (most used first), under their own names
            extra_b = [c for c in tbl.columns
                       if c not in ordered_b and c not in mm_cols
                       and c not in (T["office_name"], T["office_no"], T["rep"])]
            extra_b.sort(key=lambda c: -int(tbl[c].sum()))
            ordered_b = ordered_b + extra_b
            # the two separated fields go last
            tbl = tbl[[T["office_name"], T["office_no"], T["rep"]] + ordered_b + mm_cols]
            tot_b = tbl[ordered_b + mm_cols].sum(axis=1)
            tbl = tbl.assign(_t=tot_b).sort_values("_t", ascending=False).drop(columns="_t")
            bundle_df = tbl.reset_index(drop=True)

            if hits == 0:
                bnd_warn = T["bnd_noname"]
            if len(unknown) > 0:
                names_txt = " ; ".join(str(k) + " (" + str(v) + ")" for k, v in unknown.items())
                bnd_warn = T["bnd_unames"] + ": " + names_txt
            col_letter = chr(65 + name_idx) if name_idx < 26 else str(name_idx)
            bnd_msg = (
                T["bnd_info"] + ": " + str(b_total)
                + " | " + T["bnd_unknown"] + ": " + str(b_unknown)
                + " | " + T["bnd_nomatch"] + ": " + str(b_nomatch)
                + " | " + T["bnd_col"] + ": " + col_letter
                + " | " + T["bnd_typed"] + ": " + str(b_typed)
                + " | " + T["bnd_drop"] + ": " + str(b_drop_ru) + " / " + str(b_drop_ur)
            )

    # ===== monthly distribution sheet =====
    # month = month of the latest date in the distribution file.
    # inside that month: same line (column A) repeated -> keep only the latest date,
    # then keep statuses distributed + active, ALL item types (unknown ones keep their own name)
    monthly_df = None
    monthly_month = None
    monthly_msg = None
    dd = d_raw.dropna(subset=["date"])
    if not dd.empty:
        last_d = dd["date"].max()
        monthly_month = int(last_d.month)
        in_m = dd[(dd["date"].dt.year == last_d.year) & (dd["date"].dt.month == last_d.month)].copy()
        in_m["lkey"] = in_m["line"].map(lambda s_: last10(s_) or s_)
        in_m = in_m.sort_values("date", kind="stable")
        in_m = in_m.drop_duplicates(subset="lkey", keep="last")
        m_rows_month = len(in_m)
        in_m = in_m[in_m["status"].isin(M_STATUSES)].copy()
        m_rows_status = len(in_m)
        if live is not None:
            in_live_m = in_m["lkey"].isin(live_set)
            live_removed_m = int(in_live_m.sum())
            in_m = in_m[~in_live_m].copy()
        m_no_key = int(in_m["key"].isna().sum())
        monthly_msg = (
            "monthly: rows(no dup)=" + str(m_rows_month)
            + " | after status=" + str(m_rows_status)
            + " | no office number=" + str(m_no_key)
            + " | bad dates=" + str(bad_dates)
        )
        raw_item = in_m["item"].replace({"": BLANK_LBL, "nan": BLANK_LBL, "none": BLANK_LBL})
        in_m[T["item"]] = in_m["item"].map(item_map).fillna(raw_item)
        in_m = in_m.dropna(subset=["key"])
        if not in_m.empty:
            mt = pd.crosstab(in_m["key"], in_m[T["item"]])
            for col in M_ITEMS:
                if col not in mt.columns:
                    mt[col] = 0
            extra_items = [c for c in mt.columns if c not in M_ITEMS]
            mt = mt[M_ITEMS + extra_items]
            mt.columns.name = None
            mt[T["total"]] = mt.sum(axis=1)
            mt = mt.sort_values(T["total"], ascending=False)
            mt.index.name = T["office_no"]
            mt = mt.reset_index()
            m_names = dict(zip(agents_df["key"], agents_df[T["office_name"]]))
            m_reps = dict(zip(agents_df["key"], agents_df[T["rep"]]))
            mt.insert(0, T["office_name"], mt[T["office_no"]].map(m_names).fillna(T["unmatched"]))
            mt.insert(2, T["rep"], mt[T["office_no"]].map(m_reps).fillna("").astype(str))
            monthly_df = mt

    rep_map = dict(zip(agents_df["key"], agents_df[T["rep"]]))
    result[T["rep"]] = result[T["office_no"]].map(rep_map).fillna("")
    order_base = [
        T["office_name"], T["office_no"], T["rep"],
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

    # sort: daily line activation (red + use) biggest first, then total line activation,
    # then the distribution total
    sk = pd.DataFrame(index=result.index)
    daily_cols = [c for c in result.columns if str(c).startswith(T["last_ru"])]
    sk["a"] = result[daily_cols[0]] if daily_cols else 0
    if T["act_red"] in result.columns and T["act_use"] in result.columns:
        sk["b"] = result[T["act_red"]] + result[T["act_use"]]
    else:
        sk["b"] = 0
    sk["c"] = result[T["total"]] if T["total"] in result.columns else 0
    sorted_idx = sk.sort_values(["a", "b", "c"], ascending=False, kind="stable").index
    result = result.loc[sorted_idx].reset_index(drop=True)

    ren = {}
    for c in [RED, USE, DAILY, MONTHLY, BIG_ROUTER, SMALL_MIFI, USE_1M]:
        if c in result.columns:
            ren[c] = T["remain"] + " " + c
    result = result.rename(columns=ren)

    unmatched_df = None
    agent_key_set = set(agents_df["key"])
    um_mask = ~result[T["office_no"]].isin(agent_key_set)
    um_count = int(um_mask.sum()) if have_agents else 0
    if um_count > 0:
        # numbers found in the reports but not in agents column B: moved to their own sheet
        unmatched_df = result[um_mask].reset_index(drop=True)
        st.warning(T["um_msg"] + ": " + str(um_count))
        result = result[~um_mask].reset_index(drop=True)

    st.success(T["done"] + ": " + str(len(result)) + " | " + T["unm_rows"] + ": " + str(unmatched))
    if have_dist:
        st.info(
            T["orig"] + ": " + str(total_rows)
            + " | " + T["dedup"] + ": " + str(after_dedup)
            + " | " + T["real"] + ": " + str(len(d))
            + " | " + T["bad_dates"] + ": " + str(bad_dates)
        )
    if live is not None and have_dist:
        st.info(
            T["live_info"] + ": " + str(len(live_set))
            + " | " + T["live_main"] + ": " + str(live_removed_main)
            + " | " + T["live_month"] + ": " + str(live_removed_m)
        )
        if live_removed_main == 0 and live_removed_m == 0:
            st.warning(
                T["live_none"]
                + " | " + T["live"] + " (A): " + str(live.iloc[:3, 0].tolist())
                + " | " + T["dist"] + " (A): " + str(dist.iloc[:3, 0].tolist())
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
    result.attrs["points_src"] = points_src
    result.attrs["monthly"] = monthly_df
    result.attrs["unmatched"] = unmatched_df
    result.attrs["monthly_month"] = monthly_month
    result.attrs["monthly_msg"] = monthly_msg
    return result


# ===== formatting settings (change here) =====
FONT_SIZE = 14
POINTS_SHEET_RTL = False   # False = points sheet starts from the left side (True = from the right)
HEADER_LINE_CHARS = 19   # approx. characters per line in a header cell
HEADER_LINE_PT = 19      # height of one text line (points)
COL_WIDTH = 24
GRAY_BODY = "D9D9D9"
GRAY_HEADER = "A6A6A6"
YELLOW = "FFFF00"


def fmt_num(v):
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v):
        v = int(v)
    if isinstance(v, int):
        return "{:,}".format(v)
    return "{:,.2f}".format(v)


def build_points_table(src, tgt_net, tgt_red, tgt_use):
    # daily table of points and counts per type (net / red / use) for the month
    s2 = src.copy()
    s2["pts"] = s2["pts"].fillna(0)
    dated = s2.dropna(subset=["date"]).copy()
    if dated.empty:
        return None
    dated["day"] = dated["date"].dt.normalize()
    last_day = dated["day"].max()
    year = last_day.year
    month = last_day.month
    ndays = calendar.monthrange(year, month)[1]
    month_name = MONTHS[month - 1]
    in_month = dated[(dated["day"].dt.year == year) & (dated["day"].dt.month == month)]
    groups = ["net", "red", "use"]

    rows = []
    for day in range(1, ndays + 1):
        label = month_name + " " + str(day).zfill(2)
        if day > last_day.day:
            rows.append([label, None, None, None, None, None, None])
            continue
        sub = in_month[in_month["day"].dt.day == day]
        vals = []
        for g in groups:
            vals.append(float(sub.loc[sub["group"] == g, "pts"].sum()))
        for g in groups:
            vals.append(int((sub["group"] == g).sum()))
        rows.append([label] + vals)

    daily_sum = []
    for i in range(1, 7):
        daily_sum.append(sum(r[i] for r in rows if r[i] is not None))

    grand = []
    for g in groups:
        grand.append(float(s2.loc[s2["group"] == g, "pts"].sum()))
    for g in groups:
        grand.append(int((s2["group"] == g).sum()))

    target = [tgt_net, tgt_red, tgt_use]
    ratio = []
    for i in range(3):
        if target[i]:
            ratio.append(grand[i] / target[i])
        else:
            ratio.append(None)

    heads = [T["col_date"], T["h_net_pts"], T["h_red_pts"], T["h_use_pts"],
             T["h_net_cnt"], T["h_red_cnt"], T["h_use_cnt"]]
    disp = []
    for r in rows:
        disp.append([r[0]] + [fmt_num(v) for v in r[1:]])
    disp.append([T["f_daily"]] + [fmt_num(v) for v in daily_sum])
    disp.append([T["f_total"]] + [fmt_num(v) for v in grand])
    disp.append([T["f_target"]] + [fmt_num(v) for v in target] + ["", "", ""])
    pct = []
    for v in ratio:
        if v is None:
            pct.append("")
        else:
            pct.append("{:.2f}%".format(v * 100))
    disp.append([T["f_ratio"]] + pct + ["", "", ""])
    display_df = pd.DataFrame(disp, columns=heads)

    return {
        "title": T["pts_title"] + " " + month_name,
        "heads": heads,
        "rows": rows,
        "daily_sum": daily_sum,
        "grand": grand,
        "target": target,
        "ratio": ratio,
        "display": display_df,
    }


def write_points_sheet(ws, info):
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    blue = "1F4E79"
    ws.sheet_view.rightToLeft = POINTS_SHEET_RTL
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    light = Side(style="thin", color="BFBFBF")
    box = Border(left=light, right=light, top=light, bottom=light)
    head_fill = PatternFill("solid", start_color=blue, end_color=blue)
    band_fill = PatternFill("solid", start_color="EEF3FA", end_color="EEF3FA")
    white_fill = PatternFill("solid", start_color="FFFFFF", end_color="FFFFFF")
    foot_fill = PatternFill("solid", start_color="DCE6F1", end_color="DCE6F1")
    ncols = 7

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    t = ws.cell(row=1, column=1, value=info["title"])
    t.font = Font(size=FONT_SIZE + 4, bold=True, color=blue)
    t.alignment = center
    ws.row_dimensions[1].height = 34

    hr = 3
    for j, h in enumerate(info["heads"], start=1):
        c = ws.cell(row=hr, column=j, value=h)
        c.font = Font(size=FONT_SIZE, bold=True, color="FFFFFF")
        c.fill = head_fill
        c.alignment = center
        c.border = box
    ws.row_dimensions[hr].height = 30

    r = hr + 1
    first_data = r
    for k, row in enumerate(info["rows"]):
        fill = band_fill if k % 2 == 0 else white_fill
        for j, v in enumerate(row, start=1):
            if isinstance(v, float) and v == int(v):
                v = int(v)
            c = ws.cell(row=r, column=j, value=v)
            c.font = Font(size=FONT_SIZE)
            c.fill = fill
            c.alignment = center
            c.border = box
            if j > 1:
                c.number_format = "#,##0"
        r += 1
    last_data = r - 1

    def footer(label, values, number_format, last=False):
        nonlocal r
        cells = [label] + list(values)
        while len(cells) < ncols:
            cells.append(None)
        for j, v in enumerate(cells, start=1):
            if isinstance(v, float) and number_format == "#,##0" and v == int(v):
                v = int(v)
            c = ws.cell(row=r, column=j, value=v)
            c.font = Font(size=FONT_SIZE, bold=True)
            c.fill = foot_fill
            c.alignment = center
            if last:
                dbl = Side(style="double", color=blue)
                c.border = Border(left=light, right=light, top=light, bottom=dbl)
            else:
                c.border = box
            if j > 1:
                c.number_format = number_format
        r += 1

    footer(T["f_daily"], info["daily_sum"], "#,##0")
    footer(T["f_total"], info["grand"], "#,##0")
    footer(T["f_target"], info["target"], "#,##0")
    footer(T["f_ratio"], info["ratio"], "0.00%", last=True)

    for i in range(1, ncols + 1):
        ws.column_dimensions[get_column_letter(i)].width = 20
    ws.auto_filter.ref = "A" + str(hr) + ":" + get_column_letter(ncols) + str(last_data)
    ws.freeze_panes = "A" + str(hr + 1)


def format_excel(df, extras=None, points=None, after_points=None):
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
        max_lines = 1
        for cell in ws[1]:
            if cell.value is not None:
                n = len(textwrap.wrap(str(cell.value), HEADER_LINE_CHARS)) or 1
                max_lines = max(max_lines, n)
        ws.row_dimensions[1].height = max_lines * HEADER_LINE_PT + 6
        ws.freeze_panes = "B2"

    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
        style_sheet(writer.sheets["Sheet1"])
        if extras is not None:
            for sheet_name, sheet_df in extras:
                sheet_df.to_excel(writer, index=False, sheet_name=sheet_name)
                style_sheet(writer.sheets[sheet_name])
        if points is not None:
            ws_points = writer.book.create_sheet(T["pts_sheet"])
            write_points_sheet(ws_points, points)
        if after_points is not None:
            for sheet_name, sheet_df in after_points:
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


try:
    TARGETS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "targets.json")
except NameError:
    TARGETS_FILE = "targets.json"


def target_month_key(now=None):
    # month of the report date (= yesterday, Iraq time).
    # the target starts again from 0 when this month changes
    if now is None:
        now = datetime.now(timezone(timedelta(hours=3)))
    day = now - timedelta(days=1)
    return str(day.year) + "-" + str(day.month).zfill(2)


def load_targets():
    try:
        with open(TARGETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_targets(month_key, net, red, use):
    data = load_targets()
    data[month_key] = {"net": int(net), "red": int(red), "use": int(use)}
    keys = sorted(data.keys())
    for k in keys[:-12]:
        del data[k]
    try:
        with open(TARGETS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception:
        return False


def report_file_name(now=None):
    # file name = brand + yesterday's date (day-month), Iraq time (UTC+3)
    # example: today is the 11th of October -> "brand 10-10.xlsx"
    if now is None:
        now = datetime.now(timezone(timedelta(hours=3)))
    day = now - timedelta(days=1)
    return T["brand"] + " " + str(day.day) + "-" + str(day.month) + ".xlsx"


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


# ===== second tab: compare two months (quality reports or bundle reports) =====
CMP_STATE = "الحالة"
CMP_TREND = "الاتجاه"
CMP_DIFF = "الفرق"
CMP_NEED = "يحتاج خط"

# office level inside a month (relative to the average of the active offices of that month).
# change these two numbers to make the levels stricter or easier
GOOD_RATIO = 1.0   # good: activity >= the average of active offices
MID_RATIO = 0.5    # medium: activity >= half of that average (below = weak)

LVL_GOOD, LVL_MID, LVL_WEAK, LVL_NONE = "زين", "متوسط", "ضعيف", "لا شي"
LVL_RANK = {LVL_NONE: 0, LVL_WEAK: 1, LVL_MID: 2, LVL_GOOD: 3}
ST_CALL = "بحاجة كول سنتر"
ST_DROP = "نزل مستواه"

# sales manager rating (weights are percentages, they are re-scaled if a target is not set)
MGR_WEIGHTS_Q = {"net": 15, "red": 15, "use": 15, "act": 15, "pts": 10, "active": 15, "keep": 10, "call": 5}
MGR_WEIGHTS_B = {"act": 30, "active": 30, "keep": 25, "call": 15}
MGR_RATING = [(90, "ممتاز"), (75, "جيد جداً"), (60, "جيد"), (40, "متوسط"), (0, "ضعيف")]


def cmp_status(prev, curr):
    # trend of an office between the two months
    if prev == 0 and curr == 0:
        return "لا يشتغل"
    if prev == 0:
        return "جديد"
    if curr == 0:
        return "متوقف"
    if curr > prev:
        return "صاعد"
    if curr < prev:
        return "نازل"
    return "ثابت"


def cmp_levels(vals, mask):
    act = vals[mask & (vals > 0)]
    avg = float(act.mean()) if len(act) else 0.0

    def lv(x):
        if x <= 0:
            return LVL_NONE
        if x >= GOOD_RATIO * avg:
            return LVL_GOOD
        if x >= MID_RATIO * avg:
            return LVL_MID
        return LVL_WEAK
    return [lv(x) for x in vals]


def cmp_state(prev_lvl, curr_lvl, curr_val):
    if curr_val <= 0:
        return ST_CALL
    if curr_lvl == LVL_WEAK and prev_lvl == LVL_WEAK:
        return ST_CALL
    if LVL_RANK[prev_lvl] > LVL_RANK[curr_lvl]:
        return ST_DROP
    return curr_lvl


def cmp_need_text(red, use, net):
    missing = []
    if red <= 0:
        missing.append("ريد")
    if use <= 0:
        missing.append("يوز")
    if net <= 0:
        missing.append("نت")
    if not missing:
        return "لا يحتاج"
    txt = missing[0]
    for m in missing[1:]:
        txt += " و" + m
    return "بحاجة خط " + txt


def cmp_agents_df(agents):
    # agents: A = office name, B = office number, C = rep name
    rep = agents.iloc[:, 2] if agents.shape[1] > 2 else ""
    df = pd.DataFrame({
        "key": agents.iloc[:, 1].apply(last10),
        T["office_name"]: agents.iloc[:, 0],
        T["rep"]: rep,
    })
    return df.dropna(subset=["key"]).drop_duplicates("key")


QMETRICS = [
    "مجموع التفعيل", "تفعيل ريد", "تفعيل يوز", "تفعيل نت",
    "نقاط الاتصال (ريد ويوز)", "نقاط النت",
]


def cmp_quality_summary(q):
    # per office: activations by type and points (same columns/types as the main quality logic)
    qd = pd.DataFrame({
        "group": q.iloc[:, Q_TYPE_COL].apply(clean_code).map(QUALITY_TYPE),
        "key": q.iloc[:, Q_OFFICE_COL].apply(last10),
    })
    if q.shape[1] > Q_POINTS_COL:
        qd["pts"] = pd.to_numeric(
            q.iloc[:, Q_POINTS_COL].astype(str).str.replace(",", "", regex=False), errors="coerce"
        )
    else:
        qd["pts"] = 0.0
    qd["pts"] = qd["pts"].fillna(0)
    ignored = int(qd["group"].isna().sum())
    qd = qd.dropna(subset=["group"])
    gpts = {g: float(qd.loc[qd["group"] == g, "pts"].sum()) for g in ["red", "use", "net"]}
    gcnt = {g: int((qd["group"] == g).sum()) for g in ["red", "use", "net"]}
    qd = qd.dropna(subset=["key"])
    out = pd.DataFrame(index=pd.Index([], name="key"), columns=QMETRICS, dtype=float)
    if len(qd) > 0:
        cnt = pd.crosstab(qd["key"], qd["group"])
        for g in ["red", "use", "net"]:
            if g not in cnt.columns:
                cnt[g] = 0
        out = pd.DataFrame({
            "تفعيل ريد": cnt["red"],
            "تفعيل يوز": cnt["use"],
            "تفعيل نت": cnt["net"],
        })
        out["مجموع التفعيل"] = out["تفعيل ريد"] + out["تفعيل يوز"] + out["تفعيل نت"]
        ru = qd[qd["group"].isin(["red", "use"])].groupby("key")["pts"].sum()
        nt = qd[qd["group"] == "net"].groupby("key")["pts"].sum()
        out["نقاط الاتصال (ريد ويوز)"] = ru
        out["نقاط النت"] = nt
        out = out[QMETRICS].fillna(0)
    return out, ignored, gpts, gcnt


def cmp_bundle_rows(bnd):
    # same naming rules as the bundles sheet: known names are merged, unknown keep their own name
    name_idx, hits = detect_bundle_col(bnd)
    if name_idx is None:
        return None
    if bnd.shape[1] > BND_SUB_COL:
        sub_vals = bnd.iloc[:, BND_SUB_COL].map(norm_name)
    else:
        sub_vals = ""
    b = pd.DataFrame({
        "key": bnd.iloc[:, BND_OFFICE_COL].apply(last10),
        "name": bnd.iloc[:, name_idx].map(norm_name),
        "sub": sub_vals,
    })
    b["label"] = [classify_bundle(n, s2) for n, s2 in zip(b["name"], b["sub"])]
    raw = bnd.iloc[:, name_idx].map(
        lambda x: "" if pd.isna(x) else re.sub(r"\s+", " ", str(x)).strip()
    )
    first_seen = {}
    for nm_n, nm_raw in zip(b["name"], raw):
        if nm_n and nm_n not in first_seen:
            first_seen[nm_n] = nm_raw
    unk = b["label"].isna() & (b["name"] != "")
    b.loc[unk, "label"] = b.loc[unk, "name"].map(first_seen)
    b = b.dropna(subset=["label", "key"])
    b = b[b["label"] != SKIP_BUNDLE]
    return b[["key", "label"]]


def cmp_remaining(dist, live):
    # remaining lines per office from the distribution report (same rules as the main tab):
    # latest row per line, status distributed, known items only, minus lines found in live stock
    d = pd.DataFrame({
        "line": dist.iloc[:, 0].astype(str).str.strip(),
        "item": dist.iloc[:, 2].astype(str).str.strip().str.lower(),
        "status": dist.iloc[:, 4].astype(str).str.strip().str.lower(),
        "key": dist.iloc[:, 5].apply(last10),
        "date": pd.to_datetime(dist.iloc[:, 8], errors="coerce"),
    })
    d = d.sort_values("date", kind="stable").drop_duplicates(subset="line", keep="last")
    d = d[d["status"] == "distributed"].copy()
    d["cat"] = d["item"].map(item_map)
    d = d.dropna(subset=["cat", "key"])
    removed = 0
    if live is not None:
        live_set = set(live.iloc[:, 0].apply(last10).dropna())
        in_live = d["line"].apply(last10).isin(live_set)
        removed = int(in_live.sum())
        d = d[~in_live]
    cnt = pd.crosstab(d["key"], d["cat"])
    for col in [RED, USE, USE_1M, DAILY, MONTHLY, BIG_ROUTER, SMALL_MIFI]:
        if col not in cnt.columns:
            cnt[col] = 0
    red = cnt[RED]
    use = cnt[USE] + cnt[USE_1M]
    net = cnt[DAILY] + cnt[MONTHLY] + cnt[BIG_ROUTER] + cnt[SMALL_MIFI]
    need = {k: cmp_need_text(red[k], use[k], net[k]) for k in cnt.index}
    return need, removed


def cmp_build(adf, prev_tbl, curr_tbl, metrics, int_metrics, status_metric, lp, lc, need=None):
    keys = list(adf["key"])
    seen = set(keys)
    for k in list(prev_tbl.index) + list(curr_tbl.index):
        if k not in seen:
            seen.add(k)
            keys.append(k)
    a_set = set(adf["key"])
    mask = pd.Series([k in a_set for k in keys])
    out = pd.DataFrame({T["office_no"]: keys})
    name_map = dict(zip(adf["key"], adf[T["office_name"]]))
    rep_map = dict(zip(adf["key"], adf[T["rep"]]))
    out.insert(0, T["office_name"], out[T["office_no"]].map(name_map).fillna(T["unmatched"]))
    out.insert(2, T["rep"], out[T["office_no"]].map(rep_map).fillna(""))
    p = prev_tbl.reindex(keys).fillna(0).reset_index(drop=True)
    c = curr_tbl.reindex(keys).fillna(0).reset_index(drop=True)
    pv_s, cv_s = p[status_metric], c[status_metric]
    lev_p = cmp_levels(pv_s, mask)
    lev_c = cmp_levels(cv_s, mask)
    out[CMP_STATE] = [cmp_state(a, b, v) for a, b, v in zip(lev_p, lev_c, cv_s)]
    out[CMP_TREND] = [cmp_status(a, b) for a, b in zip(pv_s, cv_s)]
    out["المستوى (" + lp + ")"] = lev_p
    out["المستوى (" + lc + ")"] = lev_c
    for m in metrics:
        pv = p[m].round(2)
        cv = c[m].round(2)
        dv = (c[m] - p[m]).round(2)
        if m in int_metrics:
            pv, cv, dv = pv.astype(int), cv.astype(int), dv.astype(int)
        out[m + " (" + lp + ")"] = pv.values
        out[m + " (" + lc + ")"] = cv.values
        out[m + " - " + CMP_DIFF] = dv.values
    if need is not None:
        # last field: only when the distribution report was uploaded
        out[CMP_NEED] = out[T["office_no"]].map(need).fillna(cmp_need_text(0, 0, 0))
    out["_c"] = cv_s.values
    out["_p"] = pv_s.values
    out = out.sort_values(["_c", "_p"], ascending=False, kind="stable").drop(columns=["_c", "_p"])
    out = out.reset_index(drop=True)
    in_agents = out[T["office_no"]].isin(a_set)
    unmatched = out[~in_agents].reset_index(drop=True)
    main = out[in_agents].reset_index(drop=True)
    return main, unmatched


def cmp_reps(main, metric, lp, lc):
    # per rep: total of his offices in both months + trend (up / down)
    pcol = metric + " (" + lp + ")"
    ccol = metric + " (" + lc + ")"
    df = main[[T["rep"], pcol, ccol, CMP_STATE, CMP_TREND]].copy()
    df[T["rep"]] = df[T["rep"]].astype(str).str.strip().replace({"": "بدون مندوب", "nan": "بدون مندوب"})
    g = df.groupby(T["rep"])
    out = pd.DataFrame({"عدد المكاتب": g.size(), pcol: g[pcol].sum(), ccol: g[ccol].sum()})
    out[CMP_DIFF] = out[ccol] - out[pcol]
    out["النسبة %"] = [round(d / p * 100, 1) if p > 0 else None for d, p in zip(out[CMP_DIFF], out[pcol])]
    out[CMP_TREND] = [cmp_status(a, b) for a, b in zip(out[pcol], out[ccol])]
    out["مكاتب متوقفة"] = g[CMP_TREND].apply(lambda s: int((s == "متوقف").sum()))
    out["بحاجة كول سنتر"] = g[CMP_STATE].apply(lambda s: int((s == ST_CALL).sum()))
    out = out.sort_values(ccol, ascending=False).reset_index().rename(columns={T["rep"]: "المندوب"})
    return out


def cmp_rating(score):
    for lim, name in MGR_RATING:
        if score >= lim:
            return name
    return MGR_RATING[-1][1]


def cmp_manager(kind, main, metric, lp, lc, tot_prev, tot_curr, gpts_prev, gpts_curr, targets):
    # sales manager performance: targets + results + growth + health of the offices
    rows = []   # (name, prev, curr, change, standard, score, weight, note)
    weights = MGR_WEIGHTS_Q if kind == "quality" else MGR_WEIGHTS_B
    total_n = len(main)
    pcol = metric + " (" + lp + ")"
    ccol = metric + " (" + lc + ")"

    def clamp(x):
        return max(0.0, min(100.0, x))

    def growth_score(prev, curr):
        if prev <= 0:
            return (100.0 if curr > 0 else 0.0), None
        g = (curr - prev) / prev
        return clamp(60 + 200 * g), g

    if kind == "quality":
        for key, label in [("net", "تاركت النقاط - نت"), ("red", "تاركت النقاط - ريد"), ("use", "تاركت النقاط - يوز")]:
            tgt = float(targets.get(key, 0) or 0)
            if tgt <= 0:
                continue
            cur = gpts_curr[key]
            ach = cur / tgt
            rows.append((label, round(gpts_prev[key], 2), round(cur, 2), round(cur - gpts_prev[key], 2),
                         round(tgt, 2), round(clamp(ach * 100), 1), weights[key],
                         "تحقق {:.0%} من الهدف".format(ach)))
        sc, g = growth_score(tot_prev, tot_curr)
        rows.append(("نمو إجمالي التفعيل", tot_prev, tot_curr, tot_curr - tot_prev, "ثبات = 60 ، +20% = 100",
                     round(sc, 1), weights["act"], "" if g is None else "التغير {:+.0%}".format(g)))
        sp, sc_c = sum(gpts_prev.values()), sum(gpts_curr.values())
        sc, g = growth_score(sp, sc_c)
        rows.append(("نمو إجمالي النقاط", round(sp, 2), round(sc_c, 2), round(sc_c - sp, 2), "ثبات = 60 ، +20% = 100",
                     round(sc, 1), weights["pts"], "" if g is None else "التغير {:+.0%}".format(g)))
    else:
        sc, g = growth_score(tot_prev, tot_curr)
        rows.append(("نمو إجمالي الباقات", tot_prev, tot_curr, tot_curr - tot_prev, "ثبات = 60 ، +20% = 100",
                     round(sc, 1), weights["act"], "" if g is None else "التغير {:+.0%}".format(g)))

    if total_n > 0:
        act_p = int((main[pcol] > 0).sum())
        act_c = int((main[ccol] > 0).sum())
        rows.append(("نسبة المكاتب الفعّالة", "{:.0%}".format(act_p / total_n), "{:.0%}".format(act_c / total_n),
                     "{:+.0%}".format((act_c - act_p) / total_n), "كل المكاتب",
                     round(100.0 * act_c / total_n, 1), weights["active"],
                     "{} من {} مكتب".format(act_c, total_n)))
        bad = int(main[CMP_TREND].isin(["نازل", "متوقف"]).sum())
        rows.append(("نسبة المكاتب اللي ما نزلت ولا توقفت", "", "{:.0%}".format(1 - bad / total_n), "",
                     "كل المكاتب", round(100.0 * (1 - bad / total_n), 1), weights["keep"],
                     "{} مكتب نازل أو متوقف".format(bad)))
        cc = int((main[CMP_STATE] == ST_CALL).sum())
        rows.append(("نسبة المكاتب بحاجة كول سنتر", "", "{:.0%}".format(cc / total_n), "",
                     "كل ما قلّت أحسن", round(100.0 * (1 - cc / total_n), 1), weights["call"],
                     "{} مكتب".format(cc)))

    wsum = sum(r[6] for r in rows)
    final = sum(r[5] * r[6] for r in rows) / wsum if wsum > 0 else 0.0
    cols = ["البند", "السابق (" + lp + ")", "الحالي (" + lc + ")", "التغير", "الهدف / المعيار",
            "الدرجة من 100", "الوزن %", "ملاحظة"]
    df = pd.DataFrame(rows, columns=cols)
    weak = sorted(rows, key=lambda r: r[5])[:2]
    weak_txt = " ، ".join(r[0] for r in weak if r[5] < 60) or "لا توجد نقاط ضعف واضحة"
    extra = [
        ("الدرجة النهائية (من 100)", "", round(final, 1), "", "", "", "", ""),
        ("تقييم مدير المبيعات", "", cmp_rating(final), "", "", "", "", ""),
        ("أضعف المؤشرات", "", weak_txt, "", "", "", "", ""),
        ("", "", "", "", "", "", "", ""),
        ("توزيع المكاتب حسب الحالة", "", "", "", "", "", "", ""),
    ]
    for st_name, n in main[CMP_STATE].value_counts().items():
        extra.append((st_name, "", int(n), "", "", "", "", "{:.0%} من المكاتب".format(n / total_n)))
    df = pd.concat([df, pd.DataFrame(extra, columns=cols)], ignore_index=True)
    return df, final


def cmp_add_excel_chart(data, sheet, n_rows, title):
    # native Excel bar chart (previous vs current) on the reps sheet
    try:
        import openpyxl
        from openpyxl.chart import BarChart, Reference
        wb = openpyxl.load_workbook(BytesIO(data))
        ws = wb[sheet]
        ch = BarChart()
        ch.type = "col"
        ch.title = title
        ch.add_data(Reference(ws, min_col=3, max_col=4, min_row=1, max_row=n_rows + 1), titles_from_data=True)
        ch.set_categories(Reference(ws, min_col=1, min_row=2, max_row=n_rows + 1))
        ch.height = 11
        ch.width = max(20, 2.2 * n_rows)
        ws.add_chart(ch, "L2")
        buf = BytesIO()
        wb.save(buf)
        return buf.getvalue()
    except Exception:
        return data


def cmp_run(kind, agents, rep_prev, rep_curr, lp, lc, dist=None, live=None, targets=None):
    # returns a dict; on a problem {"error": [messages]}
    targets = targets or {}
    adf = cmp_agents_df(agents)
    msgs = []
    need = None
    if dist is not None:
        need, removed = cmp_remaining(dist, live)
        if live is not None:
            msgs.append("خطوط انشالت لأنها بالايف ستوك: " + str(removed))
        else:
            msgs.append("ما رفعت الايف ستوك، فالخطوط الباقية = كل الخطوط الموزعة")
    gp = gc = {"red": 0.0, "use": 0.0, "net": 0.0}
    if kind == "quality":
        p_tbl, ig1, gp, cnt_p = cmp_quality_summary(rep_prev)
        c_tbl, ig2, gc, cnt_c = cmp_quality_summary(rep_curr)
        if ig1 or ig2:
            msgs.append("صفوف كوالتي متجاهلة (نوع غير معروف): " + str(ig1) + " / " + str(ig2))
        metric = "مجموع التفعيل"
        main, um = cmp_build(adf, p_tbl, c_tbl, QMETRICS, QMETRICS[:4], metric, lp, lc, need)
        extras_tail = []
    else:
        bp = cmp_bundle_rows(rep_prev)
        bc = cmp_bundle_rows(rep_curr)
        if bp is None or bc is None:
            return {"error": ["ما لقيت عمود اسم الباقة بأحد التقريرين"]}
        p_tbl = bp.groupby("key").size().to_frame("عدد الباقات")
        c_tbl = bc.groupby("key").size().to_frame("عدد الباقات")
        metric = "عدد الباقات"
        main, um = cmp_build(adf, p_tbl, c_tbl, [metric], [metric], metric, lp, lc, need)
        # per bundle detail (long format, easy to filter in Excel)
        pc = bp.groupby(["key", "label"]).size().rename("p")
        cc = bc.groupby(["key", "label"]).size().rename("c")
        det = pd.concat([pc, cc], axis=1).fillna(0).reset_index()
        det = det[det["key"].isin(set(adf["key"]))]   # numbers not in agents are in the unmatched sheet
        if len(det) > 0:
            det["p"] = det["p"].astype(int)
            det["c"] = det["c"].astype(int)
            det["d"] = det["c"] - det["p"]
            tot_c = det.groupby("key")["c"].transform("sum")
            det = det.assign(_t=tot_c).sort_values(["_t", "key", "c"], ascending=[False, True, False])
            det = det.drop(columns="_t")
            name_map = dict(zip(adf["key"], adf[T["office_name"]]))
            rep_map = dict(zip(adf["key"], adf[T["rep"]]))
            det.insert(0, T["office_name"], det["key"].map(name_map).fillna(T["unmatched"]))
            det.insert(2, T["rep"], det["key"].map(rep_map).fillna(""))
            det = det.rename(columns={
                "key": T["office_no"], "label": "الباقة",
                "p": "العدد (" + lp + ")", "c": "العدد (" + lc + ")", "d": CMP_DIFF,
            }).reset_index(drop=True)
        else:
            det = pd.DataFrame(columns=[T["office_name"], T["office_no"], T["rep"], "الباقة"])
        extras_tail = [("تفصيل الباقات", det)]
    all_keys = set(p_tbl.index) | set(c_tbl.index)
    if len(all_keys) > 0 and len(all_keys & set(adf["key"])) == 0:
        msgs.append("ما تطابق أي رقم مكتب بالتقارير مع عمود B بالوكلاء، تأكد من الملفات")
    reps = cmp_reps(main, metric, lp, lc)
    tot_p = float(p_tbl[metric].sum()) if len(p_tbl) else 0.0
    tot_c = float(c_tbl[metric].sum()) if len(c_tbl) else 0.0
    mgr, final = cmp_manager(kind, main, metric, lp, lc, int(tot_p), int(tot_c), gp, gc, targets)
    extras = [("أداء مدير المبيعات", mgr), ("المندوبين", reps)] + extras_tail
    if len(um) > 0:
        extras.append((T["unmatched"], um))
        msgs.append("مكاتب غير مطابقة اننقلت لشيت منفصل: " + str(len(um)))
    return {"main": main, "extras": extras, "msgs": msgs, "reps": reps, "manager": mgr,
            "final": final, "metric": metric}


def cmp_show_rep_charts(reps, metric, lp, lc):
    pcol = metric + " (" + lp + ")"
    ccol = metric + " (" + lc + ")"
    if len(reps) == 0:
        return
    st.write("رسم المندوبين: " + lp + " مقابل " + lc)
    st.bar_chart(reps.set_index("المندوب")[[pcol, ccol]])
    st.write("صعود ونزول كل مندوب (الفرق)")
    d = reps[["المندوب", CMP_DIFF]].copy()
    d["اتجاه"] = d[CMP_DIFF].map(lambda v: "صاعد" if v >= 0 else "نازل")
    try:
        import altair as alt
        chart = alt.Chart(d).mark_bar().encode(
            x=alt.X("المندوب:N", sort=None),
            y=alt.Y(CMP_DIFF + ":Q"),
            color=alt.Color("اتجاه:N", scale=alt.Scale(domain=["صاعد", "نازل"], range=["#2e7d32", "#c62828"])),
            tooltip=["المندوب", CMP_DIFF, "اتجاه"],
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.bar_chart(d.set_index("المندوب")[CMP_DIFF])


def compare_page():
    st.title("مقارنة شهرين")
    kind_lbl = st.radio("نوع التقرير", ["الكوالتي", "الباقات"], horizontal=True, key="cmp_kind")
    kind = "quality" if kind_lbl == "الكوالتي" else "bundles"
    l1, l2 = st.columns(2)
    with l1:
        lp = st.text_input("اسم الشهر السابق", value="الشهر السابق", key="cmp_lp")
    with l2:
        lc = st.text_input("اسم هذا الشهر", value="هذا الشهر", key="cmp_lc")
    lp = lp.strip() or "الشهر السابق"
    lc = lc.strip() or "هذا الشهر"
    if lp == lc:
        lc = lc + " 2"
    f1, f2, f3 = st.columns(3)
    with f1:
        up_a = st.file_uploader("تقرير الوكلاء (إجباري)", key="cmp_agents")
    with f2:
        up_p = st.file_uploader("تقرير " + kind_lbl + " - " + lp, key="cmp_prev_" + kind)
    with f3:
        up_c = st.file_uploader("تقرير " + kind_lbl + " - " + lc, key="cmp_curr_" + kind)
    g1, g2 = st.columns(2)
    with g1:
        up_d = st.file_uploader("تقرير التوزيع (اختياري، لحقل: يحتاج خط)", key="cmp_dist")
    with g2:
        up_l = st.file_uploader("الايف ستوك (اختياري، مع التوزيع)", key="cmp_live")
    targets = {}
    if kind == "quality":
        saved = load_targets().get(target_month_key(), {})
        with st.expander("التاركت الشهري (نقاط) لتقييم مدير المبيعات", expanded=True):
            t1, t2, t3 = st.columns(3)
            with t1:
                targets["net"] = st.number_input("تاركت نت", min_value=0, value=int(saved.get("net", 0)), step=100, key="cmp_tn")
            with t2:
                targets["red"] = st.number_input("تاركت ريد", min_value=0, value=int(saved.get("red", 0)), step=100, key="cmp_tr")
            with t3:
                targets["use"] = st.number_input("تاركت يوز", min_value=0, value=int(saved.get("use", 0)), step=100, key="cmp_tu")
    if up_a is None or up_p is None or up_c is None:
        st.info("ارفع تقرير الوكلاء وتقريرين من نفس النوع (" + kind_lbl + ") حتى تبدأ المقارنة")
        return
    frames = []
    loads = [(f1, up_a, "الوكلاء - مقارنة"), (f2, up_p, "السابق - مقارنة"), (f3, up_c, "الحالي - مقارنة")]
    for col, up, lbl in loads:
        with col:
            sh = load_report(up, lbl)
            frames.append(pick_sheet(sh, lbl) if sh is not None else None)
    dist = live = None
    if up_d is not None:
        with g1:
            sh = load_report(up_d, "التوزيع - مقارنة")
            dist = pick_sheet(sh, "التوزيع - مقارنة") if sh is not None else None
    if up_l is not None:
        with g2:
            sh = load_report(up_l, "الايف ستوك - مقارنة")
            live = pick_sheet(sh, "الايف ستوك - مقارنة") if sh is not None else None
    if any(fr is None for fr in frames):
        return
    agents, rep_prev, rep_curr = frames
    n_rep = 4 if kind == "quality" else 1
    need = [(agents, 3, "الوكلاء"), (rep_prev, n_rep, lp), (rep_curr, n_rep, lc)]
    if dist is not None:
        need.append((dist, 9, "التوزيع"))
    for df, n, nm in need:
        if df.shape[1] < n:
            st.error("تقرير " + nm + ": عدد الأعمدة " + str(df.shape[1]) + " والمطلوب على الأقل " + str(n))
            return
    if st.button("قارن", key="cmp_go"):
        try:
            res = cmp_run(kind, agents, rep_prev, rep_curr, lp, lc, dist, live, targets)
        except Exception:
            st.error("حدث خطأ")
            st.code(traceback.format_exc())
            return
        if "error" in res:
            for m in res["error"]:
                st.error(m)
            return
        main, extras, metric = res["main"], res["extras"], res["metric"]
        st.success("تمت المقارنة. عدد المكاتب: " + str(len(main)))
        for m in res["msgs"]:
            st.info(m)
        counts = main[CMP_STATE].value_counts()
        st.info(" | ".join(k + ": " + str(int(v)) for k, v in counts.items()))
        show_table(main)
        cmp_show_rep_charts(res["reps"], metric, lp, lc)
        st.write("أداء مدير المبيعات: " + cmp_rating(res["final"]) + " ({:.1f} من 100)".format(res["final"]))
        show_table(res["manager"])
        for name, df in extras:
            if name == "تفصيل الباقات":
                st.write(name)
                st.dataframe(df, use_container_width=True)
        data = format_excel(main, extras)
        data = cmp_add_excel_chart(data, "المندوبين", len(res["reps"]), "المندوبين: " + lp + " مقابل " + lc)
        st.download_button(
            T["download"], data=data,
            file_name="comparison_" + kind + ".xlsx", mime=XLSX_MIME, key="cmp_dl",
        )


# ===== tabs "عشوائيات" (alerts, call-center list, dashboard, per-rep reports, helpers) and "كيبي اي" =====
# both read the result of the first tab (kept in st.session_state["last_result"] after "احسب")
import zipfile

try:
    KPI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kpi_targets.json")
except NameError:
    KPI_FILE = "kpi_targets.json"

STUCK_STOCK = 10   # lines left with an office that has no activation = stuck lines


def load_kpi():
    try:
        with open(KPI_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_kpi(month_key, wal, inc):
    data = load_kpi()
    data[month_key] = {"wal": int(wal), "inc": int(inc)}
    for k in sorted(data.keys())[:-12]:
        del data[k]
    try:
        with open(KPI_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True
    except Exception:
        return False


def col_like(df, base):
    for c in df.columns:
        if c == base or str(c).startswith(base + " "):
            return c
    return None


def num_col(res, base):
    c = col_like(res, base)
    if c is None:
        return None
    return pd.to_numeric(res[c], errors="coerce").fillna(0).reset_index(drop=True)


def clean_rep(s):
    return s.astype(str).str.strip().replace({"": "بدون مندوب", "nan": "بدون مندوب"})


def remaining_cols(res):
    # remaining lines per office from the first sheet: red / use / net (None = column not there)
    def total(names):
        tot = None
        for nm in names:
            c = T["remain"] + " " + nm
            if c in res.columns:
                v = pd.to_numeric(res[c], errors="coerce").fillna(0).reset_index(drop=True)
                tot = v if tot is None else tot + v
        return tot
    return total([RED]), total([USE, USE_1M]), total([DAILY, MONTHLY, BIG_ROUTER, SMALL_MIFI])


def need_text_low(red, use, net, low):
    missing = []
    if red <= low:
        missing.append("ريد")
    if use <= low:
        missing.append("يوز")
    if net <= low:
        missing.append("نت")
    if not missing:
        return ""
    txt = missing[0]
    for m in missing[1:]:
        txt += " و" + m
    return "بحاجة خط " + txt


def alerts_frame(res, low):
    # one row per office with the reasons; also the call-center list and the lines-needed list
    n = len(res)
    zero = pd.Series([0] * n)
    d = pd.DataFrame({
        T["office_name"]: res[T["office_name"]].values,
        T["office_no"]: res[T["office_no"]].values,
        T["rep"]: (clean_rep(res[T["rep"]]).values if T["rep"] in res.columns else ["بدون مندوب"] * n),
    })
    ar, au, an = num_col(res, T["act_red"]), num_col(res, T["act_use"]), num_col(res, T["act_net"])
    has_q = ar is not None and au is not None and an is not None
    if has_q:
        d["مجموع التفعيل"] = (ar + au + an).values
        dr, dn = num_col(res, T["last_ru"]), num_col(res, T["last_net"])
        last = (dr if dr is not None else zero) + (dn if dn is not None else zero)
        d["تفعيل آخر يوم"] = last.values
        pr, pn = num_col(res, T["pts_ru"]), num_col(res, T["pts_net"])
        d["النقاط"] = ((pr if pr is not None else zero) + (pn if pn is not None else zero)).round(2).values
        d["المستوى"] = cmp_levels(d["مجموع التفعيل"], pd.Series([True] * n))
    rd, us, nw = remaining_cols(res)
    has_stock = rd is not None or us is not None or nw is not None
    if has_stock:
        d["باقي ريد"] = (rd if rd is not None else zero).astype(int).values
        d["باقي يوز"] = (us if us is not None else zero).astype(int).values
        d["باقي نت"] = (nw if nw is not None else zero).astype(int).values
    call_r, info_r, need_r, prio = [], [], [], []
    for i in range(n):
        rc, ri = [], []
        tot = d["مجموع التفعيل"].iat[i] if has_q else None
        if has_q:
            if tot == 0:
                rc.append("لا تفعيل هذا الشهر")
            else:
                if d["المستوى"].iat[i] == LVL_WEAK:
                    rc.append("ضعيف التفعيل")
                if d["تفعيل آخر يوم"].iat[i] == 0:
                    ri.append("ما فعّل بآخر يوم")
        need = ""
        if has_stock:
            a, b, c = d["باقي ريد"].iat[i], d["باقي يوز"].iat[i], d["باقي نت"].iat[i]
            need = need_text_low(a, b, c, low)
            if tot == 0 and (a + b) >= STUCK_STOCK:
                rc.append("خطوط واقفة ({})".format(int(a + b)))
        call_r.append(" + ".join(rc))
        info_r.append(" + ".join(ri))
        need_r.append(need)
        if any(x == "لا تفعيل هذا الشهر" or x.startswith("خطوط واقفة") for x in rc):
            prio.append("عالي")
        elif rc:
            prio.append("متوسط")
        else:
            prio.append("")
    d["سبب الاتصال"] = call_r
    d["ملاحظات"] = info_r
    d["بحاجة خط"] = need_r
    d["الأولوية"] = prio
    base = [T["office_name"], T["office_no"], T["rep"]]
    call_cols = base + (["مجموع التفعيل", "تفعيل آخر يوم", "النقاط"] if has_q else []) + ["سبب الاتصال", "الأولوية"]
    call_df = d[d["سبب الاتصال"] != ""][call_cols].copy()
    rank = {"عالي": 0, "متوسط": 1}
    call_df["_r"] = call_df["الأولوية"].map(rank)
    sort_cols = ["_r"] + (["مجموع التفعيل"] if has_q else [])
    call_df = call_df.sort_values(sort_cols, kind="stable").drop(columns="_r").reset_index(drop=True)
    need_cols = base + (["باقي ريد", "باقي يوز", "باقي نت"] if has_stock else []) + ["بحاجة خط"]
    need_df = d[d["بحاجة خط"] != ""][need_cols].reset_index(drop=True)
    return d, call_df, need_df, has_q, has_stock


def kpi_row(label, tgt, ach, elapsed, total_days, forecast):
    cols = ["المؤشر", "التاركت", "المحقق", "النسبة %", "المتبقي", "التوقع نهاية الشهر",
            "نسبة التوقع %", "المطلوب يومياً", "الحالة"]
    row = {c: None for c in cols}
    row["المؤشر"] = label
    row["التاركت"] = tgt
    if ach is None:
        row["الحالة"] = "ما انرفع التقرير"
        return row
    row["المحقق"] = round(ach, 2)
    if tgt <= 0:
        row["الحالة"] = "لم يُحدد التاركت"
        return row
    pct = ach / tgt * 100
    remaining = max(0.0, tgt - ach)
    row["النسبة %"] = round(pct, 1)
    row["المتبقي"] = round(remaining, 2)
    if forecast and elapsed and total_days:
        fc = ach / elapsed * total_days
        fpct = fc / tgt * 100
        left = total_days - elapsed
        row["التوقع نهاية الشهر"] = round(fc, 2)
        row["نسبة التوقع %"] = round(fpct, 1)
        row["المطلوب يومياً"] = round(remaining / left, 2) if left > 0 else None
        if pct >= 100:
            row["الحالة"] = "محقق"
        elif fpct >= 100:
            row["الحالة"] = "على المسار"
        elif fpct >= 80:
            row["الحالة"] = "قريب"
        else:
            row["الحالة"] = "متأخر"
    else:
        row["الحالة"] = "محقق" if pct >= 100 else "غير محقق"
    return row


def kpi_table(res, tg):
    # achieved numbers come from the first sheet (points from the quality rows, wallet/incentive = "done" offices)
    src = res.attrs.get("points_src")
    ach = {"net": 0.0, "red": 0.0, "use": 0.0}
    elapsed = total_days = None
    has_pts = src is not None and len(src) > 0
    if has_pts:
        s2 = src.copy()
        s2["pts"] = s2["pts"].fillna(0)
        for g in ach:
            ach[g] = float(s2.loc[s2["group"] == g, "pts"].sum())
        dated = s2.dropna(subset=["date"])
        if len(dated) > 0:
            last = dated["date"].max()
            elapsed = int(last.day)
            total_days = calendar.monthrange(last.year, last.month)[1]
    rows = []
    for key, label in [("net", "تاركت نت (نقاط)"), ("red", "تاركت ريد (نقاط)"), ("use", "تاركت يوز (نقاط)")]:
        rows.append(kpi_row(label, float(tg.get(key, 0) or 0), ach[key] if has_pts else None,
                            elapsed, total_days, True))
    wal_done = int((res[T["wal"]] == "done").sum()) if T["wal"] in res.columns else None
    inc_done = int((res[T["inc"]] == "done").sum()) if T["inc"] in res.columns else None
    rows.append(kpi_row("تاركت المحفظة (عدد المكاتب)", float(tg.get("wal", 0) or 0), wal_done, None, None, False))
    rows.append(kpi_row("تاركت الحافز (عدد المكاتب)", float(tg.get("inc", 0) or 0), inc_done, None, None, False))
    return pd.DataFrame(rows), elapsed, total_days


def saved_targets_all():
    mk = target_month_key()
    tg = dict(load_targets().get(mk, {}))
    tg.update(load_kpi().get(mk, {}))
    return tg


def safe_file_name(s):
    return re.sub(r'[\\/:*?"<>|]', "_", str(s)).strip() or "rep"


def build_all_zip(res, call_df, need_df):
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        main_x = st.session_state.get("last_xlsx")
        if main_x:
            z.writestr(report_file_name(), main_x)
        z.writestr("call_center.xlsx", format_excel(call_df))
        z.writestr("need_lines.xlsx", format_excel(need_df))
        kt, _, _ = kpi_table(res, saved_targets_all())
        z.writestr("kpi.xlsx", format_excel(kt))
        z.writestr("mini_report.xlsx", format_excel(mini_report(res)[0]))
        reps = clean_rep(res[T["rep"]]) if T["rep"] in res.columns else pd.Series(["بدون مندوب"] * len(res))
        for i, rep in enumerate(sorted(set(reps)), start=1):
            sub = res[(reps == rep).values]
            z.writestr("reps/{:02d}_{}.xlsx".format(i, safe_file_name(rep)), format_excel(sub))
    return buf.getvalue()


def rep_perf(d, tg):
    # performance per rep: active offices %, share of points, and performance vs the average office
    reps = d[T["rep"]]
    n_all = len(d)
    tot_pts = float(d["النقاط"].sum())
    avg_all = tot_pts / n_all if n_all else 0
    tgt_all = sum(float(tg.get(k, 0) or 0) for k in ("net", "red", "use"))
    rows = []
    for rep in sorted(set(reps)):
        sub = d[reps == rep]
        n = len(sub)
        act = int((sub["مجموع التفعيل"] > 0).sum())
        pts = float(sub["النقاط"].sum())
        row = {
            "المندوب": rep,
            "عدد المكاتب": n,
            "مكاتب فعّالة": act,
            "نسبة المكاتب الفعّالة %": round(act / n * 100, 1) if n else 0,
            "مجموع التفعيل": int(sub["مجموع التفعيل"].sum()),
            "النقاط": round(pts, 1),
            "حصته من النقاط %": round(pts / tot_pts * 100, 1) if tot_pts else 0,
            "نسبة الأداء %": round((pts / n) / avg_all * 100, 1) if (n and avg_all) else 0,
        }
        if tgt_all > 0 and n_all:
            row["نسبة من التاركت الموزّع %"] = round(pts / (tgt_all * n / n_all) * 100, 1)
        rows.append(row)
    out = pd.DataFrame(rows).sort_values("نسبة الأداء %", ascending=False, kind="stable")
    return out.reset_index(drop=True)


def mini_report(res):
    # small report: total prep (red+use) and net package prep from the monthly distribution sheet,
    # total activation, remaining lines = prep - activation, plus wallet and incentive
    n = len(res)
    zero = pd.Series([0] * n)
    out = pd.DataFrame({
        T["office_name"]: res[T["office_name"]].values,
        T["office_no"]: res[T["office_no"]].values,
        T["rep"]: (clean_rep(res[T["rep"]]).values if T["rep"] in res.columns else ["بدون مندوب"] * n),
    })
    prep_call = zero.copy()
    prep_net = zero.copy()
    m = res.attrs.get("monthly")
    if m is not None and len(m) > 0:
        mm = m.set_index(T["office_no"])
        keys = res[T["office_no"]].values
        def pick(cols):
            tot = pd.Series([0] * n)
            for c in cols:
                if c in mm.columns:
                    tot = tot + pd.Series([mm[c].get(k, 0) for k in keys]).fillna(0)
            return tot
        prep_call = pick([RED, USE])
        prep_net = pick([DAILY])
    ar, au, an = num_col(res, T["act_red"]), num_col(res, T["act_use"]), num_col(res, T["act_net"])
    act_call = (ar if ar is not None else zero) + (au if au is not None else zero)
    act_net = an if an is not None else zero
    out["التجهيز الكلي (يوز + ريد)"] = prep_call.astype(int).values
    out["تجهيز النت (البكج)"] = prep_net.astype(int).values
    out["تفعيل كلي اتصال"] = act_call.astype(int).values
    out["تفعيل كلي نت"] = act_net.astype(int).values
    out["باقي خط اتصال"] = (prep_call - act_call).astype(int).values
    out["باقي خط نت"] = (prep_net - act_net).astype(int).values
    out[T["wal"]] = res[T["wal"]].values if T["wal"] in res.columns else [""] * n
    out[T["inc"]] = res[T["inc"]].values if T["inc"] in res.columns else [""] * n
    return out, (m is not None and len(m) > 0)


def random_page():
    st.title("عشوائيات")
    res = st.session_state.get("last_result")
    if res is None:
        st.info("احسبي بالتبويب الأول (الرئيسي) أولاً، وبعدها تطلع هنا التنبيهات واللوحة والقوائم")
        return
    low = st.number_input("نبّه إذا الباقي من الخط أقل أو يساوي", min_value=0, value=2, step=1, key="rnd_low")
    d, call_df, need_df, has_q, has_stock = alerts_frame(res, low)

    st.subheader("لوحة المؤشرات")
    n = len(d)
    cards = st.columns(6)
    with cards[0]:
        st.metric("عدد المكاتب", n)
    if has_q:
        with cards[1]:
            st.metric("مكاتب فعّالة", int((d["مجموع التفعيل"] > 0).sum()))
        with cards[2]:
            st.metric("مجموع التفعيل", int(d["مجموع التفعيل"].sum()))
        with cards[3]:
            st.metric("مجموع النقاط", round(float(d["النقاط"].sum()), 1))
    with cards[4]:
        st.metric("بحاجة كول سنتر", len(call_df))
    with cards[5]:
        st.metric("بحاجة خطوط", len(need_df))
    src = res.attrs.get("points_src")
    if src is not None and len(src) > 0:
        s2 = src.dropna(subset=["date"]).copy()
        if len(s2) > 0:
            s2["day"] = s2["date"].dt.normalize()
            last = s2["day"].max()
            s2 = s2[(s2["day"].dt.year == last.year) & (s2["day"].dt.month == last.month)]
            daily = s2.groupby(["day", "group"]).size().unstack(fill_value=0)
            daily = daily.rename(columns={"red": "ريد", "use": "يوز", "net": "نت"})
            st.write("التفعيل اليومي")
            st.line_chart(daily)
    if has_q:
        t1, t2 = st.columns(2)
        show_cols = [T["office_name"], T["rep"], "مجموع التفعيل", "النقاط"]
        with t1:
            st.write("أفضل 10 مكاتب")
            st.dataframe(d.sort_values("مجموع التفعيل", ascending=False)[show_cols].head(10), use_container_width=True)
        with t2:
            st.write("أضعف 10 مكاتب (فيها تفعيل)")
            act = d[d["مجموع التفعيل"] > 0]
            st.dataframe(act.sort_values("مجموع التفعيل")[show_cols].head(10), use_container_width=True)

    st.subheader("التنبيهات")
    a = st.columns(5)
    if has_q:
        with a[0]:
            st.metric("بدون تفعيل هذا الشهر", int((d["مجموع التفعيل"] == 0).sum()))
        with a[1]:
            st.metric("ما فعّل بآخر يوم", int((d["تفعيل آخر يوم"] == 0).sum()))
        with a[2]:
            st.metric("ضعيف التفعيل", int((d["المستوى"] == LVL_WEAK).sum()))
    with a[3]:
        st.metric("خطوط واقفة", int(d["سبب الاتصال"].str.contains("خطوط واقفة").sum()))
    with a[4]:
        st.metric("بحاجة خطوط", len(need_df))
    if not has_q:
        st.warning("ما رفعتي الكوالتي بالتبويب الأول، فتنبيهات التفعيل مو متاحة")
    if not has_stock:
        st.warning("ما رفعتي التوزيع بالتبويب الأول، فتنبيهات الخطوط مو متاحة")

    st.subheader("قائمة الكول سنتر")
    if len(call_df) == 0:
        st.info("ما أكو مكاتب تحتاج كول سنتر")
    else:
        show_table(call_df)
    st.download_button("تحميل قائمة الكول سنتر (إكسل)", data=format_excel(call_df),
                       file_name="call_center.xlsx", mime=XLSX_MIME, key="dl_call")

    st.subheader("مكاتب بحاجة خطوط")
    if len(need_df) == 0:
        st.info("كل المكاتب عندها خطوط كافية")
    else:
        show_table(need_df)
    st.download_button("تحميل قائمة الخطوط (إكسل)", data=format_excel(need_df),
                       file_name="need_lines.xlsx", mime=XLSX_MIME, key="dl_need")

    if has_q:
        st.subheader("نسبة أداء كل مندوب")
        st.caption("نسبة الأداء = معدل نقاط مكتب المندوب ÷ معدل نقاط المكتب العام × 100 (100% = مثل المعدل). نسبة التاركت تظهر إذا حددتي التاركت بتبويب كيبي اي")
        perf = rep_perf(d, saved_targets_all())
        show_table(perf)
        st.bar_chart(perf.set_index("المندوب")[["نسبة الأداء %"]])
        st.download_button("تحميل أداء المندوبين (إكسل)", data=format_excel(perf),
                           file_name="rep_performance.xlsx", mime=XLSX_MIME, key="dl_perf")

    st.subheader("تقرير جاهز لكل مندوب")
    reps = clean_rep(res[T["rep"]]) if T["rep"] in res.columns else pd.Series(["بدون مندوب"] * len(res))
    rep_names = sorted(set(reps))
    sel = st.selectbox("المندوب", rep_names, key="rnd_rep")
    sub = res[(reps == sel).values]
    st.write("عدد مكاتبه: " + str(len(sub)))
    show_table(sub)
    st.download_button("تحميل تقرير المندوب (إكسل)", data=format_excel(sub),
                       file_name="rep_" + safe_file_name(sel) + ".xlsx", mime=XLSX_MIME, key="dl_rep")

    st.subheader("تحميل الكل بزر واحد")
    st.caption("ملف ZIP فيه: الإكسل الرئيسي + الكول سنتر + الخطوط + الكيبي اي + ملف لكل مندوب")
    if st.button("جهّزي ملف الكل", key="rnd_zip"):
        st.download_button("تحميل الكل (ZIP)", data=build_all_zip(res, call_df, need_df),
                           file_name="all_reports.zip", mime="application/zip", key="dl_zip")



def kpi_page():
    st.title("كيبي اي")
    res = st.session_state.get("last_result")
    if res is None:
        st.info("احسبي بالتبويب الأول (الرئيسي) أولاً، وبعدها تطلع هنا النسب والتوقع")
        return
    mk = target_month_key()
    saved = saved_targets_all()
    with st.expander("التاركت الشهري - " + mk, expanded=True):
        k1, k2, k3, k4, k5 = st.columns(5)
        with k1:
            t_net = st.number_input("تاركت نت (نقاط)", min_value=0, value=int(saved.get("net", 0)), step=100, key="kpi_net_" + mk)
        with k2:
            t_red = st.number_input("تاركت ريد (نقاط)", min_value=0, value=int(saved.get("red", 0)), step=100, key="kpi_red_" + mk)
        with k3:
            t_use = st.number_input("تاركت يوز (نقاط)", min_value=0, value=int(saved.get("use", 0)), step=100, key="kpi_use_" + mk)
        with k4:
            t_wal = st.number_input("تاركت المحفظة (عدد مكاتب)", min_value=0, value=int(saved.get("wal", 0)), step=1, key="kpi_wal_" + mk)
        with k5:
            t_inc = st.number_input("تاركت الحافز (عدد مكاتب)", min_value=0, value=int(saved.get("inc", 0)), step=1, key="kpi_inc_" + mk)
        if st.button("حفظ التاركت", key="kpi_save"):
            ok1 = save_targets(mk, t_net, t_red, t_use)
            ok2 = save_kpi(mk, t_wal, t_inc)
            st.success("انحفظ") if (ok1 and ok2) else st.warning("ما كدرت أحفظ على السيرفر، يبقى للجلسة الحالية بس")
    tg = {"net": t_net, "red": t_red, "use": t_use, "wal": t_wal, "inc": t_inc}
    kt, elapsed, total_days = kpi_table(res, tg)
    cards = st.columns(5)
    for col, (_, r) in zip(cards, kt.iterrows()):
        with col:
            pct = r["النسبة %"]
            ach = r["المحقق"]
            val = "-" if pct is None or pd.isna(pct) else "{:.0f}%".format(pct)
            sub = "" if ach is None or pd.isna(ach) else "{:,.0f} من {:,.0f}".format(ach, r["التاركت"])
            st.metric(r["المؤشر"], val, sub, delta_color="off")
    show_table(kt)
    pct_df = kt.dropna(subset=["النسبة %"]).set_index("المؤشر")[["النسبة %"]]
    if len(pct_df) > 0:
        st.bar_chart(pct_df)
    if elapsed and total_days:
        st.caption("التوقع = المحقق ÷ الأيام اللي مضت ({}) × أيام الشهر ({}). الأيام من آخر تاريخ بتقرير الكوالتي، والنقاط من الشيت الأول".format(elapsed, total_days))
    st.download_button("تحميل الكيبي اي (إكسل)", data=format_excel(kt), file_name="kpi.xlsx",
                       mime=XLSX_MIME, key="dl_kpi")

    st.subheader("التقرير المصغّر")
    st.caption("التجهيز من شيت التوزيع الشهري (ريد + يوز، والنت البكج اليومي فقط). الباقي = التجهيز الكلي − التفعيل الكلي")
    mini, has_m = mini_report(res)
    if not has_m:
        st.warning("ما أكو شيت توزيع شهري (ارفعي التوزيع بالتبويب الأول)، فالتجهيز طالع صفر")
    show_table(mini)
    st.download_button("تحميل التقرير المصغّر (إكسل)", data=format_excel(mini), file_name=report_file_name(),
                       mime=XLSX_MIME, key="dl_mini")


def main_page():
    st.title(T["title"])

    c1, c2, c3 = st.columns(3)
    c4, c5, c6 = st.columns(3)
    c7, c8, c9 = st.columns(3)
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
    with c7:
        live_file = st.file_uploader(T["up_live"], key="live")

    mk = target_month_key()
    saved_t = load_targets().get(mk, {})
    with st.expander(T["tgt_title"] + " - " + mk, expanded=True):
        t1, t2, t3 = st.columns(3)
        with t1:
            tgt_net = st.number_input(T["tgt_net"], min_value=0, value=int(saved_t.get("net", 0)), step=100, key="tgt_net_" + mk)
        with t2:
            tgt_red = st.number_input(T["tgt_red"], min_value=0, value=int(saved_t.get("red", 0)), step=100, key="tgt_red_" + mk)
        with t3:
            tgt_use = st.number_input(T["tgt_use"], min_value=0, value=int(saved_t.get("use", 0)), step=100, key="tgt_use_" + mk)

    if agents_file is None:
        st.info(T["q_required"])
    else:
        agents = None
        dist = None
        q = None
        inc = None
        wal = None
        bnd = None
        live = None

        if agents_file is not None:
            with c1:
                sh = load_report(agents_file, T["agents"])
                if sh is not None:
                    agents = pick_sheet(sh, T["agents"])
        if dist_file is not None:
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
        if live_file is not None:
            with c7:
                sh = load_report(live_file, T["live"])
                if sh is not None:
                    live = pick_sheet(sh, T["live"])

        if agents is not None:
            with st.expander(T["preview"]):
                if agents is not None:
                    st.write(T["agents"])
                    st.dataframe(agents.head(5))
                if dist is not None:
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
                if live is not None:
                    st.write(T["live"])
                    st.dataframe(live.head(5))

            if st.button(T["calc"]):
                save_ok = save_targets(mk, tgt_net, tgt_red, tgt_use)
                if not save_ok:
                    st.caption(T["tgt_nosave"])
                try:
                    result = compute(agents, dist, q, inc, wal, bnd, live)
                    if result is not None:
                        st.session_state["last_result"] = result
                        show_table(result)
                        bundle_df = result.attrs.get("bundles")
                        mm_df = result.attrs.get("mismatch")
                        extras = []
                        after_points = []
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
                        monthly_df = result.attrs.get("monthly")
                        if monthly_df is not None:
                            m_name = T["monthly_sheet"] + " " + str(result.attrs.get("monthly_month"))
                            st.write(m_name)
                            show_table(monthly_df)
                            after_points = [(m_name, monthly_df)]
                            if result.attrs.get("monthly_msg"):
                                st.info(result.attrs.get("monthly_msg"))
                        um_df = result.attrs.get("unmatched")
                        if um_df is not None and len(um_df) > 0:
                            st.write(T["um_title"])
                            show_table(um_df)
                            after_points.append((T["unmatched"], um_df))
                        points_info = None
                        points_src = result.attrs.get("points_src")
                        if points_src is not None:
                            points_info = build_points_table(points_src, tgt_net, tgt_red, tgt_use)
                        if points_info is not None:
                            st.write(T["pts_sheet"])
                            st.dataframe(points_info["display"], use_container_width=True)
                        xlsx_bytes = format_excel(result, extras, points_info, after_points)
                        st.session_state["last_xlsx"] = xlsx_bytes
                        st.download_button(
                            T["download"],
                            data=xlsx_bytes,
                            file_name=report_file_name(),
                            mime=XLSX_MIME,
                        )
                except Exception:
                    st.error(T["err"])
                    st.code(traceback.format_exc())


tab_main, tab_cmp, tab_rnd, tab_kpi = st.tabs(["التقرير الرئيسي", "مقارنة شهرين", "عشوائيات", "كيبي اي"])
with tab_main:
    main_page()
with tab_cmp:
    compare_page()
with tab_rnd:
    random_page()
with tab_kpi:
    kpi_page()
