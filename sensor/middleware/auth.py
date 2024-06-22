from django.utils.deprecation import (MiddlewareMixin)
from django.shortcuts import HttpResponse, redirect


# class AuthMiddleware(MiddlewareMixin):
#
#     def process_request(self, request):
#         if request.path_info == '/login/':
#             return None
#         info_dict = request.session.get("info")
#         print(info_dict)
#         if info_dict:
#             return
#         return redirect('/login/')

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect

class AuthMiddleware(MiddlewareMixin):

    def process_request(self, request):
        # 定义一个需要登录的路径列表
        protected_paths = [
            # '/admin/',  # 示例路径
            '/dashboard/',  # 示例路径
        ]

        # 如果请求路径在保护路径列表中，则进行登录检查
        if request.path_info in protected_paths:
            info_dict = request.session.get("info")
            # print(info_dict)
            if info_dict:
                return None
            return redirect('/login/')

        # 对于其他路径，不进行任何处理，允许访问
        return None