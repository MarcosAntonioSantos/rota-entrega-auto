import sys
# reuse render logic
src = open(r'C:\Users\Windows 11\AppData\Local\Temp\opencode\render_model2.py', encoding='utf-8').read()
# remove the hardcoded EOF artifact by exec with argv
import runpy
# Instead, exec with modified sys.argv
sys.argv = ['render_report.py', sys.argv[1], sys.argv[2]]
exec(compile(src, 'render_model2.py', 'exec'))