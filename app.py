from models import User, Customer, Hairstyle, Appointment, Expense
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash
from functools import wraps
from flask_login import current_user, login_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect, generate_csrf
from werkzeug.utils import secure_filename
import os
from datetime import datetime

# Import extensions
from extensions import db, login_manager, migrate

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///salon.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.urandom(24)  # Use a random secret key for session management

# Initialize the db extension with app
db.init_app(app)
# Configure login manager
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.session_protection = "strong"
migrate.init_app(app, db)  # Initialize migrate here

csrf = CSRFProtect(app)

# Configure upload folders
UPLOAD_FOLDER = 'static/uploads'
CUSTOMER_IMAGES = os.path.join(UPLOAD_FOLDER, 'customers')
HAIRSTYLE_IMAGES = os.path.join(UPLOAD_FOLDER, 'hairstyles')
DEFAULT_CUSTOMER_IMAGE_FOLDER = 'static/images'

# Create upload directories if they don't exist
os.makedirs(CUSTOMER_IMAGES, exist_ok=True)
os.makedirs(HAIRSTYLE_IMAGES, exist_ok=True)
os.makedirs(DEFAULT_CUSTOMER_IMAGE_FOLDER, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}

# Import models AFTER db initialization to avoid circular imports


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom filter for currency formatting


@app.template_filter('usd')
def usd(value):
    """Format value as USD."""
    return f"${value:,.2f}"


@app.template_filter('ngn')
def ngn(value):
    """Format value as Nigerian Naira."""
    return f"₦{value:,.2f}"


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.context_processor
def inject_user():
    return dict(current_user=current_user)


@app.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf)


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_image(file, upload_folder):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{datetime.now().timestamp()}_{filename}"
        file_path = os.path.join(upload_folder, unique_filename)
        file.save(file_path)
        return unique_filename
    return None


def delete_old_image(image_path, upload_folder):
    if image_path and not image_path.startswith('default_'):
        try:
            old_file = os.path.join(upload_folder, image_path)
            if os.path.exists(old_file):
                os.remove(old_file)
        except Exception as e:
            app.logger.error(f"Error deleting old image: {str(e)}")


# Import models after db initialization
@app.route("/")
def index():
    """Public landing page"""
    hairstyles = Hairstyle.query.order_by(Hairstyle.name).limit(6).all()
    return render_template("index.html", hairstyles=hairstyles)


@app.route("/hairstyles/load-more")
def load_more_hairstyles():
    offset = request.args.get('offset', 6, type=int)
    hairstyles = Hairstyle.query.order_by(Hairstyle.name).offset(offset).limit(6).all()

    html = ""
    for hairstyle in hairstyles:
        html += f"""
        <div class="col-md-4 col-lg-3">
            <div class="card h-100 shadow-sm">
                <img src="{url_for('static', filename='uploads/hairstyles/' + hairstyle.image_path) if hairstyle.image_path != 'default_hairstyle.svg' else url_for('static', filename='images/default_hairstyle.svg')}"
                     class="card-img-top" alt="{hairstyle.name}" style="height: 200px; object-fit: cover;">
                <div class="card-body">
                    <h5 class="card-title">{hairstyle.name}</h5>
                    <p class="card-text text-muted">{hairstyle.description[:100]}{'...' if len(hairstyle.description) > 100 else ''}</p>
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="fw-bold text-primary">{ngn(hairstyle.price)}</span>
                        <a href="{url_for('login')}" class="btn btn-sm btn-outline-primary">Book Now</a>
                    </div>
                </div>
            </div>
        </div>
        """

    return jsonify({
        'html': html,
        'remaining': Hairstyle.query.count() - offset - 6
    })


