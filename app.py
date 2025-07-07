# ملف: app.py
# التطبيق الرئيسي المبسط لمشروع شهد السنيورة

import os
import logging
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session, g
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename

# استيراد الوحدات المحلية
from config import get_config, validate_config, print_config_summary
from models import db, User, Message, UserSession, AppSetting, create_tables, init_default_settings
from error_handlers import init_error_handlers, handle_validation_error, handle_authentication_error
from simple_limiter import (
    general_rate_limit, login_rate_limit, register_rate_limit, 
    message_rate_limit, add_rate_limit_headers, cleanup_old_data
)

# إنشاء التطبيق
def create_app(config_name=None):
    """
    إنشاء وتكوين تطبيق Flask

    Args:
        config_name (str): اسم بيئة التكوين

    Returns:
        Flask: مثيل التطبيق المكون
    """
    app = Flask(__name__)

    # تحميل الإعدادات
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # التحقق من صحة الإعدادات
    config_errors = validate_config(config_class)
    if config_errors:
        print("⚠️ تحذيرات الإعدادات:")
        for error in config_errors:
            print(f"   - {error}")

    # طباعة ملخص الإعدادات
    if app.debug:
        print_config_summary(config_class)

    # تهيئة الإعدادات
    config_class.init_app(app)

    # تهيئة قاعدة البيانات
    db.init_app(app)

    # تهيئة نظام تسجيل الدخول
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        """تحميل المستخدم من قاعدة البيانات"""
        return User.query.get(int(user_id))

    # تهيئة معالجات الأخطاء
    error_handler = init_error_handlers(app)

    # إضافة Headers للاستجابات
    @app.after_request
    def after_request(response):
        """إضافة Headers مفيدة لجميع الاستجابات"""
        # إضافة Rate Limit Headers
        response = add_rate_limit_headers(response)

        # إضافة Headers الأمان الأساسية
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'

        return response

    # متغيرات السياق العامة
    @app.context_processor
    def inject_global_vars():
        """حقن متغيرات عامة في جميع القوالب"""
        return {
            'app_name': app.config.get('APP_NAME', 'شهد السنيورة'),
            'app_version': app.config.get('APP_VERSION', '1.0.0'),
            'current_year': datetime.now().year,
            'is_authenticated': current_user.is_authenticated if current_user else False,
            'current_user': current_user if current_user.is_authenticated else None
        }

    # تسجيل المسارات (Routes)
    register_routes(app)

    # إنشاء الجداول والبيانات الأولية
    with app.app_context():
        create_tables(app)
        init_default_settings()

        # إنشاء مستخدم مدير افتراضي إذا لم يوجد
        create_default_admin()

    return app

