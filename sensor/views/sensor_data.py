from django.shortcuts import render
from sensor.models import Sensor_Data
from sensor.utils import paginate_items


def sensor_data(request):
    # 从数据库中获取所有DeviceData记录，按timestamp字段倒序排序
    data_list = Sensor_Data.objects.all().order_by('-timestamp')
    # 创建context字典，将data_list包含进去
    queryset = paginate_items.paginate_items(request, data_list, 30)
    # page_number = request.GET.get('page')
    # page_obj = paginator.get_page(page_number)
    context = {'items': queryset}

    # 使用render函数将数据和模板结合，生成最终的HTML页面
    return render(request, 'sensordata.html', context)
