from django.shortcuts import render
from .models import Sensor_Data, RSSI_Data
from django.views.decorators.csrf import csrf_exempt
import json
import paho.mqtt.client as mqtt
import atexit
from django.core.paginator import Paginator

MQTT_BROKER_HOST = "127.0.0.1"
MQTT_BROKER_PORT = 1883
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
            humidity=payload_data.get('humidity', 0),
            human_detection=payload_data.get('human_detection', 0),
            hydrogen=payload_data.get('hydrogen', 0),
            fire=payload_data.get('fire', 0),
            co=payload_data.get('co', 0),
            smoke=payload_data.get('smoke', 0)
        )


# Set up MQTT client
mqtt_client = mqtt.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
# Start MQTT loop in a separate thread
mqtt_client.loop_start()


@csrf_exempt
# Close MQTT connection on application shutdown
def on_shutdown():
    mqtt_client.loop_stop()


def sensor_data(request):
    # 从数据库中获取所有DeviceData记录，按timestamp字段倒序排序
    data_list = Sensor_Data.objects.all().order_by('-timestamp')
    # 创建context字典，将data_list包含进去
    paginator = Paginator(data_list, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}

    # 使用render函数将数据和模板结合，生成最终的HTML页面
    return render(request, 'sensordata.html', context)


def rssi_data(request):
    # 从数据库中获取所有RSSI记录，假设我们有一个timestamp字段来进行排序
    rssi_list = RSSI_Data.objects.all().order_by('-timestamp')  # 如果没有timestamp字段，可以使用'id'字段作为替代
    # 创建context字典，将rssi_list包含进去
    paginator = Paginator(rssi_list, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    # 使用render函数将数据和模板结合，生成最终的HTML页面
    return render(request, 'rssidata.html', context)


atexit.register(on_shutdown)


def layout(request):
    return render(request, 'layout.html')

# def check_alerts():
#     while True:
#         # Fetch the latest sensor data
#         latest_data = SensorData.objects.latest('timestamp')
#
#         # Check if any parameter exceeds the specified threshold
#         if (
#                 latest_data.temperature > temperature_threshold or
#                 latest_data.hydrogen_concentration > hydrogen_threshold or
#                 latest_data.smoke_concentration > smoke_threshold
#         ):
#             # In a real-world scenario, you would implement the logic to send an alert (e.g., via SMS)
#             # For now, let's print a message for demonstration purposes.
#             alert_message = f"ALERT: Temperature: {latest_data.temperature}, Smoke Concentration: {latest_data.smoke_concentration}"
#             print(alert_message)
#
#             # Simulate sending an SMS (replace with actual SMS sending code)
#             # send_sms(phone_number, alert_message)
#
#         # Sleep for a certain period before checking again (adjust as needed)
#         time.sleep(60)
#
# alert_thread = threading.Thread(target=check_alerts)
# alert_thread.start()


# def brokerinfo(request):
#     # Fetch all BrokerInfo objects from the database
#     all_broker_info = BrokerInfo.objects.all()
#     # all_system_info = SysInfo.objects.all()
#     # context = {
#     #     'devices_num': devices
#     #     'lasttime': devices
#     #     'devices_num': devices
#     #     'devices_num': devices
#     #     ''
#     # }
#
#     # Pass the all_broker_info variable to the template
#     return render(request, 'brokerinfo.html', {'all_broker_info': all_broker_info})
#
# def dashboard(request):
#     devices = SensorData.objects.all().order_by('-timestamp')[:10]
#     context = {
#         'devices': devices
#     }
#     return render(request, 'sensordata.html', context)
#
# def data(request):
#     all_data = SensorData.objects.all().order_by('-timestamp')[:20]
#     context = {
#         'all_data': all_data
#     }
#     return render(request, 'data.html', context)
