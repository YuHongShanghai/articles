#!/usr/bin/env python3
"""
批量替换 Markdown 中的本地图片路径为 Gitee 链接。
生成到 publish/ 目录，不修改原始文件。
"""
import os
import re
import shutil

GITEE_BASE = "https://gitee.com/yuhong1234/ffmpeg-player-tutorial/raw/master"
ARTICLES_DIR = os.path.join(os.path.dirname(__file__), '..')
OUTPUT_DIR = os.path.join(ARTICLES_DIR, 'publish')

def process_md(src_path, dst_path):
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换 ![xxx](images/yyy.png) → ![xxx](GITEE_BASE/images/yyy.png)
    new_content = re.sub(
        r'\(images/',
        f'({GITEE_BASE}/images/',
        content
    )

    count = content.count('(images/')
    with open(dst_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    return count

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    md_files = sorted([f for f in os.listdir(ARTICLES_DIR)
                       if f.endswith('.md') and os.path.isfile(os.path.join(ARTICLES_DIR, f))])

    total = 0
    for md in md_files:
        src = os.path.join(ARTICLES_DIR, md)
        dst = os.path.join(OUTPUT_DIR, md)
        count = process_md(src, dst)
        total += count
        status = f'({count} 张图片)' if count > 0 else '(无图片)'
        print(f'  ✓ {md}  {status}')

    print(f'\n完成！共处理 {len(md_files)} 个文件，替换 {total} 处图片链接')
    print(f'输出目录: {OUTPUT_DIR}')

if __name__ == '__main__':
    main()
