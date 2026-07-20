import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime
import io
import base64
from PIL import Image

# Streamlit Page Config
st.set_page_config(page_title="ဘုံရန်ပုံငွေ System", page_icon="💰", layout="wide")

# Supabase Setup
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# ----------------- Helper Functions -----------------
def get_fund_info():
    res = supabase.table("fund").select("total_amount").eq("id", 1).execute()
    if res.data:
        return res.data[0]["total_amount"]
    return 1000000.0

def authenticate_user(username, password):
    res = supabase.table("users").select("*").eq("username", username).eq("password_hash", password).execute()
    if res.data:
        return res.data[0]
    return None

def get_all_users():
    res = supabase.table("users").select("id, username, role").execute()
    return res.data if res.data else []

def get_approved_total():
    res = supabase.table("requests").select("amount").eq("status", "Approved").execute()
    if res.data:
        return sum(item["amount"] for item in res.data)
    return 0.0

# ----------------- Session State (Login System) -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

# ----------------- Login Screen -----------------
if not st.session_state.logged_in:
    st.title("💰 ဘုံရန်ပုံငွေ & Shareholder Approval System")
    st.subheader("🔐 စနစ်သို့ ဝင်ရောက်ရန် Login ဝင်ပါ")
    
    with st.form("login_form"):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        submit_button = st.form_submit_button("Login ဝင်မည်")
        
        if submit_button:
            user = authenticate_user(username_input, password_input)
            if user:
                st.session_state.logged_in = True
                st.session_state.user = user
                st.success(f"ကြိုဆိုပါတယ် {user['username']} ({user['role'].capitalize()})")
                st.rerun()
            else:
                st.error("Username သို့မဟုတ် Password မှားယွင်းနေပါသည်။")
    st.stop()

# ----------------- Main Dashboard (Logged In) -----------------
current_user = st.session_state.user

# Sidebar - User Info & Logout
st.sidebar.title("👤 အကောင့် အချက်အလက်")
st.sidebar.write(f"**အသုံးပြုသူ:** {current_user['username']}")
st.sidebar.write(f"**ရာထူး:** {current_user['role'].capitalize()}")

if st.sidebar.button("🚪 Logout ထွက်မည်"):
    st.session_state.logged_in = False
    st.session_state.user = None
    st.rerun()

st.title("💰 ဘုံရန်ပုံငွေ & Shareholder Approval System")

# Dashboard Metrics
total_fund = get_fund_info()
total_approved = get_approved_total()
current_balance = total_fund - total_approved

col1, col2, col3 = st.columns(3)
col1.metric("💵 မူလရန်ပုံငွေ (Total Fund)", f"{total_fund:,.0f} MMK")
col2.metric("💸 သုံးစွဲပြီး ပမာဏ (Approved)", f"{total_approved:,.0f} MMK")
col3.metric("📊 လက်ရှိကျန်ငွေ (Current Balance)", f"{current_balance:,.0f} MMK")

st.markdown("---")

# Navigation Tabs (Role ယူပြီး ခွဲခြားထားပါသည်)
tabs = ["📝 ငွေထုတ်ရန် တောင်းဆိုမည်", "✅ Shareholder Approval", "📊 လချုပ် စာရင်း"]
if current_user["role"] == "owner":
    tabs.append("⚙️ Owner Control (Users & System)")

selected_tab = st.tabs(tabs)

# ----------------- TAB 1: Request Money -----------------
with selected_tab[0]:
    st.subheader("✍️ ငွေထုတ်ယူရန် အကြောင်းပြချက် ပေးပါ")
    
    with st.form("request_form"):
        st.write(f"**တောင်းဆိုသူ:** {current_user['username']}")
        req_date = st.date_input("ရက်စွဲ")
        amount = st.number_input("ငွေပမာဏ (MMK):", min_value=1000.0, step=1000.0)
        reason = st.text_area("အသုံးပြုမည့် အကြောင်းပြချက်:")
        
        uploaded_file = st.file_uploader("အထောက်အထား PDF သို့မဟုတ် Image ပူးတွဲရန် (Optional)", type=["pdf", "jpg", "jpeg", "png"])
        
        submit_req = st.form_submit_button("တောင်းဆိုမှု လျှောက်ထားမည်")
        
        if submit_req:
            if amount > current_balance:
                st.error("လက်ရှိကျန်ငွေထက် ပိုမိုတောင်းဆို၍ မရပါ!")
            elif not reason:
                st.warning("အကြောင်းပြချက် ဖြည့်သွင်းပေးပါ။")
            else:
                file_b64 = None
                file_name = None
                file_type = None
                
                if uploaded_file:
                    file_bytes = uploaded_file.read()
                    file_b64 = base64.b64encode(file_bytes).decode('utf-8')
                    file_name = uploaded_file.name
                    file_type = uploaded_file.type
                
                req_data = {
                    "applicant": current_user["username"],
                    "user_id": current_user["id"],
                    "reason": reason,
                    "amount": amount,
                    "request_date": str(req_date),
                    "file_data": file_b64,
                    "file_name": file_name,
                    "file_type": file_type,
                    "status": "Pending"
                }
                
                supabase.table("requests").insert(req_data).execute()
                st.success("တောင်းဆိုမှု အောင်မြင်စွာ ပေးပို့လိုက်ပါပြီ!")
                st.rerun()

