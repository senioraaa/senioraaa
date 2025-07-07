# ملف: models.py
# نماذج قاعدة البيانات المصححة لمشروع شهد السنيورة

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import uuid
import enum

# إنشاء مثيل قاعدة البيانات
db = SQLAlchemy()

# تعداد لحالة المستخدم
class UserStatus(enum.Enum):
    ACTIVE = "active"           # نشط
    INACTIVE = "inactive"       # غير نشط
    SUSPENDED = "suspended"     # معلق
    PENDING = "pending"         # في انتظار التفعيل

# تعداد لنوع المستخدم
class UserRole(enum.Enum):
    USER = "user"               # مستخدم عادي
    ADMIN = "admin"             # مدير
    MODERATOR = "moderator"     # مشرف
    PREMIUM = "premium"         # مستخدم مميز

# تعداد لحالة الرسالة
class MessageStatus(enum.Enum):
    SENT = "sent"               # مرسلة
    DELIVERED = "delivered"     # تم التسليم
    READ = "read"               # مقروءة
    DELETED = "deleted"         # محذوفة

# نموذج المستخدم
class User(UserMixin, db.Model):
    """
    نموذج المستخدم - يحتوي على جميع بيانات المستخدمين
    """
    __tablename__ = 'users'

    # المعرف الأساسي
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # معرف فريد للمستخدم (UUID)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    # بيانات المستخدم الأساسية
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    # البيانات الشخصية
    first_name = db.Column(db.String(50), nullable=True)
    last_name = db.Column(db.String(50), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    bio = db.Column(db.Text, nullable=True)

    # صورة المستخدم
    avatar_url = db.Column(db.String(255), nullable=True)

    # حالة ونوع المستخدم
    status = db.Column(db.Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.USER, nullable=False)

    # تواريخ مهمة
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    email_verified_at = db.Column(db.DateTime, nullable=True)

    # إعدادات المستخدم
    is_email_verified = db.Column(db.Boolean, default=False, nullable=False)
    is_phone_verified = db.Column(db.Boolean, default=False, nullable=False)
    receive_notifications = db.Column(db.Boolean, default=True, nullable=False)
    is_online = db.Column(db.Boolean, default=False, nullable=False)

    # العلاقات
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', 
                                   backref='sender', lazy='dynamic', cascade='all, delete-orphan')
    received_messages = db.relationship('Message', foreign_keys='Message.receiver_id', 
                                       backref='receiver', lazy='dynamic', cascade='all, delete-orphan')

    def __init__(self, username, email, password, **kwargs):
        """
        إنشاء مستخدم جديد
        """
        self.username = username
        self.email = email
        self.set_password(password)

        # تعيين البيانات الإضافية
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def set_password(self, password):
        """
        تشفير وحفظ كلمة المرور
        """
        if not password:
            raise ValueError("كلمة المرور مطلوبة")

        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """
        التحقق من كلمة المرور
        """
        if not password or not self.password_hash:
            return False

        return check_password_hash(self.password_hash, password)

    def get_full_name(self):
        """
        الحصول على الاسم الكامل
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.username

    def is_active_user(self):
        """
        فحص ما إذا كان المستخدم نشط
        """
        return self.status == UserStatus.ACTIVE

    def is_admin(self):
        """
        فحص ما إذا كان المستخدم مدير
        """
        return self.role == UserRole.ADMIN

    def is_moderator(self):
        """
        فحص ما إذا كان المستخدم مشرف
        """
        return self.role in [UserRole.ADMIN, UserRole.MODERATOR]

    def update_last_login(self):
        """
        تحديث وقت آخر تسجيل دخول
        """
        self.last_login = datetime.now(timezone.utc)
        self.is_online = True
        db.session.commit()

    def set_offline(self):
        """
        تعيين المستخدم كغير متصل
        """
        self.is_online = False
        db.session.commit()

    def verify_email(self):
        """
        تفعيل البريد الإلكتروني
        """
        self.is_email_verified = True
        self.email_verified_at = datetime.now(timezone.utc)
        if self.status == UserStatus.PENDING:
            self.status = UserStatus.ACTIVE
        db.session.commit()

    def to_dict(self, include_sensitive=False):
        """
        تحويل المستخدم إلى قاموس
        """
        data = {
            'id': self.id,
            'uuid': self.uuid,
            'username': self.username,
            'email': self.email if include_sensitive else None,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'full_name': self.get_full_name(),
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'status': self.status.value,
            'role': self.role.value,
            'is_online': self.is_online,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }

        if include_sensitive:
            data.update({
                'phone': self.phone,
                'is_email_verified': self.is_email_verified,
                'is_phone_verified': self.is_phone_verified,
                'receive_notifications': self.receive_notifications,
                'email_verified_at': self.email_verified_at.isoformat() if self.email_verified_at else None,
            })

        return data

    def __repr__(self):
        return f'<User {self.username}>'

# نموذج الرسائل
class Message(db.Model):
    """
    نموذج الرسائل - يحتوي على جميع الرسائل المرسلة بين المستخدمين
    """
    __tablename__ = 'messages'

    # المعرف الأساسي
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    # معرف فريد للرسالة (UUID)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    # المرسل والمستقبل
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)

    # محتوى الرسالة
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text', nullable=False)  # text, image, file, etc.

    # حالة الرسالة
    status = db.Column(db.Enum(MessageStatus), default=MessageStatus.SENT, nullable=False)

    # مرفقات الرسالة
    attachment_url = db.Column(db.String(255), nullable=True)
    attachment_type = db.Column(db.String(50), nullable=True)
    attachment_size = db.Column(db.Integer, nullable=True)

    # تواريخ مهمة
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # إعدادات الرسالة
    is_edited = db.Column(db.Boolean, default=False, nullable=False)
    is_deleted = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, sender_id, receiver_id, content, **kwargs):
        """
        إنشاء رسالة جديدة
        """
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.content = content

        # تعيين البيانات الإضافية
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

    def mark_as_read(self):
        """
        تعليم الرسالة كمقروءة
        """
        if self.status != MessageStatus.READ:
            self.status = MessageStatus.READ
            self.read_at = datetime.now(timezone.utc)
            db.session.commit()

    def mark_as_deleted(self):
        """
        تعليم الرسالة كمحذوفة
        """
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
        self.status = MessageStatus.DELETED
        db.session.commit()

    def edit_content(self, new_content):
        """
        تعديل محتوى الرسالة
        """
        if not self.is_deleted:
            self.content = new_content
            self.is_edited = True
            self.updated_at = datetime.now(timezone.utc)
            db.session.commit()

    def is_read(self):
        """
        فحص ما إذا كانت الرسالة مقروءة
        """
        return self.status == MessageStatus.READ

    def can_be_edited(self, user_id):
        """
        فحص ما إذا كان يمكن تعديل الرسالة
        """
        # يمكن للمرسل تعديل الرسالة خلال 15 دقيقة من الإرسال
        if self.sender_id != user_id or self.is_deleted:
            return False

        time_limit = datetime.now(timezone.utc) - self.created_at
        return time_limit.total_seconds() < 900  # 15 دقيقة

    def can_be_deleted(self, user_id):
        """
        فحص ما إذا كان يمكن حذف الرسالة
        """
        # يمكن للمرسل أو المستقبل حذف الرسالة
        return user_id in [self.sender_id, self.receiver_id] and not self.is_deleted

    def to_dict(self, current_user_id=None):
        """
        تحويل الرسالة إلى قاموس
        """
        data = {
            'id': self.id,
            'uuid': self.uuid,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'content': self.content if not self.is_deleted else '[تم حذف الرسالة]',
            'message_type': self.message_type,
            'status': self.status.value,
            'is_edited': self.is_edited,
            'is_deleted': self.is_deleted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
        }

        # إضافة معلومات المرفقات إذا وجدت
        if self.attachment_url and not self.is_deleted:
            data.update({
                'attachment_url': self.attachment_url,
                'attachment_type': self.attachment_type,
                'attachment_size': self.attachment_size,
            })

        # إضافة معلومات إضافية للمرسل
        if current_user_id == self.sender_id:
            data.update({
                'can_edit': self.can_be_edited(current_user_id),
                'can_delete': self.can_be_deleted(current_user_id),
            })

        return data

    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.receiver_id}>'

# نموذج جلسات المستخدم (للأمان)
class UserSession(db.Model):
    """
    نموذج جلسات المستخدم - لتتبع جلسات تسجيل الدخول
    """
    __tablename__ = 'user_sessions'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_token = db.Column(db.String(255), unique=True, nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6 support
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # العلاقة مع المستخدم
    user = db.relationship('User', backref=db.backref('sessions', lazy='dynamic', cascade='all, delete-orphan'))

    def is_expired(self):
        """
        فحص ما إذا كانت الجلسة منتهية الصلاحية
        """
        return datetime.now(timezone.utc) > self.expires_at

    def is_valid(self):
        """
        فحص ما إذا كانت الجلسة صالحة
        """
        return self.is_active and not self.is_expired()

    def revoke(self):
        """
        إلغاء الجلسة
        """
        self.is_active = False
        db.session.commit()

    def __repr__(self):
        return f'<UserSession {self.id} for user {self.user_id}>'

# نموذج إعدادات التطبيق
class AppSetting(db.Model):
    """
    نموذج إعدادات التطبيق - لحفظ الإعدادات العامة
    """
    __tablename__ = 'app_settings'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    @staticmethod
    def get_setting(key, default=None):
        """
        الحصول على قيمة إعداد
        """
        setting = AppSetting.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set_setting(key, value, description=None):
        """
        تعيين قيمة إعداد
        """
        setting = AppSetting.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            setting.updated_at = datetime.now(timezone.utc)
            if description:
                setting.description = description
        else:
            setting = AppSetting(key=key, value=value, description=description)
            db.session.add(setting)

        db.session.commit()
        return setting

    def __repr__(self):
        return f'<AppSetting {self.key}>'

# دوال مساعدة لإنشاء الجداول
def create_tables(app):
    """
    إنشاء جميع الجداول في قاعدة البيانات
    """
    with app.app_context():
        db.create_all()
        print("✅ تم إنشاء جميع الجداول بنجاح")

def drop_tables(app):
    """
    حذف جميع الجداول من قاعدة البيانات
    """
    with app.app_context():
        db.drop_all()
        print("⚠️ تم حذف جميع الجداول")

def init_default_settings():
    """
    إنشاء الإعدادات الافتراضية للتطبيق
    """
    default_settings = [
        ('app_name', 'شهد السنيورة', 'اسم التطبيق'),
        ('app_version', '1.0.0', 'إصدار التطبيق'),
        ('max_message_length', '1000', 'الحد الأقصى لطول الرسالة'),
        ('allow_file_upload', 'true', 'السماح برفع الملفات'),
        ('max_file_size', '10485760', 'الحد الأقصى لحجم الملف (بايت)'),
        ('maintenance_mode', 'false', 'وضع الصيانة'),
        ('registration_enabled', 'true', 'تفعيل التسجيل الجديد'),
    ]

    for key, value, description in default_settings:
        if not AppSetting.query.filter_by(key=key).first():
            AppSetting.set_setting(key, value, description)

    print("✅ تم إنشاء الإعدادات الافتراضية")

# دالة للبحث في المستخدمين
def search_users(query, limit=10):
    """
    البحث في المستخدمين بالاسم أو البريد الإلكتروني
    """
    if not query:
        return []

    search_term = f"%{query}%"
    users = User.query.filter(
        db.or_(
            User.username.ilike(search_term),
            User.first_name.ilike(search_term),
            User.last_name.ilike(search_term),
            User.email.ilike(search_term)
        ),
        User.status == UserStatus.ACTIVE
    ).limit(limit).all()

    return users

# دالة للحصول على المحادثات الأخيرة
def get_recent_conversations(user_id, limit=20):
    """
    الحصول على المحادثات الأخيرة للمستخدم
    """
    # استعلام معقد للحصول على آخر رسالة في كل محادثة
    subquery = db.session.query(
        db.func.greatest(Message.sender_id, Message.receiver_id).label('user1'),
        db.func.least(Message.sender_id, Message.receiver_id).label('user2'),
        db.func.max(Message.created_at).label('last_message_time')
    ).filter(
        db.or_(Message.sender_id == user_id, Message.receiver_id == user_id),
        Message.is_deleted == False
    ).group_by(
        db.func.greatest(Message.sender_id, Message.receiver_id),
        db.func.least(Message.sender_id, Message.receiver_id)
    ).subquery()

    # الحصول على الرسائل الأخيرة
    conversations = db.session.query(Message).join(
        subquery,
        db.and_(
            db.or_(
                db.and_(Message.sender_id == subquery.c.user1, Message.receiver_id == subquery.c.user2),
                db.and_(Message.sender_id == subquery.c.user2, Message.receiver_id == subquery.c.user1)
            ),
            Message.created_at == subquery.c.last_message_time
        )
    ).order_by(Message.created_at.desc()).limit(limit).all()

    return conversations
