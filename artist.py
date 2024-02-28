import config 
from logging import warn
import numpy as np
import time
import serial
import json
from transformers import pipeline

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

def load_curve_data():
    try:
        with open('static/curveDict.json', 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        warn(f"Error loading curve data: {e}")
        return None


def get_sine_wave(i, w=config.canvas_dimensions[0], h=config.canvas_dimensions[1]):
    try: 
        x = np.linspace(0, w, config.horizontal_resolution)
        period = np.interp(i, [0, h], [18, 36])
        # Create values for the y-axis
        y = np.sin((x + i) / period) * 5 + i
        y.resize(config.horizontal_resolution)
        return x, y
    except Exception as e:
        warn(f"Error generating sine wave: {e}")
        return None, None
    
def get_curve(emotions, curveDict, w=config.canvas_dimensions[0], h=config.canvas_dimensions[1]):
    # Generate X with a fixed resolution
    X = np.linspace(0, w, config.horizontal_resolution)

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
            
            y = np.interp(y, (bounds_y[0], bounds_y[1]), (-config.curve_amplitude/2, config.curve_amplitude/2))
            
            # Append the y values to Y based on the score: If score=1, append y once; if score=2, append y twice, and so on
            for i in range(int(score)):
                Y.extend(y)

    # Convert Y to a numpy array and reshape it to match the desired dimensions
                
    Y = np.array(Y).flatten()               # Convert to a 1D array, if necessary
    Y.resize(config.horizontal_resolution)  # Resize to match the horizontal resolution, if necessary

    X = np.linspace(0, w, len(Y))
    X.resize(config.horizontal_resolution)  # Resize to match the horizontal resolution, if necessary

    return X, Y

def is_plotter_connected():
    try:
        s = serial.Serial(config.plotter_endpoint, config.plotter_port)
        s.close()
        return True
    except Exception as e:
        warn(f"Error checking plotter connection: {e}")
        return False

def is_plotter_ready():
    try:
        s = serial.Serial(config.plotter_endpoint, config.plotter_port)
        s.write(b"\r\n\r\n")
        time.sleep(2)
        s.flushInput()
        s.write(b"$G\n")
        grbl_out = s.readline()
        s.close()
        return grbl_out == b"ok\n"
    except Exception as e:
        warn(f"Error checking plotter readiness: {e}")
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