from django.shortcuts import render
from sensor.models import RSSI_Data
from sensor.utils import paginate_items


def rssi_data(request):
    # 从数据库中获取所有RSSI记录，假设我们有一个timestamp字段来进行排序
    rssi_list = RSSI_Data.objects.all().order_by('-timestamp')  # 如果没有timestamp字段，可以使用'id'字段作为替代
    # 创建context字典，将rssi_list包含进去
    queryset = paginate_items.paginate_items(request, rssi_list, 30)
    # page_number = request.GET.get('page')
    # page_obj = paginator.get_page(page_number)
    context = {'items': queryset}
    # 使用render函数将数据和模板结合，生成最终的HTML页面
    return render(request, 'rssidata.html', context)
