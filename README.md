# Hand Gesture Music

ระบบควบคุม Apple Music บน Windows ด้วยท่าทางมือจากกล้อง โดยใช้ MediaPipe สกัดจุดสำคัญของมือ และตัวจำแนก SVC ที่ฝึกจากข้อมูลท่ามือ รองรับการเล่น/พัก เปลี่ยนเพลง ปรับเสียง และพัก/เริ่มการควบคุม

## ความสามารถ

| ท่าทาง | การทำงาน |
|---|---|
| กำมือ | เล่น / พักเพลง |
| V นิ้วชี้–กลาง โดยพับนิ้วโป้ง | เพลงถัดไป |
| ชูนิ้วโป้ง | เพลงก่อนหน้า |
| จีบนิ้วชี้–โป้ง โดยพับอีกสามนิ้ว | กางเพิ่มเสียง / หุบลดเสียง |
| แบทั้งห้านิ้วค้าง | พัก / เริ่มการควบคุม |

- มีหน้าจับท่าทางและหน้า Now playing พร้อมชื่อเพลง ศิลปิน อัลบั้ม ภาพปก และเวลาเมื่อ Apple Music ส่งข้อมูลมา
- รับมือซ้ายและขวา ติดตามมือที่ใช้สั่งงาน และรอเมื่อสองมือแสดงคำสั่งขัดกัน
- แสดงคะแนนและความคืบหน้าการค้างท่า ป้องกันการส่งซ้ำเมื่อค้างมือ
- ปรับคะแนนขั้นต่ำ เวลาค้างท่า และเวลาปล่อยมือได้ใน Settings
- รองรับธีมมืดและสว่าง

## หลักการทำงาน

```text
Camera → MediaPipe (21 hand landmarks) → Geometric features
       → StandardScaler → SVC → Hold / release checks
       → Windows media session → Apple Music
```

ตัวจำแนกท่าเพลงรุ่นใช้งานคือ **Weighted FingerReach SVC, RBF kernel, C=10** ใช้คุณลักษณะ 58 ค่า จำแนก 4 กลุ่ม ได้แก่ neutral, next, previous และ toggle ส่วนจีบปรับเสียงและแบมือใช้เงื่อนไขทางเรขาคณิตและเวลาแยกจาก SVC

คำสั่งเพลงส่งผ่าน Windows Global System Media Transport Controls ส่วนการปรับเสียงใช้ Core Audio กับ audio session ของ Apple Music โดยไม่ปรับเสียงรวมของเครื่อง แถบเสียงภายใน Apple Music อาจไม่ขยับตามค่าใน Windows Volume Mixer

## เริ่มใช้งาน

ต้องมี **Windows, กล้อง, Python 3.11 x64 และ Apple Music for Windows** พร้อมบัญชีและเพลงที่เล่นได้

```powershell
git clone https://github.com/Chabil-S/hand-gesture-music.git
cd hand-gesture-music
./setup.ps1
```

สคริปต์ติดตั้ง dependencies และดาวน์โหลด MediaPipe Hand Landmarker จากแหล่งทางการพร้อมตรวจ SHA-256 ตัวนี้เป็นโมเดลตรวจตำแหน่งมือ ไม่ใช่ตัวจำแนกคำสั่งที่ฝึกเอง

**Repository นี้ไม่รวมข้อมูลท่ามือส่วนตัวและตัวจำแนกที่ฝึกแล้ว** การ clone เพียงอย่างเดียวจึงยังไม่พร้อมสาธิต ต้องเก็บและฝึกข้อมูลของตนเอง หรือใช้ artifacts ที่จัดเตรียมไว้แยกต่างหาก

1. เปิด `outputs/open_data_collector.cmd` เพื่อเก็บท่าทางตาม [คู่มือเก็บข้อมูล](outputs/COLLECTION_GUIDE_TH.md)
2. ตรวจและบันทึกข้างมือจริงใน `outputs/hand_verification.json` ตาม [ตัวอย่าง](docs/hand_verification.example.json)
3. ตรวจข้อมูลและฝึกตัวจำแนก:

```powershell
./.venv/Scripts/python.exe tools/audit_data.py
./.venv/Scripts/python.exe outputs/train_gestures.py
```

คำสั่งฝึกข้างต้นเป็น pipeline เริ่มต้น การทำซ้ำรุ่น Weighted FingerReach ต้องใช้ข้อมูลและน้ำหนักตามรอบพัฒนา ดู [โมเดลและการประเมิน](docs/MODEL_OVERVIEW_TH.md)

