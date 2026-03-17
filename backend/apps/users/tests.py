"""
SchoolScopedQuerysetMixin 单元测试

测试场景：
1. 独立教师模式（无学校）- 只能看到自己班级的数据
2. 学校模式（有学校）- 只能看到本学校的数据
3. 自定义字段配置
"""
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.test import APIRequestFactory

from apps.users.mixins import SchoolScopedQuerysetMixin
from apps.schools.models import School
from apps.classes.models import Class
from apps.students.models import Student

User = get_user_model()


class MockViewSet(SchoolScopedQuerysetMixin, viewsets.ModelViewSet):
    """测试用的 ViewSet，使用 Student 模型"""
    queryset = Student.objects.all()
    
    # 配置字段路径（Student 的学校通过 class_obj 关联）
    school_field = 'class_obj__school'
    head_teacher_field = 'class_obj__head_teacher'


class SchoolScopedQuerysetMixinTestCase(TestCase):
    """SchoolScopedQuerysetMixin 测试类"""
    
    @classmethod
    def setUpTestData(cls):
        """设置测试数据（整个测试类只运行一次）"""
        
        # 创建两个学校
        cls.school_a = School.objects.create(name="学校A", code="SCHOOL_A_001")
        cls.school_b = School.objects.create(name="学校B", code="SCHOOL_B_001")
        
        # 创建独立教师（无学校）
        cls.independent_teacher = User.objects.create_user(
            username='independent_teacher',
            password='testpass123',
            real_name='独立教师',
            role='head_teacher',
            school=None  # 无学校
        )
        
        # 创建学校A的教师
        cls.teacher_school_a = User.objects.create_user(
            username='teacher_a',
            password='testpass123',
            real_name='教师A',
            role='head_teacher',
            school=cls.school_a
        )
        
        # 创建学校B的教师
        cls.teacher_school_b = User.objects.create_user(
            username='teacher_b',
            password='testpass123',
            real_name='教师B',
            role='head_teacher',
            school=cls.school_b
        )
        
        # 创建班级
        # 独立教师的班级（无学校关联）
        cls.class_independent = Class.objects.create(
            name='独立班级',
            grade=4,
            class_number=1,
            academic_year='2024-2025',
            semester='第一学期',
            head_teacher=cls.independent_teacher,
            school=None
        )
        
        # 学校A的班级
        cls.class_school_a = Class.objects.create(
            name='学校A班级',
            grade=4,
            class_number=1,
            academic_year='2024-2025',
            semester='第一学期',
            head_teacher=cls.teacher_school_a,
            school=cls.school_a
        )
        
        # 学校B的班级
        cls.class_school_b = Class.objects.create(
            name='学校B班级',
            grade=4,
            class_number=1,
            academic_year='2024-2025',
            semester='第一学期',
            head_teacher=cls.teacher_school_b,
            school=cls.school_b
        )
        
        # 创建学生
        cls.student_independent = Student.objects.create(
            name='独立学生',
            class_obj=cls.class_independent
        )
        
        cls.student_school_a = Student.objects.create(
            name='学校A学生',
            class_obj=cls.class_school_a
        )
        
        cls.student_school_b = Student.objects.create(
            name='学校B学生',
            class_obj=cls.class_school_b
        )
    
    def setUp(self):
        """每个测试方法运行前执行"""
        self.factory = APIRequestFactory()
        self.view = MockViewSet.as_view({'get': 'list'})
    
    def _make_request(self, user):
        """创建带用户的请求"""
        request = self.factory.get('/api/students/')
        request.user = user
        
        # 创建 ViewSet 实例并获取 queryset
        viewset = MockViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        return viewset.get_queryset()
    
    # ==================== 独立教师模式测试 ====================
    
    def test_independent_teacher_sees_only_own_class_students(self):
        """独立教师只能看到自己班级的学生"""
        queryset = self._make_request(self.independent_teacher)
        
        # 应该只包含独立班级的学生
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.student_independent, queryset)
        self.assertNotIn(self.student_school_a, queryset)
        self.assertNotIn(self.student_school_b, queryset)
    
    def test_independent_teacher_cannot_see_school_students(self):
        """独立教师不能看到有学校的学生"""
        queryset = self._make_request(self.independent_teacher)
        
        student_names = list(queryset.values_list('name', flat=True))
        self.assertNotIn('学校A学生', student_names)
        self.assertNotIn('学校B学生', student_names)
    
    # ==================== 学校模式测试 ====================
    
    def test_school_teacher_sees_only_own_school_students(self):
        """学校教师只能看到本学校的学生"""
        queryset = self._make_request(self.teacher_school_a)
        
        # 应该只包含学校A的学生
        self.assertEqual(queryset.count(), 1)
        self.assertIn(self.student_school_a, queryset)
        self.assertNotIn(self.student_school_b, queryset)
        self.assertNotIn(self.student_independent, queryset)
    
    def test_school_teacher_cannot_see_other_school_students(self):
        """学校A教师不能看到学校B的学生"""
        queryset = self._make_request(self.teacher_school_a)
        
        student_names = list(queryset.values_list('name', flat=True))
        self.assertEqual(student_names, ['学校A学生'])
    
    def test_different_school_teachers_see_different_students(self):
        """不同学校的教师看到不同的学生"""
        queryset_a = self._make_request(self.teacher_school_a)
        queryset_b = self._make_request(self.teacher_school_b)
        
        # 两个 queryset 应该没有交集
        ids_a = set(queryset_a.values_list('id', flat=True))
        ids_b = set(queryset_b.values_list('id', flat=True))
        
        self.assertEqual(ids_a & ids_b, set())  # 交集应为空
    
    # ==================== 边界情况测试 ====================
    
    def test_user_without_school_attribute(self):
        """用户没有 school 属性时应作为独立教师处理"""
        # 创建一个没有 school 属性的用户（模拟）
        user = User.objects.create_user(
            username='no_school_attr',
            password='testpass123',
            real_name='无学校属性用户',
            role='head_teacher'
        )
        # 确保 school 为 None
        user.school = None
        user.save()
        
        queryset = self._make_request(user)
        
        # 应该返回空（因为这个用户不是任何班级的班主任）
        self.assertEqual(queryset.count(), 0)


class CustomFieldConfigTestCase(TestCase):
    """测试自定义字段配置"""
    
    @classmethod
    def setUpTestData(cls):
        cls.school = School.objects.create(name="测试学校", code="TEST_SCHOOL_001")
        cls.teacher = User.objects.create_user(
            username='test_teacher',
            password='testpass123',
            real_name='测试教师',
            role='head_teacher',
            school=cls.school
        )
    
    def test_custom_school_field_path(self):
        """测试自定义 school_field 路径"""
        # 这个测试验证 Mixin 可以正确使用自定义字段路径
        
        class CustomMockViewSet(SchoolScopedQuerysetMixin, viewsets.ModelViewSet):
            queryset = Student.objects.all()
            school_field = 'class_obj__school'  # 自定义路径
            head_teacher_field = 'class_obj__head_teacher'
        
        factory = APIRequestFactory()
        request = factory.get('/api/test/')
        request.user = self.teacher
        
        viewset = CustomMockViewSet()
        viewset.request = request
        viewset.format_kwarg = None
        
        # 不应抛出异常
        try:
            queryset = viewset.get_queryset()
            self.assertIsNotNone(queryset)
        except Exception as e:
            self.fail(f"自定义字段配置导致异常: {e}")
