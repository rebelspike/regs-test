import sqlite3
from flask import g
import os

DATABASE = 'regs.db'

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    from app import app
    with app.app_context():
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        _create_tables(db)
        _seed_data(db)
        db.close()

def _create_tables(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin','gs','faculty','student')),
            display_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
            uid TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            program TEXT NOT NULL CHECK(program IN ('Masters','PhD')),
            address TEXT,
            email TEXT,
            admit_year INTEGER DEFAULT 2024
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept TEXT NOT NULL,
            course_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            credits INTEGER NOT NULL,
            prereq1 TEXT,
            prereq2 TEXT,
            UNIQUE(dept, course_number)
        );

        CREATE TABLE IF NOT EXISTS course_schedule (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL REFERENCES courses(id),
            dept TEXT NOT NULL,
            course_number INTEGER NOT NULL,
            title TEXT NOT NULL,
            credits INTEGER NOT NULL,
            day TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            faculty_id INTEGER REFERENCES users(id),
            prereq1 TEXT,
            prereq2 TEXT
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id),
            schedule_id INTEGER NOT NULL REFERENCES course_schedule(id),
            semester TEXT NOT NULL,
            year INTEGER NOT NULL,
            grade TEXT NOT NULL DEFAULT 'IP',
            UNIQUE(student_id, schedule_id, semester, year)
        );
    ''')
    db.commit()

def _seed_data(db):
    # Skip if already seeded
    existing = db.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    if existing > 0:
        return

    import hashlib
    def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()

    # Default users
    db.execute("INSERT INTO users (username,password,role,display_name) VALUES (?,?,?,?)",
               ('admin', hp('admin123'), 'admin', 'System Administrator'))
    db.execute("INSERT INTO users (username,password,role,display_name) VALUES (?,?,?,?)",
               ('gs', hp('gs123'), 'gs', 'Graduate Secretary'))
    db.execute("INSERT INTO users (username,password,role,display_name) VALUES (?,?,?,?)",
               ('prof_smith', hp('faculty123'), 'faculty', 'Dr. Smith'))
    db.execute("INSERT INTO users (username,password,role,display_name) VALUES (?,?,?,?)",
               ('prof_jones', hp('faculty123'), 'faculty', 'Dr. Jones'))
    db.execute("INSERT INTO users (username,password,role,display_name) VALUES (?,?,?,?)",
               ('student1', hp('student123'), 'student', 'Alice Johnson'))
    db.commit()

    # Demo student
    db.execute('''INSERT INTO students (user_id,uid,first_name,last_name,program,address,email,admit_year)
                  VALUES (?,?,?,?,?,?,?,?)''',
               (5, '12345678', 'Alice', 'Johnson', 'Masters',
                '2121 Eye St NW, Washington DC', 'alice@gwu.edu', 2024))
    db.commit()

    # Course catalog
    catalog = [
        ('CSCI', 6221, 'SW Paradigms', 3, None, None),
        ('CSCI', 6461, 'Computer Architecture', 3, None, None),
        ('CSCI', 6212, 'Algorithms', 3, None, None),
        ('CSCI', 6220, 'Machine Learning', 3, None, None),
        ('CSCI', 6232, 'Networks 1', 3, None, None),
        ('CSCI', 6233, 'Networks 2', 3, 'CSCI 6232', None),
        ('CSCI', 6241, 'Database 1', 3, None, None),
        ('CSCI', 6242, 'Database 2', 3, 'CSCI 6241', None),
        ('CSCI', 6246, 'Compilers', 3, 'CSCI 6461', 'CSCI 6212'),
        ('CSCI', 6260, 'Multimedia', 3, None, None),
        ('CSCI', 6251, 'Cloud Computing', 3, 'CSCI 6461', None),
        ('CSCI', 6254, 'SW Engineering', 3, 'CSCI 6221', None),
        ('CSCI', 6262, 'Graphics 1', 3, None, None),
        ('CSCI', 6283, 'Security 1', 3, 'CSCI 6212', None),
        ('CSCI', 6284, 'Cryptography', 3, 'CSCI 6212', None),
        ('CSCI', 6286, 'Network Security', 3, 'CSCI 6283', 'CSCI 6232'),
        ('CSCI', 6325, 'Algorithms 2', 3, 'CSCI 6212', None),
        ('CSCI', 6339, 'Embedded Systems', 3, 'CSCI 6461', 'CSCI 6212'),
        ('CSCI', 6384, 'Cryptography 2', 3, 'CSCI 6284', None),
        ('ECE',  6241, 'Communication Theory', 3, None, None),
        ('ECE',  6242, 'Information Theory', 2, None, None),
        ('MATH', 6210, 'Logic', 2, None, None),
    ]
    for row in catalog:
        db.execute('INSERT INTO courses (dept,course_number,title,credits,prereq1,prereq2) VALUES (?,?,?,?,?,?)', row)
    db.commit()

    # Course schedule (from spec)
    schedule = [
        (1,  'CSCI', 6221, 'SW Paradigms', 3, 'M', '1500-1730', None, None),
        (2,  'CSCI', 6461, 'Computer Architecture', 3, 'T', '1500-1730', None, None),
        (3,  'CSCI', 6212, 'Algorithms', 3, 'W', '1500-1730', None, None),
        (4,  'CSCI', 6232, 'Networks 1', 3, 'M', '1800-2030', None, None),
        (5,  'CSCI', 6233, 'Networks 2', 3, 'T', '1800-2030', 'CSCI 6232', None),
        (6,  'CSCI', 6241, 'Database 1', 3, 'W', '1800-2030', None, None),
        (7,  'CSCI', 6242, 'Database 2', 3, 'R', '1800-2030', 'CSCI 6241', None),
        (8,  'CSCI', 6246, 'Compilers', 3, 'T', '1500-1730', 'CSCI 6461', 'CSCI 6212'),
        (9,  'CSCI', 6251, 'Cloud Computing', 3, 'M', '1800-2030', 'CSCI 6461', None),
        (10, 'CSCI', 6254, 'SW Engineering', 3, 'M', '1530-1800', 'CSCI 6221', None),
        (11, 'CSCI', 6260, 'Multimedia', 3, 'R', '1800-2030', None, None),
        (12, 'CSCI', 6262, 'Graphics 1', 3, 'W', '1800-2030', None, None),
        (13, 'CSCI', 6283, 'Security 1', 3, 'T', '1800-2030', 'CSCI 6212', None),
        (14, 'CSCI', 6284, 'Cryptography', 3, 'M', '1800-2030', 'CSCI 6212', None),
        (15, 'CSCI', 6286, 'Network Security', 3, 'W', '1800-2030', 'CSCI 6283', 'CSCI 6232'),
        (16, 'CSCI', 6384, 'Cryptography 2', 3, 'W', '1500-1730', 'CSCI 6284', None),
        (17, 'ECE',  6241, 'Communication Theory', 3, 'M', '1800-2030', None, None),
        (18, 'ECE',  6242, 'Information Theory', 2, 'T', '1800-2030', None, None),
        (19, 'MATH', 6210, 'Logic', 2, 'W', '1800-2030', None, None),
        (20, 'CSCI', 6339, 'Embedded Systems', 3, 'R', '1600-1830', 'CSCI 6461', 'CSCI 6212'),
    ]

    faculty_id = 3  # prof_smith default
    for s in schedule:
        cid, dept, cnum, title, credits, day, time_slot, p1, p2 = s
        course_row = db.execute('SELECT id FROM courses WHERE dept=? AND course_number=?', (dept, cnum)).fetchone()
        course_id = course_row[0] if course_row else None
        db.execute('''INSERT INTO course_schedule
                      (id, course_id, dept, course_number, title, credits, day, time_slot, faculty_id, prereq1, prereq2)
                      VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                   (cid, course_id, dept, cnum, title, credits, day, time_slot, faculty_id, p1, p2))
    db.commit()