@app.route('/dashboard')
@login_required
def dashboard():
    """Show salon dashboard"""
    # Get today's appointments count
    now = datetime.utcnow()
    today = now.date()
    today_appointments = Appointment.query.filter(
        db.func.date(Appointment.appointment_date) == today
    ).count()

    # Get monthly revenue
    current_month = datetime.utcnow().month
    monthly_revenue = db.session.query(db.func.sum(Appointment.amount_paid)).filter(
        db.func.extract('month', Appointment.appointment_date) == current_month,
        Appointment.completed == True
    ).scalar() or 0

    # Get monthly expenses
    monthly_expenses = db.session.query(db.func.sum(Expense.amount)).filter(
        db.func.extract('month', Expense.expense_date) == current_month
    ).scalar() or 0

    return render_template('dashboard/index.html',
                           now=now,  # Add this
                           today_appointments=today_appointments,
                           monthly_revenue=monthly_revenue,
                           monthly_expenses=monthly_expenses)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login with proper validation and security"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username:
            flash("Username is required", "danger")
            return render_template("auth/login.html")

        if not password:
            flash("Password is required", "danger")
            return render_template("auth/login.html")

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)  # Only use Flask-Login's login method

            # Remove these manual session handling lines:
            # session["user_id"] = user.id
            # session.regenerate()

            if hasattr(user, 'last_login'):
                user.last_login = datetime.utcnow()
                db.session.commit()

            flash(f"Welcome back, {user.username}!", "success")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))

        flash("Invalid username or password", "danger")

    return render_template("auth/login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Validate inputs
        if not username:
            flash("Must provide username", "danger")
            return render_template("auth/register.html")

        if not password:
            flash("Must provide password", "danger")
            return render_template("auth/register.html")

        if password != confirmation:
            flash("Passwords do not match", "danger")
            return render_template("auth/register.html")

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists", "danger")
            return render_template("auth/register.html")

        # Create new user
        try:
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                role='staff'  # Default role
            )
            db.session.add(new_user)
            db.session.commit()

            # Log the user in after registration
            login_user(new_user)
            flash("Registration successful! You are now logged in.", "success")
            return redirect(url_for("dashboard"))

        except Exception as e:
            db.session.rollback()
            flash("An error occurred during registration. Please try again.", "danger")
            app.logger.error(f"Registration error: {str(e)}")
            return render_template("auth/register.html")
    return render_template("auth/register.html")


@app.route("/hairstyles")
@login_required
def hairstyles():
    """Show all available hairstyles"""
    styles = Hairstyle.query.all()
    return render_template("hairstyles/hairstyles.html", hairstyles=styles)


@app.route("/add_hairstyle", methods=["GET", "POST"])
@login_required
def add_hairstyle():
    """Add a new hairstyle"""
    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = request.form.get("price")
        image_file = request.files.get("image")

        # In add_hairstyle route
        if not all([name, price, image_file]):
            flash("Name, price and image are required", "danger")
            return render_template("hairstyles/add_hairstyle.html")

        try:
            price = float(price)
        except ValueError:
            flash("Invalid price format", "danger")
            return render_template("hairstyles/add_hairstyle.html")

        # Save image if provided
        image_path = save_image(image_file, HAIRSTYLE_IMAGES) if image_file else None

        # Use default image if no image provided
        if not image_path:
            image_path = "default_hairstyle.jpg"

        new_hairstyle = Hairstyle(
            name=name,
            description=description,
            price=price,
            image_path=image_path
        )

        db.session.add(new_hairstyle)
        db.session.commit()

        flash("Hairstyle added successfully!", "success")
        return redirect("/hairstyles")
    else:
        return render_template("hairstyles/add_hairstyle.html")


@app.route("/edit_hairstyle/<int:hairstyle_id>", methods=["GET", "POST"])
@login_required
def edit_hairstyle(hairstyle_id):
    """Edit an existing hairstyle"""
    hairstyle = Hairstyle.query.get_or_404(hairstyle_id)

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        price = request.form.get("price")
        image_file = request.files.get("image")

        if not all([name, price]):
            flash("Name and price are required", "danger")
            return render_template("hairstyles/edit_hairstyle.html", hairstyle=hairstyle)

        try:
            price = float(price)
        except ValueError:
            flash("Invalid price format", "danger")
            return render_template("hairstyles/edit_hairstyle.html", hairstyle=hairstyle)

        # Handle image upload
        if image_file and image_file.filename:  # Check if file was actually uploaded
            if allowed_file(image_file.filename):
                # Delete old image if it's not a default one
                if hairstyle.image_path and not hairstyle.image_path.startswith('default_'):
                    try:
                        old_image_path = os.path.join(HAIRSTYLE_IMAGES, hairstyle.image_path)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    except Exception as e:
                        app.logger.error(f"Error deleting old image: {str(e)}")

                # Save new image
                filename = secure_filename(image_file.filename)
                unique_filename = f"{datetime.now().timestamp()}_{filename}"
                file_path = os.path.join(HAIRSTYLE_IMAGES, unique_filename)

                try:
                    image_file.save(file_path)
                    hairstyle.image_path = unique_filename
                except Exception as e:
                    flash("Error saving image file", "danger")
                    app.logger.error(f"Error saving image: {str(e)}")
                    return render_template("hairstyles/edit_hairstyle.html", hairstyle=hairstyle)
            else:
                flash("Invalid image file type", "danger")
                return render_template("hairstyles/edit_hairstyle.html", hairstyle=hairstyle)

        # Update other fields
        hairstyle.name = name
        hairstyle.description = description
        hairstyle.price = price

        try:
            db.session.commit()
            flash("Hairstyle updated successfully!", "success")
            return redirect(url_for("hairstyles"))
        except Exception as e:
            db.session.rollback()
            flash("Failed to update hairstyle. Please try again.", "danger")
            app.logger.error(f"Error updating hairstyle: {str(e)}")

    return render_template("hairstyles/edit_hairstyle.html", hairstyle=hairstyle)


