from django.shortcuts import render
from django.utils import timezone
from datetime import timedelta
from sensor.models import Sensor_Data
import pytz


def get_sysinfo(request):
    now = timezone.now()

    # 获取请求的时间段参数
    period = request.GET.get('period', 'last_10_minutes')

    # 定义时间段和子时间段
    time_periods = {
        'last_10_minutes': {'start': now - timedelta(minutes=10), 'interval': timedelta(minutes=2), 'points': 5},
        'last_hour': {'start': now - timedelta(hours=1), 'interval': timedelta(minutes=10), 'points': 6},
        'last_day': {'start': now - timedelta(days=1), 'interval': timedelta(hours=4), 'points': 6},
        'last_week': {'start': now - timedelta(weeks=1), 'interval': timedelta(days=1), 'points': 7},
    }

    selected_period = time_periods.get(period, time_periods['last_10_minutes'])
    start_time = selected_period['start']
    interval = selected_period['interval']
    points = selected_period['points']

    # 初始化结果列表
    unique_devices_counts = []
    total_data_counts = []
    labels = []

    # 设置本地时区
    local_tz = pytz.timezone('Asia/Shanghai')

    for i in range(points):
        end_time = start_time + interval
        recent_data = Sensor_Data.objects.filter(timestamp__gte=start_time, timestamp__lt=end_time)
        unique_devices_count = recent_data.values('device_mac').distinct().count()
        total_data_count = recent_data.count()

        unique_devices_counts.append(unique_devices_count)
        total_data_counts.append(total_data_count)

        # 转换时间到本地时区并格式化
        local_start_time = start_time.astimezone(local_tz)
        local_end_time = end_time.astimezone(local_tz)
        labels.append(f'{local_start_time.strftime("%m/%d:%H:%M")}-{local_end_time.strftime("%m/%d:%H:%M")}')

        start_time = end_time

    result = {
        'data': list(zip(labels, unique_devices_counts, total_data_counts)),
        'labels': labels,
        'unique_devices_counts': unique_devices_counts,
        'total_data_counts': total_data_counts
    }

    return render(request, 'sysinfo.html', {
        'sysinfo': result,
        'selected_period': period,
        'time_periods': list(time_periods.keys())
    })

# 示例结果格式
# {
#     'last_10_minutes': {'unique_devices_count': 5, 'total_data_count': 100},
#     'last_hour': {'unique_devices_count': 10, 'total_data_count': 500},
#     'last_day': {'unique_devices_count': 20, 'total_data_count': 2000},
#     'last_week': {'unique_devices_count': 50, 'total_data_count': 10000},
# }