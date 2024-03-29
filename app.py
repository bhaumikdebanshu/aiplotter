from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
import os
import serial
import time
import csv 
from io import StringIO
import config
from logging import warn
import artist

# Configuration
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
plotter_endpoint = config.plotter_endpoint
plotter_baudrate = config.plotter_baudrate

plotter = None 

# plotter = serial.Serial(plotter_endpoint, plotter_baudrate)

# try:
#     plotter = serial.Serial(plotter_endpoint, plotter_baudrate)
# except Exception as e:
#     warn(f"Error opening serial port: {e}")
#     plotter.close()  # Close the serial port if the app crashes


# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define a sample model
class Response(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    answerText = db.Column(db.Text)
    emotions = db.Column(db.JSON, nullable=False)  # Store emotions as JSON
    gcode_path = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return '<Response %r>' % self.id 
    
# Database Management Functions
def create_database():
    """Create all tables based on models."""
    try:
        with app.app_context():
            db.create_all()
        print("Database and tables created.")
    except Exception as e:
        warn(f"Error creating database: {e}")

def drop_database():
    """Drop all tables in the database."""
    try:
        with app.app_context():
            db.drop_all()
        print("Database and tables dropped.")
    except Exception as e:
        warn(f"Error dropping database: {e}")

# Utility Functions
def add_sample_data():
    """Add sample data to the database."""
    try:
        with app.app_context():
            emotions= artist.emotional_analysis("I'm feeling great today!")
            sample1 = Response(answerText="I'm feeling great today!", emotions=emotions)
            emotions= artist.emotional_analysis("I'm feeling terrible today.")
            sample2 = Response(answerText="I'm feeling terrible today.", emotions=emotions)
            db.session.add(sample1)
            db.session.add(sample2)
            db.session.commit()
        print("Sample data added to the database.")
    except Exception as e:
        warn(f"Error adding sample data: {e}")

def reset_database():
    """Reset the database by dropping and recreating tables."""
    try:
        drop_database()
        create_database()
        print("Database has been reset.")
    except Exception as e:
        warn(f"Error resetting database: {e}")

# Web Routes
@app.route('/')
def responses():
    responses = Response.query.all()
    return render_template('responses.html', responses=responses)

@app.route('/entry/', methods=['GET', 'POST'])
def entry():
    if request.method == 'POST':
        tempAnswer = request.form['response']
        emotion_percentages = artist.emotional_analysis(tempAnswer)
        print(emotion_percentages)

        # Get the last id from the database 
        last_id = db.session.query(Response).order_by(Response.id.desc()).first().id if db.session.query(Response).count() > 0 else -1
        new_id = (last_id + 1) % config.max_curves

        # If max_curves is reached, throw a alert on frontend
        if new_id == 0:
            return redirect(url_for('results'))

        gcode_file = artist.gcode_wrapper(tempAnswer, new_id)
        entry = Response(answerText=tempAnswer, emotions=emotion_percentages, gcode_path=gcode_file)

        db.session.add(entry)
        db.session.commit()

        return redirect(url_for('printing'))
    return render_template('entry.html')

@app.route('/printer-test/', methods=['GET', 'POST'])
def printer_test():
    # Open grbl serial port
    # s = serial.Serial(plotter_endpoint, plotter_baudrate)
    # Wake up grbl
    temp = "\r\n\r\n" 
    plotter.write(temp.encode('ascii'))
    time.sleep(2)

    # Send home command
    plotter.write("$H\n".encode('ascii'))
    time.sleep(5)

    # Print log 
    print(plotter.readline())

    plotter.flushInput()
    # plotter.close()
    # return redirect(url_for('entry'))
    return render_template('printer-test.html')

@app.route('/printing/')
def printing():
    responses = Response.query.all()
    # Open grbl serial port
    # s = serial.Serial(plotter_endpoint, plotter_baudrate)

    # Open the last gcode file
    gcode_file = Response.query.order_by(Response.id.desc()).first().gcode_path

    # Open g-code file
    # f = open('/static/test.gcode','r')
    f = open(os.path.join(basedir, gcode_file),'r')

    # Wake up grbl
    temp = "\r\n\r\n"
    plotter.write(temp.encode('ascii'))
    time.sleep(2)   # Wait for grbl to initialize 
    plotter.flushInput()  # Flush startup text in serial input
    print ('Sending gcode')

    # Stream g-code
    for line in f:
        # l = removeComment(line)
        l = line.strip() # Strip all EOL characters for streaming
        if  (l.isspace()==False and len(l)>0) :
            print ('Sending: ' + l)
            temp2 = l + "\n"
            plotter.write(temp2.encode('ascii')) # Send g-code block
            grbl_out = plotter.readline() # Wait for response with carriage return
            print (grbl_out.strip())

    # Wait here until grbl is finished to close serial port and file.
    # raw_input("  Press <Enter> to exit and disable grbl.") 

    # Close file and serial port
    f.close()
    # plotter.close()  

    return render_template('printing.html', responses = responses), {"Refresh" : "45; url= /entry"}

@app.route('/results/')
def results():
    responses = Response.query.all()
    return render_template('results.html', responses=responses)

@app.route('/diag/')
def diag():
    print("Be careful what you do here")
    return render_template('diag.html')

@app.route('/plotter-connect/')
def plotterConnect():
    print("Plotter Connected")
    global plotter
    try: 
        if plotter:
            if plotter.is_open:
                plotter.close() 
                return render_template('diag.html')
        
        plotter = serial.Serial(plotter_endpoint, plotter_baudrate)

    except Exception as e:
        warn(f"Error opening serial port: {e}")
        plotter.close()

    return render_template('diag.html')

@app.route('/plotter-home/')
def returnToHome():
    print("Seeking (0,0)")

    _ = artist.do(plotter, config.plotter_commands["wake_up"], 2)
    home_status = artist.do(plotter, config.plotter_commands["home"], 5)
    print(home_status)
    plotter.flushInput()
    
    return render_template('diag.html')

@app.route('/change-paper-pen/')
def changePaperPen():
    print("Change Paper or Pen")

    move_to_end_status = artist.do(plotter, config.plotter_commands["endpoint"], 5)
    print(move_to_end_status)
    plotter.flushInput()

    return render_template('diag.html')

@app.route('/disconnect-plotter/')
def disconnectPlotter():
    print("Disconnect Plotter")
    global plotter
    try:
        plotter.close()
    except Exception as e:
        warn(f"Error closing serial port: {e}")
    return render_template('diag.html')


@app.route('/clear/')
def clear_responses():
    try:
        # Delete all records from the table
        db.session.query(Response).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        warn(f"Error clearing responses: {e}")
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
    reset_database() if config.db_reset else None
    # add_sample_data()

    # Create static/gcode directory if it doesn't exist
    if not os.path.exists("static/gcode"):
        os.makedirs("static/gcode")

    # Run the app
    try:
        app.run(debug=True)
    except Exception as e:
        warn(f"Error running the app: {e}")
        plotter.close()  # Close the serial port if the app crashes
