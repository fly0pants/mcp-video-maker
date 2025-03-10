import os
import shutil
import argparse
from pathlib import Path


def setup_directories():
    """创建必要的目录结构"""
    directories = [
        "temp",
        "temp/videos",
        "temp/audios",
        "temp/scripts",
        "temp/thumbnails",
        "output",
        "output/videos",
        "output/audios",
        "output/scripts",
        "output/thumbnails",
        "logs",
        "assets"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")


def create_env_file():
    """创建.env文件（如果不存在）"""
    if not os.path.exists(".env"):
        shutil.copy(".env.example", ".env")
        print("Created .env file from .env.example")
    else:
        print(".env file already exists")


def clean_temp_files():
    """清理临时文件"""
    temp_dir = Path("temp")
    if temp_dir.exists():
        for item in temp_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        print("Cleaned temporary files")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="初始化TikTok风格短视频多代理协作生成系统")
    parser.add_argument("--clean", action="store_true", help="清理临时文件")
    
    args = parser.parse_args()
    
    if args.clean:
        clean_temp_files()
    else:
        setup_directories()
        create_env_file()
        
    print("初始化完成！") 