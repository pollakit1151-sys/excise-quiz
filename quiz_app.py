import streamlit as st
import re
import random
from pypdf import PdfReader

# --- 1. ฟังก์ชันโหลด PDF (เหมือนเดิมแต่เพิ่มความเสถียร) ---
@st.cache_data
def load_quiz_from_pdf(file_path):
    reader = PdfReader(file_path)
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"

    parts = re.split(r'เฉลยข้อสอบ|เฉลยท้ายเล่ม', full_text)
    exam_text = parts[0]
    answer_text = parts[1] if len(parts) > 1 else ""

    ans_map = {}
    ans_matches = re.findall(r'(\d+)\s*[\.]\s*([ก-ง])', answer_text)
    for num, ans in ans_matches:
        ans_map[int(num)] = ans

    q_pattern = re.compile(r'(\d+)\.\s*(.*?)\s+ก\.\s*(.*?)\s+ข\.\s*(.*?)\s+ค\.\s*(.*?)\s+ง\.\s*(.*?)(?=\n\d+\.|\nเฉลย|$)', re.S)
    
    parsed_data = []
    for match in q_pattern.finditer(exam_text):
        q_num = int(match.group(1))
        raw_question = match.group(2).strip().replace('\n', ' ')
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
    st.set_page_config(page_title="App ข้อสอบสรรพสามิต", layout="centered")
    pdf_file = "ข้อสอบ พรบ.60 (399)ชุดไม่เฉลย.pdf"
    
    try:
        all_data = load_quiz_from_pdf(pdf_file)
    except:
        st.error("ไม่พบไฟล์ PDF")
        return

    # --- 2. ระบบจัดการ Progress (Session State) ---
    if 'remaining_questions' not in st.session_state:
        st.session_state.remaining_questions = all_data.copy()
        st.session_state.done_count = 0
        st.session_state.total_questions = len(all_data)

    if 'current_quiz_set' not in st.session_state:
        st.session_state.current_quiz_set = []
        st.session_state.user_ans = {}
        st.session_state.submitted = False

    st.title("🎯 ฝึกทำข้อสอบ พรบ.สรรพสามิต 60")
    
    # แสดงความก้าวหน้า
    progress = st.session_state.done_count / st.session_state.total_questions
    st.progress(progress)
    st.write(f"ทำไปแล้ว {st.session_state.done_count} จากทั้งหมด {st.session_state.total_questions} ข้อ")

    # --- Sidebar ---
    with st.sidebar:
        num_to_draw = st.number_input("จำนวนข้อต่อรอบ", 1, 50, 10)
        if st.button("ล้างประวัติ/เริ่มใหม่ทั้งหมด"):
            st.session_state.clear()
            st.rerun()

    # --- 3. Logic การดึงข้อสอบใหม่ ---
    if not st.session_state.current_quiz_set and st.session_state.remaining_questions:
        # สุ่มดึงข้อสอบออกจากคลัง
        batch_size = min(len(st.session_state.remaining_questions), num_to_draw)
        selected = random.sample(st.session_state.remaining_questions, batch_size)
        
        # ลบข้อที่สุ่มได้ออกจากคลังทันที
        st.session_state.remaining_questions = [q for q in st.session_state.remaining_questions if q not in selected]
        
        # เตรียมตัวเลือก (สุ่ม ก-ง)
        for q in selected:
            d_opts = q['options'].copy()
            random.shuffle(d_opts)
            q['d_opts'] = d_opts
            
        st.session_state.current_quiz_set = selected
        st.session_state.user_ans = {}
        st.session_state.submitted = False

    # --- 4. หน้าแสดงข้อสอบ ---
    if st.session_state.current_quiz_set:
        with st.form("quiz_form"):
            for i, q in enumerate(st.session_state.current_quiz_set):
                st.subheader(f"ข้อที่ {st.session_state.done_count + i + 1} (ID: {q['id']})")
                st.write(q['question'])
                ans = st.radio("เลือกคำตอบ:", q['d_opts'], key=f"q_{q['id']}", index=None)
                if ans: st.session_state.user_ans[q['id']] = ans
                st.divider()
            
            submit_btn = st.form_submit_button("✅ ส่งข้อสอบชุดนี้")

        if submit_btn:
            st.session_state.submitted = True

        # --- 5. เมื่อตรวจคะแนนเสร็จ ---
        if st.session_state.submitted:
            score = 0
            for q in st.session_state.current_quiz_set:
                u_ans = st.session_state.user_ans.get(q['id'])
                is_correct = (u_ans == q['answer'])
                if is_correct: score += 1
                
                color = "green" if is_correct else "red"
                st.markdown(f"**ข้อ ID {q['id']}**: {q['question']}")
                st.markdown(f"👉 ตอบ: {u_ans} | เฉลย: :{color}[{q['answer']}]")
            
            st.success(f"ชุดนี้ได้คะแนน: {score} / {len(st.session_state.current_quiz_set)}")
            
            # ปุ่มเพื่อไปต่อ
            if st.button("➡️ ทำข้อสอบชุดถัดไป"):
                st.session_state.done_count += len(st.session_state.current_quiz_set)
                st.session_state.current_quiz_set = [] # ล้างเพื่อไปดึงใหม่
                st.rerun()
    else:
        st.balloons()
        st.header("🎉 ยินดีด้วย! คุณทำข้อสอบครบทุกข้อในคลังแล้ว")
        if st.button("เริ่มใหม่อีกครั้ง"):
            st.session_state.clear()
            st.rerun()

if __name__ == "__main__":
    main()