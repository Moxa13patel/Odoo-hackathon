from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import User, Question, Answer, Vote, Tag, Notification
from .forms import LoginForm, RegisterForm, QuestionForm, AnswerForm
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import or_, and_, func # Import func for count

main = Blueprint('main', __name__)


# Authentication
@main.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('Logged in successfully.')
            return redirect(url_for('main.home'))
        flash('Invalid credentials')
    return render_template('login.html', form=form)

@main.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hash_pw = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password_hash=hash_pw)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful.')
        return redirect(url_for('main.login'))
    return render_template('register.html', form=form)

@main.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out.')
    return redirect(url_for('main.home'))

#Home, Search, and Ask Question
@main.route('/')
def home():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search_query', '').strip()
    tag_filter = request.args.get('tag_filter', '').strip()

    # Base query
    query = Question.query

    # Filter by search query
    if search_query:
        query = query.filter(
            (Question.title.ilike(f"%{search_query}%")) |
            (Question.body.ilike(f"%{search_query}%"))
        )

    # Filter by tags (support multiple comma-separated tags)
    if tag_filter:
        tags_to_filter = [tag.strip() for tag in tag_filter.split(',') if tag.strip()]
        if tags_to_filter:
            # This will find questions that have AT LEAST ONE of the specified tags
            query = query.join(Question.tags).filter(Tag.name.in_(tags_to_filter))

    # Order and paginate the questions
    questions = query.order_by(Question.timestamp.desc()).paginate(page=page, per_page=10, error_out=False)

    # Get newest unanswered questions (not filtered, limited to 5)
    unanswered_questions = Question.query \
        .outerjoin(Answer) \
        .group_by(Question.id) \
        .having(func.count(Answer.id) == 0) \
        .order_by(Question.timestamp.desc()) \
        .limit(5) \
        .all()

    return render_template('home.html', questions=questions, unanswered_questions=unanswered_questions,
                           search_query=search_query, tag_filter=tag_filter) # Pass back for form persistence

@main.route('/ask', methods=['GET', 'POST'])
@login_required
def ask_question():
    form = QuestionForm()
    if form.validate_on_submit():
        # Debug print
        print("FORM TITLE:", form.title.data)
        print("FORM DESCRIPTION:", form.description.data)
        print("FORM TAGS:", form.tags.data)

        tag_names = [tag.strip() for tag in form.tags.data.split(',')]
        tags = []
        for name in tag_names:
            tag = Tag.query.filter_by(name=name).first()
            if not tag:
                tag = Tag(name=name)
                db.session.add(tag) # Add new tags to the session
            tags.append(tag)

        question = Question(
            title=form.title.data,
            body=form.description.data,
            user=current_user,
            tags=tags
        )
        db.session.add(question)
        db.session.commit()
        flash('Question posted.')
        return redirect(url_for('main.home'))

    # Also print form.errors if the form fails
    print("FORM ERRORS:", form.errors)
    return render_template('ask_question.html', form=form)


# Question Detail & Answer Posting
@main.route('/question/<int:question_id>', methods=['GET', 'POST'])
def question_detail(question_id):
    question = Question.query.get_or_404(question_id)
    form = AnswerForm()
    if form.validate_on_submit() and current_user.is_authenticated:
        # ADD THIS CHECK: Prevent banned users from answering
        if current_user.banned:
            flash("You are banned and cannot post answers.", "danger") # Added "danger" category for styling
            return redirect(url_for('main.question_detail', question_id=question.id))

        answer = Answer(body=form.body.data, question_id=question.id, user_id=current_user.id)
        db.session.add(answer)
        db.session.commit()

        # Notify question owner
        if question.user_id != current_user.id:
            notif = Notification(
                user_id=question.user_id,
                message=f"{current_user.username} answered your question.",
                link=url_for('main.question_detail', question_id=question.id)
            )
            db.session.add(notif)

        db.session.commit()
        flash("Answer posted.")
        return redirect(url_for('main.question_detail', question_id=question.id))

    # Calculate upvotes and downvotes for each answer
    for answer in question.answers:
        answer.upvotes_count = Vote.query.filter_by(answer_id=answer.id, vote_type='up').count()
        answer.downvotes_count = Vote.query.filter_by(answer_id=answer.id, vote_type='down').count()
        # Changed this line: Now 'display_vote_count' is just the upvotes_count
        answer.display_vote_count = answer.upvotes_count

    return render_template('question_detail.html', question=question, form=form)


