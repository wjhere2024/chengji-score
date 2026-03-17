"""
自定义分页类
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    标准分页类
    - 默认每页20条
    - 允许客户端通过 page_size 参数自定义每页数量
    - 最大每页1000条（支持大班级）
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000
