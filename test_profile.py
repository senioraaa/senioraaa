# ملف اختبار بسيط
from app import app, db, User

def test_profile_system():
    with app.app_context():
        # إنشاء مستخدم تجريبي
        test_user = User.query.filter_by(email='test@example.com').first()
        
        if not test_user:
            from werkzeug.security import generate_password_hash
            test_user = User(
                email='test@example.com',
                password_hash=generate_password_hash('test123'),
                is_verified=True
            )
            db.session.add(test_user)
            db.session.commit()
            print("مستخدم تجريبي تم إنشاؤه")
        
        # اختبار تحديث الملف الشخصي
        test_user.whatsapp = '+201234567890'
        test_user.preferred_platform = 'PS'
        test_user.preferred_payment = 'vodafone'
        
        from app import check_profile_completion
        test_user.profile_completed = check_profile_completion(test_user)
        
        db.session.commit()
        
        print(f"حالة الملف الشخصي: {'مكتمل' if test_user.profile_completed else 'غير مكتمل'}")
        print("اختبار النظام مكتمل ✅")

if __name__ == '__main__':
    test_profile_system()