@app.route("/delete_hairstyle/<int:hairstyle_id>", methods=["POST"])
@login_required
def delete_hairstyle(hairstyle_id):
    """Delete a hairstyle"""
    if current_user.role != 'admin':
        flash("You don't have permission to delete hairstyles", "danger")
        return redirect(url_for('hairstyles'))

    hairstyle = Hairstyle.query.get_or_404(hairstyle_id)

    try:
        # Delete hairstyle image if it's not a default one
        delete_old_image(hairstyle.image_path, HAIRSTYLE_IMAGES)

        db.session.delete(hairstyle)
        db.session.commit()
        flash("Hairstyle deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to delete hairstyle. Please try again.", "danger")
        app.logger.error(f"Error deleting hairstyle: {str(e)}")

    return redirect(url_for('hairstyles'))


@app.route("/customers")
@login_required
def customers():
    """Show all customers"""
    customers = Customer.query.order_by(Customer.name).all()
    return render_template("customers/customers.html", customers=customers)


@app.route("/customer/<int:customer_id>")
@login_required
def view_customer(customer_id):
    """View customer details and appointment history"""
    customer = Customer.query.get_or_404(customer_id)
    appointments = Appointment.query.filter_by(customer_id=customer_id)\
        .order_by(Appointment.appointment_date.desc())\
        .all()

    # Calculate total spent
    total_spent = db.session.query(db.func.sum(Appointment.amount_paid))\
        .filter(Appointment.customer_id == customer_id,
                Appointment.completed == True)\
        .scalar() or 0

    return render_template("customers/view_customer.html",
                           customer=customer,
                           appointments=appointments,
                           total_spent=total_spent)


@app.route("/add_customer", methods=["GET", "POST"])
@login_required
def add_customer():
    """Add a new customer"""
    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        gender = request.form.get("gender", "male")
        image_file = request.files.get("image")

        if not name or not phone:
            flash("Name and phone are required", "danger")
            return render_template("customers/add_customer.html")

        image_path = None
        if image_file:
            image_path = save_image(image_file, CUSTOMER_IMAGES)

        # Use default image if no image provided or upload failed
        if not image_path:
            if gender == 'female':
                # Path relative to static/uploads/customers
                image_path = os.path.join('..', DEFAULT_CUSTOMER_IMAGE_FOLDER, 'default_female.svg')
            else:
                # Path relative to static/uploads/customers
                image_path = os.path.join('..', DEFAULT_CUSTOMER_IMAGE_FOLDER, 'default_male.svg')

        new_customer = Customer(
            name=name,
            phone=phone,
            email=email,
            gender=gender,
            image_path=image_path
        )

        db.session.add(new_customer)
        db.session.commit()

        flash("Customer added successfully!", "success")
        return redirect("/customers")
    else:
        return render_template("customers/add_customer.html")


