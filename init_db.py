from app import app, db, User
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize database with tables and admin user"""
    with app.app_context():
        # Drop all tables and recreate (for development only)
        db.drop_all()
        db.create_all()
        
        # Create admin user
        admin = User(
            email='tetr48740@gmail.com',
            password_hash=generate_password_hash('123456'),
            is_verified=True,
            is_admin=True
        )
        
        db.session.add(admin)
        db.session.commit()
        
        print("Database initialized successfully!")
        print("Admin user created: tetr48740@gmail.com / 123456")

if __name__ == '__main__':
    init_database()
