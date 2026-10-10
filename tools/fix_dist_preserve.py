# -*- coding: utf-8 -*-
"""Remove the line that deletes the dist folder from build_exe.bat."""

path = 'build_exe.bat'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the line that deletes dist folder
old_line = 'if exist dist rmdir /s /q dist\n'
new_line = '# dist folder is preserved - it contains images and resources\n'

if old_line in content:
    content = content.replace(old_line, new_line)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write(content)
    print('Fixed: dist folder is now preserved')
else:
    print('ERROR: Could not find the dist deletion line')
    # Show the area around [2/7]
    idx = content.find('[2/7]')
    if idx >= 0:
        print(repr(content[idx:idx+300]))