@app.route("/edit_customer/<int:customer_id>", methods=["GET", "POST"])
@login_required
def edit_customer(customer_id):
    """Edit customer details"""
    if current_user.role != 'admin':
        flash("You don't have permission to edit customers", "danger")
        return redirect(url_for('customers'))

    customer = Customer.query.get_or_404(customer_id)

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        email = request.form.get("email")
        gender = request.form.get("gender", customer.gender or "male")
        image_file = request.files.get("image")

        if not name or not phone:
            flash("Name and phone are required", "danger")
            return render_template("customers/edit_customer.html", customer=customer)

        if image_file:
            # Delete old image if it's not a default SVG
            if customer.image_path and not customer.image_path.endswith(('.svg')):
                delete_old_image(customer.image_path, CUSTOMER_IMAGES)
            # Save new image
            image_path = save_image(image_file, CUSTOMER_IMAGES)
            if image_path:
                customer.image_path = image_path
        elif not customer.image_path:  # If no new image and no existing image
            if gender == 'female':
                customer.image_path = os.path.join(
                    '..', DEFAULT_CUSTOMER_IMAGE_FOLDER, 'default_female.svg')
            else:
                customer.image_path = os.path.join(
                    '..', DEFAULT_CUSTOMER_IMAGE_FOLDER, 'default_male.svg')
        elif customer.image_path.endswith(('.svg')) and gender != customer.gender:
            # If gender changed and it was a default SVG, update it
            if gender == 'female':
                customer.image_path = os.path.join(
                    '..', DEFAULT_CUSTOMER_IMAGE_FOLDER, 'default_female.svg')
            else:
                customer.image_path = os.path.join(
                    '..', DEFAULT_CUSTOMER_IMAGE_FOLDER, 'default_male.svg')

        customer.name = name
        customer.phone = phone
        customer.email = email
        customer.gender = gender

        db.session.commit()
        flash("Customer updated successfully!", "success")
        return redirect(url_for('customers'))

    return render_template("customers/edit_customer.html", customer=customer)


@app.route("/delete_customer/<int:customer_id>", methods=["POST"])
@login_required
def delete_customer(customer_id):
    """Delete a customer"""
    if current_user.role != 'admin':
        flash("You don't have permission to delete customers", "danger")
        return redirect(url_for('customers'))

    customer = Customer.query.get_or_404(customer_id)

    try:
        # Delete customer image if it's not a default one
        delete_old_image(customer.image_path, CUSTOMER_IMAGES)

        # First delete all appointments for this customer
        Appointment.query.filter_by(customer_id=customer_id).delete()
        # Then delete the customer
        db.session.delete(customer)
        db.session.commit()
        flash("Customer deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to delete customer. Please try again.", "danger")
        app.logger.error(f"Error deleting customer: {str(e)}")

    return redirect(url_for('customers'))


@app.route("/book_appointment", methods=["GET", "POST"])
@login_required
def book_appointment():
    """Book a new appointment"""
    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        hairstyle_id = request.form.get("hairstyle_id")
        appointment_date_str = request.form.get("appointment_date")

        if not all([customer_id, hairstyle_id, appointment_date_str]):
            flash("All fields are required", "danger")
            return redirect(url_for('book_appointment'))

        try:
            # Parse the datetime string from flatpickr (format: "Y-m-d H:i")
            appointment_date = datetime.strptime(appointment_date_str, "%Y-%m-%d %H:%M")

            # Check if appointment is in the past
            if appointment_date < datetime.now():
                flash("Appointment date cannot be in the past", "danger")
                return redirect(url_for('book_appointment'))

            # Check for existing appointments at the same time
            existing_appointment = Appointment.query.filter_by(
                appointment_date=appointment_date
            ).first()

            if existing_appointment:
                flash("There's already an appointment at this time. Please choose another time.", "danger")
                return redirect(url_for('book_appointment'))

            # Get hairstyle price
            hairstyle = Hairstyle.query.get(hairstyle_id)
            if not hairstyle:
                flash("Invalid hairstyle selected", "danger")
                return redirect(url_for('book_appointment'))

            new_appointment = Appointment(
                customer_id=customer_id,
                hairstyle_id=hairstyle_id,
                appointment_date=appointment_date,
                completed=False,
                amount_paid=hairstyle.price if hairstyle else 0
            )

            db.session.add(new_appointment)
            db.session.commit()

            flash("Appointment booked successfully!", "success")
            return redirect(url_for('appointments'))

        except ValueError as e:
            flash("Invalid date/time format. Please use the date picker.", "danger")
            app.logger.error(f"Date parsing error: {str(e)}")
            return redirect(url_for('book_appointment'))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while booking the appointment", "danger")
            app.logger.error(f"Appointment booking error: {str(e)}")
            return redirect(url_for('book_appointment'))

    # GET request
    customers = Customer.query.order_by(Customer.name).all()
    hairstyles = Hairstyle.query.order_by(Hairstyle.name).all()
    return render_template("appointments/book_appointment.html",
                           customers=customers,
                           hairstyles=hairstyles)


@app.route("/appointments")
@login_required
def appointments():
    """Show all appointments"""
    now = datetime.utcnow()
    upcoming_appointments = Appointment.query.filter(
        Appointment.appointment_date >= now,
        Appointment.completed == False
    ).order_by(Appointment.appointment_date).all()

    completed_appointments = Appointment.query.filter(
        Appointment.completed == True
    ).order_by(Appointment.appointment_date.desc()).all()

    all_appointments = Appointment.query.order_by(
        Appointment.appointment_date.desc()
    ).all()

    return render_template("appointments/appointments.html",
                           upcoming_appointments=upcoming_appointments,
                           completed_appointments=completed_appointments,
                           all_appointments=all_appointments)


