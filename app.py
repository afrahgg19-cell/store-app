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

uploaded = st.file_uploader("ارفع ملف التقارير (إكسل)", type=["xlsx", "xls"])

if uploaded:
    xls = pd.ExcelFile(uploaded)
    sheets = xls.sheet_names

    c1, c2 = st.columns(2)
    sheet_agents = c1.selectbox("شيت الوكلاء", sheets, index=0)
    sheet_dist = c2.selectbox("شيت التوزيع", sheets, index=min(1, len(sheets) - 1))

    if st.button("احسب"):
        agents = pd.read_excel(xls, sheet_name=sheet_agents, dtype=str)
        dist = pd.read_excel(xls, sheet_name=sheet_dist, dtype=str)

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
        d["الصنف"] = d["item"].map(item_map)
        d = d.dropna(subset=["الصنف"])

        merged = d.merge(agents_df, on="key", how="left")
        unmatched = int(merged["اسم المكتب"].isna().sum())

        result = pd.crosstab(
            [merged["key"], merged["اسم المكتب"].fillna("غير مطابق")],
            merged["الصنف"],
        )
        result["المجموع"] = result.sum(axis=1)
        result = result.sort_values("المجموع", ascending=False).reset_index()
        result = result.rename(columns={"key": "رقم المكتب"})

        st.success(f"تم. عدد المكاتب: {len(result)} | صفوف غير مطابقة: {unmatched}")
        st.dataframe(result, use_container_width=True)

        buf = BytesIO()
        result.to_excel(buf, index=False)
        st.download_button(
            "تحميل النتيجة (إكسل)",
            data=buf.getvalue(),
            file_name="نتيجة_التوزيع.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
