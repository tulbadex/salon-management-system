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
                    "name": "Modern Mullet Hair",
                    "price": 10000.00,
                    "description": "2024 heralds the continuation of the Modern Mullet's reign, inspired by the revival of the Y2K trend. This versatile style is rapidly gaining popularity and is expected to last. Far from a one-size-fits-all, the modern mullet embraces various interpretations, from spiky and short to curly versions. It's a trend that adapts to your style, whether you're aiming for a subtle change or a bold statement. Get ready to see this dynamic hairstyle on trendsetters across Asia.",
                    "image": "mullet_cut.svg"
                },
                {
                    "name": "Buzz Cut",
                    "price": 5000.00,
                    "description": "The buzz cut is resurging as a top trend this year, particularly in Western and ASEAN countries, thanks to its perfect match with barber culture. With a nod to the Y2K trend, reminiscent of styles popularized by several celebrity icons, the Buzz Cut is more than just a haircut – it's a fashion statement. This ultra-short style is all about embracing simplicity with a touch of edginess. For a modern twist, maintain a clean, even length all around, offering a sharp yet low-maintenance, unpretentiously chic look.",
                    "image": "buzz_cut.svg"
                },
                {
                    "name": "Textured Afro with Temple Fade",
                    "price": 6000.00,
                    "description": "Embrace the freedom and beauty of afro hair with a foam textured style that lets your coils take their natural shape. Paired with neatly faded temples, this look celebrates the natural texture of your hair while offering a sleek style that is stylish and requires minimum maintenance.",
                    "image": "textured_afro.svg"
                },
                {
                    "name": "Freeform Dreadlocks High Top Haircut",
                    "price": 7500.00,
                    "description": "Celebrate the strength and texture of your natural coily hair with a dynamic high top of freeform ‘locs. This hairstyle encourages acceptance of your hair’s natural texture but also adds a playful contrast with bleached tips, making each dreadlock interesting and unique.",
                    "image": "highlights.svg"
                },
                {
                    "name": "Short Dreadlocks with Undercut Design",
                    "price": 10000.00,
                    "description": "Elevate the cool factor of freeform dreadlocks with a twisted high top that incorporates bold designs for an extra spark. Strategic etching adds an artistic edge to the natural volume and wild curls, creating a look that’s not only visually striking but also full of personality and style. For vibrant afro curly hair, keep hair hydrated and moisturized.",
                    "image": "short_dreadlocks.svg"
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
