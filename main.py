from app import app, db
import json

with open('config.json') as f:
    config = json.load(f)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    main_config = config['main']
    if main_config.get('ssl_enabled', False):
        ssl_context = (main_config['ssl_cert'], main_config['ssl_key'])
        app.run(debug=True, host=main_config['host'], port=main_config['port'], ssl_context=ssl_context)
    else:
        app.run(debug=True, host=main_config['host'], port=main_config['port'])