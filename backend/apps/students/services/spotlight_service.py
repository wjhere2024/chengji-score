"""
学生之星智能聚焦服务
"""
import re
import random
from datetime import date, timedelta
from django.db.models import Count, Q, Max, F
from django.utils import timezone

from apps.students.models import Student, StudentRecord, StudentSpotlight, VacationSetting
from apps.teaching.models import StudentMastery, PoemLineMastery, DictationPaper

# 节假日检测库
try:
    import chinese_calendar
    HAS_CHINESE_CALENDAR = True
except ImportError:
    HAS_CHINESE_CALENDAR = False


class RecordParseService:
    """
    日常点评文本解析服务
    将自然语言文本解析为结构化的学生表现记录
    """
    
    # 正面词汇
    POSITIVE_KEYWORDS = [
        '好', '棒', '优秀', '出色', '流利', '认真', '积极', '主动', '进步',
        '帮助', '表扬', '表现好', '很好', '不错', '完成', '全对', '正确',
        '努力', '勤奋', '仔细', '细心', '整齐', '干净', '热情', '友善'
    ]
    
    # 负面词汇
    NEGATIVE_KEYWORDS = [
        '差', '错', '不好', '批评', '迟到', '缺交', '没完成', '马虎',
        '粗心', '不认真', '吵闹', '违纪', '打架', '欠交', '未完成'
    ]
    
    # 分类关键词映射
    CATEGORY_KEYWORDS = {
        'recite': ['背诵', '背书', '朗诵', '朗读'],
        'dictation': ['默写', '听写'],
        'reading': ['认读', '识字', '认字'],
        'discipline': ['纪律', '遵守', '违纪', '迟到', '早退', '课堂'],
        'labor': ['劳动', '打扫', '值日', '卫生', '整理'],
        'morality': ['帮助', '友善', '品德', '礼貌', '文明', '团结', '谦让'],
        'study': ['学习', '作业', '练习', '考试', '成绩', '进步'],
    }
    
    def parse_text(self, text, class_id=None):
        """
        解析文本，提取学生和表现描述
        支持：
        - "张三背诵流利" -> 张三: 背诵流利
        - "张迅和王浚择主动打扫卫生" -> 张迅: 主动打扫卫生, 王浚择: 主动打扫卫生
        返回: [{"student_id": 1, "student_name": "张三", "content": "背诵流利", "record_type": "positive", "category": "recite"}, ...]
        """
        # 获取学生列表用于匹配
        students_qs = Student.objects.filter(is_active=True)
        if class_id:
            students_qs = students_qs.filter(class_obj_id=class_id)
        
        students = list(students_qs.values('id', 'name', 'class_obj__name'))
        student_names = {s['name']: s for s in students}
        
        results = []
        
        # 按常见分隔符分割文本
        segments = re.split(r'[，,。.；;、\n]+', text)
        
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            
            # 在片段中查找所有学生姓名
            found_students = []
            for name, info in student_names.items():
                pos = segment.find(name)
                if pos != -1:
                    found_students.append((pos, name, info))
            
            if not found_students:
                continue
            
            # 按位置排序
            found_students.sort(key=lambda x: x[0])
            
            # 提取描述内容（姓名后面的部分）
            # 处理多学生情况：找到最后一个学生名后的内容作为共享描述
            last_student = found_students[-1]
            last_pos = last_student[0]
            last_name = last_student[1]
            
            # 移除连接词和所有学生姓名，提取纯描述
            content = segment[last_pos + len(last_name):].strip()
            
            # 清理描述开头的连接词
            content = re.sub(r'^(和|与|跟|同)+', '', content).strip()
            
            if not content:
                # 尝试从整个句子提取描述（可能姓名在中间）
                temp = segment
                for _, name, _ in found_students:
                    temp = temp.replace(name, '')
                # 移除连接词
                temp = re.sub(r'(和|与|跟|同)+', ' ', temp)
                content = temp.strip()
            
            if content:
                # 为每个识别到的学生创建记录
                for _, name, info in found_students:
                    results.append(self._build_record(info, content))
        
        return results
    
    def _build_record(self, student_info, content):
        """构建记录字典"""
        record_type = self._detect_type(content)
        category = self._detect_category(content)
        
        return {
            'student_id': student_info['id'],
            'student_name': student_info['name'],
            'class_name': student_info['class_obj__name'],
            'content': content,
            'record_type': record_type,
            'category': category
        }
    
    def _detect_type(self, content):
        """检测记录类型（正面/负面）"""
        for kw in self.NEGATIVE_KEYWORDS:
            if kw in content:
                return 'negative'
        for kw in self.POSITIVE_KEYWORDS:
            if kw in content:
                return 'positive'
        return 'neutral'
    
    def _detect_category(self, content):
        """检测分类"""
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for kw in keywords:
                if kw in content:
                    return category
        return 'other'


