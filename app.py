from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import hashlib
import os

app = Flask(__name__)
app.secret_key = 'regs_secret_key_2024'

# ─── DATABASE FUNCTIONS ──────────────────────────────────────────────────────

DATABASE = 'regs.db'

def get_db():
    """Get database connection from Flask's application context."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

def close_db(e=None):
    """Close database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database from schema.sql file."""
    schema_file = 'schema.sql'
    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file '{schema_file}' not found. Please ensure schema.sql exists in the project directory.")
    
    with app.app_context():
        db = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        
        # Read and execute the SQL schema file
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        db.executescript(schema_sql)
        db.close()
        print(f"✅ Database initialized from {schema_file}")

@app.teardown_appcontext
def teardown_db(e=None):
    close_db(e)

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ─── AUTH ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username=? AND password=?',
            (username, hash_password(password))
        ).fetchone()
        if user:
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['username'] = user['username']
            session['display_name'] = user['display_name']
            if user['role'] == 'student':
                return redirect(url_for('student_dashboard'))
            elif user['role'] == 'faculty':
                return redirect(url_for('faculty_dashboard'))
            elif user['role'] == 'gs':
                return redirect(url_for('gs_dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        uid = request.form['uid'].strip()
        username = request.form['username'].strip()
        password = request.form['password']
        first_name = request.form['first_name'].strip()
        last_name = request.form['last_name'].strip()
        program = request.form['program']
        address = request.form.get('address', '').strip()
        email = request.form.get('email', '').strip()

        if len(uid) != 8 or not uid.isdigit():
            flash('UID must be exactly 8 digits.', 'error')
            return render_template('register.html')

        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        existing_uid = db.execute('SELECT id FROM students WHERE uid=?', (uid,)).fetchone()
        if existing:
            flash('Username already taken.', 'error')
            return render_template('register.html')
        if existing_uid:
            flash('UID already registered.', 'error')
            return render_template('register.html')

        db.execute(
            'INSERT INTO users (username, password, role, display_name) VALUES (?,?,?,?)',
            (username, hash_password(password), 'student', f"{first_name} {last_name}")
        )
        user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]
        db.execute(
            'INSERT INTO students (user_id, uid, first_name, last_name, program, address, email) VALUES (?,?,?,?,?,?,?)',
            (user_id, uid, first_name, last_name, program, address, email)
        )
        db.commit()
        flash('Account created! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# ─── STUDENT ─────────────────────────────────────────────────────────────────

@app.route('/student')
def student_dashboard():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE user_id=?', (session['user_id'],)).fetchone()
    enrollments = db.execute('''
        SELECT e.id, c.dept, c.course_number, c.title, c.credits,
               cs.day, cs.time_slot, e.semester, e.year, e.grade,
               u.display_name as instructor_name
        FROM enrollments e
        JOIN course_schedule cs ON e.schedule_id = cs.id
        JOIN courses c ON cs.course_id = c.id
        LEFT JOIN users u ON cs.faculty_id = u.id
        WHERE e.student_id = ?
        ORDER BY e.year DESC, e.semester DESC
    ''', (student['id'],)).fetchall()
    return render_template('student_dashboard.html', student=student, enrollments=enrollments)

@app.route('/student/register_course', methods=['GET', 'POST'])
def student_register_course():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE user_id=?', (session['user_id'],)).fetchone()

    if request.method == 'POST':
        schedule_id = int(request.form['schedule_id'])
        semester = request.form['semester'].strip()
        year = int(request.form['year'])

        course = db.execute('SELECT * FROM course_schedule WHERE id=?', (schedule_id,)).fetchone()

        # PhD check: only 6000-level
        if student['program'] == 'PhD' and int(str(course['course_number'])[:4]) < 6000:
            flash('PhD students can only register for 6000-level courses.', 'error')
            return redirect(url_for('student_register_course'))

        # Already enrolled?
        already = db.execute(
            'SELECT id FROM enrollments WHERE student_id=? AND schedule_id=? AND semester=? AND year=?',
            (student['id'], schedule_id, semester, year)
        ).fetchone()
        if already:
            flash('You are already enrolled in this course for this semester.', 'error')
            return redirect(url_for('student_register_course'))

        # Check prerequisites (using normalized course_prerequisites table)
        prereqs = db.execute('''
            SELECT c.id as prereq_id, c.dept, c.course_number, c.title
            FROM course_prerequisites cp
            JOIN courses c ON cp.prereq_course_id = c.id
            WHERE cp.course_id = ?
        ''', (course['course_id'],)).fetchall()
        
        for prereq in prereqs:
            # Check if student has passed this prerequisite
            passed = db.execute('''
                SELECT e.id FROM enrollments e
                JOIN course_schedule cs ON e.schedule_id = cs.id
                WHERE e.student_id=? AND cs.course_id=? AND e.grade NOT IN ('IP','F','')
            ''', (student['id'], prereq['prereq_id'])).fetchone()
            
            if not passed:
                prereq_name = f"{prereq['dept']} {prereq['course_number']}"
                flash(f'Prerequisite not met: {prereq_name}', 'error')
                return redirect(url_for('student_register_course'))

        # Schedule conflict check
        existing_enrollments = db.execute('''
            SELECT cs.day, cs.time_slot FROM enrollments e
            JOIN course_schedule cs ON e.schedule_id = cs.id
            WHERE e.student_id=? AND e.semester=? AND e.year=? AND e.grade='IP'
        ''', (student['id'], semester, year)).fetchall()

        new_day = course['day']
        new_time = course['time_slot']
        time_order = {'1500-1730': 0, '1530-1800': 1, '1600-1830': 2, '1800-2030': 3}
        new_t = time_order.get(new_time, -1)

        for en in existing_enrollments:
            if en['day'] == new_day:
                existing_t = time_order.get(en['time_slot'], -1)
                # Conflict if same slot or overlapping (not 30min apart)
                if existing_t == new_t:
                    flash('Schedule conflict: same day and time.', 'error')
                    return redirect(url_for('student_register_course'))
                # 1500-1730 and 1800-2030: 30 min gap = ok
                # 1500-1730 and 1600-1830: overlap = conflict
                # 1530-1800 and 1800-2030: exactly 30 min = allowed
                combos_conflict = {(0,1),(1,0),(0,2),(2,0),(1,2),(2,1),(1,3),(3,1),(2,3),(3,2)}
                # Only allow (0,3) and (3,0) - 30 min gap between 1730 and 1800
                if (existing_t, new_t) in combos_conflict:
                    flash('Schedule conflict detected.', 'error')
                    return redirect(url_for('student_register_course'))

        db.execute(
            'INSERT INTO enrollments (student_id, schedule_id, semester, year, grade) VALUES (?,?,?,?,?)',
            (student['id'], schedule_id, semester, year, 'IP')
        )
        db.commit()
        flash('Successfully enrolled!', 'success')
        return redirect(url_for('student_dashboard'))

    # Available courses
    courses = db.execute('''
        SELECT cs.id, cs.course_id, cs.day, cs.time_slot, cs.faculty_id,
               c.dept, c.course_number, c.title, c.credits,
               u.display_name as instructor_name
        FROM course_schedule cs
        JOIN courses c ON cs.course_id = c.id
        LEFT JOIN users u ON cs.faculty_id = u.id
        ORDER BY c.dept, c.course_number
    ''').fetchall()
    return render_template('register_course.html', courses=courses)

@app.route('/student/drop/<int:enrollment_id>', methods=['POST'])
def drop_course(enrollment_id):
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE user_id=?', (session['user_id'],)).fetchone()
    enrollment = db.execute('SELECT * FROM enrollments WHERE id=? AND student_id=?',
                            (enrollment_id, student['id'])).fetchone()
    if enrollment and enrollment['grade'] == 'IP':
        db.execute('DELETE FROM enrollments WHERE id=?', (enrollment_id,))
        db.commit()
        flash('Course dropped.', 'success')
    else:
        flash('Cannot drop a completed course.', 'error')
    return redirect(url_for('student_dashboard'))

@app.route('/student/transcript')
def student_transcript():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE user_id=?', (session['user_id'],)).fetchone()
    return _get_transcript(student['id'])

@app.route('/student/profile', methods=['GET', 'POST'])
def student_profile():
    if session.get('role') != 'student':
        return redirect(url_for('login'))
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE user_id=?', (session['user_id'],)).fetchone()
    if request.method == 'POST':
        address = request.form.get('address', '').strip()
        email = request.form.get('email', '').strip()
        db.execute('UPDATE students SET address=?, email=? WHERE id=?', (address, email, student['id']))
        db.commit()
        flash('Profile updated.', 'success')
        return redirect(url_for('student_profile'))
    return render_template('student_profile.html', student=student)

# ─── FACULTY ─────────────────────────────────────────────────────────────────

@app.route('/faculty')
def faculty_dashboard():
    if session.get('role') != 'faculty':
        return redirect(url_for('login'))
    db = get_db()
    courses = db.execute('''
        SELECT cs.id, c.dept, c.course_number, c.title, cs.day, cs.time_slot
        FROM course_schedule cs
        JOIN courses c ON cs.course_id = c.id
        WHERE cs.faculty_id=?
    ''', (session['user_id'],)).fetchall()
    return render_template('faculty_dashboard.html', courses=courses)

@app.route('/faculty/grades/<int:schedule_id>', methods=['GET', 'POST'])
def faculty_grades(schedule_id):
    if session.get('role') != 'faculty':
        return redirect(url_for('login'))
    db = get_db()
    course = db.execute('''
        SELECT cs.*, c.dept, c.course_number, c.title
        FROM course_schedule cs
        JOIN courses c ON cs.course_id = c.id
        WHERE cs.id=? AND cs.faculty_id=?
    ''', (schedule_id, session['user_id'])).fetchone()
    if not course:
        flash('Access denied.', 'error')
        return redirect(url_for('faculty_dashboard'))

    if request.method == 'POST':
        enrollment_id = int(request.form['enrollment_id'])
        grade = request.form['grade']
        valid_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'F']
        if grade not in valid_grades:
            flash('Invalid grade.', 'error')
        else:
            existing = db.execute('SELECT grade FROM enrollments WHERE id=?', (enrollment_id,)).fetchone()
            if existing and existing['grade'] != 'IP':
                flash('Grade already submitted. Only GS can change it.', 'error')
            else:
                db.execute('UPDATE enrollments SET grade=? WHERE id=?', (grade, enrollment_id))
                db.commit()
                flash('Grade submitted.', 'success')
        return redirect(url_for('faculty_grades', schedule_id=schedule_id))

    enrollments = db.execute('''
        SELECT e.id, s.uid, s.first_name, s.last_name, e.semester, e.year, e.grade
        FROM enrollments e
        JOIN students s ON e.student_id = s.id
        WHERE e.schedule_id=?
        ORDER BY s.last_name
    ''', (schedule_id,)).fetchall()
    return render_template('faculty_grades.html', course=course, enrollments=enrollments)

# ─── GRAD SECRETARY ──────────────────────────────────────────────────────────

@app.route('/gs')
def gs_dashboard():
    if session.get('role') != 'gs':
        return redirect(url_for('login'))
    db = get_db()
    search = request.args.get('search', '').strip()
    program_filter = request.args.get('program', '')
    year_filter = request.args.get('admit_year', '')

    query = 'SELECT * FROM students WHERE 1=1'
    params = []
    if search:
        query += ' AND (uid LIKE ? OR last_name LIKE ? OR first_name LIKE ?)'
        params += [f'%{search}%', f'%{search}%', f'%{search}%']
    if program_filter:
        query += ' AND program = ?'
        params.append(program_filter)
    if year_filter:
        query += ' AND admit_year = ?'
        params.append(year_filter)
    query += ' ORDER BY last_name'
    students = db.execute(query, params).fetchall()
    years = [r[0] for r in db.execute('SELECT DISTINCT admit_year FROM students ORDER BY admit_year').fetchall()]
    return render_template('gs_dashboard.html', students=students, search=search,
                           program_filter=program_filter, year_filter=year_filter, years=years)

@app.route('/gs/transcript/<int:student_id>')
def gs_transcript(student_id):
    if session.get('role') not in ('gs', 'admin'):
        return redirect(url_for('login'))
    return _get_transcript(student_id)

@app.route('/gs/grades/<int:enrollment_id>', methods=['POST'])
def gs_override_grade(enrollment_id):
    if session.get('role') != 'gs':
        return redirect(url_for('login'))
    grade = request.form['grade']
    valid_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'F', 'IP']
    if grade not in valid_grades:
        flash('Invalid grade.', 'error')
    else:
        db = get_db()
        db.execute('UPDATE enrollments SET grade=? WHERE id=?', (grade, enrollment_id))
        db.commit()
        flash('Grade updated.', 'success')
    return redirect(request.referrer or url_for('gs_dashboard'))

@app.route('/gs/student/<int:student_id>/grades', methods=['GET', 'POST'])
def gs_student_grades(student_id):
    if session.get('role') != 'gs':
        return redirect(url_for('login'))
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id=?', (student_id,)).fetchone()
    if request.method == 'POST':
        enrollment_id = int(request.form['enrollment_id'])
        grade = request.form['grade']
        valid_grades = ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C', 'F', 'IP']
        if grade not in valid_grades:
            flash('Invalid grade.', 'error')
        else:
            db.execute('UPDATE enrollments SET grade=? WHERE id=?', (grade, enrollment_id))
            db.commit()
            flash('Grade updated.', 'success')
        return redirect(url_for('gs_student_grades', student_id=student_id))
    enrollments = db.execute('''
        SELECT e.id, c.dept, c.course_number, c.title, e.semester, e.year, e.grade
        FROM enrollments e
        JOIN course_schedule cs ON e.schedule_id = cs.id
        JOIN courses c ON cs.course_id = c.id
        WHERE e.student_id=?
        ORDER BY e.year DESC
    ''', (student_id,)).fetchall()
    return render_template('gs_student_grades.html', student=student, enrollments=enrollments)

# ─── ADMIN ───────────────────────────────────────────────────────────────────

@app.route('/admin')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY role, display_name').fetchall()
    return render_template('admin_dashboard.html', users=users)

@app.route('/admin/create_user', methods=['GET', 'POST'])
def admin_create_user():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']
        display_name = request.form['display_name'].strip()

        existing = db.execute('SELECT id FROM users WHERE username=?', (username,)).fetchone()
        if existing:
            flash('Username already exists.', 'error')
            return render_template('admin_create_user.html')

        db.execute('INSERT INTO users (username, password, role, display_name) VALUES (?,?,?,?)',
                   (username, hash_password(password), role, display_name))
        db.commit()
        flash(f'User {username} ({role}) created.', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_create_user.html')

@app.route('/admin/assign_faculty', methods=['GET', 'POST'])
def admin_assign_faculty():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    db = get_db()
    if request.method == 'POST':
        schedule_id = int(request.form['schedule_id'])
        faculty_id = int(request.form['faculty_id'])
        db.execute('UPDATE course_schedule SET faculty_id=? WHERE id=?', (faculty_id, schedule_id))
        db.commit()
        flash('Faculty assigned.', 'success')
        return redirect(url_for('admin_assign_faculty'))
    courses = db.execute('''
        SELECT cs.id, cs.course_id, cs.faculty_id, cs.day, cs.time_slot,
               c.dept, c.course_number, c.title
        FROM course_schedule cs
        JOIN courses c ON cs.course_id = c.id
        ORDER BY c.dept, c.course_number
    ''').fetchall()
    faculty = db.execute("SELECT * FROM users WHERE role='faculty' ORDER BY display_name").fetchall()
    return render_template('admin_assign_faculty.html', courses=courses, faculty=faculty)

# ─── TRANSCRIPT HELPER ───────────────────────────────────────────────────────

def _get_transcript(student_id):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id=?', (student_id,)).fetchone()
    enrollments = db.execute('''
        SELECT c.dept, c.course_number, c.title, c.credits,
               e.semester, e.year, e.grade, cs.day, cs.time_slot,
               u.display_name as instructor_name
        FROM enrollments e
        JOIN course_schedule cs ON e.schedule_id = cs.id
        JOIN courses c ON cs.course_id = c.id
        LEFT JOIN users u ON cs.faculty_id = u.id
        WHERE e.student_id=?
        ORDER BY e.year DESC, e.semester DESC
    ''', (student_id,)).fetchall()

    grade_points = {'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                    'C+': 2.3, 'C': 2.0, 'F': 0.0}
    total_points = 0
    total_credits = 0
    for e in enrollments:
        if e['grade'] in grade_points:
            total_points += grade_points[e['grade']] * e['credits']
            total_credits += e['credits']
    gpa = round(total_points / total_credits, 2) if total_credits > 0 else None

    role = session.get('role')
    return render_template('transcript.html', student=student, enrollments=enrollments,
                           gpa=gpa, total_credits=total_credits, role=role)

if __name__ == '__main__':
    init_db()
    print("\n✅ REGS is running at http://127.0.0.1:5000")
    print("   Default admin login: admin / admin123\n")
    app.run(debug=True, port=5000)