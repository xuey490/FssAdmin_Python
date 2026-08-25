import os
import shutil

def clear_pycache(root_path="."):
    for dirpath, dirnames, filenames in os.walk(root_path):
        if "__pycache__" in dirnames:
            cache_dir = os.path.join(dirpath, "__pycache__")
            shutil.rmtree(cache_dir)
            print(f"已删除：{cache_dir}")

if __name__ == "__main__":
    clear_pycache()
    print("所有 __pycache__ 清理完毕")