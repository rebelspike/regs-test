# REGS – Course Registration System (CS 2541W Phase 1)

## Quick Start

```bash
# 1. Install Flask (once)
pip install flask

# 2. Run the app
python3 app.py
```

Then open your browser at: **http://127.0.0.1:5000**

---

## Demo Login Credentials

| Role              | Username      | Password     |
|-------------------|---------------|--------------|
| Admin             | `admin`       | `admin123`   |
| Grad Secretary    | `gs`          | `gs123`      |
| Faculty           | `prof_smith`  | `faculty123` |
| Student           | `student1`    | `student123` |

---

## Features Implemented

### Students
- Create account (UID, first/last name, Masters/PhD program, address, email)
- Log in / log out
- Register for courses (with prerequisite checking + schedule conflict detection)
- Drop courses (only while grade is IP)
- View transcript (with GPA calculation)
- Update personal info (address, email)

### Faculty
- View assigned courses
- Submit final grades (A, A-, B+, B, B-, C+, C, F) — one time only (locked after submit)

### Grad Secretary
- View all students
- View any student's transcript
- Override/change any grade (including locked faculty grades)

### Admin
- Create users (faculty, GS, admin roles)
- Assign faculty to courses

---

## Course Schedule
All 20 courses from Appendix A are preloaded (CSCI, ECE, MATH departments).  
Time slots: 1500-1730 | 1530-1800 | 1600-1830 | 1800-2030

## Database
Uses SQLite (`regs.db`) — auto-created on first run. No external DB needed.
