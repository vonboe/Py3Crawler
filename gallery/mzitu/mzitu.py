# -*- coding:UTF-8  -*-
"""
https://www.mzitu.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import traceback
from pyquery import PyQuery as pq
from common import *


# 获取图集首页
def get_index_page():
    index_url = "https://www.mzitu.com/"
    index_response = net.http_request(index_url, method="GET")
    result = {
        "max_album_id": None,  # 最新图集id
    }
    if index_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(index_response.status))
    index_response_content = index_response.data.decode(errors="ignore")
    album_id_find = re.findall('<a href="https://www.mzitu.com/(\d+)', index_response_content)
    if len(album_id_find) == 0:
        raise crawler.CrawlerException("页面匹配图集id失败\n%s" % index_response_content)
    result["max_album_id"] = max(list(map(int, album_id_find)))
    return result


# 获取指定id的图集
def get_album_page(album_id):
    page_count = max_page_count = 1
    result = {
        "album_title": "",  # 图集标题
        "photo_url_list": [],  # 全部图片地址
        "is_delete": False,  # 是否已删除
    }
    while page_count <= max_page_count:
        if page_count == 1:
            album_pagination_url = "https://www.mzitu.com/%s" % album_id
        else:
            album_pagination_url = "https://www.mzitu.com/%s/%s" % (album_id, page_count)
        album_pagination_response = net.http_request(album_pagination_url, method="GET", is_auto_redirect=False)
        if page_count == 1 and album_pagination_response.status in [301, 404]:
            result["is_delete"] = True
            return result
        elif album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException("第%s页" % page_count + crawler.request_failre(album_pagination_response.status))
        album_pagination_response_content = album_pagination_response.data.decode(errors="ignore")
        if page_count == 1:
            # 获取图集标题
            album_title = pq(album_pagination_response_content).find(".main-title").html()
            if not album_title:
                raise crawler.CrawlerException("页面截取标题失败\n%s" % album_pagination_response_content)
            max_page_count = pq(album_pagination_response_content).find(".pagenavi span").eq(-2).html()
            result["album_title"] = album_title.strip()
            # 获取总页数
            if not crawler.is_integer(max_page_count):
                raise crawler.CrawlerException("页面截取总页数失败\n%s" % album_pagination_response_content)
            max_page_count = int(max_page_count)
        # 获取图集图片地址
        photo_list_selector = pq(album_pagination_response_content).find(".main-image img")
        if photo_list_selector.length == 0:
            if pq(album_pagination_response_content).find(".main-image").length == 0:
                raise crawler.CrawlerException("第%s页页面截取图片列表失败\n%s" % (page_count, album_pagination_response_content))
        for photo_index in range(0, photo_list_selector.length):
            result["photo_url_list"].append(photo_list_selector.eq(photo_index).attr("src"))
        page_count += 1
    return result


class MZiTu(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

    def main(self):
        # 解析存档文件，获取上一次的album id
        album_id = 1
        if os.path.exists(self.save_data_path):
            file_save_info = file.read_file(self.save_data_path)
            if not crawler.is_integer(file_save_info):
                log.error("存档内数据格式不正确")
                tool.process_exit()
            album_id = int(file_save_info)
        temp_path = ""

        try:
            # 获取图集首页
            try:
                index_response = get_index_page()
            except crawler.CrawlerException as e:
                log.error("图集首页解析失败，原因：%s" % e.message)
                raise

            log.step("最新图集id：%s" % index_response["max_album_id"])

            while album_id <= index_response["max_album_id"]:
                if not self.is_running():
                    tool.process_exit(0)
                log.step("开始解析图集%s" % album_id)

                # 获取图集
                try:
                    album_response = get_album_page(album_id)
                except crawler.CrawlerException as e:
                    log.error("图集%s解析失败，原因：%s" % (album_id, e.message))
                    raise

                if album_response["is_delete"]:
                    log.step("图集%s不存在，跳过" % album_id)
                    album_id += 1
                    continue

                log.trace("图集%s《%s》解析的全部图片：%s" % (album_id, album_response["album_title"], album_response["photo_url_list"]))
                log.step("图集%s《%s》解析获取%s张图片" % (album_id, album_response["album_title"], len(album_response["photo_url_list"])))

                photo_index = 1
                # 过滤标题中不支持的字符
                temp_path = album_path = os.path.join(self.photo_download_path, "%06d %s" % (album_id, path.filter_text(album_response["album_title"])))
                thread_list = []
                for photo_url in album_response["photo_url_list"]:
                    if not self.is_running():
                        break
                    log.step("图集%s《%s》开始下载第%s张图片 %s" % (album_id, album_response["album_title"], photo_index, photo_url))

                    # 开始下载
                    file_path = os.path.join(album_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url)))
                    thread = Download(self, file_path, photo_url, photo_index)
                    thread.start()
                    thread_list.append(thread)
                    photo_index += 1

                # 等待所有线程下载完毕
                for thread in thread_list:
                    thread.join()
                    save_file_return = thread.get_result()
                    if self.is_running() and save_file_return["status"] != 1:
                        log.error("图集%s《%s》第%s张图片 %s 下载失败，原因：%s" % (album_id, album_response["album_title"], thread.photo_index, thread.photo_url, crawler.download_failre(save_file_return["code"])))
                if self.is_running():
                    log.step("图集%s《%s》全部图片下载完毕" % (album_id, album_response["album_title"]))
                else:
                    tool.process_exit(0)

                # 图集内图片全部下载完毕
                temp_path = ""  # 临时目录设置清除
                self.total_photo_count += photo_index - 1  # 计数累加
                album_id += 1  # 设置存档记录
        except SystemExit as se:
            if se.code == 0:
                log.step("提前退出")
            else:
                log.error("异常退出")
            # 如果临时目录变量不为空，表示某个图集正在下载中，需要把下载了部分的内容给清理掉
            if temp_path:
                path.delete_dir_or_file(temp_path)
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 重新保存存档文件
        file.write_file(str(album_id), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)
        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, main_thread, file_path, photo_url, photo_index):
        crawler.DownloadThread.__init__(self, [], main_thread)
        self.file_path = file_path
        self.photo_url = photo_url
        self.photo_index = photo_index
        self.result = None

    def run(self):
        self.result = net.save_net_file(self.photo_url, self.file_path, header_list={"Referer": "https://www.mzitu.com/"})
        self.notify_main_thread()

    def get_result(self):
        return self.result


if __name__ == "__main__":
    MZiTu().main()
