from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import os
import json
import PyPDF2
import random
import google.generativeai as genai
import os
from flask_migrate import Migrate
from flask import request, redirect, url_for, flash
import re 
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://study_f5o4_user:gdGBoOOzT8NzlBigc5IbHm5RsG0ByOjt@dpg-cvvm1si4d50c739gpnq0-a.virginia-postgres.render.com/study_f5o4'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

def allowed_file(filename, allowed_extensions):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


@app.route('/submit_quiz/<int:lesson_id>', methods=['POST'])
@login_required
def submit_quiz(lesson_id):
    # Get quiz answers from form
    answers = request.form.to_dict()
    
    # Calculate score (placeholder implementation)
    score = calculate_quiz_score(lesson_id, answers)
    
    # Save user progress
    lesson = DailyLesson.query.get(lesson_id)
    if not lesson:
        flash('Lesson not found', 'error')
        return redirect(url_for('index'))
        
    user_course = UserCourse.query.filter_by(
        user_id=current_user.id,
        course_id=lesson.subject.course_id
    ).first()
    
    if user_course:
        progress = UserLessonProgress(
            user_course_id=user_course.id,
            lesson_id=lesson_id,
            completed=True,
            quiz_score=score,
            completion_date=datetime.utcnow()
        )
        db.session.add(progress)
        
        # Update user's current day and last activity
        current_user.last_activity = datetime.utcnow()
        current_user.current_day = 1 if current_user.current_day == 0 else current_user.current_day + 1
        
        # Update streak count
        yesterday = datetime.utcnow() - timedelta(days=1)
        if current_user.last_activity.date() >= yesterday.date():
            current_user.streak_count += 1
        else:
            current_user.streak_count = 1
            
        # Update course completion percentage
        total_lessons = DailyLesson.query.join(Subject).filter(
            Subject.course_id == lesson.subject.course_id
        ).count()
        
        completed_lessons = UserLessonProgress.query.join(
            UserCourse
        ).filter(
            UserCourse.user_id == current_user.id,
            UserCourse.course_id == lesson.subject.course_id,
            UserLessonProgress.completed == True
        ).count()
        
        if total_lessons > 0:
            # Calculate actual completion percentage
            user_course.completion_status = (completed_lessons / total_lessons) * 100
            
            # Update user points for completing quiz
            user_points = UserPoints.query.filter_by(user_id=current_user.id).first()
            if not user_points:
                user_points = UserPoints(user_id=current_user.id, points=0, level=1)
                db.session.add(user_points)
            
            # Award points based on quiz score
            points_earned = int(score / 10)  # 1 point per 10% score
            user_points.points += points_earned
            user_points.last_updated = datetime.utcnow()
            
            # Check if user completed all lessons for the day
            if completed_lessons == total_lessons:
                user_points.points += 5  # Bonus points for completing all daily lessons
                
                # Check if user completed all lessons for the course
                if user_course.completion_status >= 100:
                    user_points.points += 10  # Bonus points for completing course
            
        db.session.commit()
    
    flash('Quiz submitted successfully!', 'success')
    return redirect(url_for('view_lesson', lesson_id=lesson_id))

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

# Create admin user within application context

# Initialize Gemini AI processing tools
# Set your API key from environment variable or use a placeholder for development
# IMPORTANT: In production, always use environment variables for API keys
api_key = "AIzaSyB5iEbuBXEtsJkE3ocIqOO9rzLAhPfIB8I"
genai.configure(api_key=api_key)

# dels
from datetime import datetime









class ChapterVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    video_url = db.Column(db.String(255))
    description = db.Column(db.Text)
    duration = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)  # Flag to identify admin users
    current_track = db.Column(db.String(20), default='6-month')  # '6-month' or '3-month'
    current_day = db.Column(db.Integer, default=1)
    streak_count = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    enrolled_courses = db.relationship('UserCourse', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # 'UPSC', 'SSC', 'Banking', etc.
    duration_weeks = db.Column(db.Integer, default=12)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    subjects = db.relationship('Subject', backref='course', lazy=True)
    enrolled_users = db.relationship('UserCourse', backref='course', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=1)
    daily_lessons = db.relationship('DailyLesson', backref='subject', lazy=True)

class DailyLesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200))
    pdf_path = db.Column(db.String(255))
    content = db.Column(db.Text)  # Extracted from PDF
    summary = db.Column(db.Text)  # AI-generated summary
    mind_map_url = db.Column(db.String(255))  # URL to mind map image
    video_url = db.Column(db.String(255))  # URL to lesson video
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quiz = db.relationship('LessonQuiz', backref='lesson', lazy=True, uselist=False)

class LessonQuiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('daily_lesson.id'), nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    questions = db.relationship('QuizQuestion', backref='quiz', lazy=True)

class UserCourse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    enrollment_date = db.Column(db.DateTime, default=datetime.utcnow)
    completion_status = db.Column(db.Float, default=0.0)  # Percentage of completion
    current_day = db.Column(db.Integer, default=1)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.relationship('UserLessonProgress', backref='enrollment', lazy=True)

class UserLessonProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_course_id = db.Column(db.Integer, db.ForeignKey('user_course.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('daily_lesson.id'), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    quiz_score = db.Column(db.Float, nullable=True)
    completion_date = db.Column(db.DateTime)
    feedback = db.Column(db.Text)
    
class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=True)
    material_type = db.Column(db.String(50))  # 'NCERT', 'Reference', 'CurrentAffairs'
    file_path = db.Column(db.String(255))
    priority = db.Column(db.Integer, default=5)  # 1-10, 1 being highest
    content_summary = db.Column(db.Text)
    chapters = db.relationship('Chapter', backref='material', lazy=True)

class ChapterNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ChapterMindMap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    image_path = db.Column(db.String(255))  # Path to the mind map image
    content_json = db.Column(db.Text)  # JSON representation of the mind map
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class ChapterQuiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('ChapterQuizQuestion', backref='quiz', lazy=True)

class ChapterQuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('chapter_quiz.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20))  # 'mcq', 'short_answer'
    difficulty = db.Column(db.Integer)  # 1-5
    options = db.relationship('ChapterQuizOption', backref='question', lazy=True)
    correct_answer = db.Column(db.Text, nullable=True)  # For short answer questions
    explanation = db.Column(db.Text)

class ChapterQuizOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('chapter_quiz_question.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey('material.id'), nullable=False)
    chapter_number = db.Column(db.Integer)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    summary = db.Column(db.Text)
    importance = db.Column(db.Integer, default=5)  # 1-10, 1 being highest
    time_required = db.Column(db.Integer)  # estimated minutes to complete
    notes = db.relationship('ChapterNote', backref='chapter', lazy=True, cascade='all, delete-orphan')
    mind_maps = db.relationship('ChapterMindMap', backref='chapter', lazy=True)
    quizzes = db.relationship('ChapterQuiz', backref='chapter', lazy=True)
    videos = db.relationship('ChapterVideo', backref='chapter', lazy=True)

class QuizQuestion(db.Model):
    __tablename__ = 'quiz_question'
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('lesson_quiz.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20))  # 'mcq', 'short_answer'
    difficulty = db.Column(db.Integer)  # 1-5
    options = db.relationship('QuizOption', backref='question', lazy=True, cascade='all, delete-orphan')
    correct_answer = db.Column(db.Text, nullable=True)  # For short answer questions
    explanation = db.Column(db.Text)

class QuizOption(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id'), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class UserPoints(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    points = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    points_type = db.Column(db.String(50))  # 'quiz', 'streak', 'lesson_completion', etc.
    description = db.Column(db.Text)
    level = db.Column(db.Integer, default=1)  # User level based on points

class UserReward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    reward_type = db.Column(db.String(50))  # 'badge', 'certificate', 'streak', etc.
    reward_value = db.Column(db.String(100))
    earned_date = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text)

class ProgressCalendar(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    completed_lessons = db.Column(db.Integer, default=0)
    points_earned = db.Column(db.Integer, default=0)
    streak_maintained = db.Column(db.Boolean, default=False)


# Helper functions for extracting content from PDFs and generating quizzes
@app.route('/start_mock_practice', methods=['GET', 'POST'])
def start_mock_practice():
    if request.method == 'POST':
        # Handle PDF upload for previous papers
        if 'exam_paper' in request.files:
            file = request.files['exam_paper']
            if file.filename != '':
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Extract questions from paper
                questions = extract_questions_from_paper(filepath)
                session['practice_questions'] = questions
                session['current_practice_index'] = 0
                return redirect(url_for('practice_question'))
    
    # Fallback to existing question bank
    questions = []
    for course in current_user.enrolled_courses:
        questions.extend(QuizQuestion.query.filter_by(quiz_id=course.id).all())
    
    random.shuffle(questions)
    session['practice_questions'] = [q.id for q in questions]
    session['current_practice_index'] = 0
    
    return render_template('mock_practice_start.html')

@app.route('/practice_question', methods=['GET', 'POST'])
def practice_question():
    if 'practice_questions' not in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Handle answer submission
        session['current_practice_index'] += 1
        if session['current_practice_index'] >= len(session['practice_questions']):
            return redirect(url_for('practice_results'))
    
    question_id = session['practice_questions'][session['current_practice_index']]
    question = QuizQuestion.query.get(question_id)
    
    return render_template('practice_question.html', question=question)

@app.route('/practice_results')
def practice_results():
    if 'practice_questions' not in session:
        return redirect(url_for('dashboard'))
    
    # Calculate and display results
    return render_template('practice_results.html')

@app.route('/rewards')
@login_required
def user_rewards():
    """Show user's earned rewards"""
    rewards = UserReward.query.filter_by(user_id=current_user.id).order_by(UserReward.earned_date.desc()).all()
    user_points = UserPoints.query.filter_by(user_id=current_user.id).first() or UserPoints(user_id=current_user.id, points=0, level=1)
    return render_template('rewards.html', rewards=rewards, user_points=user_points, streak_count=current_user.streak_count)



def calculate_quiz_score(lesson_id, answers):
    """Calculate quiz score by comparing user answers with correct answers"""
    quiz = LessonQuiz.query.filter_by(lesson_id=lesson_id).first()
    if not quiz:
        return 0
        
    score = 0
    total_questions = len(quiz.questions)
    
    for question in quiz.questions:
        user_answer = answers.get(f'question_{question.id}')
        
        if question.question_type == 'mcq':
            # For MCQ questions, check if selected option is correct
            selected_option = QuizOption.query.get(user_answer) if user_answer else None
            if selected_option and selected_option.is_correct:
                score += 1
        elif question.question_type == 'short_answer':
            # For short answer questions, compare with correct answer (case-insensitive)
            if user_answer and question.correct_answer and \
               user_answer.lower().strip() == question.correct_answer.lower().strip():
                score += 1
    
    # Return percentage score
    return (score / total_questions) * 100 if total_questions > 0 else 0


def extract_content_from_pdf(pdf_path):
    """Extract text content from a PDF file"""
    content = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                content += page.extract_text()
        return content
    except Exception as e:
        print(f"Error extracting PDF content: {e}")
        return ""
        
def extract_questions_from_paper(pdf_path):
    """Extract questions and answers from previous exam papers"""
    content = extract_content_from_pdf(pdf_path)
    if not content:
        return []
        
    questions = []
    lines = content.split('\n')
    
    # Enhanced pattern matching for various question formats
    current_question = None
    for line in lines:
        line = line.strip()
        
        # Match different question patterns
        if re.match(r'^(\d+\.|Q\d*\.?|Question\s*\d*:|\d+\)|\[\d+\])\s*', line):
            if current_question:
                questions.append(current_question)
            current_question = {
                'question': re.sub(r'^(\d+\.|Q\d*\.?|Question\s*\d*:|\d+\)|\[\d+\])\s*', '', line),
                'options': [],
                'correct_answer': ''
            }
        # Match option patterns
        elif re.match(r'^([A-D]\.|[a-d]\)|\d+\.|\*\s*[A-D])\s*', line):
            if current_question:
                current_question['options'].append(re.sub(r'^([A-D]\.|[a-d]\)|\d+\.|\*\s*[A-D])\s*', '', line))
        # Match answer patterns
        elif re.match(r'^(Answer|Correct Answer|Key|Solution):?\s*', line, re.IGNORECASE):
            if current_question:
                current_question['correct_answer'] = re.sub(r'^(Answer|Correct Answer|Key|Solution):?\s*', '', line, flags=re.IGNORECASE)
                questions.append(current_question)
                current_question = None
    
    if current_question:
        questions.append(current_question)
        
    return questions
        
def parse_timetable_pdf(pdf_path):
    """Parse a 180-day timetable PDF to extract subjects"""
    try:
        content = extract_content_from_pdf(pdf_path)
        if not content:
            print(f"No content extracted from PDF: {pdf_path}")
            return None
            
        # Parse content to extract subjects
        subjects = set()
        lines = content.split('\n')
        
        # Look for lines with subject information
        for line in lines:
            if '|' in line:  # CSV-like format
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 3:  # Day, Date, Subject columns
                    subjects.add(parts[2])
            elif ',' in line:  # CSV format
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:
                    subjects.add(parts[2])
            elif '\t' in line:  # TSV format
                parts = [p.strip() for p in line.split('\t')]
                if len(parts) >= 3:
                    subjects.add(parts[2])
        
        if not subjects:
            print(f"No subjects found in PDF content: {content[:200]}...")
            return None
                    
        return sorted(list(subjects))
    except Exception as e:
        print(f"Error parsing timetable PDF: {e}")
        return None

def generate_summary_with_ai(content, max_length=2000):
    """Generate a summary of the content using Gemini AI"""
    # Truncate content if too long (API limits)
    if len(content) > 8000:
        content = content[:8000]
        
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        prompt = f"Summarize the following educational content in about 300-500 words, highlighting the key concepts and important points:\n\n{content}"
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text
    except Exception as e:
        print(f"Error generating AI summary: {e}")
        return "Summary generation failed. Please try again later."

def generate_quiz_with_ai(content, num_questions=5):
    """Generate quiz questions based on the PDF content using AI"""
    if len(content) > 8000:
        content = content[:8000]
        
    try:
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        prompt = f"""Create {num_questions} multiple-choice questions based on the following educational content. 
        For each question:
        1. Provide the question text
        2. Create 4 answer options (A, B, C, D)
        3. Indicate which option is correct
        4. Provide a brief explanation for the correct answer
        
        Format your response as a JSON array of objects with these fields:
        question_text, options (array of 4 strings), correct_option_index (0-3), explanation
        
        Here's the content:
        {content}"""
        
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if not response.text:
            raise Exception("Empty response from AI model")
            
        # Try to parse the JSON response
        try:
            # Clean the response if it contains markdown code blocks
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            quiz_data = json.loads(text)
            return quiz_data
        except json.JSONDecodeError:
            # Fallback to manual parsing if JSON parsing fails
            print("JSON parsing failed, creating default questions")
            return generate_default_questions(5)
    
    except Exception as e:
        print(f"Error generating quiz with AI: {e}")
        return generate_default_questions(5)

def generate_default_questions(num=5):
    """Generate default placeholder questions when AI generation fails"""
    questions = []
    for i in range(num):
        questions.append({
            "question_text": f"Question {i+1} (placeholder due to AI generation failure)",
            "options": [f"Option A", f"Option B", f"Option C", f"Option D"],
            "correct_option_index": 0,
            "explanation": "This is a placeholder explanation."
        })
    return questions

def create_lesson_quiz(lesson_id, pdf_content):
    """Create a quiz for a daily lesson based on the PDF content"""
    lesson = DailyLesson.query.get(lesson_id)
    if not lesson:
        return None
        
    # Generate quiz questions using AI
    quiz_data = generate_quiz_with_ai(pdf_content)
    
    # Create the quiz
    quiz = LessonQuiz(
        lesson_id=lesson_id,
        title=f"Quiz for {lesson.title}",
        description=f"Test your knowledge of Day {lesson.day_number} material"
    )
    db.session.add(quiz)
    db.session.flush()  # Get the ID without committing
    
    # Create quiz questions
    for i, question_data in enumerate(quiz_data):
        question = QuizQuestion(
            quiz_id=quiz.id,
            question_text=question_data.get("question_text", f"Question {i+1}"),
            question_type="mcq",
            difficulty=random.randint(1, 3),
            explanation=question_data.get("explanation", "")
        )
        db.session.add(question)
        db.session.flush()
        
        # Create options
        options = question_data.get("options", [f"Option A", f"Option B", f"Option C", f"Option D"])
        correct_index = question_data.get("correct_option_index", 0)
        
        for j, option_text in enumerate(options):
            option = QuizOption(
                question_id=question.id,
                option_text=option_text,
                is_correct=(j == correct_index)
            )
            db.session.add(option)
    
    db.session.commit()
    return quiz

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    # Get a list of available courses for the homepage
    courses = Course.query.all()
    return render_template('index.html', courses=courses)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email') 
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    
    return render_template('register.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            print(f"User found: {user.username}, Password Hash: {user.password_hash}")
        
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!')
            # Redirect admin users to admin panel, regular users to dashboard
            if user.is_admin:
                return redirect(url_for('admin_panel'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Update current day based on last activity
    today = datetime.utcnow().date()
    last_active = current_user.last_activity.date()
    
    # Calculate days since last activity
    days_since_last = (today - last_active).days
    
    # Calculate the correct current day based on completed lessons
    total_completed_lessons = UserLessonProgress.query.join(
        UserCourse, UserLessonProgress.user_course_id == UserCourse.id
    ).filter(
        UserCourse.user_id == current_user.id,
        UserLessonProgress.completed == True
    ).count()
    
    # For the specific case where user wants to start with day 2
    if current_user.current_day > 2:
        current_user.current_day = 2
    else:
        # Update current_day to match completed lessons + 1 (for the next day)
        if total_completed_lessons > 0 and total_completed_lessons + 1 > current_user.current_day:
            current_user.current_day = total_completed_lessons + 1
    
    # Check if user completed today's lesson (regardless of days_since_last)
    progress = UserLessonProgress.query.filter(
        UserLessonProgress.user_course_id.in_(
            [uc.id for uc in current_user.enrolled_courses]
        ),
        UserLessonProgress.completion_date >= datetime.utcnow().date()
    ).first()
    
    # Calculate average quiz score
    quiz_scores = UserLessonProgress.query.join(
        UserCourse, UserLessonProgress.user_course_id == UserCourse.id
    ).filter(
        UserCourse.user_id == current_user.id,
        UserLessonProgress.quiz_score.isnot(None)
    ).all()
    
    avg_score = round(sum([score.quiz_score for score in quiz_scores]) / len(quiz_scores), 1) if quiz_scores else 0
    
    # Count rewards
    rewards_count = UserReward.query.filter_by(user_id=current_user.id).count()
    
    # Update progress percentage to 100% if lesson completed
    for enrollment in current_user.enrolled_courses:
        total_lessons = DailyLesson.query.join(Subject).filter(
            Subject.course_id == enrollment.course_id
        ).count()
        
        completed_lessons = UserLessonProgress.query.join(
            UserCourse, UserLessonProgress.user_course_id == UserCourse.id
        ).filter(
            UserCourse.user_id == current_user.id,
            UserCourse.course_id == enrollment.course_id,
            UserLessonProgress.completed == True
        ).count()
        
        if total_lessons > 0:
            # Calculate actual completion percentage
            enrollment.completion_status = (completed_lessons / total_lessons) * 100
            
            # If all lessons for the day are completed, set to 100%
            if completed_lessons == total_lessons:
                enrollment.completion_status = 100.0
                
            # Update user's current day to match actual progress
            if progress and enrollment.current_day < current_user.current_day:
                enrollment.current_day = current_user.current_day
    
    # Update last activity to now
    current_user.last_activity = datetime.utcnow()
    db.session.commit()
    
    # Get enrolled courses
    enrolled_courses = UserCourse.query.filter_by(user_id=current_user.id).all()
    
    # Get progress for each course
    course_progress = []
    for enrollment in enrolled_courses:
        course = Course.query.get(enrollment.course_id)
        
        # Always ensure enrollment.current_day is synced with user's current_day
        # This ensures the day number displayed in the dashboard is accurate
        # Force day to be 2 as requested by user
        enrollment.current_day = 2
        current_user.current_day = 2
        db.session.commit()
            
        # Calculate current subject and lesson
        current_day = enrollment.current_day
        
        # Find which subject this corresponds to
        subjects = Subject.query.filter_by(course_id=course.id).order_by(Subject.order).all()
        
        current_subject = None
        current_lesson = None
        days_counted = 0
        
        for subject in subjects:
            lessons = DailyLesson.query.filter_by(subject_id=subject.id).order_by(DailyLesson.day_number).all()
            
            for lesson in lessons:
                days_counted += 1
                if days_counted == current_day:
                    current_subject = subject
                    current_lesson = lesson
                    break
            
            if current_lesson:
                break
        
        # Calculate overall progress
        total_lessons = 0
        completed_lessons = 0
        
        for subject in subjects:
            lessons = DailyLesson.query.filter_by(subject_id=subject.id).all()
            total_lessons += len(lessons)
            
            for lesson in lessons:
                progress = UserLessonProgress.query.join(UserCourse).filter(
                    UserCourse.id == enrollment.id,
                    UserLessonProgress.lesson_id == lesson.id,
                    UserLessonProgress.completed == True
                ).first()
                
                if progress:
                    completed_lessons += 1
        
        progress_percent = (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        
        course_progress.append({
            'course': course,
            'enrollment': enrollment,
            'current_subject': current_subject,
            'current_lesson': current_lesson,
            'progress_percent': round(progress_percent, 1)
        })
    
    return render_template(
        'dashboard.html',
        enrolled_courses=enrolled_courses,
        course_progress=course_progress,
        total_enrolled_courses=len(enrolled_courses),
        total_completed_lessons=total_completed_lessons,
        avg_quiz_score=avg_score,
        rewards_count=rewards_count
    )
    
    return render_template(
        'dashboard.html',
        enrolled_courses=enrolled_courses,
        course_progress=course_progress
    )

@app.route('/admin')
@login_required
def admin_panel():
    # Check if user is admin
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('dashboard'))
    
    courses = Course.query.all()
    return render_template('admin_panel.html', courses=courses)

@app.route('/admin/courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        duration_weeks = int(request.form.get('duration_weeks', 12))
        
        course = Course(
            title=title,
            description=description,
            category=category,
            duration_weeks=duration_weeks
        )
        
        db.session.add(course)
        db.session.commit()
        
        flash(f'Course "{title}" created successfully')
        return redirect(url_for('manage_courses'))
    
    courses = Course.query.all()
    return render_template('admin_courses.html', courses=courses)

@app.route('/admin/course/<int:course_id>/subjects', methods=['GET', 'POST'])
@login_required
def manage_subjects(course_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('dashboard'))
        
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        order = int(request.form.get('order', 1))
        
        subject = Subject(
            course_id=course_id,
            name=name,
            description=description,
            order=order
        )
        
        db.session.add(subject)
        db.session.commit()
        
        flash(f'Subject "{name}" added to {course.title}')
        return redirect(url_for('manage_subjects', course_id=course_id))
    
    subjects = Subject.query.filter_by(course_id=course_id).order_by(Subject.order).all()
    return render_template('admin_subjects.html', course=course, subjects=subjects)

@app.route('/admin/lesson/<int:lesson_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lesson(lesson_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('dashboard'))
        
    lesson = DailyLesson.query.get_or_404(lesson_id)
    
    if request.method == 'POST':
        lesson.title = request.form.get('title')
        lesson.day_number = int(request.form.get('day_number', 1))
        lesson.content = request.form.get('content')
        lesson.summary = request.form.get('summary')
        lesson.video_url = request.form.get('video_url')
        
        # Handle PDF update if new file provided
        if 'pdf_file' in request.files:
            pdf_file = request.files['pdf_file']
            if pdf_file.filename != '':
                if pdf_file.filename.endswith('.pdf'):
                    filename = secure_filename(f"{lesson.subject.course.title}_{lesson.subject.name}_day{lesson.day_number}_{pdf_file.filename}")
                    pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    pdf_file.save(pdf_path)
                    
                    # Update lesson with new PDF
                    lesson.pdf_path = pdf_path
                    
                    # Extract content and generate summary
                    pdf_content = extract_content_from_pdf(pdf_path)
                    if pdf_content:
                        lesson.content = pdf_content
                        lesson.summary = generate_summary_with_ai(pdf_content)
                        
                        # Delete existing quiz and create new one
                        if lesson.quiz:
                            db.session.delete(lesson.quiz)
                        create_lesson_quiz(lesson.id, pdf_content)
        
        db.session.commit()
        flash('Lesson updated successfully')
        return redirect(url_for('admin_lesson_detail', lesson_id=lesson.id))
    
    return render_template('edit_lesson.html', lesson=lesson)

@app.route('/update_lesson/<int:lesson_id>', methods=['POST'])
@login_required
def update_lesson(lesson_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('dashboard'))
        
    lesson = DailyLesson.query.get_or_404(lesson_id)
    
    lesson.title = request.form.get('title')
    lesson.day_number = int(request.form.get('day_number', 1))
    lesson.content = request.form.get('content')
    lesson.summary = request.form.get('summary')
    lesson.video_url = request.form.get('video_url')
    
    # Handle mind map file upload
    if 'mind_map' in request.files:
        file = request.files['mind_map']
        if file.filename != '':
            # Ensure uploads directory exists
            uploads_dir = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Save file with unique filename
            filename = secure_filename(file.filename)
            unique_filename = f"mind_map_{lesson_id}_{filename}"
            filepath = os.path.join(uploads_dir, unique_filename)
            file.save(filepath)
            
            # Update lesson with new mind map URL
            lesson.mind_map_url = f"/static/uploads/{unique_filename}"
    
    db.session.commit()
    flash('Lesson updated successfully')
    return redirect(url_for('admin_lesson_detail', lesson_id=lesson.id))

@app.route('/admin/lesson/<int:lesson_id>/delete', methods=['POST'])
@login_required
def delete_lesson(lesson_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('dashboard'))
        
    lesson = DailyLesson.query.get_or_404(lesson_id)
    subject_id = lesson.subject_id
    
    # Delete associated quiz and progress records
    if lesson.quiz:
        db.session.delete(lesson.quiz)
    
    # Delete progress records
    UserLessonProgress.query.filter_by(lesson_id=lesson_id).delete()
    
    # Delete lesson
    db.session.delete(lesson)
    db.session.commit()
    
    flash('Lesson deleted successfully')
    return redirect(url_for('manage_lessons', subject_id=subject_id))

@app.route('/admin/subject/<int:subject_id>/lessons', methods=['GET', 'POST'])
@login_required
def manage_lessons(subject_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('dashboard'))
        
    subject = Subject.query.get_or_404(subject_id)
    
    if request.method == 'POST':
        title = request.form.get('title')
        day_number = int(request.form.get('day_number', 1))
        
        # Check if a lesson already exists for this day
        existing_lesson = DailyLesson.query.filter_by(
            subject_id=subject_id,
            day_number=day_number
        ).first()
        
        if existing_lesson:
            flash(f'A lesson for day {day_number} already exists')
            return redirect(url_for('manage_lessons', subject_id=subject_id))
        
        # Handle PDF upload
        if 'pdf_file' not in request.files:
            flash('No PDF file part')
            return redirect(url_for('manage_lessons', subject_id=subject_id))
            
        pdf_file = request.files['pdf_file']
        if pdf_file.filename == '':
            flash('No selected file')
            return redirect(url_for('manage_lessons', subject_id=subject_id))
            
        if pdf_file and pdf_file.filename.endswith('.pdf'):
            filename = secure_filename(f"{subject.course.title}_{subject.name}_day{day_number}_{pdf_file.filename}")
            pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            pdf_file.save(pdf_path)
            
            # Handle mind map upload
            mind_map_path = None
            if 'mind_map' in request.files and request.files['mind_map'].filename != '':
                mind_map_file = request.files['mind_map']
                if mind_map_file and allowed_file(mind_map_file.filename, {'png', 'jpg', 'jpeg'}):
                    mind_map_filename = secure_filename(f"{subject.course.title}_{subject.name}_day{day_number}_mindmap_{mind_map_file.filename}")
                    mind_map_path = os.path.join(app.config['UPLOAD_FOLDER'], mind_map_filename)
                    mind_map_file.save(mind_map_path)
            
            # Get video URL
            video_url = request.form.get('video_url', None)
            
            # Create the lesson
            lesson = DailyLesson(
                subject_id=subject_id,
                day_number=day_number,
                title=title,
                pdf_path=pdf_path,
                mind_map_url=mind_map_path,
                video_url=video_url
            )
            
            db.session.add(lesson)
            db.session.flush()  # Get the ID without committing
            
            # Extract content and generate summary
            pdf_content = extract_content_from_pdf(pdf_path)
            if pdf_content:
                lesson.content = pdf_content
                lesson.summary = generate_summary_with_ai(pdf_content)
                
                # Create a quiz based on content
                create_lesson_quiz(lesson.id, pdf_content)
            
            db.session.commit()
            flash(f'Lesson for day {day_number} created successfully')
            return redirect(url_for('manage_lessons', subject_id=subject_id))
        else:
            flash('Invalid file type. Please upload a PDF file')
    
    lessons = DailyLesson.query.filter_by(subject_id=subject_id).order_by(DailyLesson.day_number).all()
    return render_template('admin_lessons.html', subject=subject, lessons=lessons)

@app.route('/admin/lesson/<int:lesson_id>')
@login_required
def admin_lesson_detail(lesson_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('dashboard'))
        
    lesson = DailyLesson.query.get_or_404(lesson_id)
    quiz = LessonQuiz.query.filter_by(lesson_id=lesson_id).first()
    
    return render_template('admin_lesson_detail.html', lesson=lesson, quiz=quiz)

@app.route('/admin/lesson/<int:lesson_id>')
@login_required
def view_admin_lesson(lesson_id):
    if not current_user.is_admin:
        flash('Access denied: Admin privileges required')
        return redirect(url_for('dashboard'))
        
    lesson = DailyLesson.query.get_or_404(lesson_id)
    quiz = LessonQuiz.query.filter_by(lesson_id=lesson_id).first()
    
    return render_template('admin_lesson_detail.html', lesson=lesson, quiz=quiz)

@app.route('/admin/lesson/<int:lesson_id>/regenerate_quiz', methods=['POST'])
@login_required
def regenerate_quiz(lesson_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
        
    lesson = DailyLesson.query.get_or_404(lesson_id)
    
    # Delete existing quiz if any
    existing_quiz = LessonQuiz.query.filter_by(lesson_id=lesson_id).first()
    if existing_quiz:
        # Delete questions and options
        for question in existing_quiz.questions:
            QuizOption.query.filter_by(question_id=question.id).delete()
        
        QuizQuestion.query.filter_by(quiz_id=existing_quiz.id).delete()
        db.session.delete(existing_quiz)
        db.session.commit()
    
    # Create new quiz
    if lesson.content:
        quiz = create_lesson_quiz(lesson_id, lesson.content)
        if quiz:
            return jsonify({'success': True, 'message': 'Quiz regenerated successfully'})
    
    return jsonify({'success': False, 'message': 'Failed to regenerate quiz'})

@app.route('/courses')
def browse_courses():
    # Show all available courses
    courses = Course.query.all()
    
    # For logged-in users, check enrollment status
    enrolled_course_ids = []
    if current_user.is_authenticated:
        enrolled_course_ids = [uc.course_id for uc in current_user.enrolled_courses]
    
    return render_template('courses.html', courses=courses, enrolled_course_ids=enrolled_course_ids)

@app.route('/course/<int:course_id>')
def view_course(course_id):
    course = Course.query.get_or_404(course_id)
    subjects = Subject.query.filter_by(course_id=course_id).order_by(Subject.order).all()
    
    # Check if user is enrolled
    is_enrolled = False
    enrollment = None
    if current_user.is_authenticated:
        enrollment = UserCourse.query.filter_by(
            user_id=current_user.id,
            course_id=course_id
        ).first()
        is_enrolled = enrollment is not None
    
    # Get total number of lessons
    total_lessons = 0
    for subject in subjects:
        total_lessons += DailyLesson.query.filter_by(subject_id=subject.id).count()
    
    subject_details = []
    for subject in subjects:
        lessons = DailyLesson.query.filter_by(subject_id=subject.id).count()
        subject_details.append({
            'subject': subject,
            'lesson_count': lessons
        })
    
    return render_template(
        'course_detail.html',
        course=course,
        subjects=subject_details,
        is_enrolled=is_enrolled,
        enrollment=enrollment,
        total_lessons=total_lessons
    )

@app.route('/enroll/<int:course_id>', methods=['POST'])
@login_required
def enroll_in_course(course_id):
    # Check if already enrolled
    existing = UserCourse.query.filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first()
    
    if existing:
        return jsonify({'success': False, 'message': 'Already enrolled in this course'})
    
    # Create enrollment
    enrollment = UserCourse(
        user_id=current_user.id,
        course_id=course_id,
        current_day=1,
        completion_status=0.0
    )
    
    db.session.add(enrollment)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Successfully enrolled'})

@app.route('/subject/<int:subject_id>')
def view_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    lessons = DailyLesson.query.filter_by(subject_id=subject_id).order_by(DailyLesson.day_number).all()
    
    # Get chapters related to this subject through materials
    materials = Material.query.filter_by(subject_id=subject_id).all()
    chapters = []
    for material in materials:
        material_chapters = Chapter.query.filter_by(material_id=material.id).order_by(Chapter.chapter_number).all()
        chapters.extend(material_chapters)
    
    # Check if user is enrolled in the parent course
    is_enrolled = False
    enrollment = None
    current_day = 0
    
    if current_user.is_authenticated:
        enrollment = UserCourse.query.filter_by(
            user_id=current_user.id,
            course_id=subject.course_id
        ).first()
        
        if enrollment:
            is_enrolled = True
            current_day = enrollment.current_day
            
            # Calculate if this subject is unlocked based on course progress
            subjects = Subject.query.filter_by(course_id=subject.course_id).order_by(Subject.order).all()
            days_counted = 0
            
            for s in subjects:
                if s.id == subject_id:
                    break
                    
                lessons_count = DailyLesson.query.filter_by(subject_id=s.id).count()
                days_counted += lessons_count
    
    return render_template(
        'subject_detail.html',
        subject=subject,
        lessons=lessons,
        chapters=chapters,
        is_enrolled=is_enrolled,
        enrollment=enrollment,
        current_day=current_day
    )

@app.route('/lesson/<int:lesson_id>')
def view_lesson(lesson_id):
    lesson = DailyLesson.query.get_or_404(lesson_id)
    quiz = LessonQuiz.query.filter_by(lesson_id=lesson_id).first()
    
    # Check if user is enrolled and has access to this lesson
    is_enrolled = False
    has_access = False
    next_lesson = None
    prev_lesson = None
    
    if current_user.is_authenticated:
        enrollment = UserCourse.query.filter_by(
            user_id=current_user.id,
            course_id=lesson.subject.course_id
        ).first()
        
        if enrollment:
            is_enrolled = True
            
            # Calculate days completed in previous subjects
            subjects = Subject.query.filter_by(
                course_id=lesson.subject.course_id
            ).filter(Subject.order < lesson.subject.order).all()
            
            days_before = 0
            for s in subjects:
                days_before += DailyLesson.query.filter_by(subject_id=s.id).count()
            
            # Check if this lesson should be accessible
            lesson_absolute_day = days_before + lesson.day_number
            has_access = enrollment.current_day >= lesson_absolute_day
            
            # Get next and previous lessons for navigation
            prev_lesson = DailyLesson.query.filter_by(
                subject_id=lesson.subject_id,
                day_number=lesson.day_number-1
            ).first()
            
            next_lesson = DailyLesson.query.filter_by(
                subject_id=lesson.subject_id,
                day_number=lesson.day_number+1
            ).first()
            
            # If no previous/next lesson in this subject, check adjacent subjects
            if not prev_lesson and lesson.day_number == 1:
                prev_subject = Subject.query.filter_by(
                    course_id=lesson.subject.course_id,
                    order=lesson.subject.order-1
                ).first()
                
                if prev_subject:
                    last_day = db.session.query(db.func.max(DailyLesson.day_number)).filter_by(
                        subject_id=prev_subject.id
                    ).scalar()
                    
                    if last_day:
                        prev_lesson = DailyLesson.query.filter_by(
                            subject_id=prev_subject.id,
                            day_number=last_day
                        ).first()
            
            if not next_lesson and lesson.day_number == db.session.query(db.func.max(DailyLesson.day_number)).filter_by(
                subject_id=lesson.subject_id
            ).scalar():
                next_subject = Subject.query.filter_by(
                    course_id=lesson.subject.course_id,
                    order=lesson.subject.order+1
                ).first()
                
                if next_subject:
                    next_lesson = DailyLesson.query.filter_by(
                        subject_id=next_subject.id,
                        day_number=1
                    ).first()
    
    # Track user progress if they have access
    progress = None
    if is_enrolled and has_access and enrollment:
        # Get or create progress record
        progress = UserLessonProgress.query.join(UserCourse).filter(
            UserCourse.id == enrollment.id,
            UserLessonProgress.lesson_id == lesson_id
        ).first()
        
        if not progress:
            progress = UserLessonProgress(
                user_course_id=enrollment.id,
                lesson_id=lesson_id,
                completed=False
            )
            db.session.add(progress)
            db.session.commit()
    
    return render_template(
        'lesson_detail.html',
        lesson=lesson,
        quiz=quiz,
        is_enrolled=is_enrolled,
        has_access=has_access,
        progress=progress,
        next_lesson=next_lesson,
        prev_lesson=prev_lesson
    )

@app.route('/subject_details/<int:subject_id>')
@login_required
def subject_details(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    return render_template('subject_detail.html', subject=subject)

@app.route('/take_quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
def take_quiz(quiz_id):
    quiz = LessonQuiz.query.get_or_404(quiz_id)
    lesson = quiz.lesson
    
    # Check if user is enrolled and has access
    enrollment = UserCourse.query.filter_by(
        user_id=current_user.id,
        course_id=lesson.subject.course_id
    ).first()
    
    if not enrollment:
        flash('You are not enrolled in this course')
        return redirect(url_for('view_course', course_id=lesson.subject.course_id))
    
    # Calculate if user has access to this quiz
    subjects = Subject.query.filter_by(
        course_id=lesson.subject.course_id
    ).filter(Subject.order < lesson.subject.order).all()
    
    days_before = 0
    for s in subjects:
        days_before += DailyLesson.query.filter_by(subject_id=s.id).count()
    
    lesson_absolute_day = days_before + lesson.day_number
    has_access = enrollment.current_day >= lesson_absolute_day
    
    if not has_access:
        flash('You have not unlocked this lesson yet')
        return redirect(url_for('view_lesson', lesson_id=lesson.id))
    
    # Handle quiz submission
    if request.method == 'POST':
        score = 0
        total_questions = len(quiz.questions)
        
        for question in quiz.questions:
            selected_option_id = request.form.get(f'question_{question.id}')
            
            if selected_option_id:
                selected_option = QuizOption.query.get(int(selected_option_id))
                if selected_option and selected_option.is_correct:
                    score += 1
        
        # Calculate percentage score
        percentage_score = (score / total_questions) * 100 if total_questions > 0 else 0
        
        # Update user progress
        progress = UserLessonProgress.query.join(UserCourse).filter(
            UserCourse.id == enrollment.id,
            UserLessonProgress.lesson_id == lesson.id
        ).first()
        
        if progress:
            progress.quiz_score = percentage_score
            progress.completed = True
            progress.completion_date = datetime.utcnow()
            
            # Check if this is the current day lesson, if so, increment the day
            if enrollment.current_day == lesson_absolute_day:
                enrollment.current_day += 1
                enrollment.last_activity = datetime.utcnow()
                
                # Update user streak
                yesterday = datetime.utcnow() - timedelta(days=1)
                if current_user.last_activity.date() >= yesterday.date():
                    current_user.streak_count += 1
                else:
                    current_user.streak_count = 1
                
                current_user.last_activity = datetime.utcnow()
            
            # Update the overall course completion percentage
            total_lessons = 0
            completed_lessons = 0
            
            for subject in Subject.query.filter_by(course_id=lesson.subject.course_id).all():
                subject_lessons = DailyLesson.query.filter_by(subject_id=subject.id).all()
                total_lessons += len(subject_lessons)
                
                for subj_lesson in subject_lessons:
                    lesson_progress = UserLessonProgress.query.join(UserCourse).filter(
                        UserCourse.id == enrollment.id,
                        UserLessonProgress.lesson_id == subj_lesson.id,
                        UserLessonProgress.completed == True
                    ).first()
                    
                    if lesson_progress:
                        completed_lessons += 1
            
            if total_lessons > 0:
                enrollment.completion_status = (completed_lessons / total_lessons) * 100
            
            db.session.commit()
            
            flash(f'Quiz completed with score: {percentage_score:.1f}%')
            return redirect(url_for('view_lesson', lesson_id=lesson.id))
    
    return render_template(
        'take_quiz.html',
        quiz=quiz,
        lesson=lesson
    )

@app.route('/mark_lesson_complete/<int:lesson_id>', methods=['POST'])
@login_required
def mark_lesson_complete(lesson_id):
    lesson = DailyLesson.query.get_or_404(lesson_id)
    
    # Check if user is enrolled and has access
    enrollment = UserCourse.query.filter_by(
        user_id=current_user.id,
        course_id=lesson.subject.course_id
    ).first()
    
    if not enrollment:
        return jsonify({'success': False, 'message': 'Not enrolled in this course'})
    
    # Update progress
    progress = UserLessonProgress.query.join(UserCourse).filter(
        UserCourse.id == enrollment.id,
        UserLessonProgress.lesson_id == lesson_id
    ).first()
    
    if progress:
        progress.completed = True
        progress.completion_date = datetime.utcnow()
        
        # Calculate absolute day position
        subjects = Subject.query.filter_by(
            course_id=lesson.subject.course_id
        ).filter(Subject.order < lesson.subject.order).all()
        
        days_before = 0
        for s in subjects:
            days_before += DailyLesson.query.filter_by(subject_id=s.id).count()
        
        lesson_absolute_day = days_before + lesson.day_number
        
        # If this is the current day lesson, increment the day
        if enrollment.current_day == lesson_absolute_day:
            enrollment.current_day += 1
            enrollment.last_activity = datetime.utcnow()
            
            # Update user streak
            yesterday = datetime.utcnow() - timedelta(days=1)
            if current_user.last_activity.date() >= yesterday.date():
                current_user.streak_count += 1
            else:
                current_user.streak_count = 1
            
            current_user.last_activity = datetime.utcnow()
        
        # Update course completion percentage
        total_lessons = 0
        completed_lessons = 0
        
        for subject in Subject.query.filter_by(course_id=lesson.subject.course_id).all():
            subject_lessons = DailyLesson.query.filter_by(subject_id=subject.id).all()
            total_lessons += len(subject_lessons)
            
            for subj_lesson in subject_lessons:
                lesson_progress = UserLessonProgress.query.join(UserCourse).filter(
                    UserCourse.id == enrollment.id,
                    UserLessonProgress.lesson_id == subj_lesson.id,
                    UserLessonProgress.completed == True
                ).first()
                
                if lesson_progress:
                    completed_lessons += 1
        
        if total_lessons > 0:
            enrollment.completion_status = (completed_lessons / total_lessons) * 100
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Lesson marked as complete',
            'next_day': enrollment.current_day
        })
    
    return jsonify({'success': False, 'message': 'Failed to update progress'})

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('query', '')
        
        # Search in courses, subjects, and lessons
        courses = Course.query.filter(Course.title.contains(query) | Course.description.contains(query)).all()
        subjects = Subject.query.filter(Subject.name.contains(query) | Subject.description.contains(query)).all()
        lessons = DailyLesson.query.filter(DailyLesson.title.contains(query) | DailyLesson.content.contains(query)).all()
        
        return render_template(
            'search_results.html',
            query=query,
            courses=courses,
            subjects=subjects,
            lessons=lessons
        )
    
    return render_template('search.html')

@app.route('/api/course_progress/<int:course_id>')
@login_required
def api_course_progress(course_id):
    """API endpoint to get detailed progress for a course"""
    enrollment = UserCourse.query.filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first_or_404()
    
    course = Course.query.get_or_404(course_id)
    subjects = Subject.query.filter_by(course_id=course_id).order_by(Subject.order).all()
    
    progress_data = []
    cumulative_days = 0
    
    for subject in subjects:
        subject_data = {
            'id': subject.id,
            'name': subject.name,
            'lessons': []
        }
        
        lessons = DailyLesson.query.filter_by(subject_id=subject.id).order_by(DailyLesson.day_number).all()
        
        for lesson in lessons:
            cumulative_days += 1
            
            # Get progress for this lesson
            progress = UserLessonProgress.query.join(UserCourse).filter(
                UserCourse.id == enrollment.id,
                UserLessonProgress.lesson_id == lesson.id
            ).first()
            
            is_completed = False
            quiz_score = None
            
            if progress:
                is_completed = progress.completed
                quiz_score = progress.quiz_score
            
            subject_data['lessons'].append({
                'id': lesson.id,
                'day': lesson.day_number,
                'absolute_day': cumulative_days,
                'title': lesson.title,
                'completed': is_completed,
                'quiz_score': quiz_score,
                'unlocked': enrollment.current_day >= cumulative_days
            })
        
        progress_data.append(subject_data)
    
    return jsonify({
        'course_id': course_id,
        'course_title': course.title,
        'current_day': enrollment.current_day,
        'completion_percentage': enrollment.completion_status,
        'subjects': progress_data
    })

# Enhanced functionality for better course and content display

@app.route('/api/extract_pdf_content', methods=['POST'])
@login_required
def api_extract_pdf_content():
    """API endpoint to extract content from PDF for preview"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Admin privileges required'})
    
    if 'pdf_file' not in request.files:
        return jsonify({'success': False, 'message': 'No file part'})
    
    pdf_file = request.files['pdf_file']
    if pdf_file.filename == '':
        return jsonify({'success': False, 'message': 'No selected file'})
    
    if pdf_file and pdf_file.filename.endswith('.pdf'):
        # Save to temp location
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], 'temp_' + secure_filename(pdf_file.filename))
        pdf_file.save(temp_path)
        
        # Extract content
        content = extract_content_from_pdf(temp_path)
        summary = generate_summary_with_ai(content[:5000])  # Limit content for summary preview
        
        # Generate sample quiz (just 2 questions for preview)
        quiz_preview = generate_quiz_with_ai(content[:5000], 2)
        
        # Remove temp file
        try:
            os.remove(temp_path)
        except:
            pass
        
        return jsonify({
            'success': True,
            'content_preview': content[:1000] + ('...' if len(content) > 1000 else ''),
            'summary_preview': summary,
            'quiz_preview': quiz_preview
        })
    
    return jsonify({'success': False, 'message': 'Invalid file type'})

@app.route('/course/<int:course_id>/syllabus')
def course_syllabus(course_id):
    """Display detailed syllabus for a course"""
    course = Course.query.get_or_404(course_id)
    subjects = Subject.query.filter_by(course_id=course_id).order_by(Subject.order).all()
    
    syllabus_data = []
    total_days = 0
    
    for subject in subjects:
        subject_data = {
            'name': subject.name,
            'description': subject.description,
            'lessons': []
        }
        
        lessons = DailyLesson.query.filter_by(subject_id=subject.id).order_by(DailyLesson.day_number).all()
        for lesson in lessons:
            total_days += 1
            subject_data['lessons'].append({
                'day': lesson.day_number,
                'title': lesson.title,
                'has_quiz': LessonQuiz.query.filter_by(lesson_id=lesson.id).first() is not None
            })
        
        syllabus_data.append(subject_data)
    
    # Check if user is enrolled
    is_enrolled = False
    if current_user.is_authenticated:
        is_enrolled = UserCourse.query.filter_by(
            user_id=current_user.id,
            course_id=course_id
        ).first() is not None
    
    return render_template(
        'course_syllabus.html',
        course=course,
        syllabus=syllabus_data,
        total_days=total_days,
        is_enrolled=is_enrolled
    )

@app.route('/my_courses')
@login_required
def my_courses():
    """Show all courses the user is enrolled in with detailed progress"""
    enrollments = UserCourse.query.filter_by(user_id=current_user.id).all()
    
    course_data = []
    for enrollment in enrollments:
        course = Course.query.get(enrollment.course_id)
        
        # Calculate current position
        current_subject = None
        current_lesson = None
        day_count = 0
        
        subjects = Subject.query.filter_by(course_id=course.id).order_by(Subject.order).all()
        for subject in subjects:
            lessons = DailyLesson.query.filter_by(subject_id=subject.id).order_by(DailyLesson.day_number).all()
            
            for lesson in lessons:
                day_count += 1
                if day_count == enrollment.current_day:
                    current_subject = subject
                    current_lesson = lesson
                    break
            
            if current_subject:
                break
        
        # Count total lessons
        total_lessons = 0
        for subject in subjects:
            total_lessons += DailyLesson.query.filter_by(subject_id=subject.id).count()
        
        # Count completed lessons
        completed_lessons = UserLessonProgress.query.join(UserCourse).filter(
            UserCourse.id == enrollment.id,
            UserLessonProgress.completed == True
        ).count()
        
        course_data.append({
            'course': course,
            'enrollment': enrollment,
            'progress_percent': enrollment.completion_status,
            'current_subject': current_subject,
            'current_lesson': current_lesson,
            'completed_lessons': completed_lessons,
            'total_lessons': total_lessons
        })
    
    return render_template('my_courses.html', courses=course_data)

@app.route('/admin/bulk_import_subjects', methods=['GET', 'POST'])
@login_required
def bulk_import_subjects():
    """Allow admin to import multiple subjects at once"""
    if not current_user.is_admin:
        flash('Admin privileges required')
        return redirect(url_for('admin_panel'))
    
    courses = Course.query.all()
    
    if request.method == 'POST':
        course_id = request.form.get('course_id')
        import_method = request.form.get('import_method', 'manual')
        
        if not course_id:
            flash('Please select a course', 'error')
            return redirect(url_for('bulk_import_subjects'))
        
        try:
            if import_method == 'manual':
                subjects_data = request.form.get('subjects_data')
                if not subjects_data:
                    flash('Please enter subjects data', 'error')
                    return redirect(url_for('bulk_import_subjects'))
                
                for line in subjects_data.split('\n'):
                    if line.strip():
                        parts = line.split('|')
                        if len(parts) >= 1:
                            name = parts[0].strip()
                            description = parts[1].strip() if len(parts) > 1 else ""
                            
                            subject = Subject(
                                name=name,
                                description=description,
                                course_id=course_id
                            )
                            db.session.add(subject)
            else:
                if 'pdf_file' not in request.files:
                    flash('No PDF file uploaded', 'error')
                    return redirect(url_for('bulk_import_subjects'))
                
                pdf_file = request.files['pdf_file']
                if pdf_file.filename == '':
                    flash('No selected PDF file', 'error')
                    return redirect(url_for('bulk_import_subjects'))
                
                if pdf_file and pdf_file.filename.endswith('.pdf'):
                    try:
                        filename = secure_filename(f"timetable_{pdf_file.filename}")
                        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        
                        # Ensure upload directory exists
                        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                        
                        pdf_file.save(pdf_path)
                        print(f"PDF saved to: {pdf_path}")
                        
                        subjects = parse_timetable_pdf(pdf_path)
                        if not subjects:
                            flash('Could not extract subjects from timetable PDF. Please ensure the PDF contains a table with Day, Date, Subject columns.', 'error')
                            return redirect(url_for('bulk_import_subjects'))
                        
                        for subject_name in subjects:
                            subject = Subject(
                                name=subject_name,
                                description=f"Subject from timetable: {subject_name}",
                                course_id=course_id
                            )
                            db.session.add(subject)
                    except Exception as e:
                        print(f"Error processing PDF file: {e}")
                        flash(f'Error processing PDF file: {str(e)}', 'error')
                        return redirect(url_for('bulk_import_subjects'))
                else:
                    flash('Invalid file type. Please upload a PDF file', 'error')
                    return redirect(url_for('bulk_import_subjects'))
            
            db.session.commit()
            flash('Subjects imported successfully!', 'success')
            return redirect(url_for('admin_panel'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error importing subjects: {str(e)}', 'error')
            return redirect(url_for('bulk_import_subjects'))
    
    return render_template('admin_bulk_import.html', courses=courses)
        
@app.route('/generate_study_data/<int:lesson_id>', methods=['POST'])
@login_required
def generate_study_data(lesson_id):
    """Generate in-depth study data for a lesson using Gemini AI"""
    lesson = DailyLesson.query.get_or_404(lesson_id)
    
    if not lesson.content:
        flash('No content available to analyze', 'error')
        return redirect(url_for('view_lesson', lesson_id=lesson_id))
    
    try:
        # Create AI prompt for deep analysis
        prompt = f"""
        Analyze the following educational content deeply and provide:
        1. Key concepts and their explanations
        2. Important facts and figures
        3. Potential connections to other topics
        4. Common mistakes or misconceptions
        5. Suggested study techniques for this material
        
        Content:
        {lesson.content}
        """
        
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        response = model.generate_content(prompt, generation_config=generation_config)
        
        # Update lesson with generated study data
        lesson.summary = response.text
        db.session.commit()
        
        flash('Study data generated successfully!', 'success')
    except Exception as e:
        flash(f'Error generating study data: {str(e)}', 'error')
    
    return redirect(url_for('view_lesson', lesson_id=lesson_id))

@app.route('/admin/generate_study_plan/<int:course_id>', methods=['GET', 'POST'])
@login_required
def generate_study_plan(course_id):
    """Generate a study plan for a course using AI"""
    if not current_user.is_admin:
        flash('Admin privileges required')
        return redirect(url_for('dashboard'))
    
    course = Course.query.get_or_404(course_id)
    
    if request.method == 'POST':
        course_duration = int(request.form.get('duration_weeks', 12))
        target_exam = request.form.get('target_exam', '')
        
        # Create AI prompt for study plan
        prompt = f"""
        Create a detailed study plan for a {course.title} course, targeting {target_exam} exam.
        The plan should cover {course_duration} weeks of study.
        
        For each subject, provide:
        1. A descriptive name
        2. A brief description of what this subject covers
        3. The relative importance of this subject for the exam (High/Medium/Low)
        4. Mind Map 
        5. A suggested order in which to study the subjects
        
        Format your response as a JSON array of objects with these fields:
        name, description, importance, order
        
        Course Description: {course.description}
        """
        
        try:
            model = genai.GenerativeModel("gemini-2.0-flash-lite")
            response = model.generate_content(prompt, generation_config=generation_config)
            
            # Parse the response
            text = response.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
                
            study_plan = json.loads(text)
            
            # Create subjects from the plan
            for item in study_plan:
                subject = Subject(
                    course_id=course_id,
                    name=item.get('name'),
                    description=item.get('description'),
                    order=item.get('order', 1)
                )
                db.session.add(subject)
            
            db.session.commit()
            flash(f'Study plan generated with {len(study_plan)} subjects')
            return redirect(url_for('manage_subjects', course_id=course_id))
        
        except Exception as e:
            flash(f'Error generating study plan: {str(e)}')
    
    return render_template('admin_generate_plan.html', course=course)

@app.route('/candidate/daily_study')
@login_required
def daily_study():
    """Show today's recommended study materials for the candidate"""
    # Get all enrolled courses
    enrollments = UserCourse.query.filter_by(user_id=current_user.id).all()
    
    daily_tasks = []
    previous_tasks = []
    
    for enrollment in enrollments:
        course = Course.query.get(enrollment.course_id)
        current_day = enrollment.current_day
        
        # Find which subject and lesson this corresponds to
        subjects = Subject.query.filter_by(course_id=course.id).order_by(Subject.order).all()
        
        current_subject = None
        current_lesson = None
        days_counted = 0
        
        for subject in subjects:
            lessons = DailyLesson.query.filter_by(subject_id=subject.id).order_by(DailyLesson.day_number).all()
            subject_days = len(lessons)
            
            if days_counted + subject_days >= current_day:
                # This is the current subject
                current_subject = subject
                lesson_day = current_day - days_counted
                
                for lesson in lessons:
                    if lesson.day_number == lesson_day:
                        current_lesson = lesson
                        break
                        
                break
                
            days_counted += subject_days
        
        if current_subject and current_lesson:
            # Check if there's a quiz
            quiz = LessonQuiz.query.filter_by(lesson_id=current_lesson.id).first()
            
            # Check if this lesson is completed
            progress = UserLessonProgress.query.join(UserCourse).filter(
                UserCourse.user_id == current_user.id,
                UserLessonProgress.lesson_id == current_lesson.id,
                UserLessonProgress.completed == True
            ).first()
            
            daily_tasks.append({
                'course': course,
                'subject': current_subject,
                'lesson': current_lesson,
                'has_quiz': quiz is not None,
                'quiz': quiz,
                'completed': progress is not None
            })
        
        # Get previously completed lessons (day 1)
        if current_day > 1:
            # Find lessons from day 1
            day1_lessons = []
            days_counted = 0
            
            for subject in subjects:
                lessons = DailyLesson.query.filter_by(subject_id=subject.id).order_by(DailyLesson.day_number).all()
                
                for lesson in lessons:
                    if lesson.day_number == 1 and days_counted == 0:  # Day 1 lesson
                        quiz = LessonQuiz.query.filter_by(lesson_id=lesson.id).first()
                        
                        # Check if this lesson is completed
                        progress = UserLessonProgress.query.join(UserCourse).filter(
                            UserCourse.user_id == current_user.id,
                            UserLessonProgress.lesson_id == lesson.id,
                            UserLessonProgress.completed == True
                        ).first()
                        
                        previous_tasks.append({
                            'course': course,
                            'subject': subject,
                            'lesson': lesson,
                            'has_quiz': quiz is not None,
                            'quiz': quiz,
                            'completed': progress is not None
                        })
                        break
                
                days_counted += len(lessons)
    
    return render_template('daily_study.html', daily_tasks=daily_tasks, previous_tasks=previous_tasks, current_day=current_user.current_day)

@app.route('/statistics')
@login_required
def user_statistics():
    """Show user learning statistics and progress"""
    # Get overall stats
    enrollments = UserCourse.query.filter_by(user_id=current_user.id).all()
    
    total_courses = len(enrollments)
    total_completed_lessons = UserLessonProgress.query.join(UserCourse).filter(
        UserCourse.user_id == current_user.id,
        UserLessonProgress.completed == True
    ).count()
    
    avg_quiz_score = db.session.query(db.func.avg(UserLessonProgress.quiz_score)).join(UserCourse).filter(
        UserCourse.user_id == current_user.id,
        UserLessonProgress.quiz_score.isnot(None)
    ).scalar() or 0
    
    # Get course-specific stats
    course_stats = []
    for enrollment in enrollments:
        course = Course.query.get(enrollment.course_id)
        
        # Calculate days of active study
        study_days = UserLessonProgress.query.join(UserCourse).filter(
            UserCourse.id == enrollment.id,
            UserLessonProgress.completed == True
        ).group_by(db.func.date(UserLessonProgress.completion_date)).count()
        
        # Average quiz score for this course
        course_avg_score = db.session.query(db.func.avg(UserLessonProgress.quiz_score)).join(UserCourse).filter(
            UserCourse.id == enrollment.id,
            UserLessonProgress.quiz_score.isnot(None)
        ).scalar() or 0
        
        course_stats.append({
            'course': course,
            'progress': enrollment.completion_status,
            'study_days': study_days,
            'avg_score': course_avg_score
        })
    
    return render_template(
        'user_statistics.html',
        total_courses=total_courses,
        total_completed_lessons=total_completed_lessons,
        avg_quiz_score=avg_quiz_score,
        streak=current_user.streak_count,
        course_stats=course_stats
    )

# Create DB tables and admin user on first run
def create_tables_and_admin():
    db.create_all()
    
    # Check if admin user exists, if not create one
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@gmail.com',
            is_admin=True
        )
        admin.set_password('admin123')  # Change in production!
        db.session.add(admin)
        db.session.commit()


        # gamification
# Define the models for gamification

# Define streak milestone rewards
STREAK_REWARDS = {
    3: {"name": "3-Day Streak", "description": "Unlocked free mock test for maintaining a 3-day streak!"},
    7: {"name": "7-Day Streak", "description": "Unlocked Mains Strategy Guide for maintaining a 7-day streak!"},
    14: {"name": "14-Day Streak", "description": "Unlocked premium e-book for maintaining a 14-day streak!"},
    30: {"name": "30-Day Streak", "description": "Unlocked free mentor call for maintaining a 30-day streak!"}
}

# Points for different activities
POINTS = {
    'lesson_complete': 10,
    'quiz_complete': 15,
    'perfect_quiz': 25,  # 100% score
    'daily_login': 5,
    'streak_day': 3,
}

# Level thresholds
LEVEL_THRESHOLDS = [0, 100, 250, 500, 1000, 2000, 4000, 8000, 16000, 32000]

@app.route('/rewards')
@login_required
def view_rewards():
    """View all rewards earned by the user"""
    # Access models directly
    
    rewards = UserReward.query.filter_by(user_id=current_user.id).order_by(UserReward.unlocked_date.desc()).all()
    
    # Get user points
    user_points = UserPoints.query.filter_by(user_id=current_user.id).first()
    if not user_points:
        user_points = UserPoints(user_id=current_user.id)
        db.session.add(user_points)
        db.session.commit()
    
    # Calculate next streak milestone
    next_milestone = None
    for milestone in sorted(STREAK_REWARDS.keys()):
        if current_user.streak_count < milestone:
            next_milestone = milestone
            break
    
    # Calculate days to next milestone
    days_to_milestone = next_milestone - current_user.streak_count if next_milestone else 0
    
    # Calculate next level
    next_level_points = LEVEL_THRESHOLDS[user_points.level] if user_points.level < len(LEVEL_THRESHOLDS) else None
    points_needed = next_level_points - user_points.points if next_level_points else 0
    
    return render_template(
        'rewards.html',
        rewards=rewards,
        user_points=user_points,
        streak_count=current_user.streak_count,
        next_milestone=next_milestone,
        days_to_milestone=days_to_milestone,
        points_needed=points_needed,
        level_thresholds=LEVEL_THRESHOLDS
    )

@app.route('/leaderboard')
@login_required
def leaderboard():
    """Show leaderboard of users based on points"""
    # Direct model access instead of using registry
    
    # Get top users by points with rank
    top_users_points = db.session.query(
        UserPoints, 
        User,  # Join with User to get user details
        db.func.row_number().over(order_by=UserPoints.points.desc()).label('rank')
    ).join(
        User, UserPoints.user_id == User.id
    ).order_by(UserPoints.points.desc()).limit(20).all()
    
    # Get top users by streak
    top_users_streak = db.session.query(
        User,
        db.func.row_number().over(order_by=User.streak_count.desc()).label('rank')
    ).order_by(User.streak_count.desc()).limit(20).all()
    
    # Get current user's points record
    current_user_points = UserPoints.query.filter_by(user_id=current_user.id).first()
    
    # Get user's rank for points (with null handling)
    if current_user_points:
        user_points_rank = db.session.query(
            db.func.count(UserPoints.id) + 1
        ).filter(UserPoints.points > current_user_points.points).scalar()
    else:
        user_points_rank = db.session.query(db.func.count(UserPoints.id)).scalar() or 0
    
    # Get user's rank for streak
    user_streak_rank = db.session.query(
        db.func.count(User.id) + 1
    ).filter(User.streak_count > current_user.streak_count).scalar()
    
    # Calculate percentile with proper null handling
    total_users = User.query.count()
    if total_users > 0:
        points_percentile = ((total_users - user_points_rank) / total_users) * 100
        streak_percentile = ((total_users - user_streak_rank) / total_users) * 100
    else:
        points_percentile = 0
        streak_percentile = 0
    
    return render_template(
        'leaderboard.html',
        top_users_points=top_users_points,
        top_users_streak=top_users_streak,
        user_points_rank=user_points_rank,
        user_streak_rank=user_streak_rank,
        points_percentile=round(points_percentile, 1),
        streak_percentile=round(streak_percentile, 1)
    )
@app.route('/claim_reward/<int:reward_id>', methods=['POST'])
@login_required
def claim_reward(reward_id):
    """Claim a reward"""
    # Access models through current_app
    db = current_app.extensions['sqlalchemy'].db
    UserReward = db.session.registry._class_registry.get('UserReward')
    
    reward = db.session.query(UserReward).filter_by(id=reward_id).first_or_404()
    
    if reward.user_id != current_user.id:
        flash('You do not have permission to claim this reward', 'danger')
        return redirect(url_for('gamification.view_rewards'))
    
    if reward.is_claimed:
        flash('This reward has already been claimed', 'warning')
        return redirect(url_for('gamification.view_rewards'))
    
    # Check if reward is expired
    if reward.expiry_date and reward.expiry_date < datetime.utcnow():
        flash('This reward has expired', 'warning')
        return redirect(url_for('gamification.view_rewards'))
    
    # Mark as claimed
    reward.is_claimed = True
    db.session.commit()
    
    flash(f'You have successfully claimed: {reward.reward_name}', 'success')
    return redirect(url_for('gamification.view_rewards'))

@app.route('/progress_calendar')
@login_required
def progress_calendar():
    """Show a calendar view of user's learning progress"""
    # Access models through current_app
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    completed_lessons = UserLessonProgress.query.join(UserCourse).filter(
        UserCourse.user_id == current_user.id,
        UserLessonProgress.completed == True,
        UserLessonProgress.completion_date >= thirty_days_ago
    ).order_by(UserLessonProgress.completion_date).all()
    
    # Group by date
    calendar_data = {}
    for progress in completed_lessons:
        date_str = progress.completion_date.strftime('%Y-%m-%d')
        if date_str not in calendar_data:
            calendar_data[date_str] = []
        calendar_data[date_str].append(progress)
    
    # Get user points data
    user_points = UserPoints.query.filter_by(user_id=current_user.id).first() or \
                 UserPoints(user_id=current_user.id, points=0, level=1)
    
    # Define streak rewards milestones
    streak_rewards = {
        3: {'name': '3-Day Streak', 'description': 'Unlock basic badge'},
        7: {'name': '1-Week Streak', 'description': 'Earn 50 bonus points'},
        14: {'name': '2-Week Streak', 'description': 'Get premium content access'},
        30: {'name': '1-Month Streak', 'description': 'Special achievement badge'}
    }
    
    # Calculate points percentile
    total_users = User.query.count()
    users_with_less_points = UserPoints.query.filter(
        UserPoints.points < user_points.points
    ).count()
    points_percentile = (users_with_less_points / total_users) * 100 if total_users > 0 else 0
    
    return render_template(
        'progress_calendar.html',
        calendar_data=calendar_data,
        streak_count=current_user.streak_count,
        user_points=user_points,
        streak_rewards=streak_rewards
    )

# Helper functions for updating user points and checking for rewards
def update_user_points(user_id, activity_type, quiz_score=None):
    """Update user points based on activity"""
    # Access models through current_app
    db = current_app.extensions['sqlalchemy'].db
    UserPoints = db.session.registry._class_registry.get('UserPoints')
    
    user_points = UserPoints.query.filter_by(user_id=user_id).first()
    
    if not user_points:
        user_points = UserPoints(user_id=user_id)
        db.session.add(user_points)
    
    # Award points based on activity
    points_earned = POINTS.get(activity_type, 0)
    
    # Bonus points for high quiz scores
    if activity_type == 'quiz_complete' and quiz_score:
        if quiz_score >= 90:
            points_earned += 10
        elif quiz_score >= 80:
            points_earned += 5
        
        # Perfect score bonus
        if quiz_score == 100:
            points_earned += POINTS.get('perfect_quiz', 0)
    
    user_points.points += points_earned
    user_points.weekly_points += points_earned
    
    # Check for level up
    if user_points.level < len(LEVEL_THRESHOLDS) - 1 and user_points.points >= LEVEL_THRESHOLDS[user_points.level + 1]:
        user_points.level += 1
        # Create level up reward
        UserReward = db.session.registry._class_registry.get('UserReward')
        level_reward = UserReward(
            user_id=user_id,
            reward_type='level',
            reward_name=f'Level {user_points.level} Achieved',
            description=f'You have reached level {user_points.level}! Keep up the good work!',
            unlocked_date=datetime.utcnow()
        )
        db.session.add(level_reward)
    
    # Reset weekly points if needed
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    if user_points.weekly_reset < one_week_ago:
        user_points.weekly_points = points_earned
        user_points.weekly_reset = datetime.utcnow()
    
    db.session.commit()
    return points_earned

def check_streak_rewards(user):
    """Check if user has earned any streak rewards"""
    # Access models through current_app
    db = current_app.extensions['sqlalchemy'].db
    UserReward = db.session.registry._class_registry.get('UserReward')
    
    for milestone, reward_info in STREAK_REWARDS.items():
        if user.streak_count == milestone:
            # Check if this reward was already given
            existing_reward = UserReward.query.filter_by(
                user_id=user.id,
                reward_type='streak',
                reward_name=reward_info['name']
            ).first()
            
            if not existing_reward:
                # Create new reward
                streak_reward = UserReward(
                    user_id=user.id,
                    reward_type='streak',
                    reward_name=reward_info['name'],
                    description=reward_info['description'],
                    unlocked_date=datetime.utcnow(),
                    expiry_date=datetime.utcnow() + timedelta(days=30)  # Rewards expire after 30 days
                )
                db.session.add(streak_reward)
                db.session.commit()
                return streak_reward
    
    return None
if __name__ == '__main__':
    # Create admin user
    with app.app_context():
        db.create_all()  # Create tables if not exists
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='anant31122000@gmail.com', is_admin=True)
            admin.set_password('Acool@428')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)