def register_routes(app):
    """
    تسجيل جميع مسارات التطبيق
    """

    # ===== الصفحة الرئيسية =====

    @app.route('/')
    @general_rate_limit()
    def index():
        """الصفحة الرئيسية"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        return render_template('index.html')

    @app.route('/dashboard')
    @login_required
    @general_rate_limit()
    def dashboard():
        """لوحة التحكم الرئيسية"""
        # الحصول على إحصائيات المستخدم
        sent_messages_count = Message.query.filter_by(
            sender_id=current_user.id,
            is_deleted=False
        ).count()

        received_messages_count = Message.query.filter_by(
            receiver_id=current_user.id,
            is_deleted=False
        ).count()

        unread_messages_count = Message.query.filter_by(
            receiver_id=current_user.id,
            is_deleted=False
        ).filter(Message.read_at.is_(None)).count()

        # الحصول على آخر الرسائل
        recent_messages = Message.query.filter(
            db.or_(
                Message.sender_id == current_user.id,
                Message.receiver_id == current_user.id
            ),
            Message.is_deleted == False
        ).order_by(Message.created_at.desc()).limit(5).all()

        stats = {
            'sent_messages': sent_messages_count,
            'received_messages': received_messages_count,
            'unread_messages': unread_messages_count,
            'total_messages': sent_messages_count + received_messages_count
        }

        return render_template('dashboard.html', 
                             stats=stats, 
                             recent_messages=recent_messages)

    # ===== مسارات المصادقة =====

    @app.route('/login', methods=['GET', 'POST'])
    @login_rate_limit()
    def login():
        """تسجيل الدخول"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        if request.method == 'POST':
            try:
                data = request.get_json() if request.is_json else request.form
                username = data.get('username', '').strip()
                password = data.get('password', '')
                remember_me = data.get('remember_me', False)

                # التحقق من صحة البيانات
                if not username or not password:
                    error_response = handle_validation_error({
                        'username': 'اسم المستخدم مطلوب' if not username else None,
                        'password': 'كلمة المرور مطلوبة' if not password else None
                    })

                    if request.is_json:
                        return jsonify(error_response), 400

                    flash('يرجى ملء جميع الحقول المطلوبة', 'error')
                    return render_template('auth/login.html')

                # البحث عن المستخدم
                user = User.query.filter(
                    db.or_(User.username == username, User.email == username)
                ).first()

                # التحقق من وجود المستخدم وكلمة المرور
                if not user or not user.check_password(password):
                    error_response = handle_authentication_error('اسم المستخدم أو كلمة المرور غير صحيحة')

                    if request.is_json:
                        return jsonify(error_response), 401

                    flash('اسم المستخدم أو كلمة المرور غير صحيحة', 'error')
                    return render_template('auth/login.html')

                # التحقق من حالة المستخدم
                if not user.is_active_user():
                    error_response = handle_authentication_error('حسابك غير مفعل أو معلق')

                    if request.is_json:
                        return jsonify(error_response), 401

                    flash('حسابك غير مفعل أو معلق، يرجى التواصل مع الإدارة', 'error')
                    return render_template('auth/login.html')

                # تسجيل الدخول
                login_user(user, remember=remember_me)
                user.update_last_login()

                # إنشاء جلسة جديدة
                create_user_session(user)

                # الاستجابة
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'تم تسجيل الدخول بنجاح',
                        'redirect_url': url_for('dashboard'),
                        'user': user.to_dict()
                    })

                flash(f'مرحباً {user.get_full_name()}!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('dashboard'))

            except Exception as e:
                app.logger.error(f"خطأ في تسجيل الدخول: {str(e)}")

                if request.is_json:
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 500,
                            'message': 'حدث خطأ أثناء تسجيل الدخول'
                        }
                    }), 500

                flash('حدث خطأ أثناء تسجيل الدخول، يرجى المحاولة مرة أخرى', 'error')

        return render_template('auth/login.html')

    @app.route('/register', methods=['GET', 'POST'])
    @register_rate_limit()
    def register():
        """تسجيل مستخدم جديد"""
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))

        # التحقق من تفعيل التسجيل
        if not app.config.get('REGISTRATION_ENABLED', True):
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'التسجيل غير متاح حالياً'
                    }
                }), 403

            flash('التسجيل غير متاح حالياً', 'error')
            return redirect(url_for('login'))

        if request.method == 'POST':
            try:
                data = request.get_json() if request.is_json else request.form

                username = data.get('username', '').strip()
                email = data.get('email', '').strip().lower()
                password = data.get('password', '')
                confirm_password = data.get('confirm_password', '')
                first_name = data.get('first_name', '').strip()
                last_name = data.get('last_name', '').strip()

                # التحقق من صحة البيانات
                errors = {}

                if not username:
                    errors['username'] = 'اسم المستخدم مطلوب'
                elif len(username) < 3:
                    errors['username'] = 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل'
                elif User.query.filter_by(username=username).first():
                    errors['username'] = 'اسم المستخدم موجود مسبقاً'

                if not email:
                    errors['email'] = 'البريد الإلكتروني مطلوب'
                elif '@' not in email:
                    errors['email'] = 'البريد الإلكتروني غير صحيح'
                elif User.query.filter_by(email=email).first():
                    errors['email'] = 'البريد الإلكتروني موجود مسبقاً'

                if not password:
                    errors['password'] = 'كلمة المرور مطلوبة'
                elif len(password) < app.config.get('PASSWORD_MIN_LENGTH', 8):
                    errors['password'] = f'كلمة المرور يجب أن تكون {app.config.get("PASSWORD_MIN_LENGTH", 8)} أحرف على الأقل'

                if password != confirm_password:
                    errors['confirm_password'] = 'كلمات المرور غير متطابقة'

                if errors:
                    error_response = handle_validation_error(errors)

                    if request.is_json:
                        return jsonify(error_response), 400

                    for field, message in errors.items():
                        flash(message, 'error')

                    return render_template('auth/register.html')

                # إنشاء المستخدم الجديد
                user = User(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name
                )

                db.session.add(user)
                db.session.commit()

                # الاستجابة
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'تم إنشاء الحساب بنجاح',
                        'redirect_url': url_for('login'),
                        'user': user.to_dict()
                    })

                flash('تم إنشاء حسابك بنجاح! يمكنك الآن تسجيل الدخول', 'success')
                return redirect(url_for('login'))

            except Exception as e:
                db.session.rollback()
                app.logger.error(f"خطأ في التسجيل: {str(e)}")

                if request.is_json:
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 500,
                            'message': 'حدث خطأ أثناء إنشاء الحساب'
                        }
                    }), 500

                flash('حدث خطأ أثناء إنشاء الحساب، يرجى المحاولة مرة أخرى', 'error')

        return render_template('auth/register.html')

    @app.route('/logout')
    @login_required
    def logout():
        """تسجيل الخروج"""
        if current_user.is_authenticated:
            # إلغاء الجلسة الحالية
            revoke_user_session(current_user)

            # تعيين المستخدم كغير متصل
            current_user.set_offline()

            # تسجيل الخروج
            logout_user()

        flash('تم تسجيل الخروج بنجاح', 'info')
        return redirect(url_for('index'))

    # ===== مسارات الرسائل =====

    @app.route('/messages')
    @login_required
    @general_rate_limit()
    def messages():
        """صفحة الرسائل"""
        page = request.args.get('page', 1, type=int)
        per_page = app.config.get('MESSAGES_PER_PAGE', 50)

        # الحصول على الرسائل
        messages_query = Message.query.filter(
            db.or_(
                Message.sender_id == current_user.id,
                Message.receiver_id == current_user.id
            ),
            Message.is_deleted == False
        ).order_by(Message.created_at.desc())

        messages_pagination = messages_query.paginate(
            page=page, per_page=per_page, error_out=False
        )

        return render_template('messages/list.html', 
                             messages=messages_pagination.items,
                             pagination=messages_pagination)

    @app.route('/messages/send', methods=['GET', 'POST'])
    @login_required
    @message_rate_limit()
    def send_message():
        """إرسال رسالة جديدة"""
        if request.method == 'POST':
            try:
                data = request.get_json() if request.is_json else request.form

                receiver_username = data.get('receiver_username', '').strip()
                content = data.get('content', '').strip()

                # التحقق من صحة البيانات
                errors = {}

                if not receiver_username:
                    errors['receiver_username'] = 'اسم المستقبل مطلوب'

                if not content:
                    errors['content'] = 'محتوى الرسالة مطلوب'
                elif len(content) > app.config.get('MAX_MESSAGE_LENGTH', 1000):
                    errors['content'] = f'الرسالة طويلة جداً (الحد الأقصى {app.config.get("MAX_MESSAGE_LENGTH", 1000)} حرف)'

                # البحث عن المستقبل
                receiver = None
                if receiver_username:
                    receiver = User.query.filter_by(username=receiver_username).first()
                    if not receiver:
                        errors['receiver_username'] = 'المستخدم غير موجود'
                    elif receiver.id == current_user.id:
                        errors['receiver_username'] = 'لا يمكنك إرسال رسالة لنفسك'
                    elif not receiver.is_active_user():
                        errors['receiver_username'] = 'المستخدم غير نشط'

                if errors:
                    error_response = handle_validation_error(errors)

                    if request.is_json:
                        return jsonify(error_response), 400

                    for field, message in errors.items():
                        flash(message, 'error')

                    return render_template('messages/send.html')

                # إنشاء الرسالة
                message = Message(
                    sender_id=current_user.id,
                    receiver_id=receiver.id,
                    content=content
                )

                db.session.add(message)
                db.session.commit()

                # الاستجابة
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'تم إرسال الرسالة بنجاح',
                        'data': message.to_dict(current_user.id)
                    })

                flash('تم إرسال الرسالة بنجاح', 'success')
                return redirect(url_for('messages'))

            except Exception as e:
                db.session.rollback()
                app.logger.error(f"خطأ في إرسال الرسالة: {str(e)}")

                if request.is_json:
                    return jsonify({
                        'success': False,
                        'error': {
                            'code': 500,
                            'message': 'حدث خطأ أثناء إرسال الرسالة'
                        }
                    }), 500

                flash('حدث خطأ أثناء إرسال الرسالة، يرجى المحاولة مرة أخرى', 'error')

        return render_template('messages/send.html')

    @app.route('/messages/<int:message_id>/read', methods=['POST'])
    @login_required
    @general_rate_limit()
    def mark_message_read(message_id):
        """تعليم الرسالة كمقروءة"""
        message = Message.query.get_or_404(message_id)

        # التحقق من الصلاحية
        if message.receiver_id != current_user.id:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': {
                        'code': 403,
                        'message': 'ليس لديك صلاحية لتعديل هذه الرسالة'
                    }
                }), 403

            flash('ليس لديك صلاحية لتعديل هذه الرسالة', 'error')
            return redirect(url_for('messages'))

        # تعليم الرسالة كمقروءة
        message.mark_as_read()

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'تم تعليم الرسالة كمقروءة'
            })

        return redirect(url_for('messages'))

    # ===== مسارات API =====

    @app.route('/api/users/search')
    @login_required
    @general_rate_limit()
    def api_search_users():
        """البحث في المستخدمين"""
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 10)), 50)

        if not query or len(query) < 2:
            return jsonify({
                'success': False,
                'error': {
                    'code': 400,
                    'message': 'يجب أن يكون البحث حرفين على الأقل'
                }
            }), 400

        # البحث في المستخدمين
        from models import search_users
        users = search_users(query, limit)

        return jsonify({
            'success': True,
            'data': [user.to_dict() for user in users],
            'count': len(users)
        })

    @app.route('/api/messages/unread-count')
    @login_required
    @general_rate_limit()
    def api_unread_messages_count():
        """عدد الرسائل غير المقروءة"""
        count = Message.query.filter_by(
            receiver_id=current_user.id,
            is_deleted=False
        ).filter(Message.read_at.is_(None)).count()

        return jsonify({
            'success': True,
            'data': {
                'unread_count': count
            }
        })

    # ===== مسارات الإدارة =====

    @app.route('/admin')
    @login_required
    @general_rate_limit()
    def admin_dashboard():
        """لوحة تحكم الإدارة"""
        if not current_user.is_admin():
            flash('ليس لديك صلاحية للوصول إلى لوحة الإدارة', 'error')
            return redirect(url_for('dashboard'))

        # إحصائيات عامة
        stats = {
            'total_users': User.query.count(),
            'active_users': User.query.filter_by(status='active').count(),
            'total_messages': Message.query.filter_by(is_deleted=False).count(),
            'online_users': User.query.filter_by(is_online=True).count()
        }

        return render_template('admin/dashboard.html', stats=stats)

