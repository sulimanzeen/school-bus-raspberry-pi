import mysql.connector
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import drivers
import serial
import pynmea2
import requests
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv


load_dotenv()


#GPIO BCM MODE  
GPIO.setmode(GPIO.BCM)
display = drivers.Lcd()

GLOBALSELFBUSID = 3
# Connect to MySQL
display.lcd_display_string("Starting...", 1)
time.sleep(1)

#FOR GPS MODULE



# CHECK IN ID = 0 // CHECK OUT ID = 1


#Timestamp Logic

utc_plus_4 = timezone(timedelta(hours=4))
current_time = datetime.now(utc_plus_4)
timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")


#MY Whatsapp API LINK
#I have my own private api set-up on another private server That handles whatsapp messages.
WHATSAPP_API_URL = "http://138.201.246.236:3000/api/sendText"

#Important function for gps



def get_gps_coordinates_First():
    """
    Reads data from NEO-6M GPS and returns latitude, longitude, altitude,
    and Google Maps link.
    Returns:
        dict: {
            "latitude": float,
            "longitude": float,
            "altitude": float,
            "google_maps": str
        }
        or None if GPS data not ready
    """
    port = serial.Serial("/dev/serial0", baudrate=9600, timeout=1)
    try:
        display.lcd_display_string("Loading GPS...", 2)
        timeout = 5  # seconds
        start_time = time.time()
        while True:
             
            if time.time() - start_time > timeout:

                print("Timeout reached. Exiting loop.")
                break
             
            data = port.readline().decode('ascii', errors='replace')
            if data.startswith('$GPGGA'):  # Position info
                msg = pynmea2.parse(data)
                latitude = msg.latitude
                longitude = msg.longitude
                altitude = msg.altitude

                # Generate Google Maps link
                google_maps = f"https://www.google.com/maps/search/?api=1&query={latitude},{longitude}"

                return {
                    "latitude": latitude,
                    "longitude": longitude,
                    "altitude": altitude,
                    "google_maps": google_maps
                }
            

    except pynmea2.ParseError:
        return None
    except Exception as e:
        print(f"GPS Error: {e}")
        return None



Location_cache = get_gps_coordinates_First()
print(get_gps_coordinates_First())

try:

    db = mysql.connector.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    database=os.getenv("DB_NAME")
)
    
    
except mysql.connector.Error as err:
    print(f"Error: {err}")
    display.lcd_clear()
    display.lcd_display_string("Error: MYSQL", 1)
    display.lcd_display_string("Can't Connect", 2)
    time.sleep(5)
    display.lcd_clear()
    exit(1)

#Connected To MYSQL!
display.lcd_display_string("Cloud Server", 1)
display.lcd_display_string("Connected!", 2)
time.sleep(5)
display.lcd_clear()

StudentSet = set()
reader = SimpleMFRC522()

GPIO.setup(21, GPIO.OUT)
GPIO.output(21, GPIO.LOW)
display.lcd_display_string("Awaiting Driver", 1)
display.lcd_display_string("To Start Trip!", 2)
time.sleep(2)

while True:
     try:
            
            cursorbus = db.cursor()
            query = f"SELECT * FROM `bus` WHERE bus_id = {GLOBALSELFBUSID}"
            cursorbus.execute(query)
            # Fetch the first row
            rowbus = cursorbus.fetchone()
            trip_status = rowbus[4] #Bus Trip status column
            if(trip_status == 1):
                 display.lcd_clear()
                 display.lcd_display_string("Trip Started", 1)
                 display.lcd_display_string("Loading...", 2)
                 
                 #BEEP Script
                 GPIO.output(21, GPIO.HIGH)
                 time.sleep(1)
                 GPIO.output(21, GPIO.LOW)
                 #Breaking this while loop. to start another while loop!
                 break
            else:
                 time.sleep(2)    
     except Exception as e:
                        
                        print(f"Error: {e}")
             



#Before running actual app. driver need to start the trip!


