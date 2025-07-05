# إنشاء هذا الملف للتجريب السريع
def fix_indentation_issues():
    """فحص وإصلاح مشاكل التباعد"""
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    for i, line in enumerate(lines):
        if 'with app.app_context():' in line:
            fixed_lines.append(line)
            # تأكد إن السطر اللي بعده مش function definition
            if i + 1 < len(lines) and lines[i + 1].strip().startswith('def '):
                fixed_lines.append('        pass  # placeholder\n')
        else:
            fixed_lines.append(line)
    
    with open('app_fixed.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print("Fixed file created as app_fixed.py")

if __name__ == '__main__':
    fix_indentation_issues()
