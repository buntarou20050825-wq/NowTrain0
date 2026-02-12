import os

# 除外したいディレクトリ・ファイル
IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.venv', 'dist', 'build', 'coverage'}
IGNORE_FILES = {'package-lock.json', 'yarn.lock', 'merge_code.py', '.DS_Store', 'all_code.txt'}
# 含めたい拡張子
TARGET_EXTS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.yml', '.yaml', '.md', '.html', '.css', '.txt'}

def merge_files(output_file='all_code.txt'):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for root, dirs, files in os.walk('.'):
            # 除外ディレクトリをスキップ
            dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
            
            for file in files:
                if file in IGNORE_FILES:
                    continue
                
                ext = os.path.splitext(file)[1]
                if ext in TARGET_EXTS:
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as infile:
                            outfile.write(f"\n\n{'='*20}\n")
                            outfile.write(f"FILE PATH: {file_path}\n")
                            outfile.write(f"{'='*20}\n")
                            outfile.write(infile.read())
                    except Exception as e:
                        print(f"Skipping {file_path}: {e}")

if __name__ == "__main__":
    merge_files()
    print("完了: all_code.txt に全コードを結合しました。")