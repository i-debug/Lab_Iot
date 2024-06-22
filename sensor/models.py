from django.db import models


class Sensor_Data(models.Model):
    device_mac = models.CharField(max_length=17)  # MAC地址通常是17个字符
    temperature = models.DecimalField(max_digits=5, decimal_places=2,null=False, default=0.0)
    hydrogen = models.IntegerField()  # 氢气浓度，使用整数表示
    co = models.IntegerField()  # 一氧化碳浓度，使用整数表示
    smoke = models.IntegerField()  # 烟雾浓度，使用整数表示
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_mac} - {self.timestamp}"


class RSSI_Data(models.Model):
    device_mac = models.CharField(max_length=17)  # 设备的MAC地址
    ap_mac = models.CharField(max_length=17)  # 接入点的MAC地址
    rssi = models.IntegerField()  # 接收信号强度，使用整数表示
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"RSSI {self.rssi} from {self.device_mac} to AP {self.ap_mac}- {self.timestamp}"

class Admin(models.Model):
    username = models.CharField(verbose_name="用户名",max_length=32)
    password = models.CharField(verbose_name="密码",max_length=64)
