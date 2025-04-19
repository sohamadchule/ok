from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pdfkit
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'apollocare_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    phone = db.Column(db.String(15))
    address = db.Column(db.String(200))
    records = db.relationship('PatientRecord', backref='patient', lazy=True)
    
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    specialization = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    records = db.relationship('PatientRecord', backref='doctor', lazy=True)

class Staff(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50))
    phone = db.Column(db.String(15))

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_name = db.Column(db.String(100), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    symptoms = db.Column(db.Text)
    department = db.Column(db.String(100))
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'))
    appointment_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PatientRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    history = db.Column(db.Text)
    diagnosis = db.Column(db.Text)
    prescriptions = db.relationship('Prescription', backref='record', lazy=True)

class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.Integer, db.ForeignKey('patient_record.id'), nullable=False)
    medicine_name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50))
    frequency = db.Column(db.String(50))
    duration = db.Column(db.String(50))
    morning = db.Column(db.Boolean, default=False)
    afternoon = db.Column(db.Boolean, default=False)
    evening = db.Column(db.Boolean, default=False)
    days = db.Column(db.String(100))  # Stored as comma-separated days (e.g., "Mon,Tue,Wed")

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

# Login Decorators
def patient_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'patient_id' not in session:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('patient_login'))
        return f(*args, **kwargs)
    return decorated_function

def doctor_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'doctor_id' not in session:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('doctor_login'))
        return f(*args, **kwargs)
    return decorated_function

def staff_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'staff_id' not in session:
            flash('Please login to access this page', 'danger')
            return redirect(url_for('staff_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    return render_template('base.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Patient Routes
@app.route('/patient/register', methods=['GET', 'POST'])
def patient_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        gender = request.form['gender']
        age = request.form['age']
        phone = request.form['phone']
        address = request.form['address']
        
        # Check if email already exists
        existing_patient = Patient.query.filter_by(email=email).first()
        if existing_patient:
            flash('Email already registered', 'danger')
            return redirect(url_for('patient_register'))
        
        hashed_password = generate_password_hash(password)
        new_patient = Patient(name=name, email=email, password=hashed_password, 
                            gender=gender, age=age, phone=phone, address=address)
        
        db.session.add(new_patient)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('patient_login'))
    
    return render_template('patient/register.html')

@app.route('/patient/login', methods=['GET', 'POST'])
def patient_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        patient = Patient.query.filter_by(email=email).first()
        
        if patient and check_password_hash(patient.password, password):
            session['patient_id'] = patient.id
            session['patient_name'] = patient.name
            flash('Login successful!', 'success')
            return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('patient/login.html')

@app.route('/patient/dashboard')
@patient_login_required
def patient_dashboard():
    patient_id = session['patient_id']
    patient = Patient.query.get(patient_id)
    records = PatientRecord.query.filter_by(patient_id=patient_id).order_by(PatientRecord.visit_date.desc()).all()
    
    latest_record = records[0] if records else None
    latest_prescriptions = []
    
    if latest_record:
        latest_prescriptions = Prescription.query.filter_by(record_id=latest_record.id).all()
    
    return render_template('patient/dashboard.html', 
                          patient=patient, 
                          records=records, 
                          latest_record=latest_record,
                          latest_prescriptions=latest_prescriptions)

@app.route('/patient/logout')
def patient_logout():
    session.pop('patient_id', None)
    session.pop('patient_name', None)
    return redirect(url_for('home'))

@app.route('/patient/prescription/<int:record_id>/download')
@patient_login_required
def download_prescription(record_id):
    record = PatientRecord.query.get_or_404(record_id)
    patient = Patient.query.get(record.patient_id)
    doctor = Doctor.query.get(record.doctor_id)
    prescriptions = Prescription.query.filter_by(record_id=record.id).all()
    
    html = render_template('patient/prescription_pdf.html', 
                          record=record, 
                          patient=patient, 
                          doctor=doctor, 
                          prescriptions=prescriptions)
    
    pdf = pdfkit.from_string(html, False)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=prescription_{record_id}.pdf'
    
    return response

# Doctor Routes
@app.route('/doctor/register', methods=['GET', 'POST'])
def doctor_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        specialization = request.form['specialization']
        phone = request.form['phone']
        
        # Check if email already exists
        existing_doctor = Doctor.query.filter_by(email=email).first()
        if existing_doctor:
            flash('Email already registered', 'danger')
            return redirect(url_for('doctor_register'))
        
        hashed_password = generate_password_hash(password)
        new_doctor = Doctor(name=name, email=email, password=hashed_password, 
                           specialization=specialization, phone=phone)
        
        db.session.add(new_doctor)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('doctor_login'))
    
    return render_template('doctor/register.html')

