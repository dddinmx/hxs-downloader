# -*- coding: utf-8 -*-
# author: dddinmx

import requests
import os
import time
from bs4 import BeautifulSoup
from ebooklib import epub
import concurrent.futures
from tqdm import tqdm
import zipfile

# 控制台颜色
green = "\033[1;32m"
red = "\033[1;31m"
dark_gray = "\033[1;30m"
light_red = "\033[91m"
reset = "\033[0;0m"

def safe_print(*args, **kwargs):
    print(*args, **kwargs)

def download_image(session, img_url, save_path, retries=3):
    for attempt in range(retries):
        try:
            with session.get(img_url, stream=True, timeout=15) as response:
                if response.status_code == 200:
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(2048):
                            f.write(chunk)
                    return True
                else:
                    print(f"  图片请求失败，状态码 {response.status_code}，第{attempt+1}次重试。")
        except Exception as e:
            print(f"  图片下载异常，第{attempt+1}次重试。异常: {e}")
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    print(f"  图片多次尝试失败: {os.path.basename(save_path)}")
    return False

def download_images_concurrently(session, img_urls, save_dir, max_workers=2):
    os.makedirs(save_dir, exist_ok=True)
    tasks = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for img_idx, img_url in enumerate(img_urls, start=1):
            img_name = f"{img_idx:02d}.jpg"
            img_path = os.path.join(save_dir, img_name)
            future = executor.submit(download_image, session, img_url, img_path)
            futures.append(future)

        for _ in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc=f"", ncols=70):
            pass

def zip_downloaded_folder(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, os.path.dirname(folder_path))
                zipf.write(abs_path, rel_path)

def cepub(root_dir, output_epub, title, cover_image_path):
    book = epub.EpubBook()
    book.set_identifier('iddddinmx')
    book.set_title(title)
    book.set_language('zh')
    book.add_author('None')

    book.spine = ['nav']
    book.toc = []

    if cover_image_path and os.path.isfile(cover_image_path):
        with open(cover_image_path, 'rb') as f:
            cover_content = f.read()
        book.set_cover("cover.jpg", cover_content)
        safe_print("✅ 已设置封面")

    chapter_id = 0
    for folder_name in sorted(os.listdir(root_dir)):
        folder_path = os.path.join(root_dir, folder_name)
        if not os.path.isdir(folder_path):
            continue

        chapter_title = f"第{folder_name}话"
        section_pages = []

        for idx, file_name in enumerate(sorted(os.listdir(folder_path)), start=1):
            if not file_name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue

            image_path = os.path.join(folder_path, file_name)
            ext = os.path.splitext(file_name)[1].lower()
            img_id = f"img_{chapter_id}_{idx}"
            img_filename = f"images/{img_id}{ext}"

            with open(image_path, 'rb') as f:
                img_item = epub.EpubItem(
                    uid=img_id,
                    file_name=img_filename,
                    media_type=f'image/{ext[1:]}',
                    content=f.read()
                )
            book.add_item(img_item)

            page = epub.EpubHtml(
                title=f"{chapter_title} - 第{idx}页",
                file_name=f"{chapter_id}_{idx}.xhtml",
                lang='zh'
            )
            page.content = f'<html><body><img src="{img_filename}" alt="page {idx}" style="max-width:100%;height:auto;"/></body></html>'
            book.add_item(page)
            book.spine.append(page)
            section_pages.append(page)

        if section_pages:
            book.toc.append((epub.Section(chapter_title), section_pages))

        chapter_id += 1

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    safe_print("✅ 成功添加章节与导航")

    epub.write_epub(output_epub, book)
    safe_print("✅ EPUB 写入完成")

    if os.path.exists(cover_image_path):
        os.remove(cover_image_path)

def main():
    url = input("\n输入漫画地址: ")
    cid = url.strip('/').split('/')[-1]
    cover_url = f"https://www.wzd1.cc/static/upload/book/{cid}/cover.jpg"
    base_url = "https://mxs12.cc"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    response = requests.get(url, timeout=5)
    soup = BeautifulSoup(response.text, 'html.parser')
    title = soup.find('h1').text.strip()

    links = soup.select('ul#detail-list-select li a')
    chapter_urls = [base_url + a['href'] for a in links]

    response = requests.get(cover_url, timeout=10)
    if response.status_code == 200:
        with open('cover.jpg', 'wb') as f:
            f.write(response.content)

    with requests.Session() as session:
        for idx, url in enumerate(chapter_urls, start=1):
            folder_name = f"{idx:02d}"
            save_dir = os.path.join(title, folder_name)

            safe_print("\n" + green + "[+] " + reset + save_dir)

            try:
                response = session.get(url, timeout=10, headers=headers)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                img_tags = soup.find_all('img', class_='lazy')
                img_urls = [img['data-original'] for img in img_tags if img.has_attr('data-original')]

                download_images_concurrently(session, img_urls, save_dir)
            except Exception as e:
                safe_print(f"章节访问失败: {url} 错误: {e}")
            safe_print("✅" + " success")

    safe_print("\n" + green + "[+] " + reset + "「下载完成」")
    #safe_print("\n" + green + "[+] " + reset + "开始生成EPUB...")
    #cepub(root_dir=title, output_epub=f"{title}.epub", title=title, cover_image_path='cover.jpg')
    #safe_print("✅ EPUB 生成成功")
    zip_path = f"{title}.zip"
    zip_downloaded_folder(title, zip_path)
    safe_print(f"✅ 已压缩为: {zip_path}")

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = red + r"""
      █████╗ ██████╗ 
     ██╔══██╗██╔══██╗ 
     ███████║██████╔╝  
     ██╔══██║██╔═══╝ 
     ██║  ██║██║  
     ╚═╝  ╚═╝╚═╝ 
    """ + reset
    safe_print(banner)
    safe_print("      author by " + light_red + "dddinmx" + reset + "\n" + dark_gray + "      Github: https://github.com/dddinmx" + reset)
    safe_print("     「漫画获取」「漫小肆韓漫」" + red + "「18+」" + reset + " https://mxs12.cc" + reset)
    main()
