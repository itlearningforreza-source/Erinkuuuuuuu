import os

for root, dirs, files in os.walk('/home/rezaahmadkhairuddin/ERIN/docs/design'):
    level = root.replace('/home/rezaahmadkhairuddin/ERIN/docs/design', '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in files:
        print(f'{subindent}{file}')

print()

for root, dirs, files in os.walk('/home/rezaahmadkhairuddin/ERIN/docs/adr'):
    level = root.replace('/home/rezaahmadkhairuddin/ERIN/docs/adr', '').count(os.sep)
    indent = ' ' * 2 * level
    print(f'{indent}{os.path.basename(root)}/')
    subindent = ' ' * 2 * (level + 1)
    for file in files:
        print(f'{subindent}{file}')