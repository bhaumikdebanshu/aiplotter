from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, MetaData
from sqlalchemy.sql import func
import os
from transformers import pipeline
import serial
import time
import csv 
from io import StringIO
import os
from transformers import pipeline
import serial
import time
import csv 
from io import StringIO


# Configuration
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define a sample model
class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    answerText = db.Column(db.Text)
    emotions = db.Column(db.JSON, nullable=False)  # Store emotions as JSON

    def __repr__(self):
        return '<Response %r>' % self.id 

    
# Database Management Functions
def create_database():
    """Create all tables based on models."""
    with app.app_context():
        db.create_all()
    print("Database and tables created.")

def drop_database():
    """Drop all tables in the database."""
    with app.app_context():
        db.drop_all()
    print("Database and tables dropped.")

# Utility Functions
def emotional_analysis(text):
    emotion_pipeline = pipeline("text-classification", model="ayoubkirouane/BERT-Emotions-Classifier", top_k=None)
    results = emotion_pipeline(text)
    emotion_dict = {result['label']: round(result['score'] * 100, 3) for result in results[0]}
    
    return emotion_dict

def add_sample_data():
    """Add sample data to the database."""
    with app.app_context():
        emotions=emotional_analysis("I'm feeling great today!")
        sample1 = Response(answerText="I'm feeling great today!", emotions=emotions)
        emotions=emotional_analysis("I'm feeling terrible today.")
        sample2 = Response(answerText="I'm feeling terrible today.", emotions=emotions)
        db.session.add(sample1)
        db.session.add(sample2)
        db.session.commit()
    print("Sample data added to the database.")

def reset_database():
    """Reset the database by dropping and recreating tables."""
    drop_database()
    create_database()
    print("Database has been reset.")

# Web Routes
@app.route('/')
def responses():
    responses = Response.query.all()
    return render_template('responses.html', responses=responses)

@app.route('/entry/', methods=['GET', 'POST'])
def entry():
    if request.method == 'POST':
        tempAnswer = request.form['response']
        emotion_percentages = emotional_analysis(tempAnswer)
        print(emotion_percentages)
        entry = Response(answerText=tempAnswer, emotions=emotion_percentages)
        db.session.add(entry)
        db.session.commit()
        return redirect(url_for('responses'))
    return render_template('entry.html')

@app.route('/printing/')
def printing():
    answers = Response.query.all()
    # Open grbl serial port
    s = serial.Serial('/dev/cu.usbmodem101',115200)

    # Open g-code file
    # f = open('/static/test.gcode','r')
    f = open(os.path.join(basedir, 'static/test.gcode'),'r')

    # Wake up grbl
    temp = "\r\n\r\n"
    s.write(temp.encode('ascii'))
    time.sleep(2)   # Wait for grbl to initialize 
    s.flushInput()  # Flush startup text in serial input
    print ('Sending gcode')

    # Stream g-code
    for line in f:
        # l = removeComment(line)
        l = line.strip() # Strip all EOL characters for streaming
        if  (l.isspace()==False and len(l)>0) :
            print ('Sending: ' + l)
            temp2 = l + "\n"
            s.write(temp2.encode('ascii')) # Send g-code block
            grbl_out = s.readline() # Wait for response with carriage return
            print (grbl_out.strip())

    # Wait here until grbl is finished to close serial port and file.
    # raw_input("  Press <Enter> to exit and disable grbl.") 

    # Close file and serial port
    f.close()
    s.close()  

    return render_template('printing.html', answers = answers), {"Refresh" : "5; url= /entry"}

@app.route('/clear/')
def clear_responses():
    try:
        # Delete all records from the table
        db.session.query(Response).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        # Handle the exception as you see fit (log it, flash a message to the user, etc.)
    return redirect(url_for('responses'))  # Redirect to the main page or wherever is appropriate

@app.route('/export/')
def export_responses():
    responses = Response.query.all()
    # Generate CSV data
    csv_data = []
    header = ["Response ID", "Prompt", "Optimism", "Joy", "Fear", "Anticipation", "Love", "Trust", "Sadness", "Pessimism", "Surprise", "Disgust", "Anger"]
    csv_data.append(header)

    for response in responses:
        values = response.emotions.values()
        values_csv = [str(value) for value in values]
        csv_row = [response.id, response.answerText] + values_csv
        csv_data.append(csv_row)

    # Convert the data into a CSV string
    si = StringIO()
    cw = csv.writer(si)
    cw.writerows(csv_data)
    output = si.getvalue()

    # Return the CSV file
    return output, 200, {
        "Content-Disposition": "attachment; filename=responses.csv",
        "Content-Type": "text/csv",
    }

# Example usage (comment out if you prefer to run these from the command line or another script)
if __name__ == "__main__":
    # Create or reset the database
    # reset_database()
    # add_sample_data()

    # Run the app
    app.run(debug=True)
