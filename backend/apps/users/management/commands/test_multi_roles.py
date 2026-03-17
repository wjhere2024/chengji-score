"""
测试多角色切换功能
验证用户的多角色配置是否正确
"""
from django.core.management.base import BaseCommand
from apps.users.models import User


class Command(BaseCommand):
    help = '测试多角色切换功能'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n=== 多角色功能测试 ===\n'))

        # 测试管理员账号
        self.stdout.write('1. 测试管理员账号 (admin)...')
        try:
            admin = User.objects.get(username='admin')
            self.stdout.write(f'   用户: {admin.real_name}')
            self.stdout.write(f'   主要角色: {admin.get_role_display()}')
            self.stdout.write(f'   所有角色: {admin.roles}')
            self.stdout.write(f'   当前激活角色: {admin.get_role_display_name()}')
            self.stdout.write(f'   拥有多个角色: {"是" if admin.has_multiple_roles else "否"}')

            # 测试角色切换
            if admin.has_multiple_roles:
                self.stdout.write('\n   测试角色切换:')
                for role in admin.roles:
                    if role != admin.current_role:
                        success = admin.switch_role(role)
                        if success:
                            self.stdout.write(f'   [OK] 切换到 {admin.get_role_display_name()} 成功')
                        else:
                            self.stdout.write(self.style.ERROR(f'   [ERROR] 切换到 {role} 失败'))

                # 恢复默认角色
                admin.switch_role(admin.role)
                self.stdout.write(f'   [OK] 恢复为默认角色: {admin.get_role_display_name()}')

            self.stdout.write(self.style.SUCCESS('   [PASS] 管理员账号测试通过'))
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('   [ERROR] 管理员账号不存在'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   [ERROR] {str(e)}'))

        # 测试班主任账号
        self.stdout.write('\n2. 测试班主任账号...')
        head_teachers = User.objects.filter(role=User.Role.HEAD_TEACHER)[:1]
        if head_teachers.exists():
            teacher = head_teachers.first()
            self.stdout.write(f'   用户: {teacher.real_name}')
            self.stdout.write(f'   主要角色: {teacher.get_role_display()}')
            self.stdout.write(f'   所有角色: {teacher.roles}')
            self.stdout.write(f'   当前激活角色: {teacher.get_role_display_name()}')
            self.stdout.write(f'   拥有多个角色: {"是" if teacher.has_multiple_roles else "否"}')

            if teacher.has_multiple_roles:
                self.stdout.write(self.style.SUCCESS('   [PASS] 班主任账号已配置多角色'))
            else:
                self.stdout.write(self.style.WARNING('   [WARNING] 班主任账号未配置多角色'))
        else:
            self.stdout.write(self.style.WARNING('   [WARNING] 没有班主任账号'))

        # 统计信息
        self.stdout.write('\n3. 多角色用户统计...')
        total_users = User.objects.count()
        multi_role_users = User.objects.filter(roles__len__gt=1).count()

        self.stdout.write(f'   总用户数: {total_users}')
        self.stdout.write(f'   多角色用户数: {multi_role_users}')

        # 按角色统计
        for role_choice in User.Role.choices:
            role_code, role_name = role_choice
            count = User.objects.filter(role=role_code).count()
            multi_count = User.objects.filter(role=role_code, roles__len__gt=1).count()
            self.stdout.write(f'   {role_name}: {count} 个 (其中 {multi_count} 个支持多角色)')

        self.stdout.write(self.style.SUCCESS('\n=== 测试完成 ===\n'))
