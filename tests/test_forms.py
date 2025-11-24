import pytest
from app import RegistrationForm, LoginForm, TransactionForm, GoalForm, VerifyEmailForm

def test_registration_form_valid(app):
    with app.app_context():
        form = RegistrationForm()
        form.username.data = 'testuser'
        form.email.data = 'test@example.com'
        form.password.data = 'password123'
        form.confirm_password.data = 'password123'

        assert form.validate() == True

def test_registration_form_invalid_username(app):
    with app.app_context():
        form = RegistrationForm()
        form.username.data = 'u'
        form.email.data = 'test@example.com'
        form.password.data = 'password123'
        form.confirm_password.data = 'password123'

        assert form.validate() == False
        assert 'Имя пользователя должно содержать от 2 до 20 символов.' in str(form.username.errors)

def test_registration_form_invalid_email(app):
    with app.app_context():
        form = RegistrationForm()
        form.username.data = 'testuser'
        form.email.data = 'invalid-email'
        form.password.data = 'password123'
        form.confirm_password.data = 'password123'

        assert form.validate() == False
        assert 'Введите корректный email адрес.' in str(form.email.errors)

def test_registration_form_password_mismatch(app):
    with app.app_context():
        form = RegistrationForm()
        form.username.data = 'testuser'
        form.email.data = 'test@example.com'
        form.password.data = 'password123'
        form.confirm_password.data = 'differentpassword'

        assert form.validate() == False
        assert 'Пароли должны совпадать.' in str(form.confirm_password.errors)

def test_login_form_valid(app):
    with app.app_context():
        form = LoginForm()
        form.email.data = 'test@example.com'
        form.password.data = 'password123'

        assert form.validate() == True

def test_login_form_invalid_email(app):
    with app.app_context():
        form = LoginForm()
        form.email.data = 'invalid-email'
        form.password.data = 'password123'

        assert form.validate() == False

def test_transaction_form_income_valid(app):
    with app.app_context():
        form = TransactionForm()
        form.amount.data = 100.0
        form.type.data = 'income'
        form.subcategory.data = 'food'
        form.description.data = 'Salary'

        assert form.validate() == True

def test_transaction_form_expense_valid(app):
    with app.app_context():
        form = TransactionForm()
        form.amount.data = 50.0
        form.type.data = 'expense'
        form.subcategory.data = 'food'
        form.description.data = 'Lunch'

        assert form.validate() == True

def test_transaction_form_expense_missing_category(app):
    with app.app_context():
        form = TransactionForm()
        form.amount.data = 50.0
        form.type.data = 'expense'
        form.description.data = 'Lunch'

        assert form.validate() == False

def test_transaction_form_negative_amount(app):
    with app.app_context():
        form = TransactionForm()
        form.amount.data = -10.0
        form.type.data = 'income'
        form.description.data = 'Invalid'

        assert form.validate() == False
        assert 'Сумма должна быть положительной.' in str(form.amount.errors)

def test_goal_form_valid(app):
    with app.app_context():
        form = GoalForm()
        form.name.data = 'New Car'
        form.target_amount.data = 20000.0
        form.current_amount.data = 5000.0
        form.description.data = 'Save for car'

        assert form.validate() == True

def test_goal_form_invalid_name(app):
    with app.app_context():
        form = GoalForm()
        form.name.data = ''
        form.target_amount.data = 1000.0

        assert form.validate() == False

def test_verify_email_form_valid(app):
    with app.app_context():
        form = VerifyEmailForm()
        form.code.data = 'ABC123'

        assert form.validate() == True

def test_verify_email_form_empty(app):
    with app.app_context():
        form = VerifyEmailForm()
        form.code.data = ''

        assert form.validate() == False