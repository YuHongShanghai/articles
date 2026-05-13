import os

d = '/Users/yuhong/Desktop/articles/opengl教程/publish'
prefix = '【从零开始学 OpenGL：现代图形渲染实战】'

files = os.listdir(d)
renamed = 0
for f in files:
    if f.endswith('.md') and not f.startswith('【'):
        old = os.path.join(d, f)
        new = os.path.join(d, prefix + f)
        os.rename(old, new)
        renamed += 1

with open('/Users/yuhong/Desktop/articles/opengl教程/rename_result.txt', 'w') as out:
    out.write(f"Total renamed: {renamed}\n\nFinal file list:\n")
    for f in sorted(os.listdir(d)):
        out.write(f"  {f}\n")
