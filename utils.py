import logging
from datetime import datetime

def setup_logging():
    """إعداد نظام السجلات"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('app.log'),
            logging.StreamHandler()
        ]
    )

def log_price_update(game, platform, price):
    """تسجيل تحديث الأسعار"""
    logger = logging.getLogger(__name__)
    logger.info(f"تم تحديث سعر {game} - {platform}: {price}")

def validate_price_format(price):
    """التحقق من صيغة السعر"""
    if not price or price == 'غير متاح':
        return True
    
    try:
        float(price)
        return True
    except ValueError:
        return False
