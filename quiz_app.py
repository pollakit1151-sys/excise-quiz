import streamlit as st
import re
import random
from pypdf import PdfReader

# --- 1. ฟังก์ชันซ่อมฟอนต์ไทยและจัดการช่องว่าง ---
def fix_thai_text(text):
    if not text: return ""
    # แก้ไขสระอำและไม้ไต่คู้ที่เพี้ยนจาก PDF
    text = text.replace('\u0e4d\u0e32', 'ำ').replace('ํ า', 'ำ').replace('ํา', 'ำ')
    # ลบช่องว่างที่เกินมาและบรรทัดว่าง
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

@st.cache_data
def load_quiz_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + "\n"

        # ซ่อมตัวอักษรก่อนจัดการ
        full_text = fix_thai_text(full_text)

        # 1. แยกส่วนข้อสอบกับเฉลยออกจากกัน
        # หาคำว่า 'เฉลย' ที่เป็นจุดแบ่งท้ายไฟล์
        split_match = re.search(r'เฉลยข้อสอบ|เฉลยท้ายเล่ม|เฉลย\s*\d+', full_text)
        if split_match:
            exam_part = full_text[:split_match.start()]
            answer_part = full_text[split_match.start():]
        else:
            exam_part = full_text
            answer_part = ""

        # 2. ตัดหัวกระดาษ: หาจุดเริ่มต้นที่แท้จริงของข้อ 1.
        # เราจะเริ่มที่เลข '1.' ที่ตามด้วยข้อความที่ไม่ใช่ตัวเลข
        start_match = re.search(r'\b1\.\s+', exam_part)
        if start_match:
            exam_part = exam_part[start_match.start():]

        # 3. สกัดคำตอบท้ายไฟล์ (รูปแบบ 1.ก 2.ข)
        ans_map = {}
        ans_matches = re.findall(r'(\d+)\s*[\.]\s*([ก-ง])', answer_part)
        for num, ans in ans_matches:
            ans_map[int(num)] = ans

        # 4. สกัดโจทย์และตัวเลือก
        # ปรับ Regex ให้ดึงเฉพาะเนื้อหาที่อยู่ระหว่าง ก. ข. ค. ง.
        # และจบที่ตัวเลขข้อถัดไป
        q_pattern = re.compile(r'(\d+)\.\s*(.*?)\s+ก\.\s*(.*?)\s+ข\.\s*(.*?)\s+ค\.\s*(.*?)\s+ง\.\s*(.*?)(?=\s*\d+\.|$)', re.S)
        
        parsed_data = []
        for match in q_pattern.finditer(exam_part):
            q_num = int(match.group(1))
            
            # ลบเลขข้อที่อาจติดมาในโจทย์ออก
            q_text = re.sub(r'^\d+\.\s*', '', match.group(2).strip())
            
            options = [
                match.group(3).strip(),
                match.group(4).strip(),
                match.group(5).strip(),
                match.group(6).strip()
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
                    "question": q_text,
                    "options": options,
                    "answer": correct_text
                })
        return parsed_data
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการอ่านไฟล์: {e}")
        return []

def main():
    st.set_page_config(page_title="App ข้อสอบสรรพสามิต 60", layout="centered")
    pdf_file = "ข้อสอบ พรบ.60 (399)ชุดไม่เฉลย.pdf"
    all_data = load_quiz_from_pdf(pdf_file)

    if not all_data:
        st.warning("ระบบกำลังโหลดข้อสอบหรือหาข้อสอบไม่เจอ กรุณาตรวจสอบว่ามีไฟล์ PDF ชื่อตรงกับที่กำหนดไว้ใน GitHub หรือไม่")
        return

    # --- Session State ---
    if 'remaining_questions' not in st.session_state:
        st.session_state.remaining_questions = all_data.copy()
        st.session_state.done_count = 0
        st.session_state.total_questions = len(all_data)
        st.session_state.current_quiz_set = []

    st.title("🎯 ฝึกทำข้อสอบ พรบ.สรรพสามิต 60")
    
    # Progress Bar
    progress = st.session_state.done_count / st.session_state.total_questions
    st.progress(progress)
    st.write(f"ทำไปแล้ว {st.session_state.done_count} จากทั้งหมด {st.session_state.total_questions} ข้อ")

    with st.sidebar:
        st.header("⚙️ ตั้งค่า")
        num_to_draw = st.number_input("จำนวนข้อต่อรอบ", 1, 50, 10)
        st.divider()
        do_shuffle_q = st.checkbox("สุ่มลำดับข้อสอบ", value=True)
        do_shuffle_opt = st.checkbox("สุ่มลำดับ ก-ง", value=True)
        if st.button("🔄 เริ่มใหม่ทั้งหมด"):
            st.session_state.clear()
            st.rerun()

    # ดึงโจทย์ใหม่ถ้าหน้าว่าง
    if not st.session_state.current_quiz_set and st.session_state.remaining_questions:
        batch_size = min(len(st.session_state.remaining_questions), num_to_draw)
        if do_shuffle_q:
            selected = random.sample(st.session_state.remaining_questions, batch_size)
        else:
            st.session_state.remaining_questions.sort(key=lambda x: x['id'])
            selected = st.session_state.remaining_questions[:batch_size]
        
        st.session_state.remaining_questions = [q for q in st.session_state.remaining_questions if q not in selected]
        
        for q in selected:
            d_opts = q['options'].copy()
            if do_shuffle_opt: random.shuffle(d_opts)
            q['d_opts'] = d_opts
            
        st.session_state.current_quiz_set = selected
        st.session_state.user_ans = {}
        st.session_state.submitted = False

    # แสดงผลข้อสอบ
    if st.session_state.current_quiz_set:
        with st.form("quiz_form"):
            for i, q in enumerate(st.session_state.current_quiz_set):
                st.subheader(f"ข้อที่ {st.session_state.done_count + i + 1}")
                st.write(q['question'])
                ans = st.radio("เลือกคำตอบ:", q['d_opts'], key=f"q_{q['id']}", index=None)
                if ans: st.session_state.user_ans[q['id']] = ans
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
            
            st.success(f"ชุดนี้ได้คะแนน: {score} / {len(st.session_state.current_quiz_set)}")
            
            if st.button("➡️ ทำข้อสอบชุดถัดไป"):
                st.session_state.done_count += len(st.session_state.current_quiz_set)
                st.session_state.current_quiz_set = [] 
                st.session_state.submitted = False
                st.rerun()
    else:
        st.balloons()
        st.header("🎉 ยินดีด้วย! ทำครบทุกข้อแล้ว")

if __name__ == "__main__":
    main()