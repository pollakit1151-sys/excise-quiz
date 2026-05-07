import streamlit as st
import streamlit.components.v1 as components  # นำเข้าตัวเสริมสำหรับรันสคริปต์เลื่อนหน้าจอ
import re
import random
from pypdf import PdfReader

# --- ฟังก์ชันสั่งให้เบราว์เซอร์เลื่อนขึ้นบนสุดอัตโนมัติ ---
def scroll_to_top():
    components.html(
        """
        <script>
            // ค้นหากรอบหน้าต่างหลักของ Streamlit แล้วสั่งให้เลื่อนไปที่พิกัด 0,0 (บนสุด)
            var body = window.parent.document.querySelector(".main");
            if (body) {
                body.scrollTo(0, 0);
            }
            window.parent.scrollTo(0, 0);
        </script>
        """,
        height=0
    )

# --- 1. ฟังก์ชันซ่อมฟอนต์ไทย ---
def fix_thai_text(text):
    if not text: return ""
    text = re.sub(r'([ก-ฮ])([\u0e48-\u0e4c]?)\s+า', r'\1\2ำ', text)
    text = re.sub(r'([ก-ฮ])\s+([\u0e48-\u0e4c]?)า', r'\1\2ำ', text)
    text = text.replace('\u0e4d\u0e32', 'ำ').replace('\u0e4d \u0e32', 'ำ')
    text = text.replace('ํ า', 'ำ').replace('ํา', 'ำ').replace(' า', 'ำ')
    text = re.sub(r' +', ' ', text)
    return text.strip()

# --- 2. ฟังก์ชันโหลด PDF ---
def load_quiz_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                page_text = re.sub(r'^\s*\d+\s*$', '', page_text, flags=re.MULTILINE)
                full_text += page_text + " "

        full_text = re.sub(r'\d*\s*ตัวอย่างข้อสอบ.*?สุรีย์\s*ศรีสุข', '', full_text)
        full_text = fix_thai_text(full_text)

        split_match = re.search(r'เฉลยข้อสอบ|เฉลยท้ายเล่ม|เฉลย\s*\d+', full_text)
        exam_part = full_text[:split_match.start()] if split_match else full_text
        answer_part = full_text[split_match.start():] if split_match else ""

        ans_map = {}
        ans_matches = re.findall(r'(\d+)\s*[\.]\s*([ก-ง])', answer_part)
        for num, ans in ans_matches:
            ans_map[int(num)] = ans

        parsed_data = []
        seen_ids = set()
        
        matches = re.finditer(r'(?:^|\s+)(\d+)\.\s+(.*?)(?=\s+\d+\.\s+|$)', exam_part, re.S)
        
        for match in matches:
            q_num = int(match.group(1))
            q_content = match.group(2)
            
            if q_num in seen_ids: continue
                
            opt_match = re.search(r'(.*?)(?:^|\s+)ก\.\s+(.*?)(?:^|\s+)ข\.\s+(.*?)(?:^|\s+)ค\.\s+(.*?)(?:^|\s+)ง\.\s+(.*)', q_content, re.S)
            
            if opt_match:
                q_text = fix_thai_text(opt_match.group(1))
                options = [
                    fix_thai_text(opt_match.group(2)),
                    fix_thai_text(opt_match.group(3)),
                    fix_thai_text(opt_match.group(4)),
                    fix_thai_text(opt_match.group(5))
                ]
                
                ans_letter = ans_map.get(q_num)
                correct_text = ""
                if ans_letter == 'ก': correct_text = options[0]
                elif ans_letter == 'ข': correct_text = options[1]
                elif ans_letter == 'ค': correct_text = options[2]
                elif ans_letter == 'ง': correct_text = options[3]

                if correct_text:
                    seen_ids.add(q_num)
                    parsed_data.append({
                        "id": q_num,
                        "question": q_text,
                        "options": options,
                        "answer": correct_text
                    })
        return parsed_data
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาด: {e}")
        return []

