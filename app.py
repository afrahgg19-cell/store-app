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
    """إذا
