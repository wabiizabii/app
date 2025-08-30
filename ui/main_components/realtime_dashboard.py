import streamlit as st
import streamlit.components.v1 as components
import os

# ตัวแปรนี้จะเก็บ Path ไปยังไฟล์ HTML ของเรา เพื่อให้โค้ดสะอาดและง่ายต่อการแก้ไข
# เราใช้ os.path.dirname(__file__) เพื่อให้แน่ใจว่าจะหาไฟล์เจอเสมอ ไม่ว่าจะรันจากที่ไหน
_COMPONENT_PATH = os.path.join(os.path.dirname(__file__), "realtime_dashboard.html")

def realtime_dashboard(height=450):
    """
    ฟังก์ชันสำหรับแสดงผล Dashboard แบบเรียลไทม์

    ฟังก์ชันนี้จะอ่านโค้ดจากไฟล์ HTML แล้วใช้ `components.html`
    ของ Streamlit เพื่อแสดงผลในแอปพลิเคชัน

    Args:
        height (int): ความสูงของ Component ที่จะแสดงผลบนหน้าจอ
    """
    try:
        # เปิดและอ่านไฟล์ HTML
        with open(_COMPONENT_PATH, 'r', encoding='utf-8') as f:
            html_code = f.read()
        
        # แสดงผล Component บนหน้าแอป Streamlit
        components.html(html_code, height=height, scrolling=True)

    except FileNotFoundError:
        st.error(
            "Error: The 'realtime_dashboard.html' component file was not found. "
            f"Please ensure it is located at: {_COMPONENT_PATH}"
        )
    except Exception as e:
        st.error(f"An error occurred while loading the real-time dashboard: {e}")

# --- ส่วนนี้สำหรับการทดสอบ Component โดยตรง (Optional) ---
# หากเรารันไฟล์นี้โดยตรง (python realtime_dashboard.py) มันจะแสดงผลตัวอย่าง
if __name__ == '__main__':
    st.set_page_config(layout="wide")
    st.title("Test: Real-time Dashboard Component")
    st.write(
        "This is a test page for the real-time dashboard. "
        "For this to work, the `mt5_data_streamer.py` service must be running in a separate terminal."
    )
    
    st.markdown("---")
    
    realtime_dashboard()