#Voting & Accepting Answers
@main.route('/vote/<int:answer_id>/<string:vote_type>')
@login_required
def vote(answer_id, vote_type):
    answer = Answer.query.get_or_404(answer_id)
    question = answer.question # Keep for notification context

    # Prevent users from voting on their own answer.
    if current_user.id == answer.user_id:
        flash("You cannot vote on your own answer.")
        return redirect(request.referrer)

    # Check if user has already voted on this answer
    existing_vote = Vote.query.filter_by(user_id=current_user.id, answer_id=answer_id).first()

    if existing_vote:
        # User is trying to vote the same way again
        if existing_vote.vote_type == vote_type:
            flash(f"You have already {vote_type}voted this answer.")
            return redirect(request.referrer)
        else:
            # User is changing their vote (e.g., from up to down, or down to up)
            # Revert previous vote's impact on points
            if existing_vote.vote_type == 'up':
                answer.user.points -= 10 # Revert points for previous upvote
                answer.user.total_upvotes -= 1 # DECREMENT total_upvotes for previous upvote
            elif existing_vote.vote_type == 'down':
                answer.user.points += 1 # Revert points for previous downvote

            # Update vote type in the Vote record
            existing_vote.vote_type = vote_type
            flash("Your vote has been changed.")
    else:
        # New vote
        vote = Vote(user_id=current_user.id, answer_id=answer_id, vote_type=vote_type)
        db.session.add(vote)
        flash("Vote recorded.")

    # Apply new vote's impact on points
    if vote_type == 'up':
        answer.user.points += 10
        answer.user.total_upvotes += 1 # INCREMENT total_upvotes for new upvote
        # Notify answer owner about upvote
        if answer.user_id != current_user.id:
            notif = Notification(
                user_id=answer.user.id,
                message=f"{current_user.username} upvoted your answer on '{question.title}'.",
                link=url_for('main.question_detail', question_id=question.id)
            )
            db.session.add(notif)
    elif vote_type == 'down':
        answer.user.points -= 1
        # Notify answer owner about downvote
        if answer.user.id != current_user.id:
            notif = Notification(
                user_id=answer.user.id,
                message=f"{current_user.username} downvoted your answer on '{question.title}'.",
                link=url_for('main.question_detail', question_id=question.id)
            )
            db.session.add(notif)

    db.session.commit()
    return redirect(request.referrer)

@main.route('/accept/<int:answer_id>')
@login_required
def accept_answer(answer_id):
    answer = Answer.query.get_or_404(answer_id)
    question = answer.question

    if current_user.id != question.user_id:
        flash("Only the question author can accept an answer.")
        return redirect(request.referrer)

    # Ensure only one answer can be accepted per question
    for ans in question.answers:
        if ans.is_accepted:
            ans.is_accepted = False
            # Deduct points if an already accepted answer is unaccepted
            ans.user.points -= 20 # Revert points from previously accepted answer
            ans.user.total_upvotes -= 1 # DECREMENT total_upvotes for unaccepted answer
            # No need to db.session.add(ans) here, as it's already in the session
            # and will be committed with the rest.

    answer.is_accepted = True
    answer.user.points += 20
    answer.user.total_upvotes += 1 # INCREMENT total_upvotes for accepted answer
    db.session.commit()

    # Notify answer owner about acceptance
    if answer.user.id != current_user.id:
        notif = Notification(
            user_id=answer.user.id,
            message=f"Your answer on '{question.title}' was accepted!",
            link=url_for('main.question_detail', question_id=question.id)
        )
        db.session.add(notif)
        db.session.commit() # Commit again to ensure notification is saved

    flash("Answer accepted.")
    return redirect(url_for('main.question_detail', question_id=question.id))

#Leaderboard
@main.route('/leaderboard')
def leaderboard():
    users = User.query.order_by(User.points.desc()).limit(10).all()
    return render_template('leaderboard.html', users=users)

# Notifications
@main.route('/notifications')
@login_required
def notifications():
    notes = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    for note in notes:
        note.read = True
    db.session.commit()
    return render_template('notifications.html', notifications=notes)

@main.route('/tags')
def tags():
    tags = db.session.query(Tag, func.count(Question.id)) \
                     .join(Tag.questions) \
                     .group_by(Tag.id) \
                     .all()
    return render_template('tags.html', tags=tags)

# User Profile Page
@main.route('/user/<int:user_id>')
def profile(user_id):
    user = User.query.get_or_404(user_id)
    # Get questions asked by the user
    asked_questions = Question.query.filter_by(user_id=user.id).order_by(Question.timestamp.desc()).all()
    # Get answers given by the user
    answered_questions = Answer.query.filter_by(user_id=user.id).order_by(Answer.timestamp.desc()).all()

    # Determine badge based on points
    badge = "Bronze"
    if user.points >= 100:
        badge = "Silver"
    if user.points >= 500:
        badge = "Gold"
    if user.points >= 1000:
        badge = "Platinum"
    if user.points >= 5000:
        badge = "Diamond"

    return render_template('profile.html', user=user, asked_questions=asked_questions, answered_questions=answered_questions, badge=badge)
