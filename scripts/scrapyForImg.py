import requests
import csv
import os
import time
import re
from bs4 import BeautifulSoup
import pandas as pd


class MovieCoverDownloader:
    def __init__(self, csv_file, img_folder='img'):
        """
        初始化电影封面下载器

        Args:
            csv_file: CSV文件路径
            img_folder: 图片保存文件夹
        """
        self.csv_file = csv_file
        self.img_folder = img_folder
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.douban.com',
        }

        # 创建图片文件夹
        os.makedirs(self.img_folder, exist_ok=True)

    def parse_csv_data(self, row):
        """
        解析CSV行数据，提取电影名称和ID

        根据你提供的CSV格式，电影名称在"original_title"列，ID在"id"列
        但实际列名可能不同，这里尝试自动检测
        """
        try:
            # 尝试常见列名
            if 'original_title' in row:
                movie_name = row['original_title']
            elif 'title' in row:
                movie_name = row['title']
            elif 'name' in row:
                movie_name = row['name']
            else:
                # 如果找不到标准列名，尝试获取第一个非空字符串列作为电影名
                for key, value in row.items():
                    if value and isinstance(value, str) and len(value.strip()) > 3:
                        movie_name = value.strip()
                        break
                else:
                    return None, None

            # 获取ID
            if 'id' in row:
                movie_id = str(row['id'])
            elif 'movie_id' in row:
                movie_id = str(row['movie_id'])
            else:
                # 如果没有ID列，使用电影名生成一个简单的ID
                movie_id = str(hash(movie_name))

            return movie_name.strip(), movie_id
        except Exception as e:
            print(f"解析数据时出错: {e}")
            return None, None

    def search_douban(self, movie_name):
        """
        从豆瓣搜索结果页直接提取第一个电影海报的URL（匹配s_ratio_poster的WebP格式）

        Args:
            movie_name: 电影名称

        Returns:
            电影封面URL，如果未找到则返回None
        """
        try:
            # 编码电影名称，使用标准的豆瓣电影搜索URL（cat=1002优先）
            encoded_name = requests.utils.quote(movie_name)
            search_url = f'https://www.douban.com/search?cat=1002&q={encoded_name}'

            # 发送搜索请求
            response = requests.get(search_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            # 解析HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # 核心逻辑：匹配搜索结果中第一个包含s_ratio_poster的图片（豆瓣电影海报标识）
            # 正则匹配：doubanio.com/view/photo/s_ratio_poster/ 路径的图片
            img_tag = soup.find('img', src=re.compile(r'doubanio\.com\/view\/photo\/s_ratio_poster\/'))
            if img_tag and 'src' in img_tag.attrs:
                img_url = img_tag['src']
                # 确保是WebP格式（豆瓣海报默认是WebP）
                if img_url.lower().endswith('.webp'):
                    return img_url

            # 备用逻辑：如果上面没找到，匹配所有豆瓣图片并筛选第一个WebP格式的海报
            img_tags = soup.find_all('img', src=re.compile(r'doubanio\.com'))
            for tag in img_tags:
                img_url = tag.get('src', '')
                if 's_ratio_poster' in img_url and img_url.lower().endswith('.webp'):
                    return img_url

            return None
        except requests.RequestException as e:
            print(f"搜索电影 '{movie_name}' 时网络错误: {e}")
            return None
        except Exception as e:
            print(f"搜索电影 '{movie_name}' 时出错: {e}")
            return None

    def download_image(self, img_url, filepath):
        """
        下载图片并保存（支持WebP格式，排除GIF）

        Args:
            img_url: 图片URL
            filepath: 保存路径

        Returns:
            bool: 是否成功下载
        """
        try:
            # 第一步：判断URL是否为GIF格式（直接过滤）
            if img_url.lower().endswith('.gif') or 'gif' in img_url.lower().split('?')[0]:
                print(f"跳过GIF图片: {img_url}")
                return False

            response = requests.get(img_url, headers=self.headers, timeout=30, stream=True)
            response.raise_for_status()

            # 第二步：检查响应的Content-Type，排除GIF并验证图片类型
            content_type = response.headers.get('content-type', '').lower()
            if 'image/gif' in content_type or 'gif' in content_type:
                print(f"响应内容为GIF格式，跳过")
                return False
            if 'image' not in content_type:
                print(f"下载的不是图片: {content_type}")
                return False

            # 保存图片（支持WebP格式）
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 检查文件大小（WebP格式图片可能较小，调整阈值为512字节）
            file_size = os.path.getsize(filepath)
            if file_size < 512:  # 小于512字节可能是错误页面
                os.remove(filepath)
                print(f"文件过小（{file_size}字节），已删除")
                return False

            return True

        except requests.RequestException as e:
            print(f"下载图片时网络错误: {e}")
            return False
        except Exception as e:
            print(f"下载图片时出错: {e}")
            return False

    def process_movies(self):
        """
        处理所有电影，下载封面图片（保存为WebP格式）
        """
        success_count = 0
        skip_count = 0
        fail_count = 0

        try:
            # 尝试不同的编码方式读取CSV
            encodings = ['utf-8', 'gbk', 'latin-1']
            df = None

            for encoding in encodings:
                try:
                    df = pd.read_csv(self.csv_file, encoding=encoding)
                    print(f"使用 {encoding} 编码成功读取CSV文件")
                    break
                except UnicodeDecodeError:
                    continue
                except Exception as e:
                    print(f"使用 {encoding} 编码读取CSV时出错: {e}")
                    continue

            if df is None:
                print("无法读取CSV文件，请检查文件编码")
                return

            # 将DataFrame转换为字典列表
            movies = df.to_dict('records')
            total_movies = len(movies)

            print(f"共找到 {total_movies} 部电影")

            for i, row in enumerate(movies, 1):
                # 解析电影名称和ID
                movie_name, movie_id = self.parse_csv_data(row)

                if not movie_name or not movie_id:
                    print(f"跳过第 {i} 行: 无法解析电影信息")
                    fail_count += 1
                    continue

                # 检查图片是否已存在（WebP格式）
                img_path = os.path.join(self.img_folder, f"{movie_id}.webp")
                if os.path.exists(img_path):
                    print(f"[{i}/{total_movies}] 跳过: {movie_name} (ID: {movie_id}) - 图片已存在")
                    skip_count += 1
                    continue

                print(f"[{i}/{total_movies}] 处理: {movie_name} (ID: {movie_id})")

                # 搜索豆瓣获取封面URL
                print(f"  正在搜索豆瓣...")
                img_url = self.search_douban(movie_name)

                if not img_url:
                    print(f"  未找到封面图片")
                    # 尝试添加年份搜索
                    if 'release_date' in row and pd.notna(row['release_date']):
                        try:
                            year = str(row['release_date'])[:4]
                            new_search_name = f"{movie_name} {year}"
                            print(f"  尝试搜索: {new_search_name}")
                            img_url = self.search_douban(new_search_name)
                        except:
                            pass

                if not img_url:
                    print(f"  最终未找到封面图片")
                    fail_count += 1

                    # 避免请求过快
                    time.sleep(5)
                    continue

                print(f"  找到封面URL: {img_url}")

                # 下载图片（WebP格式）
                print(f"  正在下载图片...")
                if self.download_image(img_url, img_path):
                    print(f"  下载成功: {img_path}")
                    success_count += 1
                else:
                    print(f"  下载失败")
                    fail_count += 1

                # 添加延迟，避免被屏蔽
                time.sleep(2)  # 2秒延迟

                # 每10部电影添加额外延迟
                if i % 10 == 0:
                    print(f"已完成 {i} 部电影，休息5秒...")
                    time.sleep(5)

            print(f"\n处理完成！")
            print(f"成功: {success_count}, 跳过: {skip_count}, 失败: {fail_count}")

        except Exception as e:
            print(f"处理过程中出错: {e}")
            import traceback
            traceback.print_exc()

    def check_progress(self):
        """
        检查下载进度（适配WebP格式）
        """
        if not os.path.exists(self.img_folder):
            print("图片文件夹不存在")
            return 0

        img_files = [f for f in os.listdir(self.img_folder) if f.endswith('.webp')]
        print(f"已下载 {len(img_files)} 张图片")
        return len(img_files)


# 使用示例
if __name__ == "__main__":
    # 配置：固定为同目录下的tmdb_5000_movies.csv
    CSV_FILE = "tmdb_5000_movies.csv"
    IMG_FOLDER = "img"  # 图片保存文件夹

    # 创建下载器
    downloader = MovieCoverDownloader(CSV_FILE, IMG_FOLDER)

    # 检查当前进度
    current_count = downloader.check_progress()
    if current_count > 0:
        print(f"发现 {current_count} 张已下载图片，将从中断处继续...")

    # 开始处理
    downloader.process_movies()

    print("程序执行完毕！")