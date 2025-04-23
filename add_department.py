# Replace 'app' with the name of your main application file (without the .py extension)
from main import app, db, Department

with app.app_context():
    # Check if department already exists
    existing = Department.query.filter_by(id=1).first()
    if existing:
        print("Department with ID 1 already exists. Updating...")
        existing.name = 'Radiology Department'
        existing.role = 'Diagnostic Imaging'
        existing.phone = '555-123-4567'
    else:
        # Create new department
        radiology = Department(
            id=1,
            name='Radiology Department',
            role='Diagnostic Imaging',
            phone='555-123-4567'
        )
        db.session.add(radiology)
    
    db.session.commit()
    print('Department added successfully')