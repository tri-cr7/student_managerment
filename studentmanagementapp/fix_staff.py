from studentapp import create_app  # Adjust if your app factory function has a different name
from studentapp.extensions import db
from studentapp.models.user import User, UserRoleEnum

# Create the app instance to load config and database connection
app = create_app()
if __name__ == "__main__":
    with app.app_context():
        # Look for staff01
        user = User.query.filter_by(username='staff01').first()

        if not user:
            print("staff01 not found, creating a new one...")
            user = User(
                username='staff01',
                email='staff01@school.local',
                full_name='Nguyen Van Staff',
                role=UserRoleEnum.STAFF,
                is_active=True,
                is_locked=False
            )
            db.session.add(user)
        else:
            print("staff01 found, updating password...")

        # Safely hash 'password123' using the model's native bcrypt method
        user.set_password('password123')
        db.session.commit()

        print("SUCCESS: Password updated and committed to the database!")