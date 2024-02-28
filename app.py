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
import json
import numpy as np

# Configuration
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
plotter_endpoint = '/dev/cu.usbmodem101'
plotter_port = 115200

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
    emotion_pipeline = pipeline(
        "text-classification",
        model="ayoubkirouane/BERT-Emotions-Classifier",
        top_k=None,
    )
    results = emotion_pipeline(text)

    # Send the % of each emotion, the total sum of all emotions is 100%
    total = sum([result["score"] for result in results[0]])
    emotion_dict = {
        result["label"]: round(result["score"] * 50 / total) for result in results[0]
    }

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

def load_curve_data():
    with open('static/curveDict.json', 'r') as f:
        data = json.load(f)
    return data

def get_sine_wave(i, w = 770, h = 2290):
    x = np.linspace(0, w, w)
    period = np.interp(i, [0, h], [18, 36])
    # Create values for the y-axis
    y = np.sin((x + i) / period) * 5 + i
    return x, y

def get_curve(emotions, curveDict, w=770, h=2290):
    import numpy as np

    # Generate X with a fixed resolution
    X = np.linspace(0, w, 1000)  # 1000 points along the width

    # Initialize Y as zeros - ensures it matches X in length
    Y = []

    for emotion, score in emotions.items():
        # Only process if score > 0 to avoid unnecessary computations
        if score > 0:
            bounds_x, bounds_y = curveDict[emotion]["bounds"]
            xsteps = len(X)//50  # Use the length of X to determine the steps
            
            # Generate x values within the bounds for the current emotion
            x = np.linspace(bounds_x[0], bounds_x[1], xsteps)
            
            # Calculate y values based on the function defined in curveDict
            y = eval(curveDict[emotion]["function"], {"np": np, "abs": abs, "min": min}, {"x": x})

            # If there is any NaN value in y, replace it with 0
            y = np.nan_to_num(y)
            
            y = np.interp(y, (bounds_y[0], bounds_y[1]), (-2.5, 2.5))
            
            # Append the y values to Y based on the score: If score=1, append y once; if score=2, append y twice, and so on
            for i in range(int(score)):
                Y.extend(y)

    # Convert Y to a numpy array and reshape it to match the desired dimensions
    Y = np.array(Y).flatten()
    Y.resize(w)

    X = np.linspace(0, w, len(Y))
    X.resize(w)

    return X, Y

def is_plotter_connected():
    try:
        s = serial.Serial(plotter_endpoint, plotter_port)
        s.close()
        return True
    except:
        return False

def is_plotter_ready():
    try:
        s = serial.Serial(plotter_endpoint, plotter_port)
        s.write(b"\r\n\r\n")
        time.sleep(2)
        s.flushInput()
        s.write(b"$G\n")
        grbl_out = s.readline()
        s.close()
        return grbl_out == b"ok\n"
    except:
        return False

def generate_gcode(points, filename="output.gcode", feed_rate=1000):
    """
    Generate a GCode file from a set of points.

    Args:
    - points (list of tuple): List of (x, y) tuples representing the points.
    - filename (str): Name of the GCode file to be written.
    - feed_rate (int): Feed rate for drawing movements.
    """
    with open(filename, 'w') as file:
        # Header
        file.write("G21 ; Set units to mm\n")
        file.write("G90 ; Absolute positioning\n")
        
        # Pen down G1 Z50
        file.write("G1 Z50\n")
        
        # Move to the starting point without drawing
        start_point = points[0]
        file.write(f"G0 X{start_point[0]} Y{start_point[1]}\n")
        
        # Optionally, lower the pen down with G0 Z0.0 here if working with a pen plotter

        # Draw to each subsequent point
        for x, y in points[1:]:
            file.write(f"G1 X{x} Y{y} F{feed_rate}\n")

        # Pen up G1 Z10
        file.write("G1 Z10\n")
        
        # Footer or end commands can be added here

    print(f"GCode file '{filename}' has been generated.")

def gcode_wrapper(prompt, i):
    curveDict = load_curve_data()
    emotions = emotional_analysis(prompt)
    x, y = get_curve(emotions, curveDict)
    x2,y2 = get_sine_wave(i)
    y = y + y2

    points = list(zip(x, y))
    
    generate_gcode(points, f"static/gcode/output_{i}.gcode")

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

        # Generate GCode
        gcode_wrapper(tempAnswer, entry.id)
        return redirect(url_for('responses'))
    return render_template('entry.html')

@app.route('/printing/')
def printing():
    answers = Response.query.all()
    # Open grbl serial port
    s = serial.Serial(plotter_endpoint, plotter_port)

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
