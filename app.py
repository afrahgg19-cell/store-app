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
    # اذا الملف فيه شيت واحد ياخذه، واذا اكثر يختار المستخدم
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

        # الوكلاء: B = رقم المكتب، A = اسم المكتب
        agents_df = pd.DataFrame({
            "key": agents.iloc[:, 1].apply(last10),
            "اسم المكتب": agents.iloc[:, 0],
        }).dropna(subset=["key"]).drop_duplicates("key")

        # التوزيع: A = رقم الخط، C = الصنف، E = الحالة، F = رقم المكتب، I = التاريخ
        d = pd.DataFrame({
            "line": dist.iloc[:, 0].astype(str).str.strip(),
            "item": dist.iloc[:, 2].astype(str).str.strip().str.lower(),
            "status": dist.iloc[:, 4].astype(str).str.strip().str.lower(),
            "key": dist.iloc[:, 5].apply(last10),
            "date": pd.to_datetime(dist.iloc[:, 8], errors="coerce"),
        })

        total_rows = len(d)
        bad_dates = int(d["date"].isna().sum())

        # نخلي آخر سجل (الاحدث تاريخ) لكل خط
        d = d.sort_values("date", kind="stable")
        d = d.drop_duplicates(subset="line", keep="last")
        after_dedup = len(d)

        # بعد ما صار عندنا آخر حالة لكل خط، نفلتر Distributed
        d = d[d["status"] == "distributed"].copy()
        d["الصنف"] = d["item"].map(item_map)
        d = d.dropna(subset=["الصنف"])

        if d.empty:
            st.error("ما بقى أي صف بعد الفلترة. تأكد من عمود E والأصناف.")
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

        st.success(
            f"تم. عدد المكاتب: {len(result)} | صفوف غير مطابقة: {unmatched}"
        )
        st.info(
            f"صفوف التوزيع الأصلية: {total_rows} | بعد إزالة المكرر (آخر تاريخ): {after_dedup} | "
            f"الموزّع فعلياً: {len(d)} | تواريخ غير مقروءة: {bad_dates}"
        )
        st.dataframe(result, use_container_width=True)

        buf = BytesIO()
        result.to_excel(buf, index=False)
        st.download_button(
            "تحميل النتيجة (إكسل)",
            data=buf.getvalue(),
            file_name="نتيجة_التوزيع.xlsx",
            mime="application/vnd.openxmlformats-officed
