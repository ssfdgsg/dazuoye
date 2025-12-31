import requests
from pyquery import PyQuery as pq
import re
import csv
from datetime import datetime

def doulist_crawler(url):
    """
    爬取豆瓣电影列表页面，提取电影详细信息
    
    参数:
        url (str): 豆瓣豆列的电影列表页面URL
        例如: https://www.douban.com/doulist/240962/
    
    返回:
        list: 包含每部电影详细信息的字典组成的列表
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://www.douban.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0',
    }
    
    try:
        print(f"📡 正在请求：{url}")
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        print(f"📊 响应状态码：{response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ 请求失败，状态码：{response.status_code}")
            return []
        
        print(f"✅ 请求成功，响应大小：{len(response.text)} 字节")
        
        doc = pq(response.text)
        doulist_item_doc = doc(".doulist-item")
        
        print(f"🔍 找到 {len(doulist_item_doc)} 部电影")
        
        if len(doulist_item_doc) == 0:
            print("⚠️  未找到电影项，可能页面结构已变化或被反爬虫拦截")
            # 保存响应内容用于调试
            with open('debug_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            print("💾 已保存响应内容到 debug_response.html 用于调试")
            return []
        
        for item in doulist_item_doc.items():
            item_dict = {}
            
            # 初始化变量
            director = None
            starring = None
            genre = None
            region = None
            year = None
            rating_nums = None
            rating_count = None
            
            # 提取基本信息
            detail_url = item(".title a").attr("href")
            title = item(".title a").text()
            rating_nums = item(".rating_nums").text()
            
            # 提取评分数量
            rating_count_text = item('.rating span:contains("人评价")').text()
            if rating_count_text:
                match = re.search(r'\d+', rating_count_text)
                if match:
                    rating_count = int(match.group(0))
            
            # 提取详细信息
            lines = item('div.abstract').text().split('\n')
            for line in lines:
                line = line.strip()
                if '导演' in line:
                    director = line.split('导演:')[-1].strip()
                elif '主演' in line:
                    starring = line.split('主演:')[-1].strip()
                elif '类型' in line:
                    genre = line.split('类型:')[-1].strip()
                elif '制片国家/地区' in line:
                    region = line.split('制片国家/地区:')[-1].strip()
                elif '年份' in line:
                    year = line.split('年份:')[-1].strip()
            
            # 组装字典
            item_dict['title'] = title
            item_dict['director'] = director
            item_dict['starring'] = starring
            item_dict['genre'] = genre
            item_dict['region'] = region
            item_dict['year'] = year
            item_dict['rating'] = rating_nums
            item_dict['rating_count'] = rating_count
            item_dict['detail_url'] = detail_url
            
            doulist.append(item_dict)
        
        return doulist
    
    except Exception as e:
        print(f"爬虫出错：{str(e)}")
        return []


def save_to_csv(movie_list, filename=None):
    """
    将电影列表保存为 CSV 文件
    
    参数:
        movie_list (list): 电影信息字典列表
        filename (str): 输出文件名，默认为带时间戳的文件名
    """
    if not movie_list:
        print("没有数据可保存")
        return
    
    if filename is None:
        filename = f"电影列表_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # CSV 列名
    fieldnames = ['title', 'director', 'starring', 'genre', 'region', 'year', 'rating', 'rating_count', 'detail_url']
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(movie_list)
        
        print(f"✅ CSV 数据已保存到文件：{filename}")
        print(f"📊 共爬取 {len(movie_list)} 部电影")
    
    except Exception as e:
        print(f"保存 CSV 文件失败：{str(e)}")


if __name__ == "__main__":
    # 爬取豆瓣电影列表
    url = 'https://www.douban.com/doulist/240962/'
    print(f"🚀 开始爬虫程序...")
    print(f"正在爬取：{url}\n")
    
    movie_list = doulist_crawler(url)
    
    if movie_list:
        # 保存为 CSV
        save_to_csv(movie_list)
        
        # 打印前几条数据预览
        print("\n📋 数据预览（前3条）：")
        for i, movie in enumerate(movie_list[:3], 1):
            print(f"\n{i}. {movie['title']}")
            print(f"   导演：{movie['director']}")
            print(f"   主演：{movie['starring']}")
            print(f"   类型：{movie['genre']}")
            print(f"   评分：{movie['rating']}")
    else:
        print("❌ 爬虫未获取到数据")
