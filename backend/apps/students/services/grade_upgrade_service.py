"""
年级升级服务
处理学生年级升级、毕业生归档等操作

重构说明：班级不再区分学年学期，升级时直接将1-5年级班级的grade+1，
六年级学生归档毕业。
"""
from django.db import transaction
from django.utils import timezone
from apps.students.models import Student
from apps.students.models_graduated import GraduatedStudent
from apps.classes.models import Class
from datetime import datetime


class GradeUpgradeService:
    """年级升级服务"""

    @staticmethod
    def check_can_upgrade(current_academic_year=None, new_academic_year=None):
        """
        检查是否可以进行年级升级

        Returns:
            dict: {'can_upgrade': bool, 'message': str, 'statistics': dict, 'warnings': list}
        """
        warnings = []

        # 检查当前月份，如果不是8-9月，给出警告
        now = datetime.now()
        current_month = now.month
        if current_month not in [8, 9]:
            warnings.append(f'当前是{current_month}月，不是开学季（8-9月），请确认是否需要在此时升级年级')

        # 统计各年级学生人数
        statistics = {}
        for grade in range(1, 7):
            students_count = Student.objects.filter(
                class_obj__grade=grade,
                class_obj__is_active=True,
                is_active=True
            ).count()
            statistics[f'grade_{grade}'] = students_count

        grade_6_students = statistics.get('grade_6', 0)

        return {
            'can_upgrade': True,
            'message': '可以进行年级升级',
            'statistics': {
                **statistics,
                'total_students': sum(statistics.values()),
                'graduating_students': grade_6_students
            },
            'warnings': warnings
        }

    @staticmethod
    @transaction.atomic
    def upgrade_grades(current_academic_year=None, new_academic_year=None, semester='第一学期'):
        """
        执行年级升级：
        1. 将六年级学生归档为毕业生
        2. 将1-5年级班级的grade直接+1（就地升级，不创建新班级）
        3. 更新各班级的班级名称

        Args:
            current_academic_year: 当前学年（用于毕业生记录，如 "2025-2026"）
            new_academic_year: 新学年（当前可不用，保留参数兼容性）
            semester: 保留参数兼容性

        Returns:
            dict: 升级结果统计
        """
        result = {
            'success': False,
            'message': '',
            'graduated_count': 0,
            'upgraded_count': 0,
            'new_classes_count': 0,
            'details': []
        }

        try:
            # 1. 处理六年级学生（归档毕业生）
            grade_6_students = Student.objects.filter(
                class_obj__grade=6,
                class_obj__is_active=True,
                is_active=True
            )

            graduated_count = 0
            graduation_year = current_academic_year or str(datetime.now().year)
            for student in grade_6_students:
                GraduatedStudent.objects.create(
                    student_id=student.student_id,
                    name=student.name,
                    gender=student.gender,
                    birth_date=student.birth_date,
                    id_number=student.id_number,
                    graduation_year=graduation_year,
                    graduation_class_name=str(student.class_obj),
                    graduation_grade=6,
                    phone=student.phone,
                    parent_name=student.parent_name,
                    parent_phone=student.parent_phone,
                    address=student.address,
                    admission_date=student.admission_date,
                    admission_year=student.admission_year,
                    enrollment_type=student.enrollment_type,
                    avatar=student.avatar,
                    notes=student.notes
                )
                student.is_active = False
                student.save()
                graduated_count += 1

            result['graduated_count'] = graduated_count
            result['details'].append(f'归档毕业生：{graduated_count} 人')

            # 2. 将1-5年级班级的grade直接+1（就地升级）
            upgraded_count = 0
            current_classes = Class.objects.filter(
                grade__in=[1, 2, 3, 4, 5],
                is_active=True
            ).order_by('-grade', 'class_number')  # 从高年级开始，避免唯一约束冲突

            for cls in current_classes:
                new_grade = cls.grade + 1
                cls.grade = new_grade
                cls.name = f'{Class.Grade(new_grade).label}{cls.class_number}班'
                cls.save(update_fields=['grade', 'name'])

                # 统计该班级升级的学生数
                student_count = Student.objects.filter(
                    class_obj=cls,
                    is_active=True
                ).count()
                upgraded_count += student_count

            result['upgraded_count'] = upgraded_count
            result['details'].extend([
                f'升级班级：{current_classes.count()} 个',
                f'升级学生：{upgraded_count} 人',
            ])

            result['success'] = True
            result['message'] = '年级升级成功'

        except Exception as e:
            result['message'] = f'年级升级失败：{str(e)}'
            raise

        return result

    @staticmethod
    def get_graduated_students(graduation_year=None, page=1, page_size=20):
        """
        获取毕业生列表

        Args:
            graduation_year: 毕业学年（可选）
            page: 页码
            page_size: 每页数量

        Returns:
            dict: 毕业生列表和统计信息
        """
        queryset = GraduatedStudent.objects.all()
        if graduation_year:
            queryset = queryset.filter(graduation_year=graduation_year)

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        students = queryset[start:end]

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'students': [
                {
                    'id': s.id,
                    'student_id': s.student_id,
                    'name': s.name,
                    'gender': s.gender,
                    'graduation_year': s.graduation_year,
                    'graduation_class_name': s.graduation_class_name,
                    'graduation_grade': s.graduation_grade,
                    'phone': s.phone,
                    'parent_name': s.parent_name,
                    'parent_phone': s.parent_phone,
                }
                for s in students
            ]
        }
