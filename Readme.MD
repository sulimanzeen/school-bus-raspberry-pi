# School Bus Raspberry Pi Controller

This project runs on a Raspberry Pi to manage student boarding and alighting using an RFID reader, GPS, an LCD, and a servo-controlled door. When a student scans their RFID tag the app records attendance to a MySQL server and notifies parents over a WhatsApp API with a Google Maps link to the bus location.

**Key features**
- Reads RFID tags (MFRC522)
- Records check-in/check-out to a remote MySQL database
- Sends WhatsApp notifications to parents (via an external API)
- Reads GPS (NEO-6M) and generates Google Maps links
- Controls a servo as a door actuator and a buzzer for feedback
- Displays status messages on an attached LCD

## Contents
- `app.py` — main application
- `drivers/` — local LCD driver and helpers
- `example.env` — environment variable template

## Hardware
- Raspberry Pi (with GPIO and serial enabled)
- MFRC522 RFID reader (SPI)
- NEO-6M GPS (UART `/dev/serial0`)
- I2C LCD (used via `drivers.Lcd`)
- Servo motor connected to GPIO16 (physical pin 36)
- Buzzer connected to GPIO21

Wiring is specific to your hardware modules; ensure SPI, I2C and serial are enabled in `raspi-config`.

## Software / Python dependencies
Install dependencies on the Raspberry Pi (run as a user with internet access):

```powershell
sudo apt update; sudo apt install -y python3-pip python3-serial
sudo pip3 install mysql-connector-python RPi.GPIO mfrc522 pynmea2 requests python-dotenv
```

Notes:
- `RPi.GPIO` must be used on a Raspberry Pi. On other platforms it will not work.
- Some packages (like `mfrc522`) may require specific library versions; test them on your Pi.

## Environment variables
Create a `.env` file in the project root (you can copy `example.env`). The app reads DB credentials from environment variables:

```env
DB_HOST=your_db_host
DB_USER=your_db_user
DB_PASS=your_db_password
DB_NAME=your_db_name
# Optionally change GLOBALSELFBUSID in `app.py` to match this bus's ID
```

## Configuration notes (in `app.py`)
- `GLOBALSELFBUSID`: integer ID identifying this bus (adjust to the bus in your DB)
- `WHATSAPP_API_URL`: currently hard-coded to the project owner’s API. Replace or proxy it if needed.
- `SERVO_PIN` is set to `16` and the buzzer uses GPIO `21` — change pins in `app.py` if your wiring differs.

## Running
On the Raspberry Pi (with GPIO access and serial/I2C enabled):

```powershell
sudo python3 app.py
```

Running as root (via `sudo`) is typically required for GPIO access.

## How it works (high level)
- On start the app attempts to read an initial GPS fix and connects to the MySQL server.
- The driver starts a trip from the database (flag). When the trip is active the app repeatedly:
	- Waits for RFID reads
	- Validates the student and bus
	- Updates the `attendance` table with check-in/check-out entries
	- Retrieves GPS coordinates and constructs a Google Maps link
	- Notifies the student’s parent via the configured WhatsApp API
	- Controls the servo to open/close the door and uses the buzzer for feedback

## Database expectations
The app expects tables similar to the following (simplified):

- `bus` (columns include `bus_id`, `driver_name`, `model`, `capacity`, `trip_status`)
- `student` (columns include `student_id`, `parent_id`, `student_bus_id`, `student_name`, `student_rfid`)
- `parent` (columns include `parent_id`, `name`, `phone`)
- `attendance` (columns include `attendance_id`, `student_id`, `bus_id`, `type`, `timestamp`)

Adjust your schema or queries in `app.py` if your database differs.

## Troubleshooting
- MySQL connection errors: verify `.env` values and network access to the DB.
- GPS issues: ensure `/dev/serial0` is enabled and the GPS module has a clear view of the sky.
- RFID not reading: check SPI wiring and the MFRC522 connections.
- Permissions/GPIO errors: run with `sudo` and ensure the user has GPIO access.
- WhatsApp messages fail: the project posts to an external API — check `WHATSAPP_API_URL` and network connectivity.

## Safety and testing
- Test hardware (servo, buzzer, RFID) with small test scripts before connecting to the DB or sending notifications.
- Keep a safe mechanical setup for the servo-controlled door to avoid pinching or injury.