@app.route('/doctor/login', methods=['GET', 'POST'])
def doctor_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        doctor = Doctor.query.filter_by(email=email).first()
        
        if doctor and check_password_hash(doctor.password, password):
            session['doctor_id'] = doctor.id
            session['doctor_name'] = doctor.name
            flash('Login successful!', 'success')
            return redirect(url_for('doctor_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('doctor/login.html')

@app.route('/doctor/dashboard')
@doctor_login_required
def doctor_dashboard():
    doctor_id = session['doctor_id']
    doctor = Doctor.query.get(doctor_id)
    appointments = Appointment.query.filter_by(doctor_id=doctor_id, status='Pending').all()
    
    return render_template('doctor/dashboard.html', doctor=doctor, appointments=appointments)

@app.route('/doctor/search_patient', methods=['POST'])
@doctor_login_required
def search_patient():
    search_term = request.form['search_term']
    
    # Search by ID or name
    patient = None
    if search_term.isdigit():
        patient = Patient.query.get(int(search_term))
    else:
        patient = Patient.query.filter(Patient.name.like(f'%{search_term}%')).first()
    
    if not patient:
        flash('Patient not found', 'danger')
        return redirect(url_for('doctor_dashboard'))
    
    records = PatientRecord.query.filter_by(patient_id=patient.id).order_by(PatientRecord.visit_date.desc()).all()
    
    return render_template('doctor/patient_history.html', patient=patient, records=records)

@app.route('/doctor/create_record/<int:patient_id>', methods=['GET', 'POST'])
@doctor_login_required
def create_record(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    doctor_id = session['doctor_id']
    
    if request.method == 'POST':
        history = request.form.get('history', '')
        diagnosis = request.form.get('diagnosis', '')
        
        new_record = PatientRecord(
            patient_id=patient_id,
            doctor_id=doctor_id,
            history=history,
            diagnosis=diagnosis
        )
        
        db.session.add(new_record)
        db.session.commit()
        
        # Handle prescription
        medicine_names = request.form.getlist('medicine_name[]')
        dosages = request.form.getlist('dosage[]')
        frequencies = request.form.getlist('frequency[]')
        durations = request.form.getlist('duration[]')
        
        mornings = request.form.getlist('morning[]')
        afternoons = request.form.getlist('afternoon[]')
        evenings = request.form.getlist('evening[]')
        
        days_list = request.form.getlist('days[]')
        
        for i in range(len(medicine_names)):
            if medicine_names[i]:
                # Check if medicine exists in database, if not add it
                medicine = Medicine.query.filter_by(name=medicine_names[i]).first()
                if not medicine:
                    new_medicine = Medicine(name=medicine_names[i])
                    db.session.add(new_medicine)
                    db.session.commit()
                
                # Create prescription
                prescription = Prescription(
                    record_id=new_record.id,
                    medicine_name=medicine_names[i],
                    dosage=dosages[i] if i < len(dosages) else '',
                    frequency=frequencies[i] if i < len(frequencies) else '',
                    duration=durations[i] if i < len(durations) else '',
                    morning=True if str(i) in mornings else False,
                    afternoon=True if str(i) in afternoons else False,
                    evening=True if str(i) in evenings else False,
                    days=days_list[i] if i < len(days_list) else ''
                )
                
                db.session.add(prescription)
        
        db.session.commit()
        flash('Patient record and prescription created successfully', 'success')
        return redirect(url_for('doctor_dashboard'))
    
    return render_template('doctor/create_record.html', patient=patient)

@app.route('/doctor/medicines')
@doctor_login_required
def get_medicines():
    medicines = Medicine.query.all()
    medicine_list = [medicine.name for medicine in medicines]
    return jsonify(medicine_list)

@app.route('/doctor/logout')
def doctor_logout():
    session.pop('doctor_id', None)
    session.pop('doctor_name', None)
    return redirect(url_for('home'))

# Staff Routes
@app.route('/staff/register', methods=['GET', 'POST'])
def staff_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        phone = request.form['phone']
        
        # Check if email already exists
        existing_staff = Staff.query.filter_by(email=email).first()
        if existing_staff:
            flash('Email already registered', 'danger')
            return redirect(url_for('staff_register'))
        
        hashed_password = generate_password_hash(password)
        new_staff = Staff(name=name, email=email, password=hashed_password, 
                         role=role, phone=phone)
        
        db.session.add(new_staff)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('staff_login'))
    
    return render_template('staff/register.html')

@app.route('/staff/login', methods=['GET', 'POST'])
def staff_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        staff = Staff.query.filter_by(email=email).first()
        
        if staff and check_password_hash(staff.password, password):
            session['staff_id'] = staff.id
            session['staff_name'] = staff.name
            session['staff_role'] = staff.role
            flash('Login successful!', 'success')
            return redirect(url_for('staff_dashboard'))
        else:
            flash('Invalid email or password', 'danger')
    
    return render_template('staff/login.html')

@app.route('/staff/dashboard')
@staff_login_required
def staff_dashboard():
    patients_count = Patient.query.count()
    doctors_count = Doctor.query.count()
    appointments_count = Appointment.query.count()
    pending_appointments = Appointment.query.filter_by(status='Pending').count()
    
    return render_template('staff/dashboard.html', 
                          patients_count=patients_count,
                          doctors_count=doctors_count,
                          appointments_count=appointments_count,
                          pending_appointments=pending_appointments)

@app.route('/staff/patients')
@staff_login_required
def staff_patients():
    patients = Patient.query.all()
    return render_template('staff/patients.html', patients=patients)

@app.route('/staff/doctors')
@staff_login_required
def staff_doctors():
    doctors = Doctor.query.all()
    return render_template('staff/doctors.html', doctors=doctors)

@app.route('/staff/appointments')
@staff_login_required
def staff_appointments():
    appointments = Appointment.query.order_by(Appointment.appointment_date.desc()).all()
    return render_template('staff/appointments.html', appointments=appointments)

@app.route('/staff/appointment/<int:id>/update', methods=['POST'])
@staff_login_required
def update_appointment(id):
    appointment = Appointment.query.get_or_404(id)
    appointment.status = request.form['status']
    db.session.commit()
    flash('Appointment status updated successfully', 'success')
    return redirect(url_for('staff_appointments'))

@app.route('/staff/logout')
def staff_logout():
    session.pop('staff_id', None)
    session.pop('staff_name', None)
    session.pop('staff_role', None)
    return redirect(url_for('home'))

# Appointment Routes
@app.route('/appointment', methods=['GET', 'POST'])
def appointment():
    if request.method == 'POST':
        patient_name = request.form['name']
        age = request.form['age']
        gender = request.form['gender']
        symptoms = request.form['symptoms']
        department = request.form['department']
        doctor_id = request.form['doctor']
        appointment_date_str = request.form['appointment_date']
        
        # Convert string date to datetime
        appointment_date = datetime.strptime(appointment_date_str, '%Y-%m-%dT%H:%M')
        
        # Check if the patient is logged in
        patient_id = session.get('patient_id')
        
        new_appointment = Appointment(
            patient_name=patient_name,
            patient_id=patient_id,
            age=age,
            gender=gender,
            symptoms=symptoms,
            department=department,
            doctor_id=doctor_id,
            appointment_date=appointment_date
        )
        
        db.session.add(new_appointment)
        db.session.commit()
        
        flash('Appointment booked successfully!', 'success')
        return redirect(url_for('appointment_confirmation', id=new_appointment.id))
    
    doctors = Doctor.query.all()
    return render_template('appointment/book.html', doctors=doctors)

@app.route('/appointment/confirmation/<int:id>')
def appointment_confirmation(id):
    appointment = Appointment.query.get_or_404(id)
    doctor = Doctor.query.get(appointment.doctor_id)
    return render_template('appointment/confirmation.html', appointment=appointment, doctor=doctor)

@app.route('/departments')
def get_departments():
    departments = [
        'Cardiology', 'Dermatology', 'Endocrinology', 'Gastroenterology',
        'Neurology', 'Oncology', 'Orthopedics', 'Pediatrics', 'Psychiatry',
        'Radiology', 'Urology'
    ]
    return jsonify(departments)

@app.route('/doctors/by-department/<department>')
def get_doctors_by_department(department):
    doctors = Doctor.query.filter_by(specialization=department).all()
    doctor_list = [{'id': doctor.id, 'name': doctor.name} for doctor in doctors]
    return jsonify(doctor_list)

# Initialize database
with app.app_context():
    db.create_all()
    
    # Add initial data if database is empty
    if not Medicine.query.first():
        common_medicines = [
            'Paracetamol', 'Aspirin', 'Ibuprofen', 'Amoxicillin',
            'Ciprofloxacin', 'Metformin', 'Omeprazole', 'Atorvastatin',
            'Levothyroxine', 'Amlodipine', 'Lisinopril', 'Ceftriaxone'
        ]
        
        for medicine_name in common_medicines:
            medicine = Medicine(name=medicine_name)
            db.session.add(medicine)
        
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)