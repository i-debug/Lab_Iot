

# 基于Wi-Fi的无锚定位

## 项目简介

这是一个基于Django框架和PlatformIO的开源物联网项目，硬件选用ESP32开发板和多种传感器。后端订阅MQTT数据并生成热力图。通过这个项目，用户可以实时监控实验室的温度、烟雾、氢气浓度等分布情况。

## 功能特点

- 多种传感器数据实时上报MQTT服务器
- 订阅MQTT消息队列中的温度数据
- 存储Topic数据到数据库
- 实时相对位置求解
- 实时生成各项理化指标热力图
- Web界面实时监看
- 方案适应性强 成本较低

## 安装指南

- Python 3.10
- Django 4.1
- MQTT Broker (本项目使用 EMQX)
  
  

## 烧录开发板固件



```cpp
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
const char *ssid = "";               // Wi-Fi网络名称
const char *password = "";          // Wi-Fi网络密码
const char *mqtt_server = ""; // MQTT服务器地址
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
  }
  // 获取 MAC 地址并生成随机 AP 名称
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char ap_ssid[32];
  snprintf(ap_ssid, sizeof(ap_ssid), "ESP32-AP-%02X%02X%02X", mac[3], mac[4], mac[5]);
  // Access Point 模式
  WiFi.softAP(ap_ssid, "password123");
}

void connectToMQTT()
{
  String clientId = generateClientId();
  mqttClient.setServer(mqtt_server, 31111); // 设置MQTT服务器和端口

  while (!mqttClient.connected())
  { // 如果客户端未连接，则尝试连接
    if (mqttClient.connect(clientId.c_str()))
    {                              // 尝试连接MQTT
      Serial.println("connected"); // 连接成功打印消息
    }
    else
    {
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
  }

  // 检查是否到了执行1分钟任务的时间
  if (currentMillis - previousMillis1m >= interval1m)
  {
    previousMillis1m = currentMillis;
    int n = WiFi.scanNetworks();
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
  }
}
```





## 修改mqtt.py配置

```
MQTT_BROKER_HOST=mqtt://your_broker_url
MQTT_BROKER_PORT=1883
SENSOR_TOPIC = "sensor"
RSSI_TOPIC = "rssi"
```

# 运行项目

```python
python manage.py runserver localhost:8000
```

# 数据体格式

```json
# 在model.py中定义

# sensor Topic：
{"device_mac":"64:B7:08:69:87:25","temperature":34,"hydrogen":0,"co":1156,"smoke":90}
# rssi Topic：
{"device_mac":"B0:A7:32:1F:5F:81","ap_mac":"28:2C:B2:4A:08:3C","rssi":-78}
```



目录结构

```
Labiot/
├── img/  # 存放图片资源
├── Labiot/  # 项目主目录
├── sensor/  # 应用目录
│   ├── middleware/  # 中间件目录
│   │   └── auth.py  # 认证中间件
│   ├── static/  # 静态文件目录
│   │   ├── css/  # CSS 文件目录
│   │   ├── fonts/  # 字体文件目录
│   │   ├── img/  # 图片文件目录
│   │   ├── js/  # JavaScript 文件目录
│   │   └── __init__.py  # 初始化文件
│   ├── templates/  # 模板文件目录
│   │   ├── __init__.py  # 初始化文件
│   │   ├── admin.html  # 管理员页面模板
│   │   ├── admin_change.html  # 管理员修改页面模板
│   │   ├── admin_edit.html  # 管理员编辑页面模板
│   │   ├── alert.html  # 警报页面模板
│   │   ├── data.html  # 数据页面模板
│   │   ├── error.html  # 错误页面模板
│   │   ├── layout.html  # 布局页面模板
│   │   ├── login.html  # 登录页面模板
│   │   ├── monitorco.html  # 一氧化碳监控页面模板
│   │   ├── monitorhydrogen.html  # 氢气监控页面模板
│   │   ├── monitorsmoke.html  # 烟雾监控页面模板
│   │   ├── monitortemp.html  # 温度监控页面模板
│   │   ├── rssidata.html  # RSSI 数据页面模板
│   │   ├── sensordata.html  # 传感器数据页面模板
│   │   └── sysinfo.html  # 系统信息页面模板
│   ├── utils/  # 工具文件目录
│   │   ├── arial.ttf  # 字体文件
│   │   ├── code.py  # 验证码工具
│   │   ├── encrypt.py  # 加密工具
│   │   └── paginate_items.py  # 分页工具
│   ├── views/  # 视图文件目录
│   │   ├── __init__.py  # 初始化文件
│   │   ├── account.py  # 账户视图
│   │   ├── admin.py  # 管理员视图
│   │   ├── admin_add.py  # 添加管理员视图
│   │   ├── heatmap.py  # 热力图视图
│   │   ├── itu_indoor_path_loss.py  # ITU 室内路径损耗模型求解距离
│   │   ├── mqtt.py  # MQTT 视图
│   │   ├── rssi_data.py  # RSSI 数据视图
│   │   ├── sensor_data.py  # 传感器数据视图
│   │   └── sysinfo.py  # 系统信息视图
│   ├── __init__.py  # 初始化文件
│   ├── admin.py  # 管理员配置文件
│   ├── apps.py  # 应用配置文件
│   ├── models.py  # 数据模型文件
│   ├── tests.py  # 测试文件
├── captcha.png  # 验证码图片
├── db.json  # 数据库JSON备份
├── db.sqlite3  # SQLite数据库文件
├── environment.yml  # 环境配置文件
├── manage.py  # Django管理脚本
└── README.md  # 项目说明文件
├── environment.yml # conda环境配置文件
├── manage.py # Django运行入口
└── README.md # 说明文档
└── main.cpp # 开发板固件 使用Arduino框架



```





## 贡献指南

欢迎任何形式的贡献！请阅读以下内容以了解如何参与。

### 提交问题

如果在使用过程中遇到问题，可以通过GitHub Issues提交问题。

### 贡献代码

1. Fork 此仓库
2. 创建你的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交你的修改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建一个新的Pull Request
   
   
   
   

## 许可证

此项目使用GNU General Public License (GPL) 3.0许可证，详情请参阅LICENSE文件。
