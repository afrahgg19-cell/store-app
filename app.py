import re
import pandas as pd
import streamlit as st
from io import BytesIO

st.set_page_config(page_title="تقرير التوزيع", layout="wide")
st.title("تقرير التوزيع حسب المكتب")

def last10(num):
    if pd.isna(num):
        return None
    s = re.sub(r"\D", "", str(num))
    return s[-10:] if s else None

item_map = {
    "pre-paid sim card - type2": "ريد",
    "pre-paid sim card": "ريد",
    "youth line sim card": "يوز",
    "white list usim preloaded with iqd 40000": "خط شهري",
    "gprs sim card with package": "خط نت يومي",
    "gprs sim card with tozed cpe cat6": "راوتر كبير",
    "gprs sim card with mifi huawei cat4": "ماي فاي صغير",
    "nms-1 million coin silver": "خط يوز مليوني",
}

def pick_sheet(file, label):
    """يرجع اسم الشيت: إذا الملف فيه شيت واحد ياخذه، وإذا أكثر يخلي المستخدم يختار"""
    xls = pd.ExcelFile(file)
    if len(xls.sheet_names) == 1:
        return xls, xls.sheet_names[0]
    return xls, st.selectbox(f"شيت {label}", xls.sheet_names)

c1, c2 = st.columns(2)
with c1:
    agents_file = st.file_uploader("ارفع تقرير الوكلاء", type=["xlsx", "xls"], key="agents")
with c2:
    dist_file = st.file_uploader("ارفع تقرير التوزيع", type=["xlsx", "xls"], key="dist")

if agents_file and dist_file:
    with c1:
        xls_a, sheet_a = pick_sheet(agents_file, "الوكلاء")
    with c2:
        xls_d, sheet_d = pick_sheet(dist_file, "التوزيع")

    if st.button("احسب"):
        agents = pd.read_excel(xls_a, sheet_name=sheet_a, dtype=str)
        dist = pd.read_excel(xls_d, sheet_name=sheet_d, dtype=str)

        # الوكلاء: A = رقم المكتب، B = اسم المكتب
        agents_df = pd.DataFrame({
            "key": agents.iloc[:, 0].apply(last10),
            "اسم المكتب": agents.iloc[:, 1],
        }).dropna(subset=["key"]).drop_duplicates("key")

        # التوزيع: C = الصنف، E = الحالة، F = رقم المكتب
        d = pd.DataFrame({
            "item": dist.iloc[:, 2].str.strip().str.lower(),
            "status": dist.iloc[:, 4].str.strip().str.lower(),
            "key": dist.iloc[:, 5].apply(last10),
        })

        d = d[d["status"] == "distributed"].copy()
