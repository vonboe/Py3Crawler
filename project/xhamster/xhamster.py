# -*- coding:UTF-8  -*-
"""
xhamster视频爬虫
https://xhamster.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
import re
import traceback
from common import *

FIRST_CHOICE_RESOLUTION = 720
VIDEO_ORIENTATION_FILTER = 7
ORIENTATION_TYPE_LIST = {
    "straight": 1,
    "shemale": 2,
    "gay": 4,
}
CATEGORY_WHITELIST = ""
CATEGORY_BLACKLIST = ""


# 获取指定视频
def get_video_page(video_id):
    video_play_url = "https://xhamster.com/videos/%s" % video_id
    # 强制使用英语
    video_play_response = net.http_request(video_play_url, method="GET")
    result = {
        "is_delete": False,  # 是否已删除
        "is_password": False,  # 是否需要密码
        "is_skip": False,  # 是否跳过
        "video_title": "",  # 视频标题
        "video_url": None,  # 视频地址
    }
    if video_play_response.status == 404 or video_play_response.status == 410 or video_play_response.status == 423:
        result["is_delete"] = True
        return result
    if video_play_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(video_play_response.status))
    video_play_response_content = video_play_response.data.decode(errors="ignore")
    if video_play_response_content.find('<div class="title">This video requires password</div>') >= 0:
        result["is_password"] = True
        return result
    script_json_html = tool.find_sub_string(video_play_response_content, "window.initials = ", ";\n")
    if not script_json_html:
        raise crawler.CrawlerException("页面截取视频信息失败\n%s" % video_play_response_content)
    script_json = tool.json_decode(script_json_html)
    if script_json is None:
        raise crawler.CrawlerException("视频信息加载失败\n%s" % script_json_html)
    # 判断是否需要跳过
    video_orientation = crawler.get_json_value(script_json, "orientation", type_check=str)
    # 过滤视频orientation
    if video_orientation in ORIENTATION_TYPE_LIST:
        if not (ORIENTATION_TYPE_LIST[video_orientation] & VIDEO_ORIENTATION_FILTER):
            result["is_skip"] = True
            return result
    else:
        log.notice("未知视频orientation：" + video_orientation)
    # 过滤视频category
    category_list = []
    for category_info in crawler.get_json_value(script_json, "videoModel", "categories", type_check=list):
        category_list.append(crawler.get_json_value(category_info, "name", type_check=str).lower())
    if CATEGORY_BLACKLIST or CATEGORY_WHITELIST:
        is_skip = True if CATEGORY_WHITELIST else False
        for category in category_list:
            if CATEGORY_BLACKLIST:
                # category在黑名单中
                if len(re.findall(CATEGORY_BLACKLIST, category)) > 0:
                    is_skip = True
                    break
            if CATEGORY_WHITELIST:
                # category在黑名单中
                if len(re.findall(CATEGORY_WHITELIST, category)) > 0:
                    is_skip = False
        if is_skip:
            result["is_skip"] = True
            return result
    # 获取视频标题
    result["video_title"] = crawler.get_json_value(script_json, "videoModel", "title", type_check=str)
    # 获取视频下载地址
    try:
        video_list = crawler.get_json_value(script_json, "videoModel", "sources", "mp4", type_check=dict)
    except crawler.CrawlerException:
        video_list = {}
        for resolution_string, video_info in crawler.get_json_value(script_json, "videoModel", "vr", "sources", default_value={}, type_check=list).items():
            video_list[resolution_string] = crawler.get_json_value(video_info, "downloadUrl", original_data=script_json, type_check=str)
        if len(video_list) == 0:
            raise
    # 各个分辨率下的视频地址
    resolution_to_url = {}
    for resolution_string in video_list:
        resolution = resolution_string.replace("p", "")
        if not crawler.is_integer(resolution):
            raise crawler.CrawlerException("视频信息分辨率字段类型不正确\n%s" % resolution_string)
        resolution = int(resolution)
        if resolution not in [144, 240, 480, 720, 960, 1440, 1920]:
            log.notice("未知视频分辨率：%s" % resolution_string)
        resolution_to_url[resolution] = video_list[resolution_string]
    # 优先使用配置中的分辨率
    if FIRST_CHOICE_RESOLUTION in resolution_to_url:
        result["video_url"] = resolution_to_url[FIRST_CHOICE_RESOLUTION]
    # 如果没有这个分辨率的视频
    else:
        # 大于配置中分辨率的所有视频中分辨率最小的那个
        for resolution in sorted(resolution_to_url.keys()):
            if resolution > FIRST_CHOICE_RESOLUTION:
                result["video_url"] = resolution_to_url[resolution]
                break
        # 如果还是没有，则所有视频中分辨率最大的那个
        if result["video_url"] is None:
            result["video_url"] = resolution_to_url[max(resolution_to_url)]
    return result


class Xhamster(crawler.Crawler):
    def __init__(self, **kwargs):
        global FIRST_CHOICE_RESOLUTION
        global VIDEO_ORIENTATION_FILTER
        global CATEGORY_WHITELIST
        global CATEGORY_BLACKLIST

        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_VIDEO: True,
            crawler.SYS_SET_PROXY: True,
            crawler.SYS_NOT_CHECK_SAVE_DATA: True,
            crawler.SYS_APP_CONFIG: (
                ("VIDEO_QUALITY", 3, crawler.CONFIG_ANALYSIS_MODE_INTEGER),
                ("VIDEO_ORIENTATION", 7, crawler.CONFIG_ANALYSIS_MODE_INTEGER),
                ("CATEGORY_WHITELIST", "", crawler.CONFIG_ANALYSIS_MODE_RAW),
                ("CATEGORY_BLACKLIST", "", crawler.CONFIG_ANALYSIS_MODE_RAW),
            ),
        }
        crawler.Crawler.__init__(self, sys_config, **kwargs)

        # 设置全局变量，供子线程调用
        video_quality = self.app_config["VIDEO_QUALITY"]
        if video_quality == 1:
            FIRST_CHOICE_RESOLUTION = 144
        if video_quality == 2:
            FIRST_CHOICE_RESOLUTION = 240
        elif video_quality == 3:
            FIRST_CHOICE_RESOLUTION = 480
        elif video_quality == 4:
            FIRST_CHOICE_RESOLUTION = 720
        elif video_quality == 5:
            FIRST_CHOICE_RESOLUTION = 960
        elif video_quality == 6:
            FIRST_CHOICE_RESOLUTION = 1440
        elif video_quality == 7:
            FIRST_CHOICE_RESOLUTION = 1920
        else:
            log.error("配置文件config.ini中key为'VIDEO_QUALITY'的值必须是一个1~3的整数，使用程序默认设置")

        video_orientation = self.app_config["VIDEO_ORIENTATION"]
        if not crawler.is_integer(video_orientation) and not (1 <= video_orientation <= 7):
            log.error("配置文件config.ini中key为'VIDEO_ORIENTATION'的值必须是一个1~7的整数，使用程序默认设置")
        VIDEO_ORIENTATION_FILTER = int(video_orientation)

        category_whitelist = self.app_config["CATEGORY_WHITELIST"]
        if category_whitelist:
            CATEGORY_WHITELIST = "|".join(category_whitelist.lower().split(",")).replace("*", "\w*")
        category_blacklist = self.app_config["CATEGORY_BLACKLIST"]
        if category_blacklist:
            CATEGORY_BLACKLIST = "|".join(category_blacklist.lower().split(",")).replace("*", "\w*")

    def main(self):
        # 解析存档文件，获取上一次的album id
        video_id = 1
        if os.path.exists(self.save_data_path):
            file_save_info = file.read_file(self.save_data_path)
            if not crawler.is_integer(file_save_info):
                log.error("存档内数据格式不正确")
                tool.process_exit()
            video_id = int(file_save_info)

        try:
            while video_id:
                if not self.is_running():
                    tool.process_exit(0)
                log.step("开始解析视频%s" % video_id)

                # 获取视频
                try:
                    video_play_response = get_video_page(video_id)
                except crawler.CrawlerException as e:
                    log.error("视频%s解析失败，原因：%s" % (video_id, e.message))
                    raise

                if video_play_response["is_delete"]:
                    log.step("视频%s已删除，跳过" % video_id)
                    video_id += 1
                    continue

                if video_play_response["is_password"]:
                    log.step("视频%s需要密码访问，跳过" % video_id)
                    video_id += 1
                    continue

                if video_play_response["is_skip"]:
                    log.step("视频%s已过滤，跳过" % video_id)
                    video_id += 1
                    continue

                log.step("开始下载视频%s《%s》 %s" % (video_id, video_play_response["video_title"], video_play_response["video_url"]))
                file_path = os.path.join(self.video_download_path, "%08d %s.mp4" % (video_id, path.filter_text(video_play_response["video_title"])))
                save_file_return = net.save_net_file(video_play_response["video_url"], file_path, head_check=True)
                if save_file_return["status"] == 1:
                    log.step("视频%s《%s》 下载成功" % (video_id, video_play_response["video_title"]))
                else:
                    log.error("视频%s《%s》 %s 下载失败，原因：%s" % (video_id, video_play_response["video_title"], video_play_response["video_url"], crawler.download_failre(save_file_return["code"])))
                self.total_video_count += 1  # 计数累加
                video_id += 1  # 设置存档记录
        except SystemExit as se:
            if se.code == 0:
                log.step("提前退出")
            else:
                log.error("异常退出")
        except Exception as e:
            log.error("未知异常")
            log.error(str(e) + "\n" + traceback.format_exc())

        # 重新保存存档文件
        file.write_file(str(video_id), self.save_data_path, file.WRITE_FILE_TYPE_REPLACE)
        log.step("全部下载完毕，耗时%s秒，共计视频%s个" % (self.get_run_time(), self.total_video_count))


if __name__ == "__main__":
    Xhamster().main()