@app.route("/complete_appointment/<int:appointment_id>")
@login_required
def complete_appointment(appointment_id):
    """Mark appointment as completed"""
    appointment = Appointment.query.get_or_404(appointment_id)

    if not appointment.completed:
        appointment.completed = True
        appointment.amount_paid = appointment.hairstyle.price
        db.session.commit()
        flash("Appointment marked as completed", "success")
    else:
        flash("Appointment was already completed", "warning")

    return redirect("/appointments")


@app.route("/delete_appointment/<int:appointment_id>", methods=["POST"])
@login_required
def delete_appointment(appointment_id):
    """Delete an appointment"""
    if current_user.role != 'admin':
        flash("You don't have permission to delete appointments", "danger")
        return redirect(url_for('appointments'))

    appointment = Appointment.query.get_or_404(appointment_id)

    try:
        db.session.delete(appointment)
        db.session.commit()
        flash("Appointment deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to delete appointment. Please try again.", "danger")
        app.logger.error(f"Error deleting appointment: {str(e)}")

    return redirect(url_for('appointments'))


@app.route("/edit_appointment/<int:appointment_id>", methods=["GET", "POST"])
@login_required
def edit_appointment(appointment_id):
    """Edit an existing appointment"""
    if current_user.role != 'admin':
        flash("You don't have permission to edit appointments", "danger")
        return redirect(url_for('appointments'))

    appointment = Appointment.query.get_or_404(appointment_id)

    if request.method == "POST":
        customer_id = request.form.get("customer_id")
        hairstyle_id = request.form.get("hairstyle_id")
        appointment_date = request.form.get("appointment_date")

        if not all([customer_id, hairstyle_id, appointment_date]):
            flash("All fields are required", "danger")
            return redirect(url_for('edit_appointment', appointment_id=appointment_id))

        try:
            appointment_date = datetime.strptime(appointment_date, "%Y-%m-%dT%H:%M")
        except ValueError:
            flash("Invalid date format", "danger")
            return redirect(url_for('edit_appointment', appointment_id=appointment_id))

        appointment.customer_id = customer_id
        appointment.hairstyle_id = hairstyle_id
        appointment.appointment_date = appointment_date

        db.session.commit()
        flash("Appointment updated successfully!", "success")
        return redirect(url_for('appointments'))

    customers = Customer.query.order_by(Customer.name).all()
    hairstyles = Hairstyle.query.order_by(Hairstyle.name).all()

    return render_template("appointments/edit_appointment.html",
                           appointment=appointment,
                           customers=customers,
                           hairstyles=hairstyles)


@app.route("/expenses")
@login_required
def expenses():
    """Show all expenses"""
    expenses = Expense.query.order_by(Expense.expense_date.desc()).all()
    return render_template("expenses/expenses.html", expenses=expenses)


@app.route("/add_expense", methods=["GET", "POST"])
@login_required
def add_expense():
    """Add a new expense"""
    if request.method == "POST":
        item = request.form.get("item")
        amount = request.form.get("amount")
        description = request.form.get("description")
        expense_date = request.form.get("expense_date")
        category = request.form.get("category")

        if not item or not amount or not category:
            flash("Item, category and amount are required", "danger")
            return render_template("expenses/add_expense.html")

        try:
            amount = float(amount)
            expense_date = datetime.strptime(
                expense_date, "%Y-%m-%d") if expense_date else datetime.utcnow()
        except ValueError:
            flash("Invalid amount or date format", "danger")
            return render_template("expenses/add_expense.html")

        new_expense = Expense(
            item=item,
            amount=amount,
            description=description,
            expense_date=expense_date,
            category=category
        )

        db.session.add(new_expense)
        db.session.commit()

        flash("Expense added successfully!", "success")
        return redirect(url_for("expenses"))

    # GET request - pass current datetime to template
    return render_template("expenses/add_expense.html", now=datetime.utcnow())


