from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.classes.models import Class
from apps.exams.models import Exam, ExamGradeSubject
from apps.schools.models import School
from apps.scores.models import Score
from apps.students.models import Student
from apps.subjects.models import Subject
from apps.users.models import User


DEMO_SCHOOL = {
    "code": "DEMO_CLASSICS",
    "name": "名著书院",
    "category": "primary",
    "province": "山东省",
    "city": "济宁市",
    "district": "梁山县",
    "address": "名著大道 108 号",
    "contact_phone": "0537-0000000",
    "is_active": True,
}

DEMO_SUBJECTS = [
    {"name": "语文", "code": "CHINESE", "order": 1, "grades": [1, 2, 3, 4, 5, 6]},
    {"name": "数学", "code": "MATH", "order": 2, "grades": [1, 2, 3, 4, 5, 6]},
    {"name": "英语", "code": "ENGLISH", "order": 3, "grades": [3, 4, 5, 6]},
    {"name": "科学", "code": "SCIENCE", "order": 4, "grades": [3, 4, 5, 6]},
    {"name": "道德与法治", "code": "ETHICS", "order": 5, "grades": [1, 2, 3, 4, 5, 6]},
]

DEMO_CLASSES = [
    {
        "grade": 1,
        "class_number": 1,
        "name": "红楼班",
        "teacher_username": "demo_honglou",
        "teacher_name": "贾夫子",
        "students": ["贾宝玉", "林黛玉", "薛宝钗", "史湘云", "王熙凤", "贾探春", "贾迎春", "贾惜春", "妙玉", "香菱", "晴雯", "袭人"],
    },
    {
        "grade": 2,
        "class_number": 1,
        "name": "西游班",
        "teacher_username": "demo_xiyou",
        "teacher_name": "唐夫子",
        "students": ["孙悟空", "猪八戒", "沙悟净", "唐三藏", "白龙马", "红孩儿", "铁扇公主", "牛魔王", "哪吒", "太白金星", "二郎神", "金角大王"],
    },
    {
        "grade": 3,
        "class_number": 1,
        "name": "水浒班",
        "teacher_username": "demo_shuihu",
        "teacher_name": "宋夫子",
        "students": ["宋江", "卢俊义", "吴用", "林冲", "武松", "鲁智深", "李逵", "杨志", "花荣", "燕青", "柴进", "扈三娘"],
    },
    {
        "grade": 4,
        "class_number": 1,
        "name": "三国班",
        "teacher_username": "demo_sanguo",
        "teacher_name": "诸葛夫子",
        "students": ["刘备", "关羽", "张飞", "诸葛亮", "赵云", "马超", "黄忠", "曹操", "孙权", "周瑜", "吕布", "貂蝉"],
    },
    {
        "grade": 5,
        "class_number": 1,
        "name": "诗经班",
        "teacher_username": "demo_shijing",
        "teacher_name": "卫夫子",
        "students": ["关雎", "蒹葭", "桃夭", "子衿", "鹿鸣", "采薇", "硕鼠", "伐檀", "氓", "伯兮", "静女", "无衣"],
    },
    {
        "grade": 6,
        "class_number": 1,
        "name": "山海班",
        "teacher_username": "demo_shanhai",
        "teacher_name": "应龙夫子",
        "students": ["精卫", "夸父", "应龙", "女娲", "后羿", "嫦娥", "共工", "祝融", "刑天", "鲲鹏", "白泽", "凤凰"],
    },
]

DEMO_EXAMS = [
    {
        "name": "春季学情诊断",
        "exam_type": Exam.ExamType.MONTHLY,
        "exam_date": date(2026, 3, 18),
        "academic_year": "2025-2026",
        "semester": "第二学期",
        "published": True,
        "description": "用于演示月度成绩录入和列表查询。",
    },
    {
        "name": "期中素养测评",
        "exam_type": Exam.ExamType.MIDTERM,
        "exam_date": date(2026, 4, 28),
        "academic_year": "2025-2026",
        "semester": "第二学期",
        "published": True,
        "description": "用于演示多班级、多科目成绩统计。",
    },
]


