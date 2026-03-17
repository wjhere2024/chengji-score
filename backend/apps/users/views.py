"""
用户视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from django.utils import timezone
from django.db.models import Q
import random
import string
import datetime
import re
from django.conf import settings
from django.core.mail import send_mail
import logging
from apps.schools.models import School

logger = logging.getLogger(__name__)
from .models import User, OperationLog, LoginQRCode, RemoteDevice, EmailVerification, WechatVerification, TeacherSchoolMembership, SchoolJoinRequest
from .serializers import (
    UserSerializer, UserCreateSerializer, UserUpdateSerializer,
    PasswordChangeSerializer, OperationLogSerializer, LoginQRCodeSerializer,
    RemoteDeviceSerializer
)
from .permissions import IsAdmin, IsSuperAdmin
from rest_framework_simplejwt.tokens import RefreshToken
import uuid


class UserViewSet(viewsets.ModelViewSet):
    """
    用户视图集
    提供用户的CRUD操作
    """
    queryset = User.objects.all()
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['username', 'real_name', 'employee_id', 'phone']
    ordering_fields = ['created_at', 'username']

    def get_serializer_class(self):
        """根据操作返回不同的序列化器"""
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        """创建用户时自动关联学校"""
        user = self.request.user
        if hasattr(user, 'school') and user.school:
            serializer.save(school=user.school)
        else:
            serializer.save()

    def get_queryset(self):
        """根据用户角色过滤数据"""
        user = self.request.user
        queryset = super().get_queryset()

        # 1. 基础过滤：只显示本学校的用户
        if hasattr(user, 'school') and user.school:
            queryset = queryset.filter(school=user.school)
            
        return queryset

    def get_permissions(self):
        """
        根据操作返回不同的权限
        - 增删改：需要超级管理员权限
        - 查看：普通管理员和超级管理员都可以
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsSuperAdmin()]
        elif self.action == 'list' or self.action == 'retrieve':
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def me(self, request):
        """获取当前用户信息"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """修改密码"""
        user = request.user

        # 演示账号不能修改密码
        if user.is_demo_account:
            return Response(
                {'error': '演示账号不能修改密码'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({'message': '密码修改成功'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        """重置用户密码（超级管理员操作）"""
        if not request.user.is_super_admin:
            return Response(
                {'error': '只有超级管理员可以重置密码'},
                status=status.HTTP_403_FORBIDDEN
            )

        user = self.get_object()

        # 演示账号不能重置密码
        if user.is_demo_account:
            return Response(
                {'error': '演示账号不能重置密码'},
                status=status.HTTP_403_FORBIDDEN
            )

        new_password = request.data.get('new_password', '123456')
        user.set_password(new_password)
        user.save()

        return Response({'message': f'密码已重置为：{new_password}'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def switch_role(self, request):
        """切换当前用户的激活角色"""
        role = request.data.get('role')

        if not role:
            return Response(
                {'error': '请提供要切换的角色'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = request.user

        # 检查用户是否拥有该角色
        if not user.has_role(role):
            return Response(
                {'error': '您没有该角色权限'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 切换角色
        success = user.switch_role(role)

        if success:
            # 返回更新后的用户信息
            serializer = self.get_serializer(user)
            return Response({
                'message': '角色切换成功',
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {'error': '角色切换失败'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get', 'post'])
    def dashboard_cards(self, request):
        """获取或保存当前用户的桌面卡片配置"""
        user = request.user
        role = user.get_active_role()

        if request.method == 'GET':
            cards = user.dashboard_cards.get(role) if user.dashboard_cards else None
            return Response({'role': role, 'cards': cards})

        # POST: 保存卡片列表
        card_ids = request.data.get('cards', [])
        if not isinstance(card_ids, list):
            return Response(
                {'error': 'cards must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not user.dashboard_cards:
            user.dashboard_cards = {}
        user.dashboard_cards[role] = card_ids
        user.save(update_fields=['dashboard_cards'])
        return Response({'role': role, 'cards': card_ids})


class OperationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    操作日志视图集
    只提供查看功能，不允许修改或删除
    """
    queryset = OperationLog.objects.all()
    serializer_class = OperationLogSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['user', 'action', 'target_model']
    search_fields = ['description', 'user__real_name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    ordering = ['-created_at']


class AuthViewSet(viewsets.ViewSet):
    """
    认证相关视图
    处理扫码登录等
    """
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def qrcode_generate(self, request):
        """生成登录二维码"""
        # 清理过期二维码(可选，为了简单先Skip或简单清理)
        # generated_token
        token = uuid.uuid4()
        qr_code = LoginQRCode.objects.create(token=token)
        return Response({'token': str(token)})

    @action(detail=False, methods=['get'])
    def qrcode_status(self, request):
        """检查二维码状态"""
        token = request.query_params.get('token')
        if not token:
            return Response({'error': 'Missing token'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            qr_code = LoginQRCode.objects.get(token=token)
            
            if qr_code.status == 'confirmed' and qr_code.user:
                # 登录成功，颁发Token
                refresh = RefreshToken.for_user(qr_code.user)
                return Response({
                    'status': 'confirmed',
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(qr_code.user).data
                })
            
            return Response({'status': qr_code.status})
            
        except LoginQRCode.DoesNotExist:
            return Response({'status': 'invalid'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def qrcode_confirm(self, request):
        """确认登录（移动端调用）"""
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Missing token'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            qr_code = LoginQRCode.objects.get(token=token)
            if qr_code.status != 'waiting':
                 return Response({'error': '二维码已失效或已使用'}, status=status.HTTP_400_BAD_REQUEST)
            
            qr_code.status = 'confirmed'
            qr_code.user = request.user
            qr_code.save()
            return Response({'message': '登录确认成功'})
            
        except LoginQRCode.DoesNotExist:
            return Response({'error': '二维码不存在'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny])
    def magic_login_token(self, request):
        """Magic Link 换取登录 Token"""
        token = request.data.get('token')
        if not token:
            return Response({'error': 'Missing token'}, status=status.HTTP_400_BAD_REQUEST)
            
        from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
        from django.conf import settings
        signer = TimestampSigner()
        
        try:
            # 验证签名 (有效期 1 小时)
            user_id = signer.unsign(token, max_age=3600)
            user = User.objects.get(id=user_id)
            
            # 颁发 Token
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            })
            
        except (BadSignature, SignatureExpired):
            return Response({'error': '链接已失效或不合法'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': '用户不存在'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def device_heartbeat(self, request):
        """设备心跳（上报属性及获取待登录Token）"""
        device_id = request.data.get('device_id')
        media_server_url = request.data.get('media_server_url')
        file_server_url = request.data.get('file_server_url')
        
        if not device_id:
            return Response({'error': 'Missing device_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            device = RemoteDevice.objects.get(device_id=device_id)
            
            # 更新心跳和可选的服务URL
            device.last_heartbeat = timezone.now()
            if media_server_url is not None:
                device.media_server_url = media_server_url
            if file_server_url is not None:
                device.file_server_url = file_server_url
            device.save()
            
            # 返回锁定状态，方便前端同步
            resp_data = {
                'status': 'ok',
                'is_locked': device.is_locked
            }
            
            if device.pending_token:
                # Consume token
                token_str = device.pending_token
                device.pending_token = None
                device.save()
                
                # Assume token is a temporary one or render it to JWT here?
                # Actually, push_login should generate a short-lived code or we handle it here.
                # Let's say push_login generates a temporary code, and we verify it?
                # Simplify: push_login saves a UUID. We trust it.
                # But we need to know WHO pushes it.
                # We need to store (token, user_id) in pending_token?
                # Current schema: pending_token is charfield.
                # Let's assume pending_token is just a flag or trigger.
                # Wait, if I just wake up the PC, how does it know which user?
                # The RemoteDevice is bound to ONE user.
                
                refresh = RefreshToken.for_user(device.user)
                resp_data.update({
                    'action': 'login',
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserSerializer(device.user).data
                })
            
            return Response(resp_data)
            
        except RemoteDevice.DoesNotExist:
            return Response({'status': 'unbound'})

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def device_bind(self, request):
        """绑定设备"""
        device_id = request.data.get('device_id')
        name = request.data.get('name')
        
        if not device_id or not name:
            return Response({'error': 'Missing params'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Check if already bound
        if RemoteDevice.objects.filter(device_id=device_id).exists():
            return Response({'error': '该设备已被绑定'}, status=status.HTTP_400_BAD_REQUEST)
            
        device = RemoteDevice.objects.create(
            user=request.user,
            device_id=device_id,
            name=name,
            media_server_url=request.data.get('media_server_url'),
            file_server_url=request.data.get('file_server_url')
        )
        return Response({
            'message': '绑定成功',
            'id': device.id
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def get_bind_code(self, request):
        """生成微信绑定口令码"""
        user = request.user
        # 如果已经绑定且没有明确要求重新绑定，可以提示
        # if user.wechat_openid:
        #    return Response({'error': '账号已绑定微信'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 清理旧的未验证绑定记录
        WechatVerification.objects.filter(user=user, type='bind', is_verified=False).delete()
        
        # 生成 6 位随机口令
        code = ''.join(random.choices(string.digits, k=6))
        
        # 创建记录，有效期 10 分钟
        WechatVerification.objects.create(
            user=user,
            code=code,
            type='bind',
            expires_at=timezone.now() + datetime.timedelta(minutes=10)
        )
        
        return Response({
            'code': code,
            'expires_in': 600,
            'message': f'请在公众号发送“绑定 {code}”完成关联'
        })

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def unbind_wechat(self, request):
        """解绑微信"""
        user = request.user
        user.wechat_openid = None
        user.save()
        return Response({'message': '解绑成功'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def device_list(self, request):
        """获取我的设备列表"""
        devices = RemoteDevice.objects.filter(user=request.user)
        serializer = RemoteDeviceSerializer(devices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def media_server_list(self, request):
        """获取全校范围内在线的媒体/文件服务器"""
        from django.utils import timezone
        import datetime
        now = timezone.now()
        thirty_seconds_ago = now - datetime.timedelta(seconds=30)
        
        # 1. 基础过滤：同校且在线
        queryset = RemoteDevice.objects.filter(
            user__school=request.user.school,
            last_heartbeat__gte=thirty_seconds_ago
        ).select_related('user')
        
        # 2. 排除掉两个 URL 都为空或为 null 的设备
        queryset = queryset.exclude(
            Q(media_server_url__isnull=True) | Q(media_server_url=''),
            Q(file_server_url__isnull=True) | Q(file_server_url='')
        )
        
        serializer = RemoteDeviceSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def device_push_login(self, request):
        """推送到设备登录"""
        device_id = request.data.get('device_id')
        try:
            device = RemoteDevice.objects.get(device_id=device_id, user=request.user)
            device.pending_token = "LOGIN_REQUEST" # We just need a signal because user is fixed
            device.save()
            return Response({'message': '推送成功'})
        except RemoteDevice.DoesNotExist:
            return Response({'error': '设备不存在或未归属您'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def agent_heartbeat(self, request):
        """桌面助手心跳"""
        device_id = request.data.get('device_id')
        if not device_id:
            return Response({'error': 'Missing device_id'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            device = RemoteDevice.objects.get(device_id=device_id)
            device.last_agent_heartbeat = timezone.now()
            
            cmd = None
            if device.pending_command:
                cmd = device.pending_command
                device.pending_command = None
                
            device.save()
            
            return Response({'command': cmd, 'status': 'ok'})
            
        except RemoteDevice.DoesNotExist:
            return Response({'status': 'unbound', 'error': 'Device not bound'})

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def device_send_command(self, request):
        """发送指令给助手"""
        device_id = request.data.get('device_id')
        command = request.data.get('command') # e.g. 'OPEN_BROWSER'
        
        if not command:
            return Response({'error': 'Missing command'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            device = RemoteDevice.objects.get(device_id=device_id, user=request.user)
            device.pending_command = command
            device.save()
            return Response({'message': '指令发送成功'})
        except RemoteDevice.DoesNotExist:
            return Response({'error': '设备不存在'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def device_lock(self, request):
        """锁定/解锁设备"""
        device_id = request.data.get('device_id')
        lock = request.data.get('lock', True)
        
        try:
            device = RemoteDevice.objects.get(device_id=device_id, user=request.user)
            device.is_locked = lock
            device.save()
            return Response({'message': '操作成功', 'is_locked': device.is_locked})
        except RemoteDevice.DoesNotExist:
            return Response({'error': '设备不存在或未归属您'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def device_send_audio(self, request):
        """发送语音到设备播放"""
        device_id = request.data.get('device_id')
        audio_file = request.files.get('audio')
        
        if not device_id or not audio_file:
            return Response({'error': 'Missing params'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            device = RemoteDevice.objects.get(device_id=device_id, user=request.user)
            
            # Save audio file
            import os
            from django.conf import settings
            
            # Determine extension
            ext = '.webm'
            if audio_file.name.endswith('.mp3'):
                ext = '.mp3'
            elif audio_file.name.endswith('.wav'):
                ext = '.wav'
                
            filename = f"broadcast_{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(settings.MEDIA_ROOT, 'broadcasts', filename)
            
            # Ensure dir exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb+') as destination:
                for chunk in audio_file.chunks():
                    destination.write(chunk)
            
            # Construct URL
            audio_url = f"{settings.MEDIA_URL}broadcasts/{filename}"
            # Full URL might be needed if frontend is on different domain, 
            # but relative URL usually works if proxy is set up. 
            # If not, client needs to prepend host. Let's send relative.
            
            # Set Command
            device.pending_command = f"PLAY_AUDIO {audio_url}"
            device.save()
            
            return Response({'message': '语音发送成功', 'url': audio_url})
            
        except RemoteDevice.DoesNotExist:
            return Response({'error': '设备不存在或未归属您'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'])
    def send_email_code(self, request):
        """发送邮箱验证码"""
        email = request.data.get('email')
        type = request.data.get('type', 'register')
        
        if not email:
            return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        # 简单校验邮箱格式
        if '@' not in email:
             return Response({'error': 'Invalid email format'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查频率（1分钟内只能发一次）
        last_code = EmailVerification.objects.filter(email=email, type=type).first()
        if last_code and (timezone.now() - last_code.created_at).seconds < 60:
             return Response({'error': '请求过于频繁，请稍后再试'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # 生成验证码
        code = ''.join(random.choices(string.digits, k=6))
        
        # 保存验证码
        EmailVerification.objects.create(
            email=email,
            code=code,
            type=type,
            expires_at=timezone.now() + datetime.timedelta(minutes=5)
        )
        
        # 开发环境也打印一份，方便调试
        if settings.DEBUG:
            print(f"============== EMAIL CODE FOR {email} ==============", flush=True)
            print(f"Code: {code}", flush=True)
            print(f"====================================================", flush=True)
            import sys
            sys.stdout.flush()
    
        # 发送邮件
        try:
            subject = '【成绩管理系统】您的验证码'
            message = f'您的验证码是：{code}，有效期5分钟。请勿将验证码泄露给他人。'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            
            send_mail(subject, message, from_email, recipient_list)
            logger.info(f"Verification code sent to {email}")
            return Response({'message': '验证码已发送'})
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {str(e)}")
            # 如果是开发环境且配置了ConsoleBackend，send_mail应该不会抛出严重异常，但如果是SMTP配置错误则会
            # 即使发送失败，如果是生产环境，最好不要把具体错误返回给前端，但为了调试方便，开发环境可以返回
            error_msg = str(e) if settings.DEBUG else '发送邮件失败，请检查邮箱地址或稍后重试'
            return Response({'error': error_msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def send_wechat_code(self, request):
        """请求微信公众号验证码（创建待验证记录）"""
        phone = request.data.get('phone')
        type = request.data.get('type', 'register')

        if not phone:
            return Response({'error': '请输入手机号'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证手机号格式
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return Response({'error': '手机号格式不正确'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查频率（1分钟内只能发一次）
        last_record = WechatVerification.objects.filter(phone=phone, type=type).order_by('-created_at').first()
        if last_record and (timezone.now() - last_record.created_at).seconds < 60:
            return Response({'error': '请求过于频繁，请稍后再试'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        # 创建待验证记录（此时没有验证码，等用户在公众号发消息后才生成）
        WechatVerification.objects.create(
            phone=phone,
            type=type,
            expires_at=timezone.now() + datetime.timedelta(minutes=5)
        )

        logger.info(f"Created wechat verification request for phone {phone}")

        return Response({
            'message': '请在微信公众号中发送您的手机号获取验证码',
            'phone': phone
        })

    @action(detail=False, methods=['post'])
    def register(self, request):
        """注册新学校和管理员（支持邮箱或手机号验证）"""
        email = request.data.get('email')
        phone = request.data.get('phone')
        code = request.data.get('code')
        password = request.data.get('password')
        school_name = request.data.get('school_name')
        real_name = request.data.get('real_name', '管理员')
        verify_type = request.data.get('verify_type', 'email')  # 'email' 或 'wechat'

        # 基本验证
        if not all([code, password, school_name]):
            return Response({'error': '请填写完整信息'}, status=status.HTTP_400_BAD_REQUEST)

        verification = None
        username = None

        if verify_type == 'wechat' and phone:
            # 微信公众号验证
            if not re.match(r'^1[3-9]\d{9}$', phone):
                return Response({'error': '手机号格式不正确'}, status=status.HTTP_400_BAD_REQUEST)

            verification = WechatVerification.objects.filter(
                phone=phone,
                code=code,
                type='register',
                is_verified=False,
                expires_at__gt=timezone.now()
            ).first()

            if not verification:
                return Response({'error': '验证码无效或已过期'}, status=status.HTTP_400_BAD_REQUEST)

            # 检查手机号是否已注册
            if User.objects.filter(phone=phone).exists():
                return Response({'error': '该手机号已被注册'}, status=status.HTTP_400_BAD_REQUEST)

            username = phone

        elif email:
            # 邮箱验证（原有逻辑）
            verification = EmailVerification.objects.filter(
                email=email,
                code=code,
                type='register',
                is_verified=False,
                expires_at__gt=timezone.now()
            ).first()

            if not verification:
                return Response({'error': '验证码无效或已过期'}, status=status.HTTP_400_BAD_REQUEST)

            # 验证邮箱是否已注册
            if User.objects.filter(username=email).exists():
                return Response({'error': '该邮箱已被注册'}, status=status.HTTP_400_BAD_REQUEST)

            username = email

        else:
            return Response({'error': '请提供邮箱或手机号'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. 创建学校
            school_code = 'SCH' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            school = School.objects.create(
                name=school_name,
                code=school_code
            )

            # 2. 创建用户
            user = User.objects.create_user(
                username=username,
                email=email or '',
                phone=phone or '',
                password=password,
                real_name=real_name,
                school=school,
                role=User.Role.SUPER_ADMIN,
                roles=[User.Role.SUPER_ADMIN],
                current_role=User.Role.SUPER_ADMIN
            )

            # 3. 标记验证码已使用
            verification.is_verified = True
            verification.save()

            # 4. 自动登录
            refresh = RefreshToken.for_user(user)

            return Response({
                'message': '注册成功',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'注册失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def register_teacher(self, request):
        """注册新教师（支持邮箱或手机号验证，自动加入慧校园平台）"""
        email = request.data.get('email')
        phone = request.data.get('phone')
        code = request.data.get('code')
        password = request.data.get('password')
        school_code = request.data.get('school_code')  # 可选，用于加入特定学校
        real_name = request.data.get('real_name')
        verify_type = request.data.get('verify_type', 'email')  # 'email' 或 'wechat'

        # 默认学校配置
        DEFAULT_SCHOOL_CODE = 'HUIXIAOYUAN'
        DEFAULT_SCHOOL_NAME = '慧校园平台'

        # 获取学校
        school = None
        if school_code:
            try:
                school = School.objects.get(code=school_code)
            except School.DoesNotExist:
                return Response({'error': '学校代码无效，请核对'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            school, created = School.objects.get_or_create(
                code=DEFAULT_SCHOOL_CODE,
                defaults={
                    'name': DEFAULT_SCHOOL_NAME,
                    'category': 'primary',
                    'is_active': True
                }
            )

        verification = None
        username = None

        if verify_type == 'wechat' and phone:
            # 微信公众号验证
            if not re.match(r'^1[3-9]\d{9}$', phone):
                return Response({'error': '手机号格式不正确'}, status=status.HTTP_400_BAD_REQUEST)

            verification = WechatVerification.objects.filter(
                phone=phone,
                code=code,
                type='register',
                is_verified=False,
                expires_at__gt=timezone.now()
            ).first()

            if not verification:
                return Response({'error': '验证码无效或已过期'}, status=status.HTTP_400_BAD_REQUEST)

            if User.objects.filter(phone=phone).exists():
                return Response({'error': '该手机号已被注册'}, status=status.HTTP_400_BAD_REQUEST)

            username = phone

        elif email:
            # 邮箱验证
            verification = EmailVerification.objects.filter(
                email=email,
                code=code,
                type='register',
                is_verified=False,
                expires_at__gt=timezone.now()
            ).first()

            if not verification:
                return Response({'error': '验证码无效或已过期'}, status=status.HTTP_400_BAD_REQUEST)

            if User.objects.filter(username=email).exists():
                return Response({'error': '该邮箱已被注册'}, status=status.HTTP_400_BAD_REQUEST)

            username = email

        else:
            return Response({'error': '请提供邮箱或手机号'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.create_user(
                username=username,
                email=email or '',
                phone=phone or '',
                password=password,
                real_name=real_name,
                school=school,
                role=User.Role.HEAD_TEACHER,
                roles=[User.Role.HEAD_TEACHER],
                current_role=User.Role.HEAD_TEACHER
            )

            # 自动创建会员关系
            TeacherSchoolMembership.objects.create(
                teacher=user,
                school=school,
                is_active=True
            )

            verification.is_verified = True
            verification.save()

            refresh = RefreshToken.for_user(user)

            return Response({
                'message': '注册成功',
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'注册失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def verify_student_invite_code(self, request):
        """验证学生邀请码，返回班级信息和未绑定的学生列表"""
        from apps.classes.models import Class
        from apps.students.models import Student

        invite_code = request.data.get('invite_code', '').strip()
        if not invite_code:
            return Response({'error': '请输入邀请码'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            cls = Class.objects.select_related('school').get(
                student_invite_code=invite_code, is_active=True
            )
        except Class.DoesNotExist:
            return Response({'error': '邀请码无效'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取未绑定账号的学生
        students = Student.objects.filter(
            class_obj=cls, user__isnull=True, is_active=True
        ).order_by('student_id').values('id', 'name', 'student_id')

        return Response({
            'class_name': str(cls),
            'school_name': cls.school.name if cls.school else '',
            'grade': cls.get_grade_display(),
            'students': list(students),
        })

    @action(detail=False, methods=['post'], permission_classes=[AllowAny], authentication_classes=[])
    def bind_student_account(self, request):
        """学生选择姓名并设置密码，完成账号绑定"""
        from apps.classes.models import Class
        from apps.students.models import Student

        invite_code = request.data.get('invite_code', '').strip()
        student_id = request.data.get('student_id')
        password = request.data.get('password', '')

        if not all([invite_code, student_id, password]):
            return Response({'error': '请填写完整信息'}, status=status.HTTP_400_BAD_REQUEST)

        if len(password) < 6:
            return Response({'error': '密码长度不能少于6位'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证邀请码
        try:
            cls = Class.objects.select_related('school').get(
                student_invite_code=invite_code, is_active=True
            )
        except Class.DoesNotExist:
            return Response({'error': '邀请码无效'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证学生
        try:
            student = Student.objects.get(id=student_id, class_obj=cls, is_active=True)
        except Student.DoesNotExist:
            return Response({'error': '学生不存在'}, status=status.HTTP_400_BAD_REQUEST)

        if student.user is not None:
            return Response({'error': '该学生已绑定账号'}, status=status.HTTP_400_BAD_REQUEST)

        # 生成用户名：优先学号，重复时加姓名拼音首字母前缀
        username = student.student_id
        if User.objects.filter(username=username).exists():
            from pypinyin import pinyin, Style
            initials = ''.join(
                p[0][0] for p in pinyin(student.name, style=Style.FIRST_LETTER) if p[0]
            ).lower()
            username = f"{initials}{student.student_id}"
            # 极端情况仍重复，追加数字
            base_username = username
            counter = 2
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                real_name=student.name,
                school=cls.school,
                role=User.Role.STUDENT,
                roles=[User.Role.STUDENT],
                current_role=User.Role.STUDENT,
            )
            student.user = user
            student.save(update_fields=['user'])

            refresh = RefreshToken.for_user(user)
            return Response({
                'message': '绑定成功',
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'real_name': user.real_name,
                    'role': user.role,
                },
                'student': {
                    'id': student.id,
                    'name': student.name,
                    'class_name': str(cls),
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': f'绑定失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def reset_student_password(self, request):
        """教师重置学生密码"""
        from apps.students.models import Student

        student_id = request.data.get('student_id')
        new_password = request.data.get('new_password', '123456')

        if not student_id:
            return Response({'error': '请指定学生'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            student = Student.objects.select_related('user', 'class_obj').get(id=student_id)
        except Student.DoesNotExist:
            return Response({'error': '学生不存在'}, status=status.HTTP_404_NOT_FOUND)

        if not student.user:
            return Response({'error': '该学生尚未绑定账号'}, status=status.HTTP_400_BAD_REQUEST)

        # 权限检查：管理员、该班班主任、该班任课教师
        user = request.user
        if not user.is_admin:
            is_head_teacher = hasattr(student.class_obj, 'head_teacher') and student.class_obj.head_teacher == user
            is_subject_teacher = student.class_obj.teaching_assignments.filter(teacher=user).exists()
            if not is_head_teacher and not is_subject_teacher:
                return Response({'error': '无权操作该学生'}, status=status.HTTP_403_FORBIDDEN)

        student.user.set_password(new_password)
        student.user.save(update_fields=['password'])

        return Response({
            'message': f'已重置 {student.name} 的密码',
            'username': student.user.username
        })

    @action(detail=False, methods=['post'])
    def reset_password_by_phone(self, request):
        """通过手机号重置密码（微信公众号验证）"""
        phone = request.data.get('phone')
        code = request.data.get('code')
        new_password = request.data.get('new_password')

        # 基本验证
        if not all([phone, code, new_password]):
            return Response({'error': '请填写完整信息'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证手机号格式
        if not re.match(r'^1[3-9]\d{9}$', phone):
            return Response({'error': '手机号格式不正确'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证密码长度
        if len(new_password) < 6:
            return Response({'error': '密码长度不能少于6位'}, status=status.HTTP_400_BAD_REQUEST)

        # 查找用户
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            return Response({'error': '该手机号未注册'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证验证码
        verification = WechatVerification.objects.filter(
            phone=phone,
            code=code,
            type='reset_password',
            is_verified=False,
            expires_at__gt=timezone.now()
        ).first()

        if not verification:
            return Response({'error': '验证码无效或已过期'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 重置密码
            user.set_password(new_password)
            user.save()

            # 标记验证码已使用
            verification.is_verified = True
            verification.save()

            logger.info(f"Password reset successful for phone {phone}")

            return Response({'message': '密码重置成功，请使用新密码登录'}, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Password reset failed for phone {phone}: {str(e)}")
            return Response({'error': f'密码重置失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ==================== 多学校会员相关接口 ====================

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def lookup_school(self, request):
        """根据学校代码查询学校信息"""
        code = request.query_params.get('code')
        if not code:
            return Response({'error': '请输入学校代码'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            school = School.objects.get(code=code, is_active=True)
            return Response({
                'id': school.id,
                'name': school.name,
                'code': school.code,
                'category': school.get_category_display()
            })
        except School.DoesNotExist:
            return Response({'error': '学校代码无效'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def apply_join_school(self, request):
        """申请加入学校"""
        school_code = request.data.get('school_code')
        migrate_classes = request.data.get('migrate_classes', False)
        migrate_students = request.data.get('migrate_students', False)

        if not school_code:
            return Response({'error': '请输入学校代码'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证学校
        try:
            school = School.objects.get(code=school_code, is_active=True)
        except School.DoesNotExist:
            return Response({'error': '学校代码无效'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查是否已是成员
        if TeacherSchoolMembership.objects.filter(
            teacher=request.user, school=school, is_active=True
        ).exists():
            return Response({'error': '您已经是该学校成员'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查是否有待审批的申请
        if SchoolJoinRequest.objects.filter(
            teacher=request.user, school=school, status='pending'
        ).exists():
            return Response({'error': '您已有待审批的申请'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查是否被封禁
        if SchoolJoinRequest.objects.filter(
            teacher=request.user, school=school, status='blocked'
        ).exists():
            return Response({'error': '您已被该学校限制申请'}, status=status.HTTP_403_FORBIDDEN)

        # 创建申请
        SchoolJoinRequest.objects.create(
            teacher=request.user,
            school=school,
            migrate_classes=migrate_classes,
            migrate_students=migrate_students
        )

        return Response({'message': '申请已提交，请等待学校管理员审批'})

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_schools(self, request):
        """获取我加入的所有学校"""
        memberships = TeacherSchoolMembership.objects.filter(
            teacher=request.user,
            is_active=True
        ).select_related('school')

        schools = [{
            'id': m.school.id,
            'name': m.school.name,
            'code': m.school.code,
            'is_current': m.school == request.user.school,
            'joined_at': m.joined_at.isoformat() if m.joined_at else None
        } for m in memberships]

        return Response(schools)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_join_requests(self, request):
        """获取我的加入申请列表"""
        requests = SchoolJoinRequest.objects.filter(
            teacher=request.user
        ).select_related('school').order_by('-created_at')

        data = [{
            'id': r.id,
            'school_name': r.school.name,
            'school_code': r.school.code,
            'status': r.status,
            'status_display': r.get_status_display(),
            'migrate_classes': r.migrate_classes,
            'migrate_students': r.migrate_students,
            'reject_reason': r.reject_reason,
            'created_at': r.created_at.isoformat()
        } for r in requests]

        return Response(data)

    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated])
    def switch_school(self, request):
        """切换当前学校"""
        school_id = request.data.get('school_id')

        if not school_id:
            return Response({'error': '请选择学校'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证是否是有效会员
        if not TeacherSchoolMembership.objects.filter(
            teacher=request.user,
            school_id=school_id,
            is_active=True
        ).exists():
            return Response({'error': '您不是该学校成员'}, status=status.HTTP_403_FORBIDDEN)

        # 更新当前学校
        request.user.school_id = school_id
        request.user.save(update_fields=['school_id'])

        return Response({
            'message': '学校切换成功',
            'user': UserSerializer(request.user).data
        })

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def join_requests(self, request):
        """获取本校的加入申请列表（管理员用）"""
        if not request.user.is_admin:
            return Response({'error': '无权限'}, status=status.HTTP_403_FORBIDDEN)

        status_filter = request.query_params.get('status', 'pending')

        queryset = SchoolJoinRequest.objects.filter(
            school=request.user.school
        ).select_related('teacher')

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        data = [{
            'id': r.id,
            'teacher_name': r.teacher.real_name,
            'teacher_phone': r.teacher.phone,
            'status': r.status,
            'status_display': r.get_status_display(),
            'migrate_classes': r.migrate_classes,
            'migrate_students': r.migrate_students,
            'reject_count': r.reject_count,
            'reject_reason': r.reject_reason,
            'created_at': r.created_at.isoformat()
        } for r in queryset]

        return Response(data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def approve_join_request(self, request, pk=None):
        """审批通过加入申请"""
        if not request.user.is_admin:
            return Response({'error': '无权限'}, status=status.HTTP_403_FORBIDDEN)

        try:
            join_request = SchoolJoinRequest.objects.get(
                pk=pk,
                school=request.user.school,
                status='pending'
            )
        except SchoolJoinRequest.DoesNotExist:
            return Response({'error': '申请不存在或已处理'}, status=status.HTTP_404_NOT_FOUND)

        # 执行数据迁移（如果需要）
        if join_request.migrate_classes:
            self._migrate_teacher_data(join_request.teacher, join_request.school)

        # 创建会员关系
        TeacherSchoolMembership.objects.get_or_create(
            teacher=join_request.teacher,
            school=join_request.school,
            defaults={'is_active': True}
        )

        # 更新申请状态
        join_request.status = 'approved'
        join_request.reviewed_by = request.user
        join_request.reviewed_at = timezone.now()
        join_request.save()

        logger.info(f"Join request {pk} approved by {request.user.real_name}")

        return Response({'message': '已通过申请'})

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def reject_join_request(self, request, pk=None):
        """拒绝加入申请"""
        if not request.user.is_admin:
            return Response({'error': '无权限'}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get('reason', '')

        try:
            join_request = SchoolJoinRequest.objects.get(
                pk=pk,
                school=request.user.school,
                status='pending'
            )
        except SchoolJoinRequest.DoesNotExist:
            return Response({'error': '申请不存在或已处理'}, status=status.HTTP_404_NOT_FOUND)

        join_request.reject_count += 1
        join_request.reject_reason = reason
        join_request.reviewed_by = request.user
        join_request.reviewed_at = timezone.now()

        if join_request.reject_count >= 2:
            join_request.status = 'blocked'
        else:
            join_request.status = 'rejected'

        join_request.save()

        logger.info(f"Join request {pk} rejected by {request.user.real_name}")

        return Response({'message': '已拒绝申请'})

    def _migrate_teacher_data(self, teacher, new_school):
        """迁移教师的班级数据到新学校"""
        from apps.classes.models import Class

        # 获取教师作为班主任的班级
        classes = Class.objects.filter(head_teacher=teacher)

        migrated_count = 0
        for cls in classes:
            # 只迁移无学校或当前学校的班级
            if cls.school is None or cls.school == teacher.school:
                cls.school = new_school
                cls.save()
                migrated_count += 1

        logger.info(f"Migrated {migrated_count} classes for teacher {teacher.real_name} to school {new_school.name}")
