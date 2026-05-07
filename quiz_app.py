@st.cache_data
def load_quiz_from_pdf(file_path):
    try:
        reader = PdfReader(file_path)
        full_text = ""
        for page in reader.pages:
            full_text += page.extract_text() + " " # ใช้ช่องว่างแทน \n ป้องกันการตัดคำผิดพลาด

        # ซ่อมตัวอักษรก่อนจัดการ
        full_text = fix_thai_text(full_text)

        # 1. แยกส่วนข้อสอบกับเฉลยออกจากกัน
        split_match = re.search(r'เฉลยข้อสอบ|เฉลยท้ายเล่ม|เฉลย\s*\d+', full_text)
        if split_match:
            exam_part = full_text[:split_match.start()]
            answer_part = full_text[split_match.start():]
        else:
            exam_part = full_text
            answer_part = ""

        # 2. ตัดหัวกระดาษ: หาจุดเริ่มต้นที่แท้จริงของข้อ 1.
        start_match = re.search(r'\b1\.\s+', exam_part)
        if start_match:
            exam_part = exam_part[start_match.start():]

        # 3. สกัดคำตอบท้ายไฟล์
        ans_map = {}
        ans_matches = re.findall(r'(\d+)\s*[\.]\s*([ก-ง])', answer_part)
        for num, ans in ans_matches:
            ans_map[int(num)] = ans

        # 4. สกัดโจทย์และตัวเลือกแบบใหม่ (สับด้วยเลขข้อก่อน)
        parsed_data = []
        
        # ตัดแบ่งข้อความตามตัวเลขข้อ (เช่น 1., 2., 3. ...)
        # pattern นีัจะหา เลขตามด้วยจุดและช่องว่าง
        raw_blocks = re.split(r'\b(\d+)\.\s+', exam_part)
        
        # raw_blocks จะมีหน้าตาแบบ: ['', '1', 'โจทย์... ก... ข...', '2', 'โจทย์... ก... ข...', ...]
        for i in range(1, len(raw_blocks)-1, 2):
            q_num_str = raw_blocks[i]
            q_content = raw_blocks[i+1]
            
            try:
                q_num = int(q_num_str)
            except ValueError:
                continue

            # สกัดหา ก. ข. ค. ง. ในก้อนข้อความของข้อนั้นๆ
            # ใช้ re.search เพื่อหา ก. ข. ค. ง. แบบที่อาจจะไม่มีการขึ้นบรรทัดใหม่
            opt_match = re.search(r'(.*?)\s+ก\.\s+(.*?)\s+ข\.\s+(.*?)\s+ค\.\s+(.*?)\s+ง\.\s+(.*)', q_content, re.S)
            
            if opt_match:
                q_text = opt_match.group(1).strip()
                options = [
                    opt_match.group(2).strip(),
                    opt_match.group(3).strip(),
                    opt_match.group(4).strip(),
                    opt_match.group(5).strip()
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