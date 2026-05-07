import streamlit as st
import re
import random
from pypdf import PdfReader

# --- ฟังก์ชันสกัดข้อมูลจาก PDF ---
@st.cache_data
def load_quiz_from_pdf(file_path):
    reader = PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    # 1. แยกส่วนโจทย์กับส่วนเฉลย (สมมติเฉลยเริ่มที่คำว่า "เฉลย")
    parts = re.split(r'เฉลยข้อสอบ|เฉลยท้ายเล่ม', full_text)
    exam_text = parts[0]
    answer_text = parts[1] if len(parts) > 1 else ""

    # 2. สกัดคำตอบ (เช่น 1.ข 2.ก)
    ans_map = {}
    ans_matches = re.findall(r'(\d+)\s*[\.]\s*([ก-ง])', answer_text)
    for num, ans in ans_matches:
        ans_map[int(num)] = ans

    # 3. สกัดโจทย์และตัวเลือก
    # Regex หา: เลขข้อ. โจทย์ ก. ข. ค. ง.
    q_pattern = re.compile(r'(\d+)\.\s*(.*?)\s+ก\.\s*(.*?)\s+ข\.\s*(.*?)\s+ค\.\s*(.*?)\s+ง\.\s*(.*?)(?=\n\d+\.|\nเฉลย|$)', re.S)
    
    parsed_data = []
    for match in q_pattern.finditer(exam_text):
        q_num = int(match.group(1))
        raw_question = match.group(2).strip().replace('\n', ' ')
        
        # ลบเลขข้อออกจากโจทย์ (เช่น "1. โจทย์" -> "โจทย์")
        clean_question = re.sub(r'^\d+\.\s*', '', raw_question)
        
        options = [
            match.group(3).strip().replace('\n', ' '),
            match.group(4).strip().replace('\n', ' '),
            match.group(5).strip().replace('\n', ' '),
            match.group(6).strip().replace('\n', ' ')
        ]
        
        ans_letter = ans_map.get(q_num)
        correct_text = ""
        if ans_letter == 'ก': correct_text = options[0]
        elif ans_letter == 'ข': correct_text = options[1]
        elif ans_letter == 'ค': correct_text = options[2]
        elif ans_letter == 'ง': correct_text = options[3]

        if correct_text:
            parsed_data.append({
                "id": q_num,
                "question": clean_question,
                "options": options,
                "answer": correct_text
            })
            
    return parsed_data

def main():
    st.set_page_config(page_title="App ฝึกทำข้อสอบ PDF", layout="centered")
    
    # ระบุชื่อไฟล์ PDF ของคุณ (ต้องอยู่ในโฟลเดอร์เดียวกัน)
    pdf_file = "ข้อสอบ พรบ.60 (399)ชุดไม่เฉลย.pdf"
    
    try:
        quiz_data = load_quiz_from_pdf(pdf_file)
    except Exception as e:
        st.error(f"ไม่พบไฟล์ PDF หรือไฟล์มีปัญหา: {e}")
        return

    st.title("🎯 ระบบฝึกทำข้อสอบจากไฟล์ PDF")
    st.write(f"โหลดข้อสอบสำเร็จทั้งหมด: {len(quiz_data)} ข้อ")

    # --- Sidebar ---
    with st.sidebar:
        st.header("⚙️ ตั้งค่า")
        num_q = st.number_input("จำนวนข้อที่จะทำ", 1, len(quiz_data), 20)
        do_shuffle_q = st.checkbox("สุ่มโจทย์", value=True)
        do_shuffle_opt = st.checkbox("สุ่มตัวเลือก (ก-ง)", value=True)
        if st.button("🔄 เริ่มใหม่"):
            st.session_state.clear()
            st.rerun()

    # --- เตรียม Session ---
    if 'current_quiz' not in st.session_state:
        selected = random.sample(quiz_data, num_q) if do_shuffle_q else quiz_data[:num_q]
        for item in selected:
            d_opts = item['options'].copy()
            if do_shuffle_opt: random.shuffle(d_opts)
            item['d_opts'] = d_opts
        st.session_state.current_quiz = selected
        st.session_state.user_ans = {}
        st.session_state.submitted = False

    # --- หน้าทำข้อสอบ ---
    with st.form("quiz_form"):
        for i, q in enumerate(st.session_state.current_quiz):
            st.subheader(f"ข้อที่ {i+1}")
            st.write(q['question']) # โจทย์จะไม่มีเลขข้อแล้ว
            
            ans = st.radio("เลือกคำตอบ:", q['d_opts'], key=f"ans_{i}", index=None)
            if ans: st.session_state.user_ans[i] = ans
            st.divider()
        
        if st.form_submit_button("✅ ส่งข้อสอบ"):
            st.session_state.submitted = True

    # --- ตรวจคะแนน ---
    if st.session_state.submitted:
        score = 0
        for i, q in enumerate(st.session_state.current_quiz):
            user_ans = st.session_state.user_ans.get(i)
            if user_ans == q['answer']: score += 1
            
            color = "green" if user_ans == q['answer'] else "red"
            st.markdown(f"**ข้อ {i+1}**: {q['question']}")
            st.markdown(f"👉 คุณตอบ: {user_ans} | เฉลย: :{color}[{q['answer']}]")
            st.divider()
        
        st.sidebar.metric("คะแนนของคุณ", f"{score} / {num_q}")
        st.balloons()

if __name__ == "__main__":
    main()