from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect


class AuthMiddleware(MiddlewareMixin):
    @staticmethod
    def process_request(request):
        # 定义需要登录的路径列表
        protected_paths = [
            # '/admin/',  # 示例路径
            '/sensordata/',
            '/rssidata/',
            '/layout/',
            '/admin/list/',
            '/admin/add/',
            '/admin/<int:nid>/edit/'
            '/admin/<int:nid>/delete/',
            '/admin/<int:nid>/reset/',
            '/monitor/temp/',
            '/monitor/smoke/',
            '/monitor/hydrogen/',
            '/monitor/co/',
            '/sysinfo/state/'
        ]

        # 如果请求路径在保护路径列表中，则进行登录检查
        if request.path_info in protected_paths:
            info_dict = request.session.get("info")
            if info_dict:
                return None
            return redirect('/login/')

        # 对于其他路径，不进行任何处理，允许访问
        return None