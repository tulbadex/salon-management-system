from datetime import datetime, timedelta
from models import User, Customer, Hairstyle, Appointment, Expense


def initialize_database(db):
    """Initialize the database with sample data"""
    try:

        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Created admin user")

        # Create staff user if not exists
        if not User.query.filter_by(username='staff').first():
            staff = User(username='staff', role='staff')
            staff.set_password('staff123')
            db.session.add(staff)
            db.session.commit()
            print("Created staff user")

        # Add sample hairstyles if none exist
        if not Hairstyle.query.first():
            hairstyles = [
                {
                    "name": "Basic Cut",
                    "price": 20.00,
                    "description": "A simple and clean haircut.",
                    "image": "basic_cut.svg"
                },
                {
                    "name": "Premium Cut",
                    "price": 35.00,
                    "description": "A more detailed and styled haircut.",
                    "image": "premium_cut.svg"
                },
                {
                    "name": "Coloring - Single Process",
                    "price": 60.00,
                    "description": "One solid color application.",
                    "image": "coloring.svg"
                },
                {
                    "name": "Highlights - Partial",
                    "price": 75.00,
                    "description": "Highlights on the top section of the hair.",
                    "image": "highlights.svg"
                },
                {
                    "name": "Updo - Special Occasion",
                    "price": 50.00,
                    "description": "Elegant styling for events.",
                    "image": "updo.svg"
                },
            ]

            for style in hairstyles:
                hairstyle = Hairstyle(
                    name=style["name"],
                    price=style["price"],
                    description=style["description"],
                    image_path=style["image"]
                )
                db.session.add(hairstyle)
            db.session.commit()
            print("Added sample hairstyles")

        # Add sample customers if none exist
        if not Customer.query.first():
            customers = [
                {
                    "name": "Alice Smith",
                    "phone": "08012345678",
                    "email": "alice.smith@example.com",
                    "gender": "female"
                },
                {
                    "name": "Bob Johnson",
                    "phone": "09087654321",
                    "email": "bob.johnson@example.com",
                    "gender": "male"
                },
                {
                    "name": "Charlie Brown",
                    "phone": "07055551212",
                    "email": "charlie.brown@example.com",
                    "gender": "male"
                },
                {
                    "name": "Diana Lee",
                    "phone": "08199990000",
                    "email": "diana.lee@example.com",
                    "gender": "female"
                },
            ]

            for cust in customers:
                image_path = f"images/default_{cust['gender']}.svg"
                customer = Customer(
                    name=cust["name"],
                    phone=cust["phone"],
                    email=cust["email"],
                    gender=cust["gender"],
                    image_path=image_path
                )
                db.session.add(customer)
            db.session.commit()
            print("Added sample customers")

        # Add sample appointments if none exist
        if not Appointment.query.first():
            customer1 = Customer.query.filter_by(name="Alice Smith").first()
            customer2 = Customer.query.filter_by(name="Bob Johnson").first()
            hairstyle1 = Hairstyle.query.filter_by(name="Basic Cut").first()
            hairstyle3 = Hairstyle.query.filter_by(name="Coloring - Single Process").first()

            if customer1 and customer2 and hairstyle1 and hairstyle3:
                appointments = [
                    {
                        "customer": customer1,
                        "hairstyle": hairstyle1,
                        "date": datetime.now() + timedelta(days=2, hours=10),
                        "completed": False
                    },
                    {
                        "customer": customer2,
                        "hairstyle": hairstyle3,
                        "date": datetime.now() + timedelta(days=3, hours=14),
                        "completed": False
                    },
                    {
                        "customer": customer1,
                        "hairstyle": hairstyle1,
                        "date": datetime.now() - timedelta(days=5, hours=9),
                        "completed": True,
                        "amount_paid": hairstyle1.price
                    },
                ]

                for appt in appointments:
                    appointment = Appointment(
                        customer_id=appt["customer"].id,
                        hairstyle_id=appt["hairstyle"].id,
                        appointment_date=appt["date"],
                        completed=appt["completed"],
                        amount_paid=appt.get("amount_paid")
                    )
                    db.session.add(appointment)
                db.session.commit()
                print("Added sample appointments")

        # Add sample expenses if none exist
        if not Expense.query.first():
            expenses = [
                {
                    "item": "Rent",
                    "amount": 1500.00,
                    "date": datetime.now() - timedelta(days=30),
                    "category": "Utilities"
                },
                {
                    "item": "Hair Products",
                    "amount": 250.50,
                    "date": datetime.now() - timedelta(days=25),
                    "category": "Supplies"
                },
                {
                    "item": "Electricity Bill",
                    "amount": 120.75,
                    "date": datetime.now() - timedelta(days=1),
                    "category": "Utilities"
                },
                {
                    "item": "Staff Salary",
                    "amount": 800.00,
                    "date": datetime.now() - timedelta(days=15),
                    "category": "Salaries"
                },
            ]

            for exp in expenses:
                expense = Expense(
                    item=exp["item"],
                    amount=exp["amount"],
                    expense_date=exp["date"],
                    category=exp["category"]
                )
                db.session.add(expense)
            db.session.commit()
            print("Added sample expenses with categories")

    except Exception as e:
        db.session.rollback()
        print(f"Error initializing database: {str(e)}")
        raise


if __name__ == '__main__':
    from app import app
    from extensions import db
    with app.app_context():
        initialize_database(db)
