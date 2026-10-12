# ไฟล์เปิดใช้งานชื่อภาษาอังกฤษ

ไฟล์ทั้งหมดอยู่ใน D:\hand-gesture-music\outputs เปลี่ยนชื่อไฟล์เปิดใช้งาน 20 ไฟล์เป็นภาษาอังกฤษโดยไม่เปลี่ยนโมเดลหรือค่าที่ผู้ใช้ตั้งไว้ เนื้อหาคำแนะนำภาษาไทยยังคงอยู่ แก้คำอ้างอิงในคู่มือให้ตรงกับชื่อใหม่

ใช้งานตอนนี้: start_music_controller.cmd เปิดหน้าควบคุมเพลง; update_model_acceptance.cmd ตรวจและใช้เป้าหมายใน acceptance_policy.json; retest_thumbs_both_hands.cmd ใช้ทวนชูโป้งสองมือ

| ชื่อเดิม | ชื่อใหม่ |
|---|---|
| เปิดระบบควบคุมเพลง.cmd | start_music_controller.cmd |
| ปรับเกณฑ์รุ่นที่ทดสอบ.cmd | update_model_acceptance.cmd |
| เปิดหน้าทดสอบ.cmd | open_connection_test.cmd |
| เปิดกล้องเก็บข้อมูล.cmd | open_data_collector.cmd |
| เก็บข้อมูลมือขวา.cmd | collect_right_hand.cmd |
| เก็บข้อมูลมือซ้าย.cmd | collect_left_hand.cmd |
| เก็บท่าสามนิ้ว.cmd | collect_three_finger.cmd |
| เก็บสามนิ้วหลายมุม.cmd | collect_three_finger_varied_angles.cmd |
| เก็บสามนิ้วหกมุม.cmd | collect_three_finger_six_angles.cmd |
| เก็บหลายมุมชุดใหม่.cmd | collect_balanced_six_angles.cmd |
| เก็บท่าคำสั่งหลายมุม.cmd | collect_commands_varied_angles.cmd |
| เก็บนิ้วโป้งขวาเพิ่ม.cmd | collect_right_thumb_supplement.cmd |
| เก็บกำมือเพิ่ม.cmd | collect_fist_supplement.cmd |
| เก็บ V มือซ้ายแก้ไข.cmd | collect_left_v_replacement.cmd |
| ยืนยันกำมือซ้าย.cmd | confirm_left_fist.cmd |
| ทดลองเทียบสองรุ่น.cmd | compare_baseline_models.cmd |
| ทดลองรุ่นแก้นิ้วโป้ง.cmd | compare_thumb_candidate.cmd |
| ทดสอบชูโป้งเฉพาะ.cmd | test_thumb_focus.cmd |
| ทดสอบรุ่นสามนิ้วหกมุม.cmd | test_weighted_angle_model.cmd |
| ทวนชูโป้งสองมือ.cmd | retest_thumbs_both_hands.cmd |

ไฟล์ .cmd ใช้เนื้อหา ASCII และบรรทัดแบบ Windows; .gitattributes กำหนด CRLF เพื่อคงรูปแบบตอน checkout ในอนาคต ชื่อไฟล์ในตารางนี้เป็นรายการย้ายชื่อเท่านั้น ไม่ใช่การแนะนำให้เก็บข้อมูลหรือทดสอบรุ่นเก่าทุกตัวอีกครั้ง
