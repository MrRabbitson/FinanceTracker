import pytest
from app import app, db

def test_app_creation(app):
    assert app is not None
    assert app.config['TESTING'] is True

def test_database_creation(app):
    with app.app_context():
        assert 'user' in db.metadata.tables
        assert 'transaction' in db.metadata.tables
        assert 'goal' in db.metadata.tables

def test_app_routes(app):
    with app.test_client() as client:
        response = client.get('/')
        assert response.status_code == 200

        response = client.get('/login')
        assert response.status_code == 200

        response = client.get('/register')
        assert response.status_code == 200

def test_404_handler(app):
    with app.test_client() as client:
        response = client.get('/nonexistent')
        assert response.status_code == 404