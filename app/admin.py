from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import current_user, login_required
from .models import User, Question, Answer, Notification
from . import db
from .forms import BroadcastForm # <--- ADD THIS LINE: Import the BroadcastForm

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def is_admin():
    # Change this line to check the 'role' attribute
    return current_user.is_authenticated and current_user.role == 'admin'


@admin_bp.before_request
def restrict_to_admin():
    if not is_admin():
        flash("Admin access only.")
        return redirect(url_for('main.home'))


@admin_bp.route('/')
def dashboard():
    questions = Question.query.all()
    users = User.query.all()
    return render_template('admin/dashboard.html', questions=questions, users=users)


@admin_bp.route('/ban/<int:user_id>')
def ban_user(user_id):
    user = User.query.get_or_404(user_id)
    # Also update this check to use 'role'
    if user.role == 'admin':
        flash("You cannot ban another admin.")
    else:
        # Assuming 'banned' column in User model is used for banning
        user.banned = True
        db.session.commit()
        flash(f"User {user.username} has been banned.")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/delete_question/<int:question_id>')
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    db.session.delete(question)
    db.session.commit()
    flash("Question deleted.")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/delete_answer/<int:answer_id>')
def delete_answer(answer_id):
    answer = Answer.query.get_or_404(answer_id)
    db.session.delete(answer)
    db.session.commit()
    flash("Answer deleted.")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/announce', methods=['GET', 'POST'])
def announce():
    form = BroadcastForm() # <--- ADD THIS LINE: Instantiate the form
    if form.validate_on_submit(): # <--- MODIFY THIS LINE: Use form.validate_on_submit()
        msg = form.message.data # <--- MODIFY THIS LINE: Get message from form data
        # Filter out banned users for announcements
        users = User.query.filter_by(banned=False).all()
        for u in users:
            notif = Notification(user_id=u.id, message=msg, link="#")
            db.session.add(notif)
        db.session.commit()
        flash("Announcement sent.")
        return redirect(url_for('admin.dashboard'))

    return render_template('admin/announce.html', form=form) # <--- MODIFY THIS LINE: Pass the form to the template
