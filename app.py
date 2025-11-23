from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import or_
from wtforms import StringField, PasswordField, FloatField, SelectField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
from datetime import datetime
import requests
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
from ai_module import generate_response, init_client

with open('config.json') as f:
    config = json.load(f)

init_client(config['ai']['hf_api_token'], config['ai']['model'])

def send_verification_email(user_email, verification_code):
    sender_email = config['email']['sender_email']
    sender_password = config['email']['sender_password']

    message = MIMEMultipart("alternative")
    message["Subject"] = "Подтверждение email адреса"
    message["From"] = sender_email
    message["To"] = user_email

    html = f"""
    <html>
    <body>
        <h2>Подтверждение регистрации</h2>
        <p>Ваш код подтверждения: <strong>{verification_code}</strong></p>
        <p>Введите этот код на сайте для завершения регистрации.</p>
    </body>
    </html>
    """

    part = MIMEText(html, "html")
    message.attach(part)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, user_email, message.as_string())

app = Flask(__name__)
app.config['SECRET_KEY'] = config['secret_key']
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance_tracker.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Вам нужно войти для просмотра этой страницы'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(6), nullable=True)
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    goals = db.relationship('Goal', backref='user', lazy=True)

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    target_amount = db.Column(db.Float, nullable=False)
    current_amount = db.Column(db.Float, default=0)
    description = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

CATEGORY_TRANSLATIONS = {
    'income': 'Доход',
    'food': 'Еда',
    'transport': 'Транспорт',
    'entertainment': 'Развлечения',
    'utilities': 'Коммунальные услуги',
    'other': 'Другое'
}

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(message='Это поле обязательно для заполнения.'), Length(min=2, max=20, message='Имя пользователя должно содержать от 2 до 20 символов.')])
    email = StringField('Email', validators=[DataRequired(message='Это поле обязательно для заполнения.'), Email(message='Введите корректный email адрес.')])
    password = PasswordField('Пароль', validators=[DataRequired(message='Это поле обязательно для заполнения.'), Length(min=6, message='Пароль должен содержать минимум 6 символов.')])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(message='Это поле обязательно для заполнения.'), EqualTo('password', message='Пароли должны совпадать.')])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(message='Это поле обязательно для заполнения.'), Email(message='Введите корректный email адрес.')])
    password = PasswordField('Пароль', validators=[DataRequired(message='Это поле обязательно для заполнения.')])
    submit = SubmitField('Войти')

class TransactionForm(FlaskForm):
    amount = FloatField('Сумма', validators=[DataRequired(message='Введите сумму.'), NumberRange(min=0, message='Сумма должна быть положительной.')])
    type = SelectField('Тип', choices=[
        ('income', 'Доход'),
        ('expense', 'Расход')
    ], validators=[DataRequired(message='Выберите тип.')])
    subcategory = SelectField('Категория расхода', choices=[
        ('food', 'Еда'),
        ('transport', 'Транспорт'),
        ('entertainment', 'Развлечения'),
        ('utilities', 'Коммунальные услуги'),
        ('other', 'Другое')
    ])
    description = TextAreaField('Описание')
    submit = SubmitField('Добавить')

class GoalForm(FlaskForm):
    name = StringField('Название цели', validators=[DataRequired(message='Введите название цели.')])
    target_amount = FloatField('Целевая сумма', validators=[DataRequired(message='Введите целевую сумму.'), NumberRange(min=0, message='Сумма должна быть положительной.')])
    current_amount = FloatField('Текущая сумма', validators=[NumberRange(min=0, message='Сумма должна быть положительной.')], default=0)
    description = TextAreaField('Описание')
    submit = SubmitField('Добавить цель')

class VerifyEmailForm(FlaskForm):
    code = StringField('Код подтверждения', validators=[DataRequired(message='Введите код.')])
    submit = SubmitField('Подтвердить')

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter(
            or_(User.email == form.email.data, User.username == form.username.data)
        ).first()
        if existing_user:
            if existing_user.email == form.email.data:
                flash('Аккаунт с таким email уже существует.', 'danger')
            else:
                flash('Имя пользователя уже занято.', 'danger')
            return render_template('register.html', form=form)
        hashed_password = generate_password_hash(form.password.data)
        verification_code = secrets.token_hex(3).upper()
        user = User(username=form.username.data, email=form.email.data, password=hashed_password, verification_code=verification_code)
        db.session.add(user)
        db.session.commit()
        try:
            send_verification_email(user.email, verification_code)
            flash('Аккаунт создан! Проверьте email для подтверждения.', 'success')
            return redirect(url_for('verify_email', user_id=user.id))
        except Exception as e:
            db.session.delete(user)
            db.session.commit()
            flash('Ошибка отправки email. Попробуйте позже.', 'danger')
    return render_template('register.html', form=form)

