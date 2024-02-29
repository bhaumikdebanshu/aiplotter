db_reset                = True                          # Reset the database on start up
plotter_endpoint_prod   = "/dev/cu.usbmodem101"         # Serial port of the plotter
plotter_endpoint_test   = "COM4" 
plotter_endpoint        = plotter_endpoint_test         # Serial port of the plotter
plotter_baudrate        = 115200                        # Baud rate of the plotter
canvas_dimensions       = (724, 2150)                   # Width and height of the canvas in mm 
horizontal_resolution   = 100                           # Number of steps in the horizontal direction (x-axis)
curve_amplitude         = 10.0                          # Amplitude of individual curves in mm
feed_rate_xy            = 1000                          # Feed rate in mm/min
feed_rate_z             = 500                           # Feed rate in mm/min
global_origin           = (0, 50)                       # Origin of the plotter in mm
curve_spacing           = 100.0                         # Distance between curves in mm (y-axis)
plotter_commands        = {
    "wake_up": "\r\n\r\n",
    "home": "$H\n",
    "endpoint": f"G0 X{canvas_dimensions[0]} Y{canvas_dimensions[1]} F{feed_rate_xy}\n"
}