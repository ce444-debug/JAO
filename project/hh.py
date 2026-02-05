import os

def export_project_structure(root_dir, output_file, exclude_dirs=('.idea', '__pycache__', '.git')):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Project Structure:\n")
        f.write("================\n\n")
        # Генерируем структуру
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            level = root.replace(root_dir, '').count(os.sep)
            indent = '│   ' * (level - 1) + '├── ' if level > 0 else ''
            f.write(f"{indent}{os.path.basename(root)}/\n")
            for file in files:
                if file.endswith('.py'):  # Только .py файлы
                    f.write(f"{'│   ' * level}├── {file}\n")
        f.write("\nFile Contents:\n")
        f.write("=============\n\n")
        # Добавляем содержимое файлов
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    f.write(f"\n--- {file_path} ---\n")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as py_file:
                            f.write(py_file.read())
                        f.write("\n")
                    except Exception as e:
                        f.write(f"Error reading file: {e}\n")

if __name__ == "__main__":
    export_project_structure('.', 'project_structure_with_files.txt')