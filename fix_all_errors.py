#!/usr/bin/env python3
"""
إصلاح جميع أخطاء flake8 بسرعة
"""

import os
import re


def fix_all_files():
    """إصلاح جميع الأخطاء"""

    # إصلاح ai_code_genius.py
    if os.path.exists("ai_code_genius.py"):
        with open("ai_code_genius.py", "r", encoding="utf-8") as f:
            content = f.read()

        # إصلاح السطر المكسور
        content = re.sub(
            r'logging\.info\("\s*=\s*\(\s*==+"\s*\)',
            'logging.info("=" * 60)',
            content,
        )

        with open("ai_code_genius.py", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ تم إصلاح ai_code_genius.py")

    # إصلاح app.py
    if os.path.exists("app.py"):
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()

        # إصلاح المشكلة الأساسية
        content = re.sub(
            r"is_deleted\s*=\s*\(\s*False\)\.count\(\),",
            "is_deleted=False).count(),",
            content,
        )

        with open("app.py", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ تم إصلاح app.py")

    # إصلاح fix_all_issues.py
    if os.path.exists("fix_all_issues.py"):
        with open("fix_all_issues.py", "r", encoding="utf-8") as f:
            content = f.read()

        # إصلاح السلسلة النصية المكسورة
        content = re.sub(
            r'content\s*=\s*\(\s*content\.replace\("True, check\s*=\s*\(\s*True\)"\s*,.*?\)\s*\)',
            'content = content.replace("True, check=True)", "capture_output=True, check=True)")',
            content,
            flags=re.DOTALL,
        )

        with open("fix_all_issues.py", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ تم إصلاح fix_all_issues.py")

    # إصلاح ultimate_auto_sync.py
    if os.path.exists("ultimate_auto_sync.py"):
        with open("ultimate_auto_sync.py", "r", encoding="utf-8") as f:
            lines = f.readlines()

        # إصلاح المسافات البادئة والكود المكسور
        fixed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]

            # البحث عن الكود المكسور وإصلاحه
            if "try:" in line and i < len(lines) - 1:
                fixed_lines.append(line)
                # التحقق من السطر التالي
                next_line = lines[i + 1] if i + 1 < len(lines) else ""
                if "subprocess.run" in next_line or "pass" in next_line:
                    if not next_line.strip().startswith("    "):
                        # إضافة المسافات البادئة الصحيحة
                        fixed_lines.append("    " + next_line.lstrip())
                    else:
                        fixed_lines.append(next_line)
                    i += 1
                else:
                    fixed_lines.append("    pass\n")
            else:
                fixed_lines.append(line)
            i += 1

        # إصلاح الكود المكسور
        content = "".join(fixed_lines)
        content = re.sub(
            r"capture_output\s*=\s*\(\s*capture_output,\s*check\s*=\s*\(\s*True\)",
            "capture_output=True, check=True",
            content,
        )

        with open("ultimate_auto_sync.py", "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ تم إصلاح ultimate_auto_sync.py")

    # إصلاح الملفات الأخرى
    for filename in ["ultimate_flake8_fixer.py", "ultimate_flake8_killer.py"]:
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read()

            # إصلاح السلاسل النصية المكسورة
            content = re.sub(r'"\s*=\s*\(\s*="\s*\)', '" =="', content)

            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✅ تم إصلاح {filename}")

    print("\n🎉 تم إصلاح جميع الأخطاء!")


if __name__ == "__main__":
    fix_all_files()
