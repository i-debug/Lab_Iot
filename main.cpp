#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <Adafruit_Sensor.h>
#include <DHT.h>

#define DHTPIN 26               // 定义温湿度传感器的数据引脚
#define DHTTYPE DHT11           // 设置使用的DHT类型DHT11
const int GPIO_MQ8_PIN = 33;    // 定义氢气传感器MQ8的数据引脚
const int GPIO_MQ7_PIN = 35;    // 定义一氧化碳传感器MQ7的数据引脚
const int GPIO_MQ2_PIN = 34;    // 定义烟雾传感器MQ2的数据引脚
const int WiFi_threehold = -80; // 定义RSSI阈值
DHT dht(DHTPIN, DHTTYPE);
const char *ssid = "106";               // Wi-Fi网络名称
const char *password = "he888888";          // Wi-Fi网络密码
const char *mqtt_server = "192.168.1.58"; // MQTT服务器地址
const char *rssi_topic = "rssi";            // RSSI主题，用于发布RSSI扫描数据
const char *sensor_topic = "sensor";        // Sensor主题，用于发布传感器数据
unsigned long previousMillis10s = 0;        // 上次10秒任务执行的时间
unsigned long previousMillis1m = 0;         // 上次1分钟任务执行的时间
const long interval10s = 10000;             // 10秒间隔
const long interval1m = 60000;              // 1分钟间隔

WiFiClient espClient;               // 创建一个WiFi客户端对象
PubSubClient mqttClient(espClient); // 创建一个MQTT客户端对象

String generateClientId() // 生成一个随机的客户端ID
{
  uint32_t randomNumber = esp_random(); // 生成一个随机数
  String clientId = "ESP32Client_" + WiFi.macAddress() + String(randomNumber, HEX);
  clientId.replace(":", ""); // 移除MAC地址中的冒号
  return clientId;
}

void connectToWiFi()
{
  // STA_AP模式
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
  // 获取 MAC 地址并生成随机 AP 名称
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char ap_ssid[32];
  snprintf(ap_ssid, sizeof(ap_ssid), "ESP32-AP-%02X%02X%02X", mac[3], mac[4], mac[5]);
  // Access Point 模式
  WiFi.softAP(ap_ssid, "password123");
  Serial.println("Access Point Started");
  Serial.println(" connected!"); // 连接成功后打印消息
  Serial.print("IP Address: ");  // 打印IP地址
  Serial.println(WiFi.localIP());
}

void connectToMQTT()
{
  String clientId = generateClientId();
  mqttClient.setServer(mqtt_server, 31111); // 设置MQTT服务器和端口

  while (!mqttClient.connected())
  { // 如果客户端未连接，则尝试连接
    Serial.print("Attempting MQTT connection...");
    if (mqttClient.connect(clientId.c_str()))
    {                              // 尝试连接MQTT
      Serial.println("connected"); // 连接成功打印消息
    }
    else
    {
      Serial.print("failed, rc="); // 连接失败打印错误代码
      Serial.print(mqttClient.state());
      Serial.println(" try again in 5 seconds");
      delay(5000); // 延时后重试
    }
  }
}

void setup()
{
  Serial.begin(115200); // 开始串行通信
  connectToWiFi();      // 连接WiFi
  connectToMQTT();      // 连接MQTT服务器
  dht.begin();          // DHT初始化
  pinMode(GPIO_MQ8_PIN, INPUT);
  pinMode(GPIO_MQ7_PIN, INPUT);
  pinMode(GPIO_MQ2_PIN, INPUT);
}

void loop()
{
  if (!mqttClient.connected())
  {
    connectToMQTT();
  }
  mqttClient.loop();
  unsigned long currentMillis = millis(); // 获取当前时间
  // 检查是否到了执行10秒任务的时间
  if (currentMillis - previousMillis10s >= interval10s)
  {
    previousMillis10s = currentMillis;
    Serial.println("10秒任务开始");
    // 10秒任务
    float t = dht.readTemperature();
    String formattedTemperature = String(t, 2); // 将温度格式化为两位小数的字符串
    int mq8 = analogRead(GPIO_MQ8_PIN);
    int mq7 = analogRead(GPIO_MQ7_PIN);
    int mq2 = analogRead(GPIO_MQ2_PIN);
    // 生成属性 JSON
    DynamicJsonDocument obj(512);
    obj["device_mac"] = WiFi.softAPmacAddress();
    obj["temperature"] = t; // 字符串转回float，已经是两位小数
    obj["hydrogen"] = mq8;
    obj["co"] = mq7;
    obj["smoke"] = mq2;
    char attributes[512];
    serializeJson(obj, attributes);
    mqttClient.publish(sensor_topic, attributes);
    Serial.println("10秒任务结束");
  }

  // 检查是否到了执行1分钟任务的时间
  if (currentMillis - previousMillis1m >= interval1m)
  {
    previousMillis1m = currentMillis;
    Serial.println("1分钟任务开始");
    Serial.println("Scan start");
    int n = WiFi.scanNetworks();
    Serial.print("Scanned NumNetworks=");
    Serial.println(n);
    Serial.println("Scan done");

    if (n == 0)
    {
      Serial.println("No networks found");
    }
    else
    {
      int skippedCount = 0; // 定义一个计数器变量用于统计跳过的AP数量
      for (int i = 0; i < n; ++i)
      {
        if (WiFi.RSSI(i) > WiFi_threehold)
        {
          DynamicJsonDocument obj(512);                // 创建JSON文档
          obj["device_mac"] = WiFi.softAPmacAddress(); // 添加本机的AP_MAC地址
          obj["ap_mac"] = WiFi.BSSIDstr(i);            // 添加AP的MAC地址
          obj["rssi"] = WiFi.RSSI(i);                  // 添加AP的RSSI值
          char jsonBuffer[512];                        // 创建字符缓冲区
          serializeJson(obj, jsonBuffer);              // 序列化JSON文档
          mqttClient.publish(rssi_topic, jsonBuffer);  // 发布JSON数据到MQTT主题
          obj.clear();                                 // 清除JSON文档
          delay(100);                                  // 延迟100ms
        }
        else
        {
          skippedCount++; // 跳过的AP数量加1
        }
      }
    }
    Serial.println("1分钟任务结束");
    Serial.println("-----------------------------------------------------------------------");
  }
}