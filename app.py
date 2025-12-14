import asyncio
import mysql.connector
import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522
import time
import drivers
import serial
import pynmea2
import requests
import os
import sys
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import json
#Self BUS ID
GLOBALSELFBUSID = 3


#MYSQL Credientials
load_dotenv()


#GPIO BCM MODE  
GPIO.setmode(GPIO.BCM)
display = drivers.Lcd()

# Connect to MySQL
display.lcd_display_string("Starting...", 1)
time.sleep(1)

#FOR GPS MODULE






#Timestamp Logic

utc_plus_4 = timezone(timedelta(hours=4))
current_time = datetime.now(utc_plus_4)
timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")


#MY Whatsapp API LINK
#I have my own private api set-up on another private server That handles whatsapp messages.
WHATSAPP_API_URL = "http://138.201.246.236:3000/api/sendText"


#Important function for gps


async def get_gps_coordinates_First():
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
    port = serial.Serial("/dev/serial0", baudrate=9600, timeout=2)
    try:
        display.lcd_display_string("Loading GPS...", 2)
        timeout = 1  # seconds
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
                port.close()
                return {
                    "latitude": latitude,
                    "longitude": longitude,
                    "altitude": altitude,
                    "google_maps": google_maps
                }
            

    except pynmea2.ParseError:
       
                  return {
                    "latitude": 0,
                    "longitude": 0,
                    "altitude": 0,
                    "google_maps": None
                }
    except Exception as e:
        print(f"GPS Error: {e}")
        return {
                    "latitude": 0,
                    "longitude": 0,
                    "altitude": 0,
                    "google_maps": None
                }


#Try to get gps coordinates. 

#print(get_gps_coordinates_First())




async def RFIDRead():
        reader = SimpleMFRC522()
        RFIDid, text = await asyncio.to_thread(reader.read)
        print(RFIDid, text)
        return (RFIDid, text)


#Door COnfiguration
SERVO_PIN = 16   # <-- GPIO16 = physical pin 36
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)  # 50Hz PWM for servo
pwm.start(0)

async def set_angle(angle):
    duty = angle / 18 + 2.5
    pwm.ChangeDutyCycle(duty)
    await asyncio.sleep(0.5)


async def open_door():
     print("Opening door to 115°...")
     await set_angle(115)
     
     


async def close_door():
     print("Closing door to 0°...")
     await set_angle(0)
     

#Event Handler for Trip Checking while RFID_READER IS ACTIVE (BLOCKING FUNCTION)
async def check_trip_status():
    while True:
         try:
              

                db = mysql.connector.connect(
                host=os.getenv("DB_HOST"),
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"),
                database=os.getenv("DB_NAME")
                )

                await asyncio.sleep(1)
                db.autocommit = True
                cursorbus = db.cursor(buffered=False)
                query = f"SELECT * FROM bus WHERE bus_id = {GLOBALSELFBUSID}"
                cursorbus.execute(query)
                rowbus = cursorbus.fetchone()
                Current_Bus_Trip_Status = rowbus[4]

                if Current_Bus_Trip_Status == 0:
                    display.lcd_clear()
                    display.lcd_display_string("Trip Ended", 1)
                    display.lcd_display_string("New Session...", 2)
                    # two beeps
                    for _ in range(2):
                        GPIO.output(21, GPIO.HIGH)
                        await asyncio.sleep(1)
                        GPIO.output(21, GPIO.LOW)
                        await asyncio.sleep(1)
                    print("Trip Ended! , New session...")
                    os.execl(sys.executable, sys.executable, *sys.argv)

                await asyncio.sleep(1)  # wait 1 second before next DB check  

         except mysql.connector.Error as err:
                print(f"Error: {err}")
                display.lcd_clear()
                display.lcd_display_string("Error: MYSQL", 1)
                display.lcd_display_string("Can't Connect", 2)
                await asyncio.sleep(5)
                display.lcd_clear()
                os.execl(sys.executable, sys.executable, *sys.argv)

                
                