# ----------------- TAB 2: Approval & Reject -----------------
with selected_tab[1]:
    st.subheader("🗳️ လျှောက်ထားချက်များအား စစ်ဆေး/အတည်ပြုရန်")
    
    pending_res = supabase.table("requests").select("*").eq("status", "Pending").execute()
    pending_requests = pending_res.data if pending_res.data else []
    
    if not pending_requests:
        st.info("လက်ရှိတွင် စစ်ဆေးရန် တောင်းဆိုချက်များ မရှိပါ။")
    else:
        for req in pending_requests:
            with st.expander(f"📌 {req['applicant']} - {req['amount']:,.0f} MMK ({req['request_date']})"):
                st.write(f"**အကြောင်းပြချက်:** {req['reason']}")
                
                # Attachment Display (PDF / Image)
                if req.get("file_data"):
                    st.write("**ပူးတွဲပါ အထောက်အထား:**")
                    file_bytes = base64.b64decode(req["file_data"])
                    
                    if req.get("file_type") and "image" in req["file_type"]:
                        img = Image.open(io.BytesIO(file_bytes))
                        st.image(img, caption=req["file_name"], use_column_width=True)
                    else:
                        st.download_button("📄 PDF ဖိုင် ဒေါင်းလုဒ်ဆွဲရန်", file_bytes, file_name=req["file_name"])
                
                col_app, col_rej = st.columns(2)
                
                # Approve
                if col_app.button(f"✅ Approve (အတည်ပြုမည်)", key=f"app_{req['id']}"):
                    supabase.table("requests").update({"status": "Approved"}).eq("id", req['id']).execute()
                    st.success("Approve လုပ်ပြီးပါပြီ!")
                    st.rerun()
                
                # Reject with Note
                with col_rej:
                    reject_note = st.text_input("Reject လုပ်ရသည့် အကြောင်းပြချက်:", key=f"note_{req['id']}")
                    if st.button(f"❌ Reject (ငြင်းပယ်မည်)", key=f"rej_{req['id']}"):
                        if not reject_note:
                            st.warning("Reject လုပ်ရသည့် အကြောင်းပြချက် ရေးပေးပါ။")
                        else:
                            supabase.table("requests").update({
                                "status": "Rejected",
                                "reject_note": reject_note
                            }).eq("id", req['id']).execute()
                            st.error("Reject လုပ်ပြီးပါပြီ!")
                            st.rerun()

# ----------------- TAB 3: Statement & Export -----------------
with selected_tab[2]:
    st.subheader("📜 လချုပ် ရာဇဝင်နှင့် မှတ်တမ်းများ")
    
    all_res = supabase.table("requests").select("id, applicant, amount, reason, request_date, status, reject_note").execute()
    all_requests = all_res.data if all_res.data else []
    
    if all_requests:
        df = pd.DataFrame(all_requests)
        df.rename(columns={
            "id": "ID", "applicant": "လျှောက်ထားသူ", "amount": "ပမာဏ",
            "reason": "အကြောင်းပြချက်", "request_date": "ရက်စွဲ",
            "status": "အခြေအနေ", "reject_note": "Reject မှတ်ချက်"
        }, inplace=True)
        
        st.dataframe(df, use_container_width=True)
        
        # Excel Export
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Report')
        excel_data = output.getvalue()
        
        st.download_button(
            label="📥 Excel Report ဒေါင်းလုဒ်ဆွဲရန်",
            data=excel_data,
            file_name=f"Fund_Report_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("မှတ်တမ်းများ မရှိသေးပါ။")

# ----------------- TAB 4: Owner Control Panel -----------------
if current_user["role"] == "owner":
    with selected_tab[3]:
        st.subheader("⚙️ Owner Only Management Panel")
        
        # 1. User Management (ထည့်ခြင်း/ပြင်ခြင်း)
        st.markdown("### 👥 Shareholder အကောင့်များ စီမံရန်")
        
        users_list = get_all_users()
        st.table(pd.DataFrame(users_list))
        
        with st.expander("➕ Shareholder အကောင့်အသစ် ထည့်မည်"):
            new_user = st.text_input("Username သစ်:")
            new_pass = st.text_input("Password သစ်:", type="password")
            new_role = st.selectbox("Role", ["shareholder", "owner"])
            
            if st.button("အကောင့်ဖန်တီးမည်"):
                if new_user and new_pass:
                    res = supabase.table("users").insert({
                        "username": new_user,
                        "password_hash": new_pass,
                        "role": new_role
                    }).execute()
                    st.success("User အသစ် ဖန်တီးပြီးပါပြီ!")
                    st.rerun()
                else:
                    st.warning("အချက်အလက်များ ပြည့်စုံစွာ ဖြည့်ပါ။")

        st.markdown("---")
        
        # 2. Delete Requests Records
        st.markdown("### 🗑️ စာရင်းမှ မှတ်တမ်းများ ဖျက်ပစ်ရန်")
        
        all_reqs = supabase.table("requests").select("id, applicant, amount, status").execute().data
        if all_reqs:
            req_options = {f"ID: {r['id']} | {r['applicant']} | {r['amount']} MMK | ({r['status']})": r['id'] for r in all_reqs}
            selected_to_delete = st.selectbox("ဖျက်လိုသည့် စာရင်းကို ရွေးပါ:", list(req_options.keys()))
            
            if st.button("❌ ရွေးချယ်ထားသော စာရင်းကို ဖျက်မည်"):
                del_id = req_options[selected_to_delete]
                supabase.table("requests").delete().eq("id", del_id).execute()
                st.success("စာရင်းကို ဖျက်ပြီးပါပြီ!")
                st.rerun()
