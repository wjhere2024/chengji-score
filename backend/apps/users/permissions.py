"""
用户权限类
"""
from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """
    超级管理员权限（可增删改查用户）
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_super_admin


class IsAdmin(permissions.BasePermission):
    """
    管理员权限（包括超级管理员和普通管理员，普通管理员只读）
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_admin


class IsHeadTeacher(permissions.BasePermission):
    """
    班主任权限
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_head_teacher


class IsSubjectTeacher(permissions.BasePermission):
    """
    任课教师权限
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_subject_teacher


class IsAdminOrHeadTeacher(permissions.BasePermission):
    """
    管理员或班主任权限
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_admin or request.user.is_head_teacher)
        )
