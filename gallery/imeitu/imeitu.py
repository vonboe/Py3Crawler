# -*- coding:UTF-8  -*-
"""
https://imeitu.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import traceback
from common import *


# 获取指定一页图集
def get_latest_album_id():
    max_album_id = 0
    for category_type in [1, 2]:
        api_url = "https://api.shen100.com/api/dynamic/getCategoryDynamic"
        query_data = {
            "type": category_type,  # 1 图片， 2 视频
            "categoryId": "1",  # 最新
            "start": "1",
            "length": "1",
        }
        api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
        max_album_id = max(max_album_id, crawler.get_json_value(api_response.json_data, "data", "list", 0, "id", type_check=int))
    return max_album_id


# 获取指定图集
def get_album_page(album_id):
    api_url = "https://api.shen100.com/api/dynamic/getDynamicDetail"
    query_data = {
        "id": album_id,
    }
    api_response = net.http_request(api_url, method="GET", fields=query_data, json_decode=True)
    result = {
        "album_title": "",  # 作品标题
        "is_delete": False,  # 是否已删除
        "is_pending": False,  # 是否未审核
        "photo_url_list": [],  # 全部图片地址
        "video_url": None,  # 视频地址
    }
    if api_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(api_response.status))
    try:
        response_data = crawler.get_json_value(api_response.json_data, "data", type_check=dict)
    except crawler.CrawlerException:
        error_msg = crawler.get_json_value(api_response.json_data, "msg", default_value="", type_check=str)
        if error_msg == "该动态已被删除":
            result["is_delete"] = True
            return result
        elif error_msg == "该动态还未审核通过":
            result["is_pending"] = True
            return result
        raise
    # 图集类型（图片/视频）
    album_type = crawler.get_json_value(response_data, "type", original_data=api_response.json_data, type_check=int)
    if album_type == 1:  # 图片
        result["photo_url_list"] = crawler.get_json_value(response_data, "url", original_data=api_response.json_data, type_check=str).split(",")
    elif album_type == 2:  # 视频
        result["video_url"] = crawler.get_json_value(response_data, "url", original_data=api_response.json_data, type_check=str)
    else:
        raise crawler.CrawlerException("未知的图集类型\n%s" % api_response.json_data)
    # 获取作品标题
    result["album_title"] = crawler.get_json_value(response_data, "title", original_data=api_response.json_data, type_check=str)
    return result


class IMeitu(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_DOWNLOAD_VIDEO: True,
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
            # 获取最新图片/视频ID
            try:
                max_album_id = get_latest_album_id()
            except crawler.CrawlerException as e:
                log.error("最新作品ID解析失败，原因：%s" % e.message)
                raise
            log.step("最新作品ID：%s" % max_album_id)

            while album_id <= max_album_id:
                if not self.is_running():
                    tool.process_exit(0)
                log.step("开始解析作品%s" % album_id)

                try:
                    album_response = get_album_page(album_id)
                except crawler.CrawlerException as e:
                    log.error("作品%s解析失败，原因：%s" % (album_id, e.message))
                    raise

                if album_response["is_delete"]:
                    log.step("作品%s已删除，跳过" % album_id)
                elif album_response["is_pending"]:
                    log.error("作品%s审核未通过，跳过" % album_id)

                if self.is_download_photo and len(album_response["photo_url_list"]) > 0:
                    photo_index = 1
                    temp_path = album_path = os.path.join(self.photo_download_path, "%04d %s" % (album_id, path.filter_text(album_response["album_title"])))
                    for photo_url in album_response["photo_url_list"]:
                        log.step("开始下载作品%s第%s张图片 %s" % (album_id, photo_index, photo_url))

                        photo_file_path = os.path.join(album_path, "%02d.%s" % (photo_index, net.get_file_type(photo_url)))
                        save_file_return = net.save_net_file(photo_url, photo_file_path)
                        if save_file_return["status"] == 1:
                            log.step("作品%s第%s张图片下载成功" % (album_id, photo_index))
                        else:
                            log.error("作品%s第%s张图片 %s 下载失败，原因：%s" % (album_id, photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
                        photo_index += 1
                    self.total_photo_count += photo_index - 1  # 计数累加

                if self.is_download_video and album_response["video_url"] is not None:
                    log.step("开始下载作品%s视频 %s" % (album_id, album_response["video_url"]))

                    video_file_path = os.path.join(self.video_download_path, "%04d %s.%s" % (album_id, path.filter_text(album_response["album_title"]), net.get_file_type(album_response["video_url"])))
                    save_file_return = net.save_net_file(album_response["video_url"], video_file_path)
                    if save_file_return["status"] == 1:
                        log.step("作品%s视频下载成功" % album_id)
                    else:
                        log.error("作品%s视频 %s 下载失败，原因：%s" % (album_id, album_response["video_url"], crawler.download_failre(save_file_return["code"])))
                    self.total_video_count += 1  # 计数累加

                # 图集内图片全部下载完毕
                temp_path = ""  # 临时目录设置清除
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
        self.result = net.save_net_file(self.photo_url, self.file_path)
        self.notify_main_thread()

    def get_result(self):
        return self.result


if __name__ == "__main__":
    IMeitu().main()
