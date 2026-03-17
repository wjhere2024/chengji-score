"""
为现有用户添加多角色支持
根据用户实际担任的角色(班主任、任课教师)来配置多角色权限
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.users.models import User


class Command(BaseCommand):
    help = '为现有用户添加多角色支持(基于实际担任角色)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='指定要更新的用户名(不指定则更新所有用户)'
        )
        parser.add_argument(
            '--force-admin-multi-role',
            action='store_true',
            help='强制为所有管理员添加班主任和教师角色(不检查实际担任情况)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('开始更新多角色配置...'))
        self.force_admin = options.get('force_admin_multi_role', False)

        try:
            with transaction.atomic():
                if options['username']:
                    # 更新指定用户
                    self.update_user(options['username'])
                else:
                    # 更新所有用户
                    self.update_all_users()

            self.stdout.write(self.style.SUCCESS('\n[OK] 多角色配置更新完成！'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'[ERROR] 更新失败：{str(e)}'))
            raise

    def get_user_actual_roles(self, user):
        """
        获取用户实际担任的角色
        基于数据库中的实际数据判断
        """
        from apps.classes.models import Class
        from apps.teachers.models import TeachingAssignment

        actual_roles = set()

        # 1. 主要角色必须包含
        actual_roles.add(user.role)

        # 2. 检查是否是班主任(担任某个班级的班主任)
        is_head_teacher = Class.objects.filter(head_teacher=user).exists()
        if is_head_teacher:
            actual_roles.add(User.Role.HEAD_TEACHER.value)

        # 3. 检查是否是任课教师(有任课安排)
        is_subject_teacher = TeachingAssignment.objects.filter(teacher=user).exists()
        if is_subject_teacher:
            actual_roles.add(User.Role.SUBJECT_TEACHER.value)

        # 4. 对于管理员的特殊处理
        if user.role in [User.Role.SUPER_ADMIN, User.Role.ADMIN]:
            if self.force_admin:
                # 如果使用强制模式,管理员可以切换到所有角色
                if user.role == User.Role.SUPER_ADMIN:
                    actual_roles = {User.Role.SUPER_ADMIN.value, User.Role.ADMIN.value,
                                   User.Role.HEAD_TEACHER.value, User.Role.SUBJECT_TEACHER.value}
                else:
                    actual_roles = {User.Role.ADMIN.value, User.Role.HEAD_TEACHER.value,
                                   User.Role.SUBJECT_TEACHER.value}
            else:
                # 正常模式下,管理员始终保留管理员角色
                # 但只有在实际担任班主任或教师时才添加对应角色
                pass

        return sorted(list(actual_roles))

    def update_user(self, username):
        """更新指定用户的多角色配置"""
        try:
            user = User.objects.get(username=username)
            old_roles = user.roles.copy() if user.roles else []

            # 获取用户实际担任的角色
            new_roles = self.get_user_actual_roles(user)

            user.roles = new_roles
            if not user.current_role or user.current_role not in new_roles:
                user.current_role = user.role
            user.save()

            self.stdout.write(self.style.SUCCESS(
                f'  [OK] {user.real_name}({username})：{user.get_role_display()}'
            ))
            self.stdout.write(f'       旧角色: {old_roles}')
            self.stdout.write(f'       新角色: {new_roles}')

        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'  [ERROR] 用户不存在：{username}'))

    def update_all_users(self):
        """更新所有用户的多角色配置"""
        if self.force_admin:
            self.stdout.write(self.style.WARNING(
                '\n[提示] 使用强制模式：所有管理员将获得班主任和教师角色'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                '\n[提示] 使用智能模式：仅为实际担任角色的用户添加对应权限'
            ))

        users = User.objects.all().order_by('role', 'real_name')

        stats = {
            'updated': 0,
            'unchanged': 0,
            'by_role': {}
        }

        for user in users:
            old_roles = user.roles.copy() if user.roles else []
            new_roles = self.get_user_actual_roles(user)

            if old_roles != new_roles:
                user.roles = new_roles
                if not user.current_role or user.current_role not in new_roles:
                    user.current_role = user.role
                user.save()

                stats['updated'] += 1
                role_display = user.get_role_display()
                if role_display not in stats['by_role']:
                    stats['by_role'][role_display] = 0
                stats['by_role'][role_display] += 1

                self.stdout.write(f'  [OK] {user.real_name}({user.username})')
                self.stdout.write(f'       {old_roles} -> {new_roles}')
            else:
                stats['unchanged'] += 1

        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS(f'更新完成：'))
        self.stdout.write(f'  - 已更新: {stats["updated"]} 人')
        self.stdout.write(f'  - 无变化: {stats["unchanged"]} 人')

        if stats['by_role']:
            self.stdout.write('\n按角色统计：')
            for role, count in stats['by_role'].items():
                self.stdout.write(f'  - {role}: {count} 人')

