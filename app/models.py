# MultipleFiles/models.py

from datetime import datetime
from . import db
from flask_login import UserMixin

# Many-to-many for Tags
question_tags = db.Table(
    'question_tags',
    db.Column('question_id', db.Integer, db.ForeignKey('question.id')),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'))
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(10), default='user')  # guest/user/admin
    points = db.Column(db.Integer, default=0)
    banned = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(255), nullable=True, default='default.jpg') # NEW: Field for profile picture
    total_upvotes = db.Column(db.Integer, default=0) # NEW: Field for total upvotes received

    questions = db.relationship('Question', backref='user', lazy=True)
    answers = db.relationship('Answer', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

    @property
    def is_admin(self):
        # This property checks if the user has the 'admin' role.
        # It's a convenient way to check admin status without affecting existing functions.
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    answers = db.relationship('Answer', backref='question', lazy=True, cascade="all, delete-orphan")
    tags = db.relationship('Tag', secondary=question_tags, backref=db.backref('questions', lazy='dynamic'))

    def __repr__(self):
        return f'<Question {self.title}>'

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_accepted = db.Column(db.Boolean, default=False)
    # votes_count = db.Column(db.Integer, default=0) # <--- This line was commented out in your provided code,
                                                    #      so no change is needed here.

    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    votes = db.relationship('Vote', backref='answer', lazy=True)

    def __repr__(self):
        return f'<Answer {self.id} for Q{self.question_id}>'

class Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vote_type = db.Column(db.String(10))  # 'up' or 'down'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=False)

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.String(255))
    link = db.Column(db.String(255))
    read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Notification {self.id} to User {self.user_id}>'

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True)

    def __repr__(self):
        return f'<Tag {self.name}>'
