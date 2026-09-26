# 🎓 Smart Attendance System

A face-recognition-based attendance management system built with **Flask, MySQL, and InsightFace**.

The system allows teachers to register students, create lecture sessions, capture classroom photos, automatically recognize registered students, mark attendance, view attendance history, and export attendance records.

---

## 📌 Overview

Traditional attendance systems require manual entry or additional hardware such as RFID cards or biometric devices.

This project uses **face recognition** to automate classroom attendance.

A teacher can:

1. Register students with their basic academic information.
2. Capture or upload a student's face.
3. Generate and store the student's face embedding.
4. Create a subject and lecture session.
5. Upload one or multiple classroom photographs.
6. Detect faces in the photographs.
7. Compare detected faces with registered students.
8. Automatically mark recognized students as **PRESENT**.
9. View attendance history.
10. Export attendance records to Excel.

---

# ✨ Features

### 👨‍🏫 Teacher Dashboard

- Manage students
- Manage subjects
- Create lecture sessions
- Take attendance
- View attendance history
- Export attendance records

### 👨‍🎓 Student Registration

Students can be registered with:

- Student name
- Enrollment number
- Department
- Semester
- Division
- Face image

### 🧠 Face Recognition

The system uses **InsightFace** to:

- Detect faces
- Generate face embeddings
- Compare faces
- Identify registered students
- Ignore unknown students

### 📸 Multi-Photo Attendance

Teachers can upload multiple classroom photographs for a single lecture.

This helps when:

- Students are sitting in different areas of the classroom.
- One photograph does not contain everyone.
- The classroom is large.
- Some students are partially hidden in one photograph.

### 🚫 Duplicate Prevention

If a student is recognized in multiple photographs during the same lecture, the system prevents duplicate attendance records.

### 📚 Lecture Management

Attendance can be organized by:

- Subject
- Lecture
- Date
- Time
- Department
- Semester
- Division

### 📊 Attendance History

Teachers can review previously recorded attendance sessions.

### 📥 Excel Export

Attendance records can be exported for further use in Excel or other spreadsheet software.

---

# 🏗️ System Workflow

```text
                    ┌──────────────────────┐
                    │    Teacher Login /   │
                    │      Dashboard       │
                    └──────────┬───────────┘
                               │
                 ┌─────────────┴─────────────┐
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐         ┌─────────────────┐
        │ Register        │         │ Create Lecture  │
        │ Student         │         │ Session         │
        └────────┬────────┘         └────────┬────────┘
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐         ┌─────────────────┐
        │ Capture / Upload│         │ Upload Classroom│
        │ Face            │         │ Photos          │
        └────────┬────────┘         └────────┬────────┘
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐         ┌─────────────────┐
        │ InsightFace     │         │ Face Detection  │
        │ Embedding       │         │                 │
        └────────┬────────┘         └────────┬────────┘
                 │                           │
                 ▼                           ▼
        ┌─────────────────┐         ┌─────────────────┐
        │ Store Student   │◄────────│ Face Matching   │
        │ Embedding       │         │                 │
        └─────────────────┘         └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Mark Attendance │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Attendance      │
                                    │ History         │
                                    └────────┬────────┘
                                             │
                                             ▼
                                    ┌─────────────────┐
                                    │ Excel Export    │
                                    └─────────────────┘
