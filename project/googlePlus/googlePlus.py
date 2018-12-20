# -*- coding:UTF-8  -*-
"""
Google Plus图片爬虫
https://plus.google.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import time
import traceback
from common import *


# 获取指定token后的一页相册
def get_one_page_blog(account_id, token):
    result = {
        "blog_info_list": [],  # 全部日志信息
        "next_page_key": None,  # 下一页token
    }
    # 截取页面中的JS数据
    if token:
        api_url = "https://get.google.com/_/AlbumArchiveUi/data"
        post_data = {"f.req": '[[[113305009,[{"113305009":["%s",null,2,16,"%s"]}],null,null,0]]]' % (account_id, token)}
        blog_pagination_response = net.http_request(api_url, method="POST", fields=post_data)
        if blog_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
        blog_pagination_response_content = blog_pagination_response.data.decode(errors="ignore")
        script_json_html = tool.find_sub_string(blog_pagination_response_content, ")]}'", None).strip()
        if not script_json_html:
            raise crawler.CrawlerException("页面截取日志信息失败\n%s" % blog_pagination_response_content)
        script_json = tool.json_decode(script_json_html)
        if script_json is None:
            raise crawler.CrawlerException("日志信息加载失败\n%s" % script_json_html)
        if not (len(script_json) == 3 and len(script_json[0]) == 3 and crawler.check_sub_key(("113305009",), script_json[0][2])):
            raise crawler.CrawlerException("日志信息格式不正确\n%s" % script_json)
        script_json = script_json[0][2]["113305009"]
    else:
        blog_pagination_url = "https://get.google.com/albumarchive/%s/albums/photos-from-posts" % account_id
        blog_pagination_response = net.http_request(blog_pagination_url, method="GET")
        if blog_pagination_response.status == 400:
            raise crawler.CrawlerException("账号不存在")
        elif blog_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(blog_pagination_response.status))
        blog_pagination_response_content = blog_pagination_response.data.decode(errors="ignore")
        script_json_html = tool.find_sub_string(blog_pagination_response_content, "AF_initDataCallback({key: 'ds:0'", "</script>")
        script_json_html = tool.find_sub_string(script_json_html, "return ", "}});")
        if not script_json_html:
            raise crawler.CrawlerException("页面截取日志信息失败\n%s" % blog_pagination_response_content)
        script_json = tool.json_decode(script_json_html)
        if script_json is None:
            raise crawler.CrawlerException("日志信息加载失败\n%s" % script_json_html)
    if len(script_json) != 3:
        raise crawler.CrawlerException("日志信息格式不正确\n%s" % script_json)
    # 获取下一页token
    result["next_page_key"] = script_json[2]
    # 获取日志信息
    if script_json[1] is not None:
        for data in script_json[1]:
            result_blog_info = {
                "blog_id": None,  # 日志id
                "blog_time": None,  # 日志发布时间
            }
            blog_data = []
            for temp_data in data:
                if crawler.check_sub_key(("113305016",), temp_data):
                    blog_data = temp_data["113305016"][0]
                    break
            if len(blog_data) >= 5:
                # 获取日志id
                result_blog_info["blog_id"] = blog_data[0]
                # 获取日志发布时间
                if not crawler.is_integer(blog_data[4]):
                    raise crawler.CrawlerException("日志时间类型不正确\n%s" % blog_data)
                result_blog_info["blog_time"] = int(int(blog_data[4]) / 1000)
            else:
                raise crawler.CrawlerException("日志信息格式不正确\n%s" % script_json)
            result["blog_info_list"].append(result_blog_info)
    return result


# 获取指定id的相册页
def get_album_page(account_id, album_id):
    # 图片只有一页：https://get.google.com/albumarchive/102249965218267255722/album/AF1QipPLt_v4vK2Jkqcm5DOtFl6aHWZMTdu0A4mOpOFN?source=pwa
    # 图片不止一页：https://get.google.com/albumarchive/109057690948151627836/album/AF1QipMg1hsC4teQFP5xaBioWo-1SCr4Hphh4mfc0ZZX?source=pwa
    album_url = "https://get.google.com/albumarchive/%s/album/%s" % (account_id, album_id)
    result = {
        "photo_url_list": [],  # 全部图片地址
    }
    album_response = net.http_request(album_url, method="GET")
    if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    album_response_content = album_response.data.decode(errors="ignore")
    script_json_html = tool.find_sub_string(album_response_content, "AF_initDataCallback({key: 'ds:0'", "</script>")
    script_json_html = tool.find_sub_string(script_json_html, "return ", "}});")
    if not script_json_html:
        raise crawler.CrawlerException("页面截取相册信息失败\n%s" % album_response_content)
    script_json = tool.json_decode(script_json_html)
    if script_json is None:
        raise crawler.CrawlerException("相册信息加载失败\n%s" % script_json_html)
    try:
        # 没有任何图片的相册 https://get.google.com/albumarchive/103672820480928504638/album/AF1QipNSBnvfO0HfByOvPJzxYGMsEdd0KYIdCMA0m-43
        if len(script_json[4]) == 1:
            return result
        user_key = script_json[4][0]
        continue_token = script_json[3]
        for data in script_json[4][1]:
            result["photo_url_list"].append(data[1])
    except IndexError:
        raise crawler.CrawlerException("相册信息格式不正确\n%s" % script_json_html)
    # 判断是不是还有下一页
    while continue_token:
        api_url = "https://get.google.com/_/AlbumArchiveUi/data"
        post_data = {"f.req": '[[[113305010,[{"113305010":["%s",null,24,"%s"]}],null,null,0]]]' % (user_key, continue_token)}
        photo_pagination_response = net.http_request(api_url, method="POST", fields=post_data, encode_multipart=False)
        if photo_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
            raise crawler.CrawlerException(crawler.request_failre(album_response.status))
        continue_data_html = tool.find_sub_string(photo_pagination_response.data.decode(errors="ignore"), ")]}'", None).strip()
        continue_data = tool.json_decode(continue_data_html)
        if continue_data is None:
            raise crawler.CrawlerException("相册信息加载失败\n%s" % continue_data_html)
        try:
            continue_token = continue_data[0][2]["113305010"][3]
            for data in continue_data[0][2]["113305010"][4][1]:
                result["photo_url_list"].append(data[1])
        except ValueError:
            raise crawler.CrawlerException("相册信息格式不正确\n%s" % script_json_html)
    return result


# 过滤图片地址（跳过视频）
def filter_photo_url(photo_url):
    return photo_url.find("/video.googleusercontent.com/") != -1 or photo_url.find("/video-downloads.googleusercontent.com/") != -1


class GooglePlus(crawler.Crawler):
    def __init__(self, **kwargs):
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_SET_PROXY: True,
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 解析存档文件
        # account_id  photo_count  album_id  (account_name)  (file_path)
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0", "0"])

    def main(self):
        # 循环下载每个id
        thread_list = []
        for account_id in sorted(self.account_list.keys()):
            # 提前结束
            if not self.is_running():
                break

            # 开始下载
            thread = Download(self.account_list[account_id], self)
            thread.start()
            thread_list.append(thread)

            time.sleep(1)

        # 等待子线程全部完成
        while len(thread_list) > 0:
            thread_list.pop().join()

        # 未完成的数据保存
        if len(self.account_list) > 0:
            file.write_file(tool.list_to_string(list(self.account_list.values())), self.temp_save_data_path)

        # 重新排序保存存档文件
        crawler.rewrite_save_file(self.temp_save_data_path, self.save_data_path)

        log.step("全部下载完毕，耗时%s秒，共计图片%s张" % (self.get_run_time(), self.total_photo_count))


class Download(crawler.DownloadThread):
    def __init__(self, account_info, main_thread):
        crawler.DownloadThread.__init__(self, account_info, main_thread)
        self.account_id = self.account_info[0]
        if len(self.account_info) >= 4 and self.account_info[3]:
            self.display_name = self.account_info[3]
        else:
            self.display_name = self.account_info[0]
        if len(self.account_info) >= 5 and self.account_info[4]:
            self.account_team = self.account_info[4]
        else:
            self.account_team = ""
        self.step("开始")

    # 获取所有可下载日志
    def get_crawl_list(self):
        key = ""
        blog_info_list = []
        is_over = False
        # 获取全部还未下载过需要解析的相册
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析token：%s页日志" % key)

            # 获取一页相册
            try:
                blog_pagination_response = get_one_page_blog(self.account_id, key)
            except crawler.CrawlerException as e:
                self.error("token：%s页日志解析失败，原因：%s" % (key, e.message))
                raise

            self.trace("token：%s页解析的全部日志：%s" % (key, blog_pagination_response["blog_info_list"]))
            self.step("token：%s页解析获取%s个日志" % (key, len(blog_pagination_response["blog_info_list"])))

            # 寻找这一页符合条件的日志
            for blog_info in blog_pagination_response["blog_info_list"]:
                # 检查是否达到存档记录
                if blog_info["blog_time"] > int(self.account_info[2]):
                    blog_info_list.append(blog_info)
                else:
                    is_over = True
                    break

            if not is_over:
                if blog_pagination_response["next_page_key"]:
                    # 设置下一页token
                    key = blog_pagination_response["next_page_key"]
                else:
                    is_over = True

        return blog_info_list

    # 解析单个日志
    def crawl_blog(self, blog_info):
        self.step("开始解析日志 %s" % blog_info["blog_id"])
        
        # 获取相册页
        try:
            album_response = get_album_page(self.account_id, blog_info["blog_id"])
        except crawler.CrawlerException as e:
            self.error("相册%s解析失败，原因：%s" % (blog_info["blog_id"], e.message))
            raise

        if len(album_response["photo_url_list"]) == 0:
            self.error("相册%s没有解析到图片" % blog_info["blog_id"])
            self.account_info[2] = str(blog_info["blog_time"])  # 设置存档记录
            return

        self.trace("相册%s解析的全部图片：%s" % (blog_info["blog_id"], album_response["photo_url_list"]))
        self.step("相册%s解析获取%s张图片" % (blog_info["blog_id"], len(album_response["photo_url_list"])))

        photo_index = int(self.account_info[1]) + 1
        for photo_url in album_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            # 过滤图片地址
            if filter_photo_url(photo_url):
                continue
            self.step("开始下载第%s张图片 %s" % (photo_index, photo_url))

            file_path = os.path.join(self.main_thread.photo_download_path, self.account_team, self.display_name, "%04d.jpg" % photo_index)
            save_file_return = net.save_net_file(photo_url, file_path, need_content_type=True)
            if save_file_return["status"] == 1:
                # 设置临时目录
                self.temp_path_list.append(save_file_return["file_path"])
                self.step("第%s张图片下载成功" % photo_index)
                photo_index += 1
            else:
                self.error("第%s张图片 %s 下载失败，原因：%s" % (photo_index, photo_url, crawler.download_failre(save_file_return["code"])))

        # 相册内图片全部下载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += (photo_index - 1) - int(self.account_info[1])  # 计数累加
        self.account_info[1] = str(photo_index - 1)  # 设置存档记录
        self.account_info[2] = str(blog_info["blog_time"])  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载日志
            blog_info_list = self.get_crawl_list()
            self.step("需要下载的全部相册解析完毕，共%s个" % len(blog_info_list))

            # 从最早的相册开始下载
            while len(blog_info_list) > 0:
                self.crawl_blog(blog_info_list.pop())
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
            # 如果临时目录变量不为空，表示某个日志正在下载中，需要把下载了部分的内容给清理掉
            self.clean_temp_path()
        except Exception as e:
            self.error("未知异常")
            self.error(str(e) + "\n" + traceback.format_exc(), False)

        # 保存最后的信息
        with self.thread_lock:
            file.write_file("\t".join(self.account_info), self.main_thread.temp_save_data_path)
            self.main_thread.total_photo_count += self.total_photo_count
            self.main_thread.account_list.pop(self.account_id)
        self.step("下载完毕，总共获得%s张图片" % self.total_photo_count)
        self.notify_main_thread()


if __name__ == "__main__":
    GooglePlus().main()