while True:
    try:
        
        #Buzzer Pin
        display.lcd_clear()

        
        if(Current_Bus_Trip_Status == 1):
              display.lcd_display_string("Trip Ended", 1)
              display.lcd_display_string("New Session...", 2)
              #TWO BEEPS
              GPIO.output(21, GPIO.HIGH)
              time.sleep(1)
              GPIO.output(21, GPIO.LOW)
              time.sleep(1)
              GPIO.output(21, GPIO.HIGH)
              time.sleep(1)
              GPIO.output(21, GPIO.LOW)
              
              #Starting the loop again as new session :)
              continue




        display.lcd_display_string("Pass Your Key", 1)  # Write line of text to first line of display
        display.lcd_display_string("Card", 2)
        print("Hold tag near the reader...")
        RFIDid, text = reader.read()
        # Turn on buzzer
        GPIO.output(21, GPIO.HIGH)
        time.sleep(0.5)
        display.lcd_clear()
        GPIO.output(21, GPIO.LOW)
        print(f"ID: {RFIDid}\nText: {text}")
    except KeyboardInterrupt:
        display.lcd_clear()
        GPIO.output(21, GPIO.LOW)
        print("Exiting...")    
    finally:
         # Create a cursor object
        cursor = db.cursor()
        cursor2 = db.cursor()
        cursor3 = db.cursor()

        # Write your SELECT query
        query = f"SELECT * FROM `student` WHERE student_rfid = {RFIDid}"
        querybusdetails = f"SELECT * FROM `bus` WHERE `bus_id` = {GLOBALSELFBUSID}"
        querybustripstatus = f"SELECT * FROM `bus` WHERE bus_id = {GLOBALSELFBUSID}"
        # Execute the query
        cursor.execute(query)
        
        # Fetch the first row
        row = cursor.fetchone()

        cursor2.execute(querybusdetails)
        row2 = cursor2.fetchone()
        cursor3.execute(querybustripstatus)
        row3 = cursor2.fetchone()
        Current_Bus_Trip_Status = row3[4] #Trip status

        
        
        if row:
            # [student_id, parent_id, student_name, student_rfid]
            student_name = row[3]  # Assuming student_name is the third column column
            student_id = row[0]
            parent_id = row[1]
            student_bus_id = row[2]

            bus_id = row2[0]
            bus_driver_name = row2[1]
            bus_model = row2[2]
            bus_capacity = row2[3]

            

            if(student_bus_id != GLOBALSELFBUSID):
                 #Two beeps for wrong bus!
                 display.lcd_display_string("Access Denied:", 1)
                 display.lcd_display_string("Wrong Bus!", 2)
                 GPIO.output(21, GPIO.HIGH)
                 time.sleep(0.5)
                 GPIO.output(21, GPIO.LOW)
                 time.sleep(0.5)
                 GPIO.output(21, GPIO.HIGH)
                 time.sleep(0.5)
                 display.lcd_clear()
                 GPIO.output(21, GPIO.LOW)
                 continue

            print(f"Student Found: {student_name} ")
            
            if(RFIDid in StudentSet):
                StudentSet.remove(RFIDid)
                display.lcd_display_string("Checked Out:", 1)
                display.lcd_display_string(f'ID: {student_name}', 2)
                queryCheckingIN = """
                INSERT INTO attendance (student_id, bus_id, type, timestamp)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """
                values = (student_id, student_bus_id, 1)

                cursor.execute(queryCheckingIN, values)
                db.commit()
                #GRAB GPS DATA HERE 
                coords = get_gps_coordinates_First() # Get GPS coordinates
                print(coords)
                if(coords is None):
                     #Last caught location. just for handling errors
                     coords = Location_cache
                     
                display.lcd_clear()
                display.lcd_display_string("Checked In:", 1)
                display.lcd_display_string(f'ID: {student_name}', 2)
                queryCheckingIN = """
                INSERT INTO attendance (student_id, bus_id, type, timestamp)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """
                values = (student_id, student_bus_id, 0)
                
                cursor.execute(queryCheckingIN, values)
                db.commit()
                if coords:
                        
                        google_link = coords['google_maps']

                        query = "SELECT * FROM `parent` WHERE `parent_id` = %s"
                        cursor.execute(query, (parent_id,))
                        parent_result = cursor.fetchone()
                        parent_name = parent_result[1]  # name is the second column
                        parent_phone = parent_result[2]  # phone number is the third column

                        # Create message text dynamically
                        message_text = (
                            f"Hello {parent_name},\n"
                            f"Your child {student_name} has just Checked-OUT from school bus with ID {student_bus_id} "
                            f"at location {google_link} "
                            f"on {timestamp}."
                        )

                        # JSON payload
                        payload = {
                            "chatId": f"{parent_phone}@c.us",
                            "text": f"{message_text}!",
                            "session": "default"
                        }
                            # Send POST request
                        try:
                            response = requests.post(WHATSAPP_API_URL, json=payload)
                            # Print response status and content
                            print(f"POST REQUEST SENT | Status code: {response.status_code}")
                            # print(f"Response: {response.text}")
                        except Exception as e:
                            print(f"Error: {e}")


                        print("Google Maps URL:", google_link)
                        #logic to send sms with link
                else:
                    #logic send message gps not available    
                    print("GPS data not available.")

                    query = "SELECT * FROM `parent` WHERE `parent_id` = %s"
                    cursor.execute(query, (parent_id,))
                    parent_result = cursor.fetchone()
                    parent_name = parent_result[1]  # name is the second column
                    parent_phone = parent_result[2]  # phone number is the third column

                    # Create message text dynamically
                    message_text = (
                            f"Hello {parent_name},\n"
                            f"Your child {student_name} has just Checked-OUT from school bus with ID {student_bus_id} "
                            f"at location NOT AVAIABLE! "
                            f"on {timestamp}."
                    )

                            # JSON payload
                    payload = {
                            "chatId": f"{parent_phone}@c.us",
                            "text": f"{message_text}!",
                            "session": "default"
                    }
                            # Send POST request
                    try:
                                response = requests.post(WHATSAPP_API_URL, json=payload)
                                # Print response status and content
                                print(f"POST REQUEST SENT | Status code: {response.status_code}")
                                # print(f"Response: {response.text}")
                    except Exception as e:
                        print(f"Error: {e}")
                #OPEN DOOR FOR 5 SECONDS AND THEN CLOSE!

                
                
            else:

                if(len(StudentSet) >= bus_capacity):
                 #Two beeps for bus overcrow
                 display.lcd_display_string("Access Denied:", 1)
                 display.lcd_display_string("Bus Overcrowded!", 2)
                 GPIO.output(21, GPIO.HIGH)
                 time.sleep(0.5)
                 GPIO.output(21, GPIO.LOW)
                 time.sleep(0.5)
                 GPIO.output(21, GPIO.HIGH)
                 time.sleep(0.5)
                 display.lcd_clear()
                 GPIO.output(21, GPIO.LOW)
                 continue


                StudentSet.add(RFIDid)
                display.lcd_display_string("Querying...", 1)  
                
                coords = get_gps_coordinates_First() # Get GPS coordinates
                print(coords)
                if(coords is None):
                     #Last caught location. just for handling errors
                     coords = Location_cache
                     
                display.lcd_clear()
                display.lcd_display_string("Checked In:", 1)
                display.lcd_display_string(f'ID: {student_name}', 2)
                queryCheckingIN = """
                INSERT INTO attendance (student_id, bus_id, type, timestamp)
                VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                """
                values = (student_id, student_bus_id, 0)
                
                cursor.execute(queryCheckingIN, values)
                db.commit()
                if coords:
                        
                        google_link = coords['google_maps']

                        query = "SELECT * FROM `parent` WHERE `parent_id` = %s"
                        cursor.execute(query, (parent_id,))
                        parent_result = cursor.fetchone()
                        parent_name = parent_result[1]  # name is the second column
                        parent_phone = parent_result[2]  # phone number is the third column

                        # Create message text dynamically
                        message_text = (
                            f"Hello {parent_name},\n"
                            f"Your child {student_name} has just Checked-IN to school bus with ID {student_bus_id} "
                            f"at location {google_link} "
                            f"on {timestamp}."
                        )

                        # JSON payload
                        payload = {
                            "chatId": f"{parent_phone}@c.us",
                            "text": f"{message_text}!",
                            "session": "default"
                        }
                            # Send POST request
                        try:
                            response = requests.post(WHATSAPP_API_URL, json=payload)
                            # Print response status and content
                            print(f"POST REQUEST SENT | Status code: {response.status_code}")
                            # print(f"Response: {response.text}")
                        except Exception as e:
                            print(f"Error: {e}")


                        print("Google Maps URL:", google_link)
                        #logic to send sms with link
                else:
                    #logic send message gps not available    
                    print("GPS data not available.")

                    query = "SELECT * FROM `parent` WHERE `parent_id` = %s"
                    cursor.execute(query, (parent_id,))
                    parent_result = cursor.fetchone()
                    parent_name = parent_result[1]  # name is the second column
                    parent_phone = parent_result[2]  # phone number is the third column

                    # Create message text dynamically
                    message_text = (
                            f"Hello {parent_name},\n"
                            f"Your child {student_name} has just Checked-IN to school bus with ID {student_bus_id} "
                            f"at location NOT AVAIABLE! "
                            f"on {timestamp}."
                    )

                            # JSON payload
                    payload = {
                            "chatId": f"{parent_phone}@c.us",
                            "text": f"{message_text}!",
                            "session": "default"
                    }
                            # Send POST request
                    try:
                                response = requests.post(WHATSAPP_API_URL, json=payload)
                                # Print response status and content
                                print(f"POST REQUEST SENT | Status code: {response.status_code}")
                                # print(f"Response: {response.text}")
                    except Exception as e:
                        print(f"Error: {e}")
              
                       

                #GRAB GPS DATA HERE

                #OPEN DOOR FOR 5 SECONDS AND THEN CLOSE!

                #API TO SEND MESSAGE!


            #GPIO.cleanup()
            print("SLeeping for 2 seconds before next read...")
            time.sleep(5)
            display.lcd_clear()
        else:
            print("Student Not Found")
            display.lcd_display_string("Unknown Key!", 1)
            display.lcd_display_string("Access Denied!", 2)
            GPIO.output(21, GPIO.HIGH)
            time.sleep(2)
            GPIO.output(21, GPIO.LOW)
            #GPIO.cleanup()
            print("SLeeping for 2 seconds before next read...")
            time.sleep(5)
            display.lcd_clear()

