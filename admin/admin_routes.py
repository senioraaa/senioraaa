# admin/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def admin_dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/users')
def admin_users():
    return render_template('admin/users.html')

# أضف المزيد من الروتات حسب الحاجة