4. เปิด Apple Music เริ่มเพลง แล้วเปิด `outputs/start_music_controller.cmd`
5. เปิดกล้อง แอปเริ่มในโหมดดูผล กดเริ่มควบคุมและปล่อยมือก่อนทำคำสั่ง

ค่ามาตรฐานของการยืนยันท่าคือคะแนน 80%, ค้าง 0.6 วินาที และปล่อย 0.35 วินาที ค่าที่ใช้จริงอ่านจาก Settings หรือ `outputs/live_settings.json` แบมือใช้เวลาค้าง 1.2 วินาที

## โครงสร้างโครงการ

| ตำแหน่ง | เนื้อหา |
|---|---|
| `outputs/gesture_music_app.py` | แอปหลักและการทำงานร่วมกันของกล้อง โมเดล และ UI |
| `outputs/music_ui.py`, `outputs/music_display.py` | หน้าจอและข้อมูลเพลง |
| `outputs/gesture_features.py`, `outputs/joint_features.py` | การสร้างคุณลักษณะจากจุดมือ |
| `outputs/control_runtime.py`, `outputs/dynamic_gestures.py` | เงื่อนไขยืนยันคำสั่งและท่าปรับเสียง/แบมือ |
| `outputs/media_connection_probe.py`, `outputs/apple_music_volume.py` | เชื่อมต่อเครื่องเล่นและระดับเสียง |
| `outputs/gesture_collector.py`, `outputs/train_gestures.py` | เก็บข้อมูลและฝึกตัวจำแนก |
| `tools/` | ตรวจข้อมูล เปรียบเทียบ ประเมิน และเปิดใช้โมเดล |
| `tests/` | การตรวจพฤติกรรมส่วนประกอบของระบบ |
| `docs/` | คู่มือใช้งานและข้อมูลโมเดล |
| `docs/development/` | บันทึกทดลองย้อนหลัง ไม่ใช่คู่มือรุ่นปัจจุบัน |

ข้อมูลดิบ โมเดล บันทึกเพลง และค่าความชอบส่วนตัวเก็บในเครื่องและถูกกันออกจาก Git

## ผลทดสอบและข้อจำกัด

ผล Test ของรุ่นใช้งานบนชุดที่ยังไม่เคยประเมิน 634 เฟรม ให้ Accuracy หลังใช้คะแนนขั้นต่ำ 80% เท่ากับ **91.32% (579/634)** เป็นผลจากข้อมูลผู้จัดทำคนเดียว จึงยังไม่ยืนยันประสิทธิภาพกับผู้ใช้ทั่วไป

การเล่นคลิปข้อมูลบันทึกผ่านเงื่อนไขยืนยันคำสั่งได้คำสั่งถูกต้องครั้งเดียว 11/12 คลิปคำสั่ง และไม่ส่งคำสั่ง 9/9 คลิป neutral/สามนิ้ว ผลนี้ไม่รวมความสำเร็จของ Apple Music การปรับเสียง หรือการควบคุมด้วยแบมือ ดูรายละเอียดและขอบเขตใน [โมเดลและการประเมิน](docs/MODEL_OVERVIEW_TH.md)

การตรวจมืออาจได้รับผลจากแสง มุม ระยะ และการบังนิ้ว คะแนนที่แสดงเป็นคะแนนโมเดล ไม่ใช่ความน่าจะเป็นที่สอบเทียบแล้ว และไม่ใช่ Accuracy ของระบบ

## คู่มือและการตรวจระบบ

ดู [สารบัญเอกสาร](docs/README.md), [คู่มือหน้าจอ](docs/UI_GUIDE_TH.md), [ท่าปรับเสียงและแบมือ](docs/EXTRA_GESTURES_GUIDE_TH.md) และ [การตั้งค่า](docs/RUNTIME_SETTINGS_GUIDE_TH.md)

ตัวอย่างการตรวจส่วนประกอบที่ไม่ส่งคำสั่งไปยังเครื่องเล่น:

```powershell
./.venv/Scripts/python.exe tests/check_gesture_gate.py
./.venv/Scripts/python.exe tests/check_finger_reach.py
./.venv/Scripts/python.exe tests/check_dynamic_gestures.py
./.venv/Scripts/python.exe tests/check_apple_music_volume.py
```

การตรวจส่วนประกอบไม่ทดแทนการทดลองกล้องและเสียงจริง
