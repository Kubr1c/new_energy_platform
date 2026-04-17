from flask import Flask
from models.database import db
from config import Config
from sqlalchemy import text

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

with app.app_context():
    try:
        with db.engine.connect() as conn:
            # Check if column exists
            result = conn.execute(text("SHOW COLUMNS FROM predict_result LIKE 'model_type'"))
            if not result.fetchone():
                print("Adding 'model_type' column to 'predict_result' table...")
                conn.execute(text("ALTER TABLE predict_result ADD COLUMN model_type VARCHAR(30) DEFAULT 'attention_lstm'"))
                print("Column added successfully.")
            else:
                print("'model_type' column already exists in 'predict_result'.")
    except Exception as e:
        print(f"Error upgrading database: {e}")
