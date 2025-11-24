import pytest
from app import db
from app import User, Transaction, Goal
from werkzeug.security import generate_password_hash
from flask_login import login_user

def test_index_route(client):
    response = client.get('/')
    assert response.status_code == 200
    assert b'Finance Tracker' in response.data or b'index' in response.data.lower()

def test_register_route_get(client):
    response = client.get('/register')
    assert response.status_code == 200
    assert b'register' in response.data.lower()

def test_register_route_post_success(client, app, monkeypatch):
    def mock_send_email(*args, **kwargs):
        pass

    monkeypatch.setattr('app.send_verification_email', mock_send_email)

    with app.app_context():
        data = {
            'username': 'testuser8',
            'email': 'test8@example.com',
            'password': 'password123',
            'confirm_password': 'password123'
        }
        response = client.post('/register', data=data, follow_redirects=True)
        assert response.status_code == 200
        user = User.query.filter_by(email='test8@example.com').first()
        assert user is not None
        assert user.username == 'testuser8'

def test_login_route_get(client):
    response = client.get('/login')
    assert response.status_code == 200
    assert b'login' in response.data.lower()

def test_login_route_post_success(client, app):
    with app.app_context():
        hashed_password = generate_password_hash('password123')
        user = User(username='testuser9', email='test9@example.com', password=hashed_password, email_verified=True)
        db.session.add(user)
        db.session.commit()

        data = {
            'email': 'test9@example.com',
            'password': 'password123'
        }
        response = client.post('/login', data=data, follow_redirects=True)
        assert response.status_code == 200
        assert b'dashboard' in response.data.lower()

def test_dashboard_route_requires_login(client):
    response = client.get('/dashboard', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower()

def test_add_transaction_route_requires_login(client):
    response = client.get('/add_transaction', follow_redirects=True)
    assert response.status_code == 200
    assert b'login' in response.data.lower()

def test_add_transaction_post_success(client, app):
    with app.app_context():
        hashed_password = generate_password_hash('password123')
        user = User(username='testuser10', email='test10@example.com', password=hashed_password, email_verified=True)
        db.session.add(user)
        db.session.commit()

        with client:
            client.post('/login', data={'email': 'test10@example.com', 'password': 'password123'}, follow_redirects=True)
            data = {
                'amount': '100',
                'type': 'income',
                'subcategory': 'food',
                'description': 'Test income'
            }
            response = client.post('/add_transaction', data=data, follow_redirects=True)
            assert response.status_code == 200
            transaction = Transaction.query.filter_by(user_id=user.id).first()
            assert transaction is not None
            assert transaction.amount == 100

def test_analytics_route(client, app):
    with app.app_context():
        hashed_password = generate_password_hash('password123')
        user = User(username='testuser11', email='test11@example.com', password=hashed_password, email_verified=True)
        db.session.add(user)
        db.session.commit()

        with client:
            client.post('/login', data={'email': 'test11@example.com', 'password': 'password123'})
            response = client.get('/analytics')
            assert response.status_code == 200
            assert b'analytics' in response.data.lower()

def test_404_route(client):
    response = client.get('/nonexistent')
    assert response.status_code == 404