def create_user_session(user):
    """
    إنشاء جلسة جديدة للمستخدم
    """
    try:
        import secrets
        from datetime import timedelta

        # إنشاء رمز الجلسة
        session_token = secrets.token_urlsafe(32)

        # تحديد وقت انتهاء الجلسة
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)

        # إنشاء سجل الجلسة
        user_session = UserSession(
            user_id=user.id,
            session_token=session_token,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            expires_at=expires_at
        )

        db.session.add(user_session)
        db.session.commit()

        # حفظ رمز الجلسة في session
        session['session_token'] = session_token

    except Exception as e:
        logging.error(f"خطأ في إنشاء جلسة المستخدم: {str(e)}")

def revoke_user_session(user):
    """
    إلغاء جلسة المستخدم الحالية
    """
    try:
        session_token = session.get('session_token')
        if session_token:
            user_session = UserSession.query.filter_by(
                user_id=user.id,
                session_token=session_token,
                is_active=True
            ).first()

            if user_session:
                user_session.revoke()

        # مسح رمز الجلسة من session
        session.pop('session_token', None)

    except Exception as e:
        logging.error(f"خطأ في إلغاء جلسة المستخدم: {str(e)}")

def create_default_admin():
    """
    إنشاء مستخدم مدير افتراضي إذا لم يوجد
    """
    try:
        # التحقق من وجود مدير
        admin_exists = User.query.filter_by(role='admin').first()

        if not admin_exists:
            # إنشاء مدير افتراضي
            admin_user = User(
                username='admin',
                email='admin@shahd-senior.com',
                password='admin123',  # يجب تغييرها فوراً
                first_name='مدير',
                last_name='النظام',
                role='admin',
                status='active',
                is_email_verified=True
            )

            db.session.add(admin_user)
            db.session.commit()

            print("✅ تم إنشاء مستخدم المدير الافتراضي:")
            print("   اسم المستخدم: admin")
            print("   كلمة المرور: admin123")
            print("   ⚠️ يرجى تغيير كلمة المرور فوراً!")

    except Exception as e:
        db.session.rollback()
        logging.error(f"خطأ في إنشاء المدير الافتراضي: {str(e)}")

# تشغيل التطبيق
if __name__ == '__main__':
    # تحديد بيئة التشغيل
    config_name = os.environ.get('FLASK_ENV', 'development')

    # إنشاء التطبيق
    app = create_app(config_name)

    # تنظيف البيانات القديمة دورياً
    import threading
    import time

    def cleanup_task():
        """مهمة تنظيف البيانات القديمة"""
        while True:
            try:
                with app.app_context():
                    cleanup_old_data()
                time.sleep(3600)  # كل ساعة
            except Exception as e:
                logging.error(f"خطأ في مهمة التنظيف: {str(e)}")
                time.sleep(300)  # إعادة المحاولة بعد 5 دقائق

    # تشغيل مهمة التنظيف في خيط منفصل
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()

    # تشغيل التطبيق
    port = int(os.environ.get('PORT', 5000))
    debug = app.config.get('DEBUG', False)

    print(f"🚀 تشغيل تطبيق شهد السنيورة على المنفذ {port}")
    print(f"🔧 وضع التطوير: {'مفعل' if debug else 'معطل'}")
    print(f"🌐 الرابط: http://localhost:{port}")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug,
        threaded=True
    )
