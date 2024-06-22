from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


def paginate_items(request, queryset, items_per_page):
    paginator = Paginator(queryset, items_per_page)
    page = request.GET.get('page')
    try:
        items = paginator.page(page)
    except PageNotAnInteger:
        items = paginator.page(1)
    except EmptyPage:
        items = paginator.page(paginator.num_pages)

    return items
