import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
from supabase import create_client, Client
import base64

# --- Page Configuration ---
st.set_page_config(
    page_title="ဘုံရန်ပုံငွေ & Approval System",
    page_icon="💰",
    layout="wide"
)

# --- 1. Supabase Client Setup ---
# Secrets မိုလို့ Streamlit Cloud Secrets ထဲမှာ ထည့်ထားရပါမည်
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("Supabase API Secrets မတွေ့ရှိပါ။ Streamlit Advanced Settings ထဲတွင် Secrets ထည့်ပေးပါ။")
    st.stop()

# Helper Functions
def get_fund_info():
    response = supabase.table("fund").select("total_amount, admin_password").eq("id", 1).execute()
    if response.data:
        return response.data[0]["total_amount"], response.data[0]["admin_password"]
    return 1000000, "1234"

def update_fund_amount(new_amount):
    supabase.table("fund").update({"total_amount": new_amount}).eq("id", 1).execute()

def update_admin_password(new_pass):
    supabase.table("fund").update({"admin_password": new_pass}).eq("id", 1).execute()

# --- 2. App ၏ Header နှင့် လက်ကျန်ငွေ ပြသခြင်း ---
st.title("💰 ဘုံရန်ပုံငွေ & Shareholder Approval System")

total_fund, admin_password = get_fund_info()

# Approved ဖြစ်ပြီးသား စာရင်းများ ပေါင်းလဒ်
approved_res = supabase.table("requests").select("amount").eq("status", "Approved").execute()
approved_total = sum([item['amount'] for item in approved_res.data]) if approved_res.data else 0.0

current_balance = total_fund - approved_total

# Top Info Card
col_bal1, col_bal2, col_bal3 = st.columns(3)
with col_bal1:
    st.metric(label="💵 မူလရန်ပုံငွေ (Total Fund)", value=f"{total_fund:,.0f} MMK")
with col_bal2:
    st.metric(label="💸 သုံးစွဲပြီး ပမာဏ (Total Approved)", value=f"{approved_total:,.0f} MMK")
with col_bal3:
    st.metric(label="📊 လက်ရှိကျန်ငွေ (Current Balance)", value=f"{current_balance:,.0f} MMK")

st.divider()

# Tab ၄ ခု ခွဲခြားထားခြင်း
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 ငွေထုတ်ရန် တောင်းဆိုမည်", 
    "✅ Shareholder Approval", 
    "📊 လချုပ် စာရင်း & Excel Export",
    "⚙️ ရန်ပုံငွေ ပြင်ဆင်ခြင်း (Owner Only)"
])

# --- Tab 1: Request တင်ရန် ---
with tab1:
    st.subheader("ငွေထုတ်ယူရန် အကြောင်းပြချက် ပေးပါ")
    
    col_a, col_b = st.columns(2)
    with col_a:
        applicant = st.selectbox("တောင်းခံသူ (Shareholder):", ["Shareholder 1", "Shareholder 2", "Shareholder 3", "Shareholder 4"])
        amount = st.number_input("ငွေပမာဏ (MMK):", min_value=1000, step=5000)
    
    with col_b:
        request_date = st.date_input("ရက်စွဲ (Date):", value=datetime.today())
        reason = st.text_input("အသုံးပြုမည့် အကြောင်းပြချက်:")
    
    uploaded_file = st.file_uploader("📄 အထောက်အထား PDF ဖိုင်တွဲရန် (Optional):", type=["pdf"])
    
    if st.button("Submit Request", type="primary"):
        if reason:
            file_b64 = None
            file_name = None
            if uploaded_file is not None:
                file_bytes = uploaded_file.read()
                file_b64 = base64.b64encode(file_bytes).decode('utf-8')
                file_name = uploaded_file.name
                
            data_payload = {
                "applicant": applicant,
                "reason": reason,
                "amount": amount,
                "request_date": str(request_date),
                "file_data": file_b64,
                "file_name": file_name,
                "approvals": 0,
                "status": "Pending"
            }
            supabase.table("requests").insert(data_payload).execute()
            st.success("Request တင်ပြီးပါပြီ! ကျန် Shareholder ၃ ယောက်ရဲ့ Approve ကို စောင့်ပါ။")
            st.rerun()
        else:
            st.warning("အကြောင်းပြချက် ဖြည့်ပေးပါ။")

