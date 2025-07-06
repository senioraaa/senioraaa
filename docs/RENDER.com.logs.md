2025-07-06T00:51:37.812680228Z     return _bootstrap._gcd_import(name[level:], package, level)
2025-07-06T00:51:37.812686888Z   File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
2025-07-06T00:51:37.812861262Z   File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
2025-07-06T00:51:37.812912272Z   File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
2025-07-06T00:51:37.812997284Z   File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
2025-07-06T00:51:37.813039725Z   File "<frozen importlib._bootstrap_external>", line 879, in exec_module
2025-07-06T00:51:37.813171828Z   File "<frozen importlib._bootstrap_external>", line 1017, in get_code
2025-07-06T00:51:37.81326758Z   File "<frozen importlib._bootstrap_external>", line 947, in source_to_code
2025-07-06T00:51:37.813304971Z   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
2025-07-06T00:51:37.813378772Z   File "/opt/render/project/src/app.py", line 4149
2025-07-06T00:51:37.813382542Z     def safe_add_column(table, column, column_type):
2025-07-06T00:51:37.813385093Z IndentationError: expected an indented block after 'for' statement on line 4148
2025-07-06T00:51:39.59134889Z ==> Exited with status 1
2025-07-06T00:51:39.608621008Z ==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
2025-07-06T00:51:46.222621343Z ==> Running 'gunicorn app:app'
2025-07-06T00:51:47.820451573Z Traceback (most recent call last):
2025-07-06T00:51:47.820479774Z   File "/opt/render/project/src/.venv/bin/gunicorn", line 8, in <module>
2025-07-06T00:51:47.820550795Z     sys.exit(run())
2025-07-06T00:51:47.820556056Z   File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/wsgiapp.py", line 67, in run
2025-07-06T00:51:47.820614647Z     WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()
2025-07-06T00:51:47.820619237Z   File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/base.py", line 236, in run
2025-07-06T00:51:47.82076191Z     super().run()
2025-07-06T00:51:47.82077208Z   File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/base.py", line 72, in run
2025-07-06T00:51:47.820833761Z     Arbiter(self).run()
2025-07-06T00:51:47.820838441Z   File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/arbiter.py", line 58, in __init__
2025-07-06T00:51:47.820948244Z     self.setup(app)
2025-07-06T00:51:47.820952794Z   File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/arbiter.py", line 118, in setup
2025-07-06T00:51:47.821034206Z     self.app.wsgi()
2025-07-06T00:51:47.821039356Z   File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/base.py", line 67, in wsgi
2025-07-06T00:51:47.821111677Z     self.callable = self.load()
2025-07-06T00:51:47.821116467Z   File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/wsgiapp.py", line 58, in load
2025-07-06T00:51:47.821214109Z     return self.load_wsgiapp()
2025-07-06T00:51:47.82121974Z   File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/wsgiapp.py", line 48, in load_wsgiapp
2025-07-06T00:51:47.821286541Z     return util.import_app(self.app_uri)
2025-07-06T00:51:47.821291641Z   File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/util.py", line 371, in import_app
2025-07-06T00:51:47.821435864Z     mod = importlib.import_module(module)
2025-07-06T00:51:47.821443514Z   File "/opt/render/project/python/Python-3.10.11/lib/python3.10/importlib/__init__.py", line 126, in import_module
2025-07-06T00:51:47.821496555Z     return _bootstrap._gcd_import(name[level:], package, level)
2025-07-06T00:51:47.821503215Z   File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
2025-07-06T00:51:47.821617098Z   File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
2025-07-06T00:51:47.821685529Z   File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
2025-07-06T00:51:47.821754801Z   File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
2025-07-06T00:51:47.821798862Z   File "<frozen importlib._bootstrap_external>", line 879, in exec_module
2025-07-06T00:51:47.821889804Z   File "<frozen importlib._bootstrap_external>", line 1017, in get_code
2025-07-06T00:51:47.821963935Z   File "<frozen importlib._bootstrap_external>", line 947, in source_to_code
2025-07-06T00:51:47.822019376Z   File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
2025-07-06T00:51:47.822091438Z   File "/opt/render/project/src/app.py", line 4149
2025-07-06T00:51:47.822096758Z     def safe_add_column(table, column, column_type):
2025-07-06T00:51:47.822099578Z IndentationError: expected an indented block after 'for' statement on line 4148
2025-07-06T00:54:29.604655153Z 127.0.0.1 - - [06/Jul/2025:00:54:29 +0000] "HEAD /ping HTTP/1.1" 200 0 "https://senioraa.onrender.com/ping" "Mozilla/5.0+(compatible; UptimeRobot/2.0; http://www.uptimerobot.com/)"
