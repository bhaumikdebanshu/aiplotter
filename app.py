import os
import serial
import time
from flask import Flask, render_template, request, url_for, redirect
from flask_sqlalchemy import SQLAlchemy

from sqlalchemy.sql import func

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] =\
        'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    answerText = db.Column(db.Text)

    def __repr__(self):
        return f'<Answer {self.id}>'


@app.route('/')
def responses():
    answers = Answer.query.all()
    return render_template('responses.html', answers=answers)

@app.route('/entry/', methods=('GET', 'POST'))
def entry():
    if request.method == 'POST':
        tempAnswer = request.form['response']
        entry = Answer(answerText = tempAnswer)
        db.session.add(entry)
        db.session.commit()

        return redirect(url_for('printing'))
    
    return render_template('entry.html')

@app.route('/printing/')
def printing():
    answers = Answer.query.all()
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