# --- Tab 2: Approve ပေးရန် ---
with tab2:
    st.subheader("ခွင့်ပြုချက်ပေးရန် စာရင်းများ")
    st.info("💡 ကျန် Shareholder ၃ ယောက် Approve ပေးပါက ငွေထုတ်ယူခွင့် ရရှိမည် ဖြစ်သည်။")
    
    pending_res = supabase.table("requests").select("*").eq("status", "Pending").order("id", desc=True).execute()
    pending_requests = pending_res.data
    
    if not pending_requests:
        st.success("လက်ရှိတွင် စစ်ဆေးရန် Pending Request များ မရှိပါ။")
    
    for req in pending_requests:
        req_id = req["id"]
        req_applicant = req["applicant"]
        req_reason = req["reason"]
        req_amount = req["amount"]
        req_date = req["request_date"]
        req_file_data = req["file_data"]
        req_file_name = req["file_name"]
        req_approvals = req["approvals"]
        
        col1, col2 = st.columns([4, 2])
        with col1:
            st.markdown(f"**{req_applicant}** | 📅 {req_date}")
            st.markdown(f"**အကြောင်းပြချက်:** {req_reason} ({req_amount:,.0f} MMK)")
            st.caption(f"လက်ရှိ Approvals: {req_approvals}/3")
            
            if req_file_data and req_file_name:
                pdf_bytes = base64.b64decode(req_file_data)
                st.download_button(
                    label=f"📎 {req_file_name} (PDF ကြည့်ရန်)",
                    data=pdf_bytes,
                    file_name=req_file_name,
                    mime="application/pdf",
                    key=f"pdf_{req_id}"
                )
        
        with col2:
            if st.button("Approve ပေးမည်", key=f"app_{req_id}"):
                new_count = req_approvals + 1
                new_status = "Approved" if new_count >= 3 else "Pending"
                
                supabase.table("requests").update({"approvals": new_count, "status": new_status}).eq("id", req_id).execute()
                st.success("Approve ပေးလိုက်ပါပြီ!")
                st.rerun()
        st.divider()

# --- Tab 3: Excel Export ---
with tab3:
    st.subheader("အသုံးစရိတ် စာရင်းများနှင့် လချုပ် Excel ထုတ်ရန်")
    
    all_res = supabase.table("requests").select("id, request_date, applicant, reason, amount, file_name, approvals, status").order("id", desc=True).execute()
    
    if all_res.data:
        df_all = pd.DataFrame(all_res.data)
        df_all.rename(columns={
            "request_date": "Date",
            "applicant": "Applicant",
            "reason": "Reason",
            "amount": "Amount_MMK",
            "file_name": "Attachment",
            "approvals": "Approvals",
            "status": "Status"
        }, inplace=True)
        st.dataframe(df_all, use_container_width=True)
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_all.to_excel(writer, index=False, sheet_name='Monthly_Report')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 လချုပ် စာရင်းအား Excel File အဖြစ် ဒေါင်းလုဒ်ဆွဲမည်",
            data=excel_data,
            file_name=f"Monthly_Fund_Report_{datetime.now().strftime('%Y_%m')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.write("လက်ရှိတွင် စာရင်းဒေတာ မရှိသေးပါ။")

# --- Tab 4: Owner Only Settings ---
with tab4:
    st.subheader("🔒 Owner / Admin စက်တင်")
    st.caption("ဘုံရန်ပုံငွေ ပမာဏသစ် ပြောင်းလဲခြင်းနှင့် Password ပြောင်းလဲခြင်းများကို ပိုင်ရှင်တစ်ဦးတည်းသာ ပြုလုပ်နိုင်ပါသည်။")
    
    pwd_input = st.text_input("Owner Password ရိုက်ထည့်ပါ:", type="password")
    
    if pwd_input == admin_password:
        st.success("🔓 Owner Access Granted!")
        
        st.divider()
        st.markdown("### 💰 ၁။ ရန်ပုံငွေ ပမာဏသစ် ပြောင်းလဲရန်")
        st.write(f"လက်ရှိ မူလရန်ပုံငွေ: **{total_fund:,.0f} MMK**")
        
        new_fund_val = st.number_input("ရန်ပုံငွေ ပမာဏသစ် ထည့်ပါ (MMK):", min_value=0.0, value=float(total_fund), step=50000.0)
        if st.button("ရန်ပုံငွေ ပမာဏသစ် အတည်ပြုမည်"):
            update_fund_amount(new_fund_val)
            st.success("ရန်ပုံငွေ ပမာဏသစ် အောင်မြင်စွာ ပြောင်းလဲပြီးပါပြီ!")
            st.rerun()
            
        st.divider()
        st.markdown("### 🔑 ၂။ Owner Password ပြောင်းလဲရန်")
        new_pass_input = st.text_input("Password အသစ် ရိုက်ထည့်ပါ:", type="password")
        if st.button("Password အသစ် ပြောင်းမည်"):
            if new_pass_input:
                update_admin_password(new_pass_input)
                st.success("Password အသစ် ပြောင်းလဲပြီးပါပြီ!")
                st.rerun()
            else:
                st.warning("Password အသစ် ရိုက်ထည့်ပါ။")
    elif pwd_input:
        st.error("❌ Password မှားယွင်းနေပါသည်။")
