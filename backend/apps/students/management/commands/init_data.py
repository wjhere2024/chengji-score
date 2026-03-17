"""
初始化系统数据
创建默认管理员、科目、班级，并导入学生数据
"""
import os
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.users.models import User
from apps.subjects.models import Subject
from apps.classes.models import Class
from apps.students.models import Student


class Command(BaseCommand):
    help = '初始化系统数据：创建管理员、科目、班级，导入学生'

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-admin',
            action='store_true',
            help='跳过创建管理员账号'
        )
        parser.add_argument(
            '--skip-subjects',
            action='store_true',
            help='跳过创建科目'
        )
        parser.add_argument(
            '--skip-students',
            action='store_true',
            help='跳过导入学生'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始初始化系统数据...'))

        try:
            with transaction.atomic():
                # 1. 创建管理员账号
                if not options['skip_admin']:
                    self.create_admin()

                # 2. 创建科目
                if not options['skip_subjects']:
                    self.create_subjects()

                # 3. 创建班级
                self.create_classes()

                # 4. 导入学生数据
                if not options['skip_students']:
                    self.import_students()

            self.stdout.write(self.style.SUCCESS('✓ 系统数据初始化完成！'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ 初始化失败：{str(e)}'))
            raise

    def create_admin(self):
        """创建默认管理员账号"""
        self.stdout.write('创建管理员账号...')

        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'real_name': '系统管理员',
                'role': User.Role.ADMIN,
                'roles': [User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.SUBJECT_TEACHER],
                'current_role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True
            }
        )

        if created:
            admin.set_password('admin123')
            admin.save()
            self.stdout.write(self.style.SUCCESS('  ✓ 管理员账号创建成功'))
            self.stdout.write(self.style.WARNING('  账号：admin  密码：admin123'))
            self.stdout.write(self.style.SUCCESS('  ✓ 可切换身份：管理员、班主任、任课教师'))
        else:
            # 更新已存在的管理员账号，添加多角色支持
            if not admin.roles or len(admin.roles) <= 1:
                admin.roles = [User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.SUBJECT_TEACHER]
                admin.current_role = User.Role.ADMIN
                admin.save()
                self.stdout.write(self.style.SUCCESS('  ✓ 管理员账号已更新为多身份'))
            else:
                self.stdout.write('  - 管理员账号已存在')

    def create_subjects(self):
        """创建默认科目"""
        self.stdout.write('创建科目...')

        subjects_data = [
            {'name': '语文', 'code': 'CHINESE', 'order': 1, 'applicable_grades': [1, 2, 3, 4, 5, 6]},
            {'name': '数学', 'code': 'MATH', 'order': 2, 'applicable_grades': [1, 2, 3, 4, 5, 6]},
            {'name': '英语', 'code': 'ENGLISH', 'order': 3, 'applicable_grades': [3, 4, 5, 6]},
            {'name': '科学', 'code': 'SCIENCE', 'order': 4, 'applicable_grades': [3, 4, 5, 6]},
            {'name': '道德与法治', 'code': 'ETHICS', 'order': 5, 'applicable_grades': [1, 2, 3, 4, 5, 6]},
            {'name': '音乐', 'code': 'MUSIC', 'order': 6, 'applicable_grades': [1, 2, 3, 4, 5, 6]},
            {'name': '美术', 'code': 'ART', 'order': 7, 'applicable_grades': [1, 2, 3, 4, 5, 6]},
            {'name': '体育', 'code': 'PE', 'order': 8, 'applicable_grades': [1, 2, 3, 4, 5, 6]},
        ]

        count = 0
        for subject_data in subjects_data:
            _, created = Subject.objects.get_or_create(
                code=subject_data['code'],
                defaults=subject_data
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ 创建了 {count} 个科目'))

    def create_classes(self):
        """创建班级"""
        self.stdout.write('创建班级...')

        # 根据现有数据创建6个班级（一1到六1）
        classes_data = [
            {'grade': 1, 'class_number': 1, 'name': '一1班'},
            {'grade': 2, 'class_number': 1, 'name': '二1班'},
            {'grade': 3, 'class_number': 1, 'name': '三1班'},
            {'grade': 4, 'class_number': 1, 'name': '四1班'},
            {'grade': 5, 'class_number': 1, 'name': '五1班'},
            {'grade': 6, 'class_number': 1, 'name': '六1班'},
        ]

        count = 0
        for class_data in classes_data:
            _, created = Class.objects.get_or_create(
                grade=class_data['grade'],
                class_number=class_data['class_number'],
                academic_year='2024-2025',
                semester='第二学期',
                defaults={'name': class_data['name']}
            )
            if created:
                count += 1

        self.stdout.write(self.style.SUCCESS(f'  ✓ 创建了 {count} 个班级'))

    def import_students(self):
        """导入学生数据"""
        self.stdout.write('导入学生数据...')

        # 查找CSV文件目录
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        data_dir = os.path.join(project_root, '..', 'data')

        # 如果data目录不存在，尝试当前目录
        if not os.path.exists(data_dir):
            data_dir = os.path.join(project_root, '..')

        csv_files = [
            '2025.6柳园小学1-6花名册_一1.csv',
            '2025.6柳园小学1-6花名册_二1.csv',
            '2025.6柳园小学1-6花名册_三1.csv',
            '2025.6柳园小学1-6花名册_四1.csv',
            '2025.6柳园小学1-6花名册_五1.csv',
            '2025.6柳园小学1-6花名册_六1.csv',
        ]

        total_count = 0
        grade_map = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6}

        for csv_file in csv_files:
            file_path = os.path.join(data_dir, csv_file)

            if not os.path.exists(file_path):
                self.stdout.write(self.style.WARNING(f'  ! 文件不存在：{csv_file}'))
                continue

            try:
                # 读取CSV（跳过前两行标题）
                df = pd.read_csv(file_path, encoding='utf-8-sig', skiprows=2)

                # 解析班级名称
                for cn_grade, num_grade in grade_map.items():
                    if cn_grade in csv_file:
                        class_obj = Class.objects.filter(
                            grade=num_grade,
                            class_number=1
                        ).first()
                        break

                if not class_obj:
                    self.stdout.write(self.style.WARNING(f'  ! 找不到班级：{csv_file}'))
                    continue

                # 导入学生
                count = 0
                for _, row in df.iterrows():
                    student_id = str(row.get('考号', '')).strip()
                    name = str(row.get('姓名', '')).strip()

                    if not student_id or not name or student_id == 'nan' or name == 'nan':
                        continue

                    _, created = Student.objects.update_or_create(
                        student_id=student_id,
                        defaults={
                            'name': name,
                            'class_obj': class_obj,
                            'is_active': True
                        }
                    )

                    if created:
                        count += 1

                total_count += count
                self.stdout.write(f'  ✓ {class_obj.name}：导入 {count} 名学生')

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ 导入 {csv_file} 失败：{str(e)}'))

        # 更新班级学生人数
        for class_obj in Class.objects.all():
            class_obj.update_student_count()

        self.stdout.write(self.style.SUCCESS(f'  ✓ 总共导入 {total_count} 名学生'))
