from extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


class User(UserMixin, db.Model):
    __tablename__ = 'users'  # Explicit table name
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='staff')  # 'admin' or 'staff'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    gender = db.Column(db.String(10))  # 'male' or 'female'
    image_path = db.Column(db.String(200))
    registration_date = db.Column(db.DateTime, default=datetime.utcnow)
    appointments = db.relationship('Appointment', backref='customer', lazy=True)


class Hairstyle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image_path = db.Column(db.String(200), nullable=False, default='default_hairstyle.svg')
    appointments = db.relationship('Appointment', backref='hairstyle', lazy=True)


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    hairstyle_id = db.Column(db.Integer, db.ForeignKey('hairstyle.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    amount_paid = db.Column(db.Float)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    amount = db.Column(db.Float, nullable=False)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