# --- 3. การทำงานหลักของแอป ---
def main():
    st.set_page_config(page_title="App ข้อสอบสรรพสามิต 60", layout="centered")
    
    # ตรวจสอบคำสั่งให้เลื่อนหน้าจอขึ้นบนสุด
    if 'do_scroll_top' in st.session_state and st.session_state.do_scroll_top:
        scroll_to_top()
        st.session_state.do_scroll_top = False # ทำเสร็จแล้วก็ปิดไว้
        
    pdf_file = "ข้อสอบ พรบ.60 (399)ชุดไม่เฉลย.pdf"
    all_data = load_quiz_from_pdf(pdf_file)

    if not all_data:
        st.warning("กำลังโหลดข้อสอบ...")
        return

    if 'remaining_questions' not in st.session_state:
        st.session_state.remaining_questions = all_data.copy()
        st.session_state.done_count = 0
        st.session_state.total_questions = len(all_data)
        st.session_state.current_quiz_set = []

    st.title("🎯 ฝึกทำข้อสอบ พรบ.สรรพสามิต 60")
    
    progress_val = st.session_state.done_count / st.session_state.total_questions
    st.progress(progress_val)
    st.write(f"ทำไปแล้ว {st.session_state.done_count} จากทั้งหมด {st.session_state.total_questions} ข้อ")

    with st.sidebar:
        st.header("⚙️ ตั้งค่า")
        num_to_draw = st.number_input("จำนวนข้อต่อรอบ", 1, 50, 10)
        st.divider()
        do_shuffle_q = st.checkbox("สุ่มลำดับข้อสอบ", value=True)
        if st.button("🔄 เริ่มใหม่ทั้งหมด"):
            st.session_state.clear()
            st.rerun()

    if not st.session_state.current_quiz_set and st.session_state.remaining_questions:
        batch_size = min(len(st.session_state.remaining_questions), num_to_draw)
        if do_shuffle_q:
            selected = random.sample(st.session_state.remaining_questions, batch_size)
        else:
            st.session_state.remaining_questions.sort(key=lambda x: x['id'])
            selected = st.session_state.remaining_questions[:batch_size]
        
        st.session_state.remaining_questions = [q for q in st.session_state.remaining_questions if q not in selected]
        st.session_state.current_quiz_set = selected
        st.session_state.user_ans = {}
        st.session_state.submitted = False

    if st.session_state.current_quiz_set:
        with st.form("quiz_form"):
            for i, q in enumerate(st.session_state.current_quiz_set):
                st.subheader(f"ข้อที่ {st.session_state.done_count + i + 1}")
                st.write(q['question'])
                
                labels = ["ก. ", "ข. ", "ค. ", "ง. "]
                display_options = [labels[idx] + opt for idx, opt in enumerate(q['options'])]
                
                unique_key = f"radio_{i}_{q['id']}"
                ans = st.radio("เลือกคำตอบ:", display_options, key=unique_key, index=None)
                
                if ans:
                    st.session_state.user_ans[unique_key] = ans[3:] 
                st.divider()
            
            if st.form_submit_button("✅ ส่งข้อสอบชุดนี้"):
                st.session_state.submitted = True
                st.session_state.do_scroll_top = True # สั่งให้เลื่อนขึ้นบนตอนดูเฉลย
                st.rerun()

        if st.session_state.submitted:
            score = 0
            for i, q in enumerate(st.session_state.current_quiz_set):
                unique_key = f"radio_{i}_{q['id']}"
                u_ans = st.session_state.user_ans.get(unique_key)
                
                is_correct = (u_ans == q['answer'])
                if is_correct: score += 1
                
                color = "green" if is_correct else "red"
                st.markdown(f"**ข้อที่ {st.session_state.done_count + i + 1}**")
                st.write(q['question'])
                st.markdown(f"👉 คุณตอบ: {u_ans if u_ans else 'ไม่ได้ตอบ'} | เฉลยคือ: :{color}[{q['answer']}]")
            
            st.success(f"ชุดนี้ได้คะแนน: {score} / {len(st.session_state.current_quiz_set)}")
            
            if st.button("➡️ ทำข้อสอบชุดถัดไป"):
                st.session_state.done_count += len(st.session_state.current_quiz_set)
                st.session_state.current_quiz_set = [] 
                st.session_state.submitted = False
                st.session_state.do_scroll_top = True # สั่งให้เลื่อนขึ้นบนตอนทำชุดใหม่
                st.rerun()
    else:
        st.balloons()
        st.header("🎉 ยินดีด้วย! คุณทำข้อสอบครบทุกข้อแล้ว")

if __name__ == "__main__":
    main()