class SpotlightService:
    """
    学生之星智能选取服务
    """
    
    def get_today_spotlights(self, class_id, period='daily'):
        """获取今日之星列表"""
        today = date.today()
        
        if period == 'weekly':
            # 本周一开始
            start_date = today - timedelta(days=today.weekday())
        elif period == 'monthly':
            # 本月1日
            start_date = today.replace(day=1)
        else:
            start_date = today
        
        return StudentSpotlight.objects.filter(
            class_obj_id=class_id,
            period=period,
            spotlight_date=start_date
        ).select_related('student', 'class_obj')
    
    def generate_spotlights(self, class_id, period='daily', count=None, user=None):
        """
        智能生成之星
        算法：
        1. 公平性优先 - 优先选择很久没有获选的学生
        2. 表现加权 - 近期有突出表现的学生加分
        3. 随机因素 - 增加不确定性
        """
        today = date.today()
        
        # 确定生效日期
        if period == 'weekly':
            spotlight_date = today - timedelta(days=today.weekday())
        elif period == 'monthly':
            spotlight_date = today.replace(day=1)
        else:
            spotlight_date = today
        
        # 检查是否已存在
        existing = StudentSpotlight.objects.filter(
            class_obj_id=class_id,
            period=period,
            spotlight_date=spotlight_date
        )
        if existing.exists():
            return list(existing)
        
        # 获取班级学生
        students = list(Student.objects.filter(
            class_obj_id=class_id,
            is_active=True
        ))
        
        if not students:
            return []
        
        # 计算选取数量
        if count is None:
            count = max(1, len(students) // 5)  # 默认每天约1/5的学生
            count = min(count, 3)  # 最多3人
        
        # ===== 生日勋章逻辑 =====
        birthday_students = self._get_birthday_students(students, today)
        
        # 计算每个学生的分数（排除生日学生，他们直接入选）
        non_birthday_students = [s for s in students if s not in birthday_students]
        student_scores = []
        for student in non_birthday_students:
            score = self._calculate_student_score(student, period)
            student_scores.append((student, score))
        
        # 按分数排序，取前N名（保留名额给生日学生后的数量）
        student_scores.sort(key=lambda x: x[1], reverse=True)
        remaining_count = max(0, count - len(birthday_students))
        selected = [s[0] for s in student_scores[:remaining_count]]
        
        # 创建之星记录
        results = []
        
        # 先为生日学生创建记录（带生日勋章）
        for student in birthday_students:
            achievements = self._collect_achievements(student)
            # 在最前面插入生日勋章
            achievements.insert(0, {
                'type': 'birthday',
                'title': '🎂 生日勋章',
                'detail': f'祝{student.name}生日快乐！愿你在新的一岁更加优秀！'
            })
            spotlight = StudentSpotlight.objects.create(
                student=student,
                class_obj_id=class_id,
                period=period,
                spotlight_date=spotlight_date,
                source='auto',
                achievements=achievements,
                created_by=user
            )
            results.append(spotlight)
        
        # 再为普通选中的学生创建记录
        for student in selected:
            achievements = self._collect_achievements(student)
            spotlight = StudentSpotlight.objects.create(
                student=student,
                class_obj_id=class_id,
                period=period,
                spotlight_date=spotlight_date,
                source='auto',
                achievements=achievements,
                created_by=user
            )
            results.append(spotlight)
        
        return results
    
    def _get_birthday_students(self, students, check_date):
        """
        获取需要授予生日勋章的学生
        规则：
        1. 今天是生日的学生
        2. 如果生日在周末、法定节假日或寒暑假，提前到最近的工作日发放
        """
        birthday_students = []
        
        for student in students:
            if not student.birth_date:
                continue
            
            # 检查今天是否是生日
            if self._is_birthday_match(student.birth_date, check_date):
                birthday_students.append(student)
                continue
            
            # 检查未来一段时间内是否有生日需要提前发放
            # 寒暑假可能很长，检查范围更大
            max_look_ahead = 60 if self._is_in_vacation(check_date) else 7
            
            for days_ahead in range(1, max_look_ahead + 1):
                future_date = check_date + timedelta(days=days_ahead)
                if self._is_birthday_match(student.birth_date, future_date):
                    # 检查未来生日那天是否是非工作日
                    if self._is_non_working_day(future_date):
                        # 检查今天是否是发放的最佳时机（最后一个工作日）
                        if self._is_last_working_day_before(check_date, future_date):
                            birthday_students.append(student)
                    break
        
        return birthday_students
    
    def _is_birthday_match(self, birth_date, check_date):
        """检查某日期是否是某人的生日（忽略年份）"""
        return birth_date.month == check_date.month and birth_date.day == check_date.day
    
    def _is_non_working_day(self, check_date):
        """
        检查是否是非工作日
        包括：周末、法定节假日、寒暑假
        """
        # 使用 chinese-calendar 检测法定节假日
        if HAS_CHINESE_CALENDAR:
            try:
                if chinese_calendar.is_holiday(check_date):
                    return True
            except Exception:
                pass
        
        # 周末
        if check_date.weekday() >= 5:
            return True
        
        # 寒暑假
        if self._is_in_vacation(check_date):
            return True
        
        return False
    
    def _is_in_vacation(self, check_date, school=None):
        """
        检查是否在寒暑假期间
        优先使用管理员配置的假期表，否则使用自动计算
        """
        # 优先使用配置表
        if VacationSetting.is_in_vacation(check_date, school):
            return True
        
        # 如果没有配置，使用默认规则
        month = check_date.month
        year = check_date.year
        
        # 暑假（默认7-8月）
        if month in (7, 8):
            return True
        
        # 寒假（根据春节动态计算）
        if HAS_CHINESE_CALENDAR:
            try:
                # 获取当年或下一年的春节日期
                if month >= 9:
                    spring_festival = self._get_spring_festival(year + 1)
                else:
                    spring_festival = self._get_spring_festival(year)
                
                if spring_festival:
                    # 寒假范围：春节前14天 到 元宵节后7天
                    winter_vacation_start = spring_festival - timedelta(days=14)
                    winter_vacation_end = spring_festival + timedelta(days=22)
                    
                    if winter_vacation_start <= check_date <= winter_vacation_end:
                        return True
            except Exception:
                pass
        
        # 备用方案
        if month == 1 and check_date.day >= 10:
            return True
        if month == 2 and check_date.day <= 28:
            return True
        
        return False
    
    def _get_spring_festival(self, year):
        """获取指定年份的春节日期（正月初一）"""
        if not HAS_CHINESE_CALENDAR:
            return None
        
        try:
            # chinese-calendar 提供 get_holidays 可以获取节日
            # 春节通常是1月-2月间
            for month in (1, 2):
                for day in range(1, 29):
                    try:
                        d = date(year, month, day)
                        # 检查是否是春节（使用节日名称）
                        holiday_name = chinese_calendar.get_holiday_detail(d)
                        if holiday_name and '春节' in str(holiday_name):
                            return d
                    except Exception:
                        continue
        except Exception:
            pass
        
        return None
    
    def _is_last_working_day_before(self, check_date, target_date):
        """
        检查 check_date 是否是 target_date 之前的最后一个工作日
        """
        # 从 check_date 到 target_date 之间不应该有其他工作日
        current = check_date + timedelta(days=1)
        while current < target_date:
            if not self._is_non_working_day(current):
                return False  # 中间还有其他工作日
            current += timedelta(days=1)
        
        # check_date 本身必须是工作日
        return not self._is_non_working_day(check_date)
    
    def recommend_spotlight(self, student_id, reason, teacher_comment='', period='daily', user=None):
        """
        教师推荐之星
        """
        today = date.today()
        student = Student.objects.get(id=student_id)
        
        # 确定生效日期
        if period == 'weekly':
            spotlight_date = today - timedelta(days=today.weekday())
        elif period == 'monthly':
            spotlight_date = today.replace(day=1)
        else:
            spotlight_date = today
        
        # 检查是否已存在
        existing = StudentSpotlight.objects.filter(
            student=student,
            class_obj=student.class_obj,
            period=period,
            spotlight_date=spotlight_date
        ).first()
        
        if existing:
            # 更新现有记录
            existing.source = 'recommend'
            existing.recommend_reason = reason
            existing.teacher_comment = teacher_comment
            existing.save()
            return existing
        
        # 收集系统数据作为补充
        achievements = self._collect_achievements(student)
        
        # 添加推荐理由作为第一条亮点
        achievements.insert(0, {
            'type': 'recommend',
            'title': '教师推荐',
            'detail': reason
        })
        
        spotlight = StudentSpotlight.objects.create(
            student=student,
            class_obj=student.class_obj,
            period=period,
            spotlight_date=spotlight_date,
            source='recommend',
            recommend_reason=reason,
            teacher_comment=teacher_comment,
            achievements=achievements,
            created_by=user
        )
        
        return spotlight
    
    def _calculate_student_score(self, student, period):
        """
        计算学生的选取分数
        分数越高越优先被选中
        """
        score = 0
        today = date.today()
        
        # 1. 公平性分数 (40%) - 距离上次获选越久分数越高
        last_spotlight = StudentSpotlight.objects.filter(
            student=student,
            period=period
        ).order_by('-spotlight_date').first()
        
        if last_spotlight:
            days_since = (today - last_spotlight.spotlight_date).days
            fairness_score = min(days_since * 5, 100)  # 每天5分，最高100分
        else:
            fairness_score = 100  # 从未获选，最高分
        
        score += fairness_score * 0.4
        
        # 2. 表现分数 (40%) - 近期有正面记录
        if period == 'daily':
            record_days = 7
        elif period == 'weekly':
            record_days = 14
        else:
            record_days = 30
        
        recent_date = today - timedelta(days=record_days)
        
        # 日常点评正面记录
        positive_records = StudentRecord.objects.filter(
            student=student,
            record_type='positive',
            record_date__gte=recent_date
        ).count()
        
        # 默写/认读表现
        mastery_progress = StudentMastery.objects.filter(
            student=student,
            updated_at__gte=timezone.now() - timedelta(days=record_days),
            status=1  # 已掌握
        ).count()
        
        performance_score = min((positive_records * 10 + mastery_progress * 5), 100)
        score += performance_score * 0.4
        
        # 3. 随机分数 (20%)
        random_score = random.randint(0, 100)
        score += random_score * 0.2
        
        return score
    
    def _collect_achievements(self, student):
        """
        收集学生的亮点数据
        """
        achievements = []
        today = date.today()
        week_ago = today - timedelta(days=7)
        
        # 1. 日常点评中的正面记录
        recent_records = StudentRecord.objects.filter(
            student=student,
            record_type='positive',
            record_date__gte=week_ago
        ).order_by('-record_date')[:3]
        
        for record in recent_records:
            achievements.append({
                'type': record.category,
                'title': record.get_category_display(),
                'detail': record.content
            })
        
        # 2. 默写表现
        recent_mastered = StudentMastery.objects.filter(
            student=student,
            status=1,
            updated_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        if recent_mastered > 0:
            achievements.append({
                'type': 'dictation',
                'title': '默写达人',
                'detail': f'本周掌握{recent_mastered}个词语'
            })
        
        # 3. 认读表现
        read_mastered = StudentMastery.objects.filter(
            student=student,
            read_status=1,
            last_read_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        if read_mastered > 0:
            achievements.append({
                'type': 'reading',
                'title': '认读之星',
                'detail': f'本周认读正确{read_mastered}个词语'
            })
        
        # 4. 古诗背诵
        poem_mastered = PoemLineMastery.objects.filter(
            student=student,
            upper_to_lower_status=1,
            updated_at__gte=timezone.now() - timedelta(days=7)
        ).count()
        
        if poem_mastered > 0:
            achievements.append({
                'type': 'recite',
                'title': '背诵先锋',
                'detail': f'本周完成{poem_mastered}句古诗背诵'
            })
        
        # 如果没有收集到任何亮点，添加一条默认的
        if not achievements:
            achievements.append({
                'type': 'study',
                'title': '学习进步',
                'detail': '持续努力学习中'
            })
        
        return achievements
