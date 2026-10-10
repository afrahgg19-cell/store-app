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
    """إذا الملف فيه شيت واحد ياخذه، وإذا أكثر يخلي المستخدم يختار"""
    xls = pd.ExcelFile(file)
    if len(xls.sheet_names) == 1:
        return xls, xls.sheet_names[0]
    return xls, st.selectbox(f"شيت {label}", xls.sheet_names, key=f"sheet_{label}")


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

        # ===== تشخيص (احذفه بعد ما يشتغل الكود) =====
        with st.expander("تشخيص: شنو انقرأ من الملفات", expanded=True):
            st.write("أعمدة الوكلاء:", list(agents.columns), "| عدد الصفوف:", len(agents))
            st.write("أعمدة التوزيع:", list(dist.columns), "| عدد الصفوف:", len(dist))
            st.write("عينة من الوكلاء:")
            st.dataframe(agents.head(5))
            st.write("عينة من التوزيع:")
            st.dataframe(dist.head(5))
        # ============================================

        # الوكلاء: A = رقم المكتب، B = اسم المكتب
        agents_df = pd.DataFrame({
            "key": agents.iloc[:, 0].apply(last10),
            "اسم المكتب": agents.iloc[:, 1],
        }).dropna(subset=["key"]).drop_duplicates("key")

        # التوزيع: C = الصنف، E = الحالة، F = رقم المكتب
        d = pd.DataFrame({
            "item": dist.iloc[:, 2].astype(str).str.strip().str.lower(),
            "status": dist.iloc[:, 4].astype(str).str.strip().str.lower(),
            "key": dist.iloc[:, 5].apply(last10),
        })

        st.write("قيم عمود E الموجودة:", d["status"].value_counts().head(10).to_dict())
        d = d[d["status"] == "distributed"].copy()
        st.write("صفوف بعد فلتر Distributed:", len(d))

        st.write("قيم عمود C الموجودة:", d["item"].value_counts().head(15).to_dict())
        d["الصنف"] = d["item"].map(item_map)
        d = d.dropna(subset=["الصنف"])
        st.write("صفوف بعد تصنيف الأصناف:", len(d))

        if d.empty:
            st.error("ما بقى أي صف بعد الفلترة. شوف القيم اللي ظهرت فوق وقارنها بالأسماء.")
            st.stop()

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
