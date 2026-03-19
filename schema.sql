-- ============================================================================
-- REGS Database Schema + Seed Data (3NF Normalized)
-- ============================================================================

-- Drop tables in reverse order of dependencies
DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS course_schedule;
DROP TABLE IF EXISTS course_prerequisites;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS users;

-- ─── USERS & ROLES ──────────────────────────────────────────────────────────
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin','gs','faculty','student')),
    display_name TEXT NOT NULL
);

-- Pre-hashed SHA-256 passwords for the default accounts
-- admin/admin123, gs/gs123, faculty123, student123
INSERT INTO users (id, username, password, role, display_name) VALUES
(1, 'admin', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin', 'System Administrator'),
(2, 'gs', '2b0889c14e6485fe6d97cfde6ef42fd2555bf71f4919f69f17d3a37952cb23ad', 'gs', 'Graduate Secretary'),
(3, 'prof_smith', '27041f5856c7387a997252694afb048d1aa939228ffcdbd6285b979b8da20e7a', 'faculty', 'Dr. Smith'),
(4, 'prof_jones', '27041f5856c7387a997252694afb048d1aa939228ffcdbd6285b979b8da20e7a', 'faculty', 'Dr. Jones'),
(5, 'student1', '703b0a3d6ad75b649a28adde7d83c6251da457549263bc7ff45ec709b0a8448b', 'student', 'Alice Johnson');

CREATE TABLE students (
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

INSERT INTO students (id, user_id, uid, first_name, last_name, program, address, email, admit_year) VALUES
(1, 5, '12345678', 'Alice', 'Johnson', 'Masters', '2121 Eye St NW, Washington DC', 'alice@gwu.edu', 2024);

-- ─── COURSES (3NF - No Transitive Dependencies) ────────────────────────────
CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dept TEXT NOT NULL,
    course_number INTEGER NOT NULL,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL,
    UNIQUE(dept, course_number)
);

INSERT INTO courses (id, dept, course_number, title, credits) VALUES
(1, 'CSCI', 6221, 'SW Paradigms', 3),
(2, 'CSCI', 6461, 'Computer Architecture', 3),
(3, 'CSCI', 6212, 'Algorithms', 3),
(4, 'CSCI', 6220, 'Machine Learning', 3),
(5, 'CSCI', 6232, 'Networks 1', 3),
(6, 'CSCI', 6233, 'Networks 2', 3),
(7, 'CSCI', 6241, 'Database 1', 3),
(8, 'CSCI', 6242, 'Database 2', 3),
(9, 'CSCI', 6246, 'Compilers', 3),
(10, 'CSCI', 6260, 'Multimedia', 3),
(11, 'CSCI', 6251, 'Cloud Computing', 3),
(12, 'CSCI', 6254, 'SW Engineering', 3),
(13, 'CSCI', 6262, 'Graphics 1', 3),
(14, 'CSCI', 6283, 'Security 1', 3),
(15, 'CSCI', 6284, 'Cryptography', 3),
(16, 'CSCI', 6286, 'Network Security', 3),
(17, 'CSCI', 6325, 'Algorithms 2', 3),
(18, 'CSCI', 6339, 'Embedded Systems', 3),
(19, 'CSCI', 6384, 'Cryptography 2', 3),
(20, 'ECE', 6241, 'Communication Theory', 3),
(21, 'ECE', 6242, 'Information Theory', 2),
(22, 'MATH', 6210, 'Logic', 2);

-- ─── PREREQUISITES (Junction Table - Many-to-Many) ─────────────────────────
CREATE TABLE course_prerequisites (
    course_id INTEGER NOT NULL REFERENCES courses(id),
    prereq_course_id INTEGER NOT NULL REFERENCES courses(id),
    PRIMARY KEY (course_id, prereq_course_id)
);

-- Mapping prerequisites by course ID
INSERT INTO course_prerequisites (course_id, prereq_course_id) VALUES
(6, 5),           -- Networks 2 requires Networks 1
(8, 7),           -- Database 2 requires Database 1
(9, 2), (9, 3),   -- Compilers requires Computer Architecture & Algorithms
(11, 2),          -- Cloud Computing requires Computer Architecture
(12, 1),          -- SW Engineering requires SW Paradigms
(14, 3),          -- Security 1 requires Algorithms
(15, 3),          -- Cryptography requires Algorithms
(16, 14), (16, 5),-- Network Security requires Security 1 & Networks 1
(17, 3),          -- Algorithms 2 requires Algorithms
(18, 2), (18, 3), -- Embedded Systems requires Computer Architecture & Algorithms
(19, 15);         -- Cryptography 2 requires Cryptography

-- ─── SCHEDULE (3NF - No Redundant Data) ────────────────────────────────────
CREATE TABLE course_schedule (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL REFERENCES courses(id),
    day TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    faculty_id INTEGER REFERENCES users(id)
);

INSERT INTO course_schedule (id, course_id, day, time_slot, faculty_id) VALUES
(1, 1, 'M', '1500-1730', 3),
(2, 2, 'T', '1500-1730', 3),
(3, 3, 'W', '1500-1730', 3),
(4, 5, 'M', '1800-2030', 3),
(5, 6, 'T', '1800-2030', 3),
(6, 7, 'W', '1800-2030', 3),
(7, 8, 'R', '1800-2030', 3),
(8, 9, 'T', '1500-1730', 3),
(9, 11, 'M', '1800-2030', 3),
(10, 12, 'M', '1530-1800', 3),
(11, 10, 'R', '1800-2030', 3),
(12, 13, 'W', '1800-2030', 3),
(13, 14, 'T', '1800-2030', 3),
(14, 15, 'M', '1800-2030', 3),
(15, 16, 'W', '1800-2030', 3),
(16, 19, 'W', '1500-1730', 3),
(17, 20, 'M', '1800-2030', 3),
(18, 21, 'T', '1800-2030', 3),
(19, 22, 'W', '1800-2030', 3),
(20, 18, 'R', '1600-1830', 3);

-- ─── ENROLLMENTS ────────────────────────────────────────────────────────────
CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    schedule_id INTEGER NOT NULL REFERENCES course_schedule(id),
    semester TEXT NOT NULL,
    year INTEGER NOT NULL,
    grade TEXT NOT NULL DEFAULT 'IP',
    UNIQUE(student_id, schedule_id, semester, year)
);