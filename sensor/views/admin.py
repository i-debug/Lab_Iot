from django.shortcuts import render
from sensor.models import Admin
from sensor.utils import paginate_items


def admin_list(request):

    # info_dict = request.session["info"]

    # search
    data_dict = {}
    search_data = request.GET.get('q', "")
    if search_data:
        data_dict["username__contains"] = search_data

    # get data by search result
    queryset = Admin.objects.filter(**data_dict)
    paginated_items = paginate_items.paginate_items(request, queryset, 10)
    context = {
        'items': paginated_items,
        "search_data": search_data,
               }
    return render(request, 'admin.html', context)
