# School Bus Raspberry Pi Controller

![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)

This project runs on a Raspberry Pi and manages student boarding and alighting using an MFRC522 RFID reader, a NEO-6M GPS, an I2C LCD, and a servo-controlled door. When a student scans their RFID tag, the app records attendance in a MySQL database and notifies parents via a WhatsApp API that includes a Google Maps link to the bus location.

This project is licensed under the Creative Commons Attribution-NonCommercial 4.0 International License (CC BY-NC 4.0). See the [LICENSE](LICENSE) file for full terms.

## Commercial licensing
Commercial use of this project is **not permitted** under CC BY-NC 4.0.

If you wish to use this project in a commercial product, service, or deployment,
please contact the copyright holder to request a commercial license.

This project was not licensed prior to the inclusion of the `LICENSE` file.
No rights were granted before that time. All current and future use of this repository
is governed by the CC BY-NC 4.0 license unless explicitly stated otherwise.

**Key features**
- Async event loop (uses `asyncio`) with non-blocking RFID/GPS handling
- Reads RFID tags (MFRC522 via `mfrc522.SimpleMFRC522`)
- Records check-in/check-out to a remote MySQL database (`mysql-connector-python`)
- Sends WhatsApp notifications to parents (via a configurable HTTP API)
- Reads GPS (NEO-6M over `/dev/serial0`) and builds Google Maps links
- Controls a servo door (PWM on GPIO16) and a buzzer (GPIO21)
- Displays status messages on an attached I2C LCD via `drivers.Lcd`

## Contents
- [app.py](app.py) — main application
- [drivers/](drivers/) — local LCD driver and helpers
- [example.env](example.env) — environment variable template

## Hardware
- Raspberry Pi (with GPIO, SPI, I2C and serial enabled)
- MFRC522 RFID reader (SPI) — used via `mfrc522.SimpleMFRC522`
- NEO-6M GPS (UART `/dev/serial0`) — app parses GPGGA sentences
- I2C LCD (used via `drivers.Lcd`)
- Servo motor connected to GPIO16 (BCM numbering, physical pin 36)
- Buzzer connected to GPIO21 (BCM)

Ensure SPI, I2C and serial are enabled (use `raspi-config` or equivalent).

## Software / Python dependencies
Install dependencies on the Raspberry Pi (run as a user with internet access):

```bash
sudo apt update
sudo apt install -y python3-pip python3-serial
sudo pip3 install mysql-connector-python RPi.GPIO mfrc522 pynmea2 requests python-dotenv
```

Notes:
- `RPi.GPIO` and direct serial access only work on a Raspberry Pi.
- The `mfrc522` package exposes `SimpleMFRC522` used by the app.

## Environment variables
Create a `.env` file in the project root (you can copy `example.env`). The app reads DB credentials and the WhatsApp API key from environment variables:

```env
DB_HOST=your_db_host
DB_USER=your_db_user
DB_PASS=your_db_password
DB_NAME=your_db_name
Whatsapp-API-KEY=your_api_key_here
```

The app also uses a hard-coded `WHATSAPP_API_URL` value in `app.py`; change it there if you run your own API instance.

## Configuration notes (in `app.py`)
- `GLOBALSELFBUSID` (default `3`): integer ID identifying this bus — set it to match the `bus_id` in the database for this Pi.
- `WHATSAPP_API_URL`: endpoint used to POST WhatsApp message payloads.
- `SERVO_PIN` is set to `16` (BCM) and the buzzer uses GPIO `21` — change pins in `app.py` if your wiring differs.
- Serial port: the GPS is read from `/dev/serial0` at 9600 baud.

## Runtime behaviour
- On start the app attempts an initial GPS fix and connects to the MySQL server.
- The app waits for a driver to set the `bus.trip_status` flag in the DB; once the trip is active it will:
	- Prompt for RFID tags and read them using `SimpleMFRC522`.
	- Validate the student record and whether they belong to this bus.
	- Insert records into `attendance` for check-in/check-out (the code uses `type` values where `0`/`1` correspond to check-in/check-out in the app comments).
	- Maintain an in-memory student list synced back to the `bus.student_list` JSON field.
	- Read GPS coordinates for each event and include a Google Maps URL in WhatsApp notifications sent to the parent.
	- Control the servo to open/close the door and use the buzzer for audible feedback.
	- A background task monitors the `bus` row for trip status changes and restarts the process when a trip ends.

## Database expectations
The app expects tables similar to the following (simplified):

- `bus` — expected to include `bus_id`, `driver_name`, `model`, `capacity`, `trip_status`, `student_list` (JSON)
- `student` — expected to include `student_id`, `parent_id`, `student_bus_id`, `student_name`, `student_rfid`
- `parent` — expected to include `parent_id`, `name`, `phone`
- `attendance` — expected to include `attendance_id`, `student_id`, `bus_id`, `type`, `timestamp`

Adjust your schema or queries in `app.py` if your database differs.

## Running
On the Raspberry Pi (with GPIO access and serial/I2C enabled):

```bash
sudo python3 app.py
```

Running as root (via `sudo`) is typically required for GPIO access.

## Troubleshooting
- MySQL connection errors: verify `.env` values and network access to the DB.
- GPS issues: ensure `/dev/serial0` is enabled and the GPS module has a clear view of the sky; the app parses GPGGA sentences.
- RFID not reading: check SPI wiring and the MFRC522 connections.
- Permissions/GPIO errors: run with `sudo` and ensure the user has GPIO access.


## Safety and testing
- Test hardware (servo, buzzer, RFID) with small test scripts before connecting to the DB or sending notifications.
- Keep a safe mechanical setup for the servo-controlled door to avoid pinching or injury.



