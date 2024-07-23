from sensor.models import Sensor_Data, RSSI_Data
from django.views.decorators.csrf import csrf_exempt
import json
import paho.mqtt.client as mqtt
import atexit


MQTT_BROKER_HOST = "192.168.1.58"
MQTT_BROKER_PORT = 31111
SENSOR_TOPIC = "sensor"
RSSI_TOPIC = "rssi"


def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(RSSI_TOPIC)
    client.subscribe(SENSOR_TOPIC)


def on_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode('utf-8')
    payload_data = json.loads(payload)  # 将接收到的payload解析成字典

    if topic == RSSI_TOPIC:
        # 解析并存储来自RSSI_TOPIC的数据
        RSSI_Data.objects.create(
            device_mac=payload_data.get('device_mac', ''),
            ap_mac=payload_data.get('ap_mac', ''),
            rssi=payload_data.get('rssi', 0)
        )
    elif topic == SENSOR_TOPIC:
        # 解析并存储来自SENSOR_TOPIC的数据
        Sensor_Data.objects.create(
            device_mac=payload_data.get('device_mac', ''),
            temperature=payload_data.get('temperature', 0),
            hydrogen=payload_data.get('hydrogen', 0),
            co=payload_data.get('co', 0),
            smoke=payload_data.get('smoke', 0)
        )


mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
mqtt_client.loop_start()


@csrf_exempt
def on_shutdown():
    mqtt_client.loop_stop()


atexit.register(on_shutdown)