@app.route('/verify_email/<int:user_id>', methods=['GET', 'POST'])
def verify_email(user_id):
    user = User.query.get_or_404(user_id)
    if user.email_verified:
        flash('Email уже подтвержден.', 'info')
        return redirect(url_for('login'))
    form = VerifyEmailForm()
    if form.validate_on_submit():
        if form.code.data.upper() == user.verification_code:
            user.email_verified = True
            user.verification_code = None
            db.session.commit()
            flash('Email подтвержден! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Неверный код.', 'danger')
    return render_template('verify_email.html', form=form, user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            if not user.email_verified:
                flash('Подтвердите email перед входом.', 'warning')
                return redirect(url_for('verify_email', user_id=user.id))
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный email или пароль.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    global CATEGORY_MAPPING
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    goals = Goal.query.filter_by(user_id=current_user.id).all()
    
    balance = sum(t.amount for t in transactions)
    df = pd.DataFrame([(t.amount, t.category) for t in transactions if t.amount < 0], columns=['amount', 'category'])
    if not df.empty:
        CATEGORY_MAPPING = {
            'income': 'Доход',
            'food': 'Еда', 
            'transport': 'Транспорт',
            'entertainment': 'Развлечения',
            'utilities': 'Коммунальные услуги',
            'other': 'Другое'
        }


        _category_spending = df.groupby('category')['amount'].sum().abs().to_dict()
        category_spending = {CATEGORY_MAPPING[k]: v for k, v in _category_spending.items()}
    else:
        category_spending = {}

    for goal in goals:
        progress = (goal.current_amount / goal.target_amount * 100) if goal.target_amount > 0 else 0
        goal.progress_percent = min(int(progress), 100)
        goal.is_completed = goal.current_amount >= goal.target_amount
    CATEGORY_MAPPING = {
        'income': 'Доход',
        'food': 'Еда',
        'transport': 'Транспорт',
        'entertainment': 'Развлечения',
        'utilities': 'Коммунальные услуги',
        'other': 'Другое'
    }
    return render_template('dashboard.html', transactions=transactions, goals=goals, balance=balance, category_spending=category_spending, category_mapping=CATEGORY_MAPPING)

@app.route('/add_transaction', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    if request.method == 'POST':
        if form.type.data == 'expense' and not form.subcategory.data:
            form.subcategory.errors.append('Выберите категорию.')
        elif form.validate_on_submit():
            if form.type.data == 'income':
                amount = form.amount.data
                category = 'income'
            else:
                amount = -form.amount.data
                category = form.subcategory.data
            transaction = Transaction(
                amount=amount,
                category=category,
                description=form.description.data,
                user_id=current_user.id
            )
            db.session.add(transaction)
            db.session.commit()
            if category == 'income':
                goals = Goal.query.filter_by(user_id=current_user.id).all()
                if goals:
                    income_amount = transaction.amount
                    for goal in goals:
                        goal.current_amount += income_amount
                    db.session.commit()
            flash('Транзакция добавлена!', 'success')
            return redirect(url_for('dashboard'))
    return render_template('add_transaction.html', form=form)

@app.route('/add_goal', methods=['GET', 'POST'])
@login_required
def add_goal():
    form = GoalForm()
    if form.validate_on_submit():
        goal = Goal(
            name=form.name.data,
            target_amount=form.target_amount.data,
            current_amount=form.current_amount.data,
            description=form.description.data,
            user_id=current_user.id
        )
        db.session.add(goal)
        db.session.commit()
        flash('Цель добавлена!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_goal.html', form=form)

@app.route('/edit_transaction/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        abort(403)
    form = TransactionForm()
    if request.method == 'POST':
        if form.type.data == 'expense' and not form.subcategory.data:
            form.subcategory.errors.append('Выберите категорию.')
        elif form.validate_on_submit():
            if form.type.data == 'income':
                amount = form.amount.data
                category = 'income'
            else:
                amount = -form.amount.data
                category = form.subcategory.data
            transaction.amount = amount
            transaction.category = category
            transaction.description = form.description.data
            db.session.commit()
            flash('Транзакция обновлена!', 'success')
            return redirect(url_for('dashboard'))
    else:
        if transaction.amount > 0:
            form.type.data = 'income'
            form.amount.data = transaction.amount
        else:
            form.type.data = 'expense'
            form.amount.data = -transaction.amount
            form.subcategory.data = transaction.category
        form.description.data = transaction.description
    return render_template('edit_transaction.html', form=form)

@app.route('/delete_transaction/<int:id>', methods=['POST'])
@login_required
def delete_transaction(id):
    transaction = Transaction.query.get_or_404(id)
    if transaction.user_id != current_user.id:
        abort(403)
    db.session.delete(transaction)
    db.session.commit()
    flash('Транзакция удалена!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/edit_goal/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_goal(id):
    goal = Goal.query.get_or_404(id)
    if goal.user_id != current_user.id:
        abort(403)
    form = GoalForm()
    if form.validate_on_submit():
        goal.name = form.name.data
        goal.target_amount = form.target_amount.data
        goal.current_amount = form.current_amount.data
        goal.description = form.description.data
        db.session.commit()
        flash('Цель обновлена!', 'success')
        return redirect(url_for('dashboard'))
    else:
        form.name.data = goal.name
        form.target_amount.data = goal.target_amount
        form.current_amount.data = goal.current_amount
        form.description.data = goal.description
    return render_template('edit_goal.html', form=form)

@app.route('/delete_goal/<int:id>', methods=['POST'])
@login_required
def delete_goal(id):
    goal = Goal.query.get_or_404(id)
    if goal.user_id != current_user.id:
        abort(403)
    db.session.delete(goal)
    db.session.commit()
    flash('Цель удалена!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/analytics')
@login_required
def analytics():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    
    df = pd.DataFrame([(t.amount, t.category, t.date) for t in transactions], columns=['amount', 'category', 'date'])
    df['date'] = pd.to_datetime(df['date'])
    spending_df = df[df['amount'] < 0]
    if not spending_df.empty:
        

        CATEGORY_MAPPING = {
            'income': 'Доход',
            'food': 'Еда',
            'transport': 'Транспорт', 
            'entertainment': 'Развлечения',
            'utilities': 'Коммунальные услуги',
            'other': 'Другое'
        }

        spending_by_category = spending_df.groupby('category')['amount'].sum().abs().rename(index=CATEGORY_MAPPING)
        monthly_spending = spending_df.groupby(spending_df['date'].dt.to_period('M'))['amount'].sum().abs()
        monthly_spending = monthly_spending.rename(lambda x: str(x))
        top_category = spending_by_category.idxmax()
    else:
        spending_by_category = pd.Series(dtype=float)
        monthly_spending = pd.Series(dtype=float)
        top_category = None
    advice = []
    if top_category:
        advice.append(f"Вы тратите больше всего на {top_category}. Попробуйте сократить расходы в этой категории.")
    if df['amount'].sum() < 0:
        advice.append("Ваши расходы превышают доходы. Рассмотрите возможность увеличения доходов или сокращения расходов.")

    return render_template('analytics.html',
                         spending_by_category=spending_by_category.to_dict(),
                         monthly_spending=monthly_spending.to_dict(),
                         advice=advice)

@app.route('/get_ai_tips')
@login_required
def get_ai_tips():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    df = pd.DataFrame([(t.amount, t.category, t.date) for t in transactions], columns=['amount', 'category', 'date'])
    balance = df['amount'].sum() if not df.empty else 0
    transactions_list = "\n".join([
        f"{t.date.strftime('%Y-%m-%d')}: {t.amount} руб, категория: {CATEGORY_TRANSLATIONS.get(t.category, t.category)}, описание: {t.description or 'нет'}"
        for t in transactions
    ])
    goals = Goal.query.filter_by(user_id=current_user.id).all()
    goals_list = "\n".join([f"Цель: {g.name}, цель: {g.target_amount} руб, текущая: {g.current_amount} руб, описание: {g.description or 'нет'}" for g in goals])
    top_spending_summary = "Нет данных о расходах."
    spending_breakdown = "Расходы по категориям отсутствуют."
    if not df.empty:
        spending_df = df[df['amount'] < 0]
        if not spending_df.empty:
            category_totals = spending_df.groupby('category')['amount'].sum().abs().to_dict()
            if category_totals:
                top_category_key = max(category_totals, key=category_totals.get)
                top_spending_summary = (
                    f"Больше всего пользователь тратит на {CATEGORY_TRANSLATIONS.get(top_category_key, top_category_key)}: "
                    f"{category_totals[top_category_key]:.2f} руб."
                )
                spending_lines = [
                    f"{CATEGORY_TRANSLATIONS.get(cat, cat)}: {amount:.2f} руб"
                    for cat, amount in category_totals.items()
                ]
                spending_breakdown = "\n".join(spending_lines)
    prompt = (
        "На основе финансовых данных пользователя предоставь персонализированные советы по управлению деньгами. "
        "Обязательно укажи, на что пользователь тратит больше всего, и предложи конкретные способы сократить расходы по этой категории. "
        "Будь краток, дай 3-5 советов. Отвечай на русском языке. Не используй смайлы или эмодзи в ответе. "
        f"Пользователь имеет баланс: {balance} руб.\n"
        f"{top_spending_summary}\n"
        "Расходы по категориям:\n"
        f"{spending_breakdown}\n"
        "Транзакции:\n"
        f"{transactions_list or 'Нет транзакций.'}\n"
        "Цели:\n"
        f"{goals_list or 'Нет целей.'}"
    )
    try:
        ai_tips = generate_response(prompt)
    except Exception as e:
        ai_tips = "Не удалось получить советы от ИИ."
    return {'tips': ai_tips}

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    return send_from_directory('assets', filename)

@app.route('/chat', methods=['POST'])
def chat():
    if not config['ai'].get('enabled', True):
        return {'message': "ИИ отключен в конфигурации."}
    data = request.get_json()
    user_message = data['message']
    current_page = data.get('page', '/')
    user_data_context = "Данные пользователя:\n"
    if current_user.is_authenticated:
        transactions = Transaction.query.filter_by(user_id=current_user.id).all()
        goals = Goal.query.filter_by(user_id=current_user.id).all()
        balance = sum(t.amount for t in transactions)
        transactions_list = "\n".join([
            f"{t.date.strftime('%Y-%m-%d')}: {t.amount} руб, категория: {CATEGORY_TRANSLATIONS.get(t.category, t.category)}, описание: {t.description or 'нет'}"
            for t in transactions
        ]) or "Транзакции отсутствуют."
        goals_list = "\n".join([
            f"Цель: {g.name}, целевая сумма: {g.target_amount} руб, текущая: {g.current_amount} руб, описание: {g.description or 'нет'}"
            for g in goals
        ]) or "Цели отсутствуют."
        user_data_context += (
            f"- Баланс: {balance} руб.\n"
            f"- Количество транзакций: {len(transactions)}\n"
            f"- Количество целей: {len(goals)}\n"
            f"- Email подтвержден: {'да' if current_user.email_verified else 'нет'}\n"
            f"Транзакции:\n{transactions_list}\n"
            f"Цели:\n{goals_list}\n"
        )
    else:
        user_data_context += "Пользователь не авторизован, персональные данные недоступны.\n"
    system_content = """Ты - помощник по сайту финансового трекера. Отвечай на вопросы пользователей о сайте на русском языке максимально лаконично.

Описание сайта:
- Главная страница (/): Приветствие, кнопки Войти или Зарегистрироваться.
- Регистрация (/register): Форма с полями: имя пользователя, email, пароль, подтверждение пароля.
- Вход (/login): Форма с полями: email, пароль.
- Панель (/dashboard): После входа. Показывает баланс, последние транзакции, расходы по категориям (диаграмма), финансовые цели с прогрессом.
- Добавить транзакцию (/add_transaction): Форма с типом (доход/расход), суммой, категорией расхода (если расход), описанием.
- Добавить цель (/add_goal): Форма с названием, целевой суммой, текущей суммой, описанием.
- Аналитика (/analytics): Диаграммы расходов по категориям и по месяцам, советы по экономии.
- Переключение темы: Кнопка в шапке для темной/светлой темы.

Инструкции: Отвечай максимально лаконично, помогай с навигацией и использованием сайта. Учитывай текущую страницу пользователя."""
    prompt = f"{system_content}\n\n{user_data_context}\nТекущая страница: {current_page}\nВопрос: {user_message}"
    try:
        bot_message = generate_response(prompt)
        return {'message': bot_message}
    except Exception as e:
        print(f"AI Error: {e}")
        return {'message': "Ошибка ИИ. Попробуйте позже."}

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
