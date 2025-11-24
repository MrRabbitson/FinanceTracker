import pytest
import json
import os
import tempfile
from app import app as flask_app, db

TEST_CONFIG = {
    "main": {
        "host": "127.0.0.1",
        "port": 5000,
        "ssl_enabled": False,
        "ssl_cert": "",
        "ssl_key": ""
    },
    "ai": {
        "enabled": False,
        "model": "test_model",
        "hf_api_token": "test_token"
    },
    "email": {
        "sender_email": "test@example.com",
        "sender_password": "test_password"
    },
    "secret_key": "test_secret_key"
}

@pytest.fixture(scope='function')
def app():
    original_config = None
    config_path = 'config.json'
    if os.path.exists(config_path):
        with open(config_path) as f:
            original_config = json.load(f)

    with open(config_path, 'w') as f:
        json.dump(TEST_CONFIG, f)

    db_fd, db_path = tempfile.mkstemp()

    flask_app.config['TESTING'] = True
    flask_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    flask_app.config['WTF_CSRF_ENABLED'] = False

    with flask_app.app_context():
        db.create_all()

    yield flask_app

    with flask_app.app_context():
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)
    if original_config:
        with open(config_path, 'w') as f:
            json.dump(original_config, f)
    else:
        os.remove(config_path)

@pytest.fixture(scope='function')
def client(app):
    return app.test_client()