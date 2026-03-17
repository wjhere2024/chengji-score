"""
学豆工具函数 - 用于统一处理学豆变动逻辑
"""
from django.db.models import F


def update_beans_by_status_change(student_id, old_status, new_status, source, detail=''):
    """
    根据掌握状态变化更新学豆
    
    规则:
    - 未测试(0)/需加强(2) → 掌握(1): +1 豆
    - 掌握(1) → 需加强(2): -1 豆
    - 其他情况: 不变
    
    Args:
        student_id: 学生ID
        old_status: 旧状态 (0=未测试, 1=掌握, 2=需加强)
        new_status: 新状态
        source: 来源 ('dictation', 'reading', 'comment', 'correction')
        detail: 详情说明
    
    Returns:
        int: 学豆变动数量 (可能为 +1, -1, 或 0)
    """
    from apps.students.models import Student, BeanLog
    
    bean_change = 0
    
    # 变成掌握: +1
    if old_status != 1 and new_status == 1:
        bean_change = 1
    # 掌握变成错误: -1
    elif old_status == 1 and new_status == 2:
        bean_change = -1
    
    if bean_change != 0:
        # 更新学生学豆总数（确保不会变成负数）
        Student.objects.filter(id=student_id).update(
            learning_beans=F('learning_beans') + bean_change
        )
        # 记录日志
        BeanLog.objects.create(
            student_id=student_id,
            amount=bean_change,
            source=source,
            detail=detail
        )
    
    return bean_change


def calculate_beans_batch(student_id, items_status_changes, source, detail=''):
    """
    批量计算学豆变动（用于一次性提交多个词语的场景）
    
    Args:
        student_id: 学生ID
        items_status_changes: 列表，每项为 (old_status, new_status) 元组
        source: 来源
        detail: 详情
    
    Returns:
        int: 总学豆变动数量
    """
    from apps.students.models import Student, BeanLog
    
    total_change = 0
    for old_status, new_status in items_status_changes:
        if old_status != 1 and new_status == 1:
            total_change += 1
        elif old_status == 1 and new_status == 2:
            total_change -= 1
    
    if total_change != 0:
        Student.objects.filter(id=student_id).update(
            learning_beans=F('learning_beans') + total_change
        )
        BeanLog.objects.create(
            student_id=student_id,
            amount=total_change,
            source=source,
            detail=detail
        )
    
    return total_change
