import network
import usocket as socket
import ustruct as struct
import ubinascii
import uhashlib
import random
import time
from machine import Pin, I2C, reset
import select
import onewire
import ds18x20
import ssd1306
import ujson
import restPythonAltiria

ds_pin = Pin(19)

# Configuración del pin donde está conectado el sensor KY-031
Signal_PIN = Pin(23, Pin.IN, Pin.PULL_UP)
# Configuracion de onewire para el sensor ds18b20
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
# Configuracion de display OLED
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
#Configure kickstand o pata lateral de la moto
kickstand_PIN = Pin(27, Pin.IN, Pin.PULL_UP)

# Variable globale para controlar la conexión WebSocket
ws_conn = None
# iniciar el dispositivo onewire
roms = ds_sensor.scan()
# iniciar display OLED
i2c_devices = i2c.scan()

def set_message(temperature, kickstand, hit):
    response = {
        "temperatura": temperature,
        "kickstand": kickstand,
        "hit": hit
    }
    return response

if len(i2c_devices) == 0:
    print("No se detectaron dispositivos I2C.")
else:
    print("Dispositivo I2C detectado en la dirección:", hex(i2c_devices[0]))

# Inicializar el OLED si se ha detectado
if i2c_devices:
    print("Intentando imprimir")
    oled = ssd1306.SSD1306_I2C(128, 64, i2c)

    # Limpia la pantalla
    oled.fill(0)

    # Escribe texto en la pantalla
    oled.text('OLED funcionando!', 0, 0)
    oled.show()

    # Dibuja un rectángulo
    oled.rect(0, 20, 128, 44, 1)
    oled.show()

ap = network.WLAN(network.STA_IF)
# Activar la interfaz de cliente
ap.active(True)

# Conectar a la red Wi-Fi con SSID y contraseña
ssid = 'moto'      # Reemplaza con el nombre de tu red Wi-Fi
password = 'soytuperra'    # Reemplaza con la contraseña de tu red Wi-Fi
ap.connect(ssid, password)

# Esperar hasta que se establezca la conexión
print("Conectando a la red Wi-Fi...")
while not ap.isconnected():
    time.sleep(1)

# Mostrar la dirección IP asignada al ESP32
print("Conectado con éxito!")
print("Dirección IP:", ap.ifconfig()[0])

def websocket_handshake(conn):
    request = conn.recv(1024)
    headers = request.decode().split("\r\n")
    websocket_key = None
    for header in headers:
        if "Sec-WebSocket-Key" in header:
            websocket_key = header.split(": ")[1]

    if websocket_key:
        sha1 = uhashlib.sha1(websocket_key.encode() + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
        websocket_accept = ubinascii.b2a_base64(sha1.digest()).decode().strip()

        conn.send("HTTP/1.1 101 Switching Protocols\r\n")
        conn.send("Upgrade: websocket\r\n")
        conn.send("Connection: Upgrade\r\n")
        conn.send(f"Sec-WebSocket-Accept: {websocket_accept}\r\n\r\n")

def leer_sensor():
    ds_sensor.convert_temp()
    kisckstand_status = kickstand_PIN.value()
    rom = roms[0]
    time.sleep(1)
    #respuesta = {
    #    "temperatura": ds_sensor.read_temp(rom),
    #    "kickstand": kisckstand_status
    #}
    respuesta = set_message(ds_sensor.read_temp(rom), kisckstand_status, 0)
    respuesta_json = ujson.dumps(respuesta)
    return respuesta_json

def hit(pin):
    global ws_conn
    print('Hit detected!')
    if ws_conn:
        try:
            value_hit = ujson.dumps(set_message(0, 0, 1))
            event_message = f"{value_hit}"
            frame_header = bytearray([0x81, len(event_message)])
            ws_conn.send(frame_header + event_message.encode())
        except Exception as e:
            print("Error sending WebSocket message:", e)
            ws_conn = None
        restPythonAltiria.altiriaSms('573153362377','Mensaje de prueba', '', True)

def kickstand_change(pin):
    global ws_conn
    print('Cambio en pata detectado!')
    if ws_conn:
        try:
            value_kickstand = ujson.dumps(set_message(0, 1, 0))
            event_message = f"{value_kickstand}"
            frame_header = bytearray([0x81, len(event_message)])
            ws_conn.send(frame_header + event_message.encode())
        except Exception as e:
            print("Error al enviar el mensaje WebSocket de pata:", e)
            ws_conn = None

#Signal_PIN.irq(trigger=Pin.IRQ_FALLING, handler=hit)
kickstand_PIN.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=hit)

def http_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("", 80))
    server_socket.listen(5)

    print("Esperando solicitud HTTP para iniciar WebSocket...")

    while True:
        conn, addr = server_socket.accept()
        request = conn.recv(1024).decode()
        print("Solicitud HTTP recibida: ", request)

        if "GET /start" in request:
            response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\nWebSocket iniciado"
            conn.send(response)
            conn.close()

            websocket_server()

def websocket_server():
    global ws_conn
    print("Iniciando WebSocket...")

    tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_socket.bind(("", 81))
    tcp_socket.listen(1)

    while True:
        ws_conn, addr = tcp_socket.accept()
        print("Nueva conexión desde %s" % str(addr))
        websocket_handshake(ws_conn)
        try:
            while True:
                sensor_value = leer_sensor()
                print("Valor del sensor:", sensor_value)

                event_message = f"{sensor_value}"
                frame_header = bytearray([0x81, len(event_message)])
                ws_conn.send(frame_header + event_message.encode())

                time.sleep(3)
        except Exception as e:
            print("Error en la conexión WebSocket:", e)
        finally:
            ws_conn.close()
            ws_conn = None

http_server()
