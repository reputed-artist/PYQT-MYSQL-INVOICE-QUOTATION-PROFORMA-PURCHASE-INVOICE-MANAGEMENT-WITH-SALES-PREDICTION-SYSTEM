# -*- coding: utf-8 -*-
"""Fix build_exe.bat script structure."""

path = 'build_exe.bat'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the problematic sections
# 1. Remove the standalone 'pause' after [7/7] section
# 2. Remove the duplicate PyInstaller command
# 3. Add a final pause at the very end

output = []
in_pause_section = False
in_pyinstaller_section = False
skip_lines = set()

for i, line in enumerate(lines):
    # Skip the standalone pause (it's after the [7/7] section)
    if line.strip() == 'pause' and i > 100 and i < 110:
        continue
    
    # Skip the duplicate PyInstaller section (after the first pause)
    if 'Command: python -m PyInstaller' in line:
        in_pyinstaller_section = True
        continue
    if in_pyinstaller_section and 'python -m PyInstaller' in line:
        in_pyinstaller_section = False
        continue
    if in_pyinstaller_section:
        if 'ERROR: PyInstaller build failed' in line:
            # Keep this error handling
            in_pyinstaller_section = False
            skip_lines.add(i)
        elif line.strip() == 'pause':
            # Keep this pause after error
            continue
        elif line.strip() == '@':
            # Keep the end marker
            continue
        if i in skip_lines:
            continue
        if 'echo  Command: python' in line:
            continue
        if 'echo.' in line and 'PyInstaller build completed' not in line:
            continue
        if 'echo  PyInstaller build completed successfully.' in line:
            continue
        if 'echo.' in line and i > 120:
            continue
        output.append(line)
        continue
    
    output.append(line)

# Add a final pause at the end
output.append('@pause\n')

with open(path, 'w', encoding='utf-8', newline='') as f:
    f.writelines(output)

print('build_exe.bat fixed with final pause')
