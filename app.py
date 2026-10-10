import re
import pandas as pd

# ===== عدّل هنا =====
FILE = "التقارير.xlsx"
SHEET_AGENTS = "الوكلاء"
SHEET_DIST = "التوزيع"
# ====================

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

agents = pd.read_excel(FILE, sheet_name=SHEET_AGENTS, dtype=str)
dist = pd.read_excel(FILE, sheet_name=SHEET_DIST, dtype=str)

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

# فلتر Distributed + تصنيف + تجاهل الأصناف الأخرى
d = d[d["status"] == "distributed"].copy()
d["الصنف"] = d["item"].map(item_map)
d = d.dropna(subset=["الصنف"])

# الربط بالمكتب
merged = d.merge(agents_df, on="key", how="left")
print("صفوف ما انطبقت على مكتب:", merged["اسم المكتب"].isna().sum())

# شيت واحد: صف لكل مكتب، عمود لكل صنف
result = pd.crosstab(
    [merged["key"], merged["اسم المكتب"].fillna("غير مطابق")],
    merged["الصنف"],
)
result["المجموع"] = result.sum(axis=1)
result = result.sort_values("المجموع", ascending=False).reset_index()
result = result.rename(columns={"key": "رقم المكتب"})

result.to_excel("نتيجة_التوزيع.xlsx", index=False)
print(result)
