import pytest
from app import db, User, Transaction, Goal
from werkzeug.security import generate_password_hash
from datetime import datetime

def test_user_creation(app):
    with app.app_context():
        user = User(username='testuser1', email='test1@example.com', password='hashedpass')
        db.session.add(user)
        db.session.commit()

        assert user.id is not None
        assert user.username == 'testuser1'
        assert user.email == 'test1@example.com'
        assert user.email_verified == False

def test_transaction_creation(app):
    with app.app_context():
        user = User(username='testuser2', email='test2@example.com', password='hashedpass')
        db.session.add(user)
        db.session.commit()

        transaction = Transaction(amount=100.0, category='income', description='Test transaction', user_id=user.id)
        db.session.add(transaction)
        db.session.commit()

        assert transaction.id is not None
        assert transaction.amount == 100.0
        assert transaction.category == 'income'
        assert transaction.user_id == user.id

def test_goal_creation(app):
    with app.app_context():
        user = User(username='testuser3', email='test3@example.com', password='hashedpass')
        db.session.add(user)
        db.session.commit()

        goal = Goal(name='Test Goal', target_amount=1000.0, current_amount=100.0, description='Test goal', user_id=user.id)
        db.session.add(goal)
        db.session.commit()

        assert goal.id is not None
        assert goal.name == 'Test Goal'
        assert goal.target_amount == 1000.0
        assert goal.current_amount == 100.0
        assert goal.user_id == user.id

def test_user_transaction_relationship(app):
    with app.app_context():
        user = User(username='testuser4', email='test4@example.com', password='hashedpass')
        db.session.add(user)
        db.session.commit()

        transaction = Transaction(amount=-50.0, category='food', description='Lunch', user_id=user.id)
        db.session.add(transaction)
        db.session.commit()

        assert transaction.user == user
        assert transaction in user.transactions

def test_user_goal_relationship(app):
    with app.app_context():
        user = User(username='testuser5', email='test5@example.com', password='hashedpass')
        db.session.add(user)
        db.session.commit()

        goal = Goal(name='Vacation', target_amount=5000.0, user_id=user.id)
        db.session.add(goal)
        db.session.commit()

        assert goal.user == user
        assert goal in user.goals

def test_transaction_date_default(app):
    with app.app_context():
        user = User(username='testuser6', email='test6@example.com', password='hashedpass')
        db.session.add(user)
        db.session.commit()

        before = datetime.utcnow()
        transaction = Transaction(amount=200.0, category='income', user_id=user.id)
        db.session.add(transaction)
        db.session.commit()
        after = datetime.utcnow()

        assert before <= transaction.date <= after

def test_goal_progress_calculation(app):
    with app.app_context():
        user = User(username='testuser7', email='test7@example.com', password='hashedpass')
        db.session.add(user)
        db.session.commit()

        goal = Goal(name='Car', target_amount=10000.0, current_amount=2500.0, user_id=user.id)
        db.session.add(goal)
        db.session.commit()

        assert goal.current_amount / goal.target_amount == 0.25