is_task_created = False
async def main():
    global is_task_created

    #Try to connect to cloud MYSQL
    await close_door()
    
    Location_cache = await get_gps_coordinates_First()
    print(Location_cache)
    try:

        db = mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME")
    )
        
        db.autocommit = True  

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        display.lcd_clear()
        display.lcd_display_string("Error: MYSQL", 1)
        display.lcd_display_string("Can't Connect", 2)
        await asyncio.sleep(5)
        display.lcd_clear()
        exit(1)

    #Connected To MYSQL!
    display.lcd_display_string("Cloud Server", 1)
    display.lcd_display_string("Connected!", 2)
    await asyncio.sleep(5)
    display.lcd_clear()



    
    #For local student set handling. uncomment for testing only!
    #StudentSet = set()


    GPIO.setup(21, GPIO.OUT)
    GPIO.output(21, GPIO.LOW)
    display.lcd_display_string("Awaiting Driver", 1)
    display.lcd_display_string("To Start Trip!", 2)
    await asyncio.sleep(2)
    #Before running actual app. driver need to start the trip!
    #Waiting for driver to start the trip!
    while True:
        try:
                
                cursorbus = db.cursor(buffered=False) #so it doesn't show old data :)
                
                query = f"SELECT * FROM `bus` WHERE bus_id = {GLOBALSELFBUSID}"
                cursorbus.execute(query)
                # Fetch the first row
                rowbus = cursorbus.fetchone()
                trip_status = rowbus[4] #Bus Trip status column
                # print(trip_status)
                if(trip_status == 1):
                    display.lcd_clear()
                    display.lcd_display_string("Trip Started", 1)
                    display.lcd_display_string("Loading...", 2)
                    
                    #BEEP Script
                    GPIO.output(21, GPIO.HIGH)
                    await asyncio.sleep(1)
                    GPIO.output(21, GPIO.LOW)
                    #Breaking this while loop. to start another while loop!
                    break
                else:
                    await asyncio.sleep(2)
                    continue    
        except Exception as e:
                            
                            print(f"Error: {e}")
                





    #Start the app!
    
    
    while True:
        try:
            
            #Buzzer Pin
            display.lcd_clear()
            

            cursorbus = db.cursor(buffered=False) #so it doesn't show old data :/
                
            query = f"SELECT * FROM `bus` WHERE bus_id = {GLOBALSELFBUSID}"
            cursorbus.execute(query)
            rowbus = cursorbus.fetchone()
            Current_Bus_Trip_Status = rowbus[4] #Bus Trip status column
            if(Current_Bus_Trip_Status == 0):
                display.lcd_display_string("Trip Ended", 1)
                display.lcd_display_string("New Session...", 2)
                #TWO BEEPS
                GPIO.output(21, GPIO.HIGH)
                await asyncio.sleep(1)
                GPIO.output(21, GPIO.LOW)
                await asyncio.sleep(1)
                GPIO.output(21, GPIO.HIGH)
                await asyncio.sleep(1)
                GPIO.output(21, GPIO.LOW)
                
                #Starting the loop again as new session :/
                print("Trip Ended! , New session...")
                
                os.execl(sys.executable, sys.executable, *sys.argv)


        

            display.lcd_display_string("Pass Your Key", 1)  # Write line of text to first line of display
            display.lcd_display_string("Card", 2)
            print("Hold tag near the reader...")

            #Event Handler CHECK TRIP STATUS!
            
            if(is_task_created == False):
                 db_task = asyncio.create_task(check_trip_status())  #Perfect handler for detecting stop trip while reading!
                 is_task_created = True   
            RFIDid, text = await RFIDRead()

            # Turn on buzzer
            GPIO.output(21, GPIO.HIGH)
            await asyncio.sleep(0.5)
            display.lcd_clear()
            GPIO.output(21, GPIO.LOW)
            print(f"ID: {RFIDid}\nText: {text}")
        except KeyboardInterrupt:
            display.lcd_clear()
            GPIO.output(21, GPIO.LOW)
            print("Exiting...") 
        except SystemExit:
            break 
        finally:
            
            # Create a cursor object
            cursor = db.cursor(buffered=False)
            cursor2 = db.cursor(buffered=False)
            

            # Write your SELECT query
            query = f"SELECT * FROM `student` WHERE student_rfid = {RFIDid}"
            querybusdetails = f"SELECT * FROM `bus` WHERE `bus_id` = {GLOBALSELFBUSID}"
            
            # Execute the query
            cursor.execute(query)
            
            # Fetch the first row
            row = cursor.fetchone()

            cursor2.execute(querybusdetails)
            row2 = cursor2.fetchone()
        
            

            
            
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
                bus_trip_status = row2[4]
                bus_student_list_JSON = row2[5]
                bus_student_list_JSON_LOAD = json.loads(bus_student_list_JSON)    # becomes a Python list
                StudentSet = set(bus_student_list_JSON_LOAD)




                

                if(student_bus_id != GLOBALSELFBUSID):
                    #Two beeps for wrong bus!
                    display.lcd_display_string("Access Denied:", 1)
                    display.lcd_display_string("Wrong Bus!", 2)
                    GPIO.output(21, GPIO.HIGH)
                    await asyncio.sleep(1)
                    GPIO.output(21, GPIO.LOW)
                    await asyncio.sleep(1)
                    GPIO.output(21, GPIO.HIGH)
                    await asyncio.sleep(1)
                    display.lcd_clear()
                    GPIO.output(21, GPIO.LOW)
                    continue

                print(f"Student Found: {student_name} ")
                

                if(bus_trip_status == 0 ):
                    display.lcd_display_string("Trip Ended", 1)
                    display.lcd_display_string("New Session...", 2)
                    #TWO BEEPS
                    GPIO.output(21, GPIO.HIGH)
                    await asyncio.sleep(1)
                    GPIO.output(21, GPIO.LOW)
                    await asyncio.sleep(1)
                    GPIO.output(21, GPIO.HIGH)
                    await asyncio.sleep(1)
                    GPIO.output(21, GPIO.LOW)
                
                    #Starting the loop again as new session :/
                    print("Trip Ended! , New session...")
                
                    os.execl(sys.executable, sys.executable, *sys.argv)

                if(RFIDid in StudentSet):
                    StudentSet.remove(RFIDid)
                    display.lcd_display_string("Checked Out:", 1)
                    display.lcd_display_string(f'ID: {student_name}', 2)
                    # CHECK IN ID = 0 // CHECK OUT ID = 1
                    queryCheckingIN = """
                    INSERT INTO attendance (student_id, bus_id, type, timestamp)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    """
                    values = (student_id, student_bus_id, 1)

                    cursor.execute(queryCheckingIN, values)
                    db.commit()
                    #GRAB GPS DATA HERE 
                    coords = await get_gps_coordinates_First() # Get GPS coordinates
                    print(coords)
                    if(coords is None):
                        #Last caught location. just for handling errors
                        coords = Location_cache
                        
                    display.lcd_clear()
                    await open_door()
                    display.lcd_display_string("Checked Out:", 1)
                    display.lcd_display_string(f'ID: {student_name}', 2)
                    # CHECK IN ID = 0 // CHECK OUT ID = 1
                    queryCheckingIN = """
                    INSERT INTO attendance (student_id, bus_id, type, timestamp)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    """
                    values = (student_id, student_bus_id, 0)
                    
                    cursor.execute(queryCheckingIN, values)
                    db.commit()

                    #Sync student list to cloud
                    Student_Set_JSONString = json.dumps(list(StudentSet))
                    query_update_student_list = """
                                                UPDATE `bus`
                                                SET `student_list` = %s,
                                                    `google_map` = %s
                                                WHERE `bus`.`bus_id` = %s
                                            """
                                            
                    google_maps = None

                    if isinstance(coords, dict):
                        google_maps = coords.get('google_maps')

                    cursor.execute(
                        query_update_student_list,
                        (
                            Student_Set_JSONString,
                            google_maps,
                            GLOBALSELFBUSID
                        )
                    )

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
                            
                            # Headers
                            headers = {
                                "X-Api-Key": os.getenv("Whatsapp-API-KEY")
                            }
                            # JSON payload
                            payload = {
                                "chatId": f"{parent_phone}@c.us",
                                "text": f"{message_text}!",
                                "session": "default"
                            }
                                # Send POST request
                            try:
                                response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
                                # Print response status and content
                                print(f"POST REQUEST SENT | Status code: {response.status_code}")
                                # print(f"Response: {response.text}")
                            except Exception as e:
                                print(f"Error: {e}")


                            print("Google Maps URL:", google_link)
                            #logic to send sms with link
                            await asyncio.sleep(4)
                            await close_door()
                            await asyncio.sleep(1)
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
                        

                       # Headers
                        headers = {
                                "X-Api-Key": os.getenv("Whatsapp-API-KEY")
                            }
                            # JSON payload
                        payload = {
                                "chatId": f"{parent_phone}@c.us",
                                "text": f"{message_text}!",
                                "session": "default"
                        }
                                # Send POST request
                        try:
                                response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
                                # Print response status and content
                                print(f"POST REQUEST SENT | Status code: {response.status_code}")
                                # print(f"Response: {response.text}")
                        except Exception as e:
                                
                                print(f"Error: {e}")
                    #OPEN DOOR FOR 5 SECONDS AND THEN CLOSE!
                        await asyncio.sleep(4)
                        await close_door()
                        await asyncio.sleep(1)
                    
                    
                else:

                    if(len(StudentSet) >= bus_capacity):
                        #Two beeps for bus overcrow
                        display.lcd_display_string("Access Denied:", 1)
                        display.lcd_display_string("Bus Overcrowded!", 2)
                        GPIO.output(21, GPIO.HIGH)
                        await asyncio.sleep(1)
                        GPIO.output(21, GPIO.LOW)
                        await asyncio.sleep(1)
                        GPIO.output(21, GPIO.HIGH)
                        await asyncio.sleep(1)
                        display.lcd_clear()
                        GPIO.output(21, GPIO.LOW)
                        continue


                    StudentSet.add(RFIDid)
                    display.lcd_display_string("Querying...", 1)  
                    
                    coords = await get_gps_coordinates_First() # Get GPS coordinates
                    print(coords)
                    if(coords is None):
                        #Last caught location. just for handling errors
                        coords = Location_cache
                        
                    display.lcd_clear()
                    await open_door()
                    display.lcd_display_string("Checked In:", 1)
                    display.lcd_display_string(f'ID: {student_name}', 2)
                    # CHECK IN ID = 0 // CHECK OUT ID = 1
                    queryCheckingIN = """
                    INSERT INTO attendance (student_id, bus_id, type, timestamp)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    """
                    values = (student_id, student_bus_id, 0)
                    
                    cursor.execute(queryCheckingIN, values)
                    db.commit()

                    #Sync student list to cloud
                    Student_Set_JSONString = json.dumps(list(StudentSet))
                    query_update_student_list = """
                                                UPDATE `bus`
                                                SET `student_list` = %s,
                                                    `google_map` = %s
                                                WHERE `bus`.`bus_id` = %s
                                            """
                    google_maps = None

                    if isinstance(coords, dict):
                        google_maps = coords.get('google_maps')

                    cursor.execute(
                        query_update_student_list,
                        (
                            Student_Set_JSONString,
                            google_maps,
                            GLOBALSELFBUSID
                        )
                    )
                    
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

                            # Headers
                            headers = {
                                "X-Api-Key": os.getenv("Whatsapp-API-KEY")
                            }
                            # JSON payload
                            payload = {
                                "chatId": f"{parent_phone}@c.us",
                                "text": f"{message_text}!",
                                "session": "default"
                            }
                                # Send POST request
                            try:
                                response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
                                # Print response status and content
                                print(f"POST REQUEST SENT | Status code: {response.status_code}")
                                # print(f"Response: {response.text}")
                            except Exception as e:
                                print(f"Error: {e}")


                            print("Google Maps URL:", google_link)
                            #logic to send sms with link
                            await asyncio.sleep(4)
                            await close_door()
                            await asyncio.sleep(1)
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

                        # Headers
                        headers = {
                                "X-Api-Key": os.getenv("Whatsapp-API-KEY")
                            }
                            # JSON payload
                        payload = {
                                "chatId": f"{parent_phone}@c.us",
                                "text": f"{message_text}!",
                                "session": "default"
                        }
                                # Send POST request
                        try:
                                response = requests.post(WHATSAPP_API_URL, json=payload, headers=headers)
                                # Print response status and content
                                print(f"POST REQUEST SENT | Status code: {response.status_code}")
                                # print(f"Response: {response.text}")
                        except Exception as e:
                                print(f"Error: {e}")

                        await asyncio.sleep(4)
                        await close_door()
                        await asyncio.sleep(1)
                    
                        

                

                    #OPEN DOOR FOR 5 SECONDS AND THEN CLOSE!

                


                #GPIO.cleanup()
                print("SLeeping for 2 seconds before next read...")
                await asyncio.sleep(1)
                display.lcd_clear()
            else:
                print("Student Not Found")
                display.lcd_display_string("Unknown Key!", 1)
                display.lcd_display_string("Access Denied!", 2)
                GPIO.output(21, GPIO.HIGH)
                await asyncio.sleep(1)
                GPIO.output(21, GPIO.LOW)
                #GPIO.cleanup()
                print("SLeeping for 2 seconds before next read...")
                await asyncio.sleep(1)
                display.lcd_clear()

asyncio.run(main())