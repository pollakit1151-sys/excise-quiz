import streamlit as st
import re
import random
from pypdf import PdfReader

# --- 1. ฟังก์ชันพิเศษสำหรับซ่อมฟอนต์ภาษาไทยที่เพี้ยน ---
def fix_thai_text(text):
    if not text:
        return ""
    # แก้ไขสระอำที่แยกส่วน (ํ + า -> ำ)
    text = text.replace('\u0e4d\u0e32', 'ำ')
    # แก้ไขกรณีมีช่องว่างแทรกระหว่างสระ (ํ า -> ำ)
    text = text.replace('ํ า', 'ำ')
    # ลบช่องว่างที่เกินมาจากการสกัดข้อความ (มักเกิดในภาษาไทย)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

@st.cache_data
def load_quiz_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"

        # ซ่อมตัวอักษรทั้งไฟล์ก่อนเริ่มจัดการ
        full_text = fix_thai_text(full_text)

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
            
            # ดึงโจทย์และตัวเลือก พร้อมทำความสะอาดตัวอักษรอีกรอบ
            raw_question = fix_thai_text(match.group(2))
            clean_question = re.sub(r'^\d+\.\s*', '', raw_question)
            
            options = [
                fix_thai_text(match.group(3)),
                fix_thai_text(match.group(4)),
                fix_thai_text(match.group(5)),
                fix_thai_text(match.group(6))
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
    except Exception as e:
        return []

def main():
    st.set_page_config(page_title="App ข้อสอบสรรพสามิต", layout="centered")
    pdf_file = "ข้อสอบ พรบ.60 (399)ชุดไม่เฉลย.pdf"
    all_data = load_quiz_from_pdf(pdf_file)

    if not all_data:
        st.error("ไม่พบไฟล์ PDF หรือไฟล์มีปัญหา")
        return

    if 'remaining_questions' not in st.session_state:
        st.session_state.remaining_questions = all_data.copy()
        st.session_state.done_count = 0
        st.session_state.total_questions = len(all_data)

    if 'current_quiz_set' not in st.session_state:
        st.session_state.current_quiz_set = []
        st.session_state.user_ans = {}
        st.session_state.submitted = False

    st.title("🎯 ฝึกทำข้อสอบ พรบ.สรรพสามิต 60")
    
    progress = st.session_state.done_count / st.session_state.total_questions
    st.progress(progress)
    st.write(f"ความคืบหน้า: {st.session_state.done_count} / {st.session_state.total_questions} ข้อ")

    with st.sidebar:
        st.header("⚙️ ตั้งค่า")
        num_to_draw = st.number_input("จำนวนข้อต่อรอบ", 1, 50, 10)
        st.divider()
        do_shuffle_q = st.checkbox("สุ่มลำดับข้อสอบ", value=True)
        do_shuffle_opt = st.checkbox("สุ่มลำดับตัวเลือก (ก-ง)", value=True)
        st.divider()
        if st.button("🔄 เริ่มใหม่ทั้งหมด"):
            st.session_state.clear()
            st.rerun()

    if not st.session_state.current_quiz_set and st.session_state.remaining_questions:
        batch_size = min(len(st.session_state.remaining_questions), num_to_draw)
        if do_shuffle_q:
            selected = random.sample(st.session_state.remaining_questions, batch_size)
        else:
            temp_list = sorted(st.session_state.remaining_questions, key=lambda x: x['id'])
            selected = temp_list[:batch_size]
        
        st.session_state.remaining_questions = [q for q in st.session_state.remaining_questions if q not in selected]
        
        for q in selected:
            d_opts = q['options'].copy()
            if do_shuffle_opt:
                random.shuffle(d_opts)
            q['d_opts'] = d_opts
            
        st.session_state.current_quiz_set = selected
        st.session_state.user_ans = {}
        st.session_state.submitted = False

    if st.session_state.current_quiz_set:
        with st.form("quiz_form"):
            for i, q in enumerate(st.session_state.current_quiz_set):
                st.subheader(f"ข้อที่ {st.session_state.done_count + i + 1}")
                st.write(q['question'])
                ans = st.radio("เลือกคำตอบ:", q['d_opts'], key=f"q_{q['id']}", index=None)
                if ans:
                    st.session_state.user_ans[q['id']] = ans
                st.divider()
            
            if st.form_submit_button("✅ ส่งข้อสอบชุดนี้"):
                st.session_state.submitted = True
                st.rerun()

        if st.session_state.submitted:
            score = 0
            for q in st.session_state.current_quiz_set:
                u_ans = st.session_state.user_ans.get(q['id'])
                is_correct = (u_ans == q['answer'])
                if is_correct: score += 1
                
                color = "green" if is_correct else "red"
                st.markdown(f"**ข้อที่ {st.session_state.done_count + st.session_state.current_quiz_set.index(q) + 1}**")
                st.write(q['question'])
                st.markdown(f"👉 คุณตอบ: {u_ans if u_ans else 'ไม่ได้ตอบ'} | เฉลยคือ: :{color}[{q['answer']}]")
                st.divider()
            
            st.success(f"ชุดนี้ได้คะแนน: {score} / {len(st.session_state.current_quiz_set)}")
            
            if st.button("➡️ ทำข้อสอบชุดถัดไป"):
                st.session_state.done_count += len(st.session_state.current_quiz_set)
                st.session_state.current_quiz_set = [] 
                st.session_state.submitted = False
                st.rerun()
    else:
        st.balloons()
        st.header("🎉 ยินดีด้วย! คุณทำข้อสอบครบทุกข้อแล้ว")

if __name__ == "__main__":
    main()