@app.route("/edit_expense/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    """Edit an existing expense"""
    if current_user.role != 'admin':
        flash("You don't have permission to edit expenses", "danger")
        return redirect(url_for('expenses'))

    expense = Expense.query.get_or_404(expense_id)

    if request.method == "POST":
        item = request.form.get("item")
        amount = request.form.get("amount")
        description = request.form.get("description")
        expense_date = request.form.get("expense_date")
        category = request.form.get("category")

        if not item or not amount or not category:
            flash("Item, category and amount are required", "danger")
            return render_template("expenses/edit_expense.html", expense=expense)

        try:
            amount = float(amount)
            expense_date = datetime.strptime(expense_date, "%Y-%m-%d")
        except ValueError:
            flash("Invalid amount or date format", "danger")
            return render_template("expenses/edit_expense.html", expense=expense)

        expense.item = item
        expense.amount = amount
        expense.description = description
        expense.expense_date = expense_date
        expense.category = category

        db.session.commit()
        flash("Expense updated successfully!", "success")
        return redirect(url_for('expenses'))

    return render_template("expenses/edit_expense.html", expense=expense)


@app.route("/delete_expense/<int:expense_id>", methods=["POST"])
@login_required
def delete_expense(expense_id):
    """Delete an expense"""
    if current_user.role != 'admin':
        flash("You don't have permission to delete expenses", "danger")
        return redirect(url_for('expenses'))

    expense = Expense.query.get_or_404(expense_id)

    try:
        db.session.delete(expense)
        db.session.commit()
        flash("Expense deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to delete expense. Please try again.", "danger")
        app.logger.error(f"Error deleting expense: {str(e)}")

    return redirect(url_for('expenses'))


@app.route("/reports")
@login_required
def reports():
    """Show sales and expense reports"""
    # Monthly sales data
    monthly_sales = db.session.query(
        db.func.strftime('%Y-%m', Appointment.appointment_date).label('month'),
        db.func.sum(Appointment.amount_paid).label('total_sales'),
        db.func.count(Appointment.id).label('appointment_count')
    ).filter(
        Appointment.completed == True
    ).group_by('month').order_by('month').all()

    # Expense by category
    expense_by_category = db.session.query(
        Expense.item,
        db.func.sum(Expense.amount).label('total_amount')
    ).group_by(Expense.item).all()

    return render_template("reports/index.html",
                           monthly_sales=monthly_sales,
                           expense_by_category=expense_by_category)


@app.route("/users")
@login_required
def users():
    if current_user.role != 'admin':
        flash("You don't have permission to view this page", "danger")
        return redirect(url_for('dashboard'))
    users = User.query.all()
    return render_template("users/users.html", users=users)


@app.route("/add_user", methods=["GET", "POST"])
@login_required
def add_user():
    """Admin-only user creation"""
    if current_user.role != 'admin':
        flash("You don't have permission to add users", "danger")
        return redirect(url_for('dashboard'))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role", "staff")

        if not username:
            flash("Username is required", "danger")
            return render_template("users/add_user.html")

        if not password or len(password) < 8:
            flash("Password must be at least 8 characters", "danger")
            return render_template("users/add_user.html")

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists", "danger")
            return render_template("users/add_user.html")

        try:
            new_user = User(
                username=username,
                role=role
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash("User created successfully!", "success")
            return redirect(url_for("users"))
        except Exception as e:
            db.session.rollback()
            flash("An error occurred. Please try again.", "danger")
            app.logger.error(f"User creation error: {str(e)}")

    return render_template("users/add_user.html")


@app.route("/edit_user/<int:user_id>", methods=["GET", "POST"])
@login_required
def edit_user(user_id):
    if current_user.role != 'admin':
        flash("You don't have permission to edit users", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)

    if request.method == "POST":
        user.username = request.form.get("username")
        user.role = request.form.get("role")

        # Handle password change if provided
        new_password = request.form.get("password")
        if new_password and len(new_password) >= 8:
            user.set_password(new_password)
            flash("Password updated successfully", "success")
        elif new_password:
            flash("Password must be at least 8 characters", "danger")
            return render_template("users/edit_user.html", user=user)

        db.session.commit()
        flash("User updated successfully!", "success")
        return redirect(url_for("users"))

    return render_template("users/edit_user.html", user=user)


@app.route("/delete_user/<int:user_id>")
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        flash("You don't have permission to delete users", "danger")
        return redirect(url_for('dashboard'))

    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        flash("You cannot delete your own account", "danger")
        return redirect(url_for('users'))

    user = User.query.get_or_404(user_id)

    try:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Failed to delete user. Please try again.", "danger")
        app.logger.error(f"Error deleting user: {str(e)}")

    return redirect(url_for("users"))


if __name__ == '__main__':
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()

        from init_db import initialize_database
        initialize_database()

    app.run(debug=True)