class Command(BaseCommand):
    help = "Create a fresh demo school with themed classes, students, exams, and scores"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing demo school data before recreating it",
        )

    def handle(self, *args, **options):
        with transaction.atomic():
            school = self.prepare_school(reset=options["reset"])
            subjects = self.prepare_subjects(school)
            admin = self.prepare_admin(school)
            classes = self.prepare_classes(school)
            self.prepare_students(classes)
            exams = self.prepare_exams(school, admin, subjects)
            self.prepare_scores(classes, exams, subjects, admin)

        self.stdout.write(self.style.SUCCESS("Demo data ready."))
        self.stdout.write("School code: DEMO_CLASSICS")
        self.stdout.write("Admin username: demo_admin")
        self.stdout.write("Admin password: demo123456")

    def prepare_school(self, reset=False):
        school = School.objects.filter(code=DEMO_SCHOOL["code"]).first()
        if school and reset:
            self.stdout.write("Resetting existing demo school data...")
            self.reset_demo_data(school)
            school = None

        if school is None:
            school = School.objects.create(**DEMO_SCHOOL)
            self.stdout.write(f"Created school: {school.name}")
        else:
            for field, value in DEMO_SCHOOL.items():
                setattr(school, field, value)
            school.save()
            self.stdout.write(f"Updated school: {school.name}")
        return school

    def reset_demo_data(self, school):
        Score.objects.filter(student__class_obj__school=school).delete()
        ExamGradeSubject.objects.filter(exam__school=school).delete()
        Exam.objects.filter(school=school).delete()
        Student.objects.filter(class_obj__school=school).delete()
        Class.objects.filter(school=school).delete()
        User.objects.filter(school=school, is_demo_account=True).delete()
        Subject.objects.filter(school=school).delete()
        school.delete()

    def prepare_subjects(self, school):
        subjects = {}
        for item in DEMO_SUBJECTS:
            subject, _ = Subject.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "description": f"{school.name}演示科目",
                    "school": school,
                    "applicable_grades": item["grades"],
                    "full_score": Decimal("100.0"),
                    "pass_score": Decimal("60.0"),
                    "excellent_score": Decimal("90.0"),
                    "order": item["order"],
                    "is_active": True,
                },
            )
            subjects[subject.code] = subject
        self.stdout.write(f"Prepared {len(subjects)} subjects.")
        return subjects

    def prepare_admin(self, school):
        admin, _ = User.objects.get_or_create(
            username="demo_admin",
            defaults={
                "real_name": "演示管理员",
                "school": school,
                "role": User.Role.ADMIN,
                "roles": [User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.SUBJECT_TEACHER],
                "current_role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
                "is_demo_account": True,
            },
        )
        admin.real_name = "演示管理员"
        admin.school = school
        admin.role = User.Role.ADMIN
        admin.roles = [User.Role.ADMIN, User.Role.HEAD_TEACHER, User.Role.SUBJECT_TEACHER]
        admin.current_role = User.Role.ADMIN
        admin.is_staff = True
        admin.is_superuser = True
        admin.is_demo_account = True
        admin.set_password("demo123456")
        admin.save()
        self.stdout.write("Prepared demo admin.")
        return admin

    def prepare_classes(self, school):
        classes = []
        for item in DEMO_CLASSES:
            teacher = self.prepare_teacher(school, item["teacher_username"], item["teacher_name"])
            class_obj, _ = Class.objects.update_or_create(
                school=school,
                grade=item["grade"],
                class_number=item["class_number"],
                defaults={
                    "name": item["name"],
                    "head_teacher": teacher,
                    "classroom": f"{item['grade']}号教学楼 {item['class_number']}0{item['grade']} 教室",
                    "description": f"{school.name}{item['name']}演示班级",
                    "is_active": True,
                },
            )
            classes.append((class_obj, item["students"]))
        self.stdout.write(f"Prepared {len(classes)} classes.")
        return classes

    def prepare_teacher(self, school, username, real_name):
        teacher, _ = User.objects.get_or_create(
            username=username,
            defaults={
                "real_name": real_name,
                "school": school,
                "role": User.Role.HEAD_TEACHER,
                "roles": [User.Role.HEAD_TEACHER, User.Role.SUBJECT_TEACHER],
                "current_role": User.Role.HEAD_TEACHER,
                "is_staff": True,
                "is_demo_account": True,
            },
        )
        teacher.real_name = real_name
        teacher.school = school
        teacher.role = User.Role.HEAD_TEACHER
        teacher.roles = [User.Role.HEAD_TEACHER, User.Role.SUBJECT_TEACHER]
        teacher.current_role = User.Role.HEAD_TEACHER
        teacher.is_staff = True
        teacher.is_demo_account = True
        teacher.set_password("demo123456")
        teacher.save()
        return teacher

    def prepare_students(self, classes):
        total = 0
        for class_obj, student_names in classes:
            for index, name in enumerate(student_names, start=1):
                student_id = f"25{class_obj.grade:02d}{class_obj.class_number:02d}{index:02d}"
                gender = Student.Gender.FEMALE if index % 2 == 0 else Student.Gender.MALE
                Student.objects.update_or_create(
                    student_id=student_id,
                    defaults={
                        "name": name,
                        "class_obj": class_obj,
                        "gender": gender,
                        "admission_year": 2025 - class_obj.grade + 1,
                        "is_active": True,
                        "notes": f"{class_obj.name}演示学生",
                    },
                )
                total += 1
            class_obj.update_student_count()
        self.stdout.write(f"Prepared {total} students.")

    def prepare_exams(self, school, admin, subjects):
        exams = []
        for item in DEMO_EXAMS:
            exam, _ = Exam.objects.update_or_create(
                school=school,
                name=item["name"],
                defaults={
                    "exam_type": item["exam_type"],
                    "academic_year": item["academic_year"],
                    "semester": item["semester"],
                    "exam_date": item["exam_date"],
                    "description": item["description"],
                    "is_published": item["published"],
                    "is_active": True,
                    "created_by": admin,
                    "applicable_grades": [1, 2, 3, 4, 5, 6],
                },
            )
            exam.subjects.set(subjects.values())
            ExamGradeSubject.objects.filter(exam=exam).delete()
            for grade in range(1, 7):
                for subject in self.get_grade_subjects(grade, subjects):
                    ExamGradeSubject.objects.get_or_create(exam=exam, grade=grade, subject=subject)
            exams.append(exam)
        self.stdout.write(f"Prepared {len(exams)} exams.")
        return exams

    def prepare_scores(self, classes, exams, subjects, admin):
        total = 0
        for exam_index, exam in enumerate(exams, start=1):
            for class_obj, _ in classes:
                class_students = list(class_obj.students.order_by("student_id"))
                for student in class_students:
                    grade_subjects = self.get_grade_subjects(class_obj.grade, subjects)
                    for subject in grade_subjects:
                        value = self.build_score(student.name, subject.name, class_obj.grade, exam_index)
                        Score.objects.update_or_create(
                            student=student,
                            exam=exam,
                            subject=subject,
                            defaults={
                                "score": value,
                                "created_by": admin,
                                "notes": f"{exam.name}演示成绩",
                            },
                        )
                        total += 1
        self.stdout.write(f"Prepared {total} scores.")

    def get_grade_subjects(self, grade, subjects):
        codes = ["CHINESE", "MATH", "ETHICS"]
        if grade >= 3:
            codes.extend(["ENGLISH", "SCIENCE"])
        return [subjects[code] for code in codes]

    def build_score(self, student_name, subject_name, grade, exam_index):
        seed = sum(ord(char) for char in f"{student_name}{subject_name}{grade}{exam_index}")
        base = 68 + (seed % 25)
        if subject_name == "语文":
            base += 4
        elif subject_name == "数学":
            base += 2
        elif subject_name == "英语":
            base += 1
        value = min(base, 98)
        return Decimal(f"{value}.0")
