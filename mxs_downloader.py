# -*- coding: utf-8 -*-
# author: dddinmx

import requests
import os
import time
from bs4 import BeautifulSoup
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
                    print("\n"+red + "[+] " + reset+f"图片请求失败，第{attempt+1}次重试。")
        except Exception as e:
            print("\n"+red + "[+] " + reset+f"图片请求失败，第{attempt+1}次重试。")
        if attempt < retries - 1:
            time.sleep(2 ** attempt)
    print("\n"+red + "[+] " + reset+f"图片多次尝试失败: {os.path.basename(save_path)}")
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

            for attempt in range(3):
                try:
                    response = session.get(url, timeout=10, headers=headers)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.text, 'html.parser')
                    img_tags = soup.find_all('img', class_='lazy')
                    img_urls = [img['data-original'] for img in img_tags if img.has_attr('data-original')]

                    download_images_concurrently(session, img_urls, save_dir)
                    print(f"\r✅ 下载成功" + " " * 20)
                    break  # 成功则跳出循环
                except Exception as e:
                    if attempt < 2:
                        time.sleep(2 ** attempt)
                        print("\n"+red + "[+] " + reset +f"重试 {attempt + 1}/3：{save_dir} 请求失败，重试中...")
                    else:
                        print("\n"+red + "[+] " + reset + "章节请求超时")

    safe_print("\n" + green + "[+] " + reset + "「下载完成」")
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
