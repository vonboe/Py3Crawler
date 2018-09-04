# -*- coding:UTF-8  -*-
"""
半次元图片爬虫
https://bcy.net/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
import threading
import time
import traceback
from pyquery import PyQuery as pq
from common import *
from common import crypto

COOKIE_INFO = {}
IS_AUTO_FOLLOW = True
IS_LOCAL_SAVE_SESSION = False
IS_LOGIN = True
SESSION_DATA_PATH = None


# 生成session cookies
def init_session():
    # 如果有登录信息（初始化时从浏览器中获得）
    if "_csrf_token" in COOKIE_INFO and COOKIE_INFO["_csrf_token"]:
        cookies_list = COOKIE_INFO
    else:
        cookies_list = None
    home_url = "https://bcy.net"
    home_response = net.http_request(home_url, method="GET", cookies_list=cookies_list)
    if home_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        set_cookie = net.get_cookies_from_response_header(home_response.headers)
        COOKIE_INFO.update(set_cookie)
        if "_csrf_token" in COOKIE_INFO:
            return True
    return False


# 检测登录状态
def check_login():
    if "_csrf_token" in COOKIE_INFO and COOKIE_INFO["_csrf_token"]:
        home_url = "https://bcy.net/home/account"
        home_response = net.http_request(home_url, method="GET", cookies_list=COOKIE_INFO, is_auto_redirect=False)
        if home_response.status == net.HTTP_RETURN_CODE_SUCCEED:
            if home_response.data.decode(errors="ignore").find('<a href="/login">登录</a>') == -1:
                return True
    # 没有浏览器cookies，尝试读取文件
    else:
        # 从文件中读取账号密码
        account_data = tool.json_decode(crypto.Crypto().decrypt(file.read_file(SESSION_DATA_PATH)), {})
        if crawler.check_sub_key(("email", "password"), account_data):
            if _do_login(account_data["email"], account_data["password"]):
                return True
    return False


# 登录
def login_from_console():
    # 从命令行中输入账号密码
    while True:
        email = input(crawler.get_time() + " 请输入邮箱: ")
        password = input(crawler.get_time() + " 请输入密码: ")
        while True:
            input_str = input(crawler.get_time() + " 是否使用这些信息(Y)es或重新输入(N)o: ")
            input_str = input_str.lower()
            if input_str in ["y", "yes"]:
                if _do_login(email, password):
                    if IS_LOCAL_SAVE_SESSION:
                        file.write_file(crypto.Crypto().encrypt(json.dumps({"email": email, "password": password})), SESSION_DATA_PATH, file.WRITE_FILE_TYPE_REPLACE)
                    return True
                return False
            elif input_str in ["n", "no"]:
                break


# 模拟登录请求
def _do_login(email, password):
    if "_csrf_token" not in COOKIE_INFO:
        return False
    login_url = "https://bcy.net/public/dologin"
    login_post = {"email": email, "password": password, "_csrf_token": COOKIE_INFO["_csrf_token"], "remember": "1"}
    header_list = {
        "Referer": "https://bcy.net/",
        "X-Requested-With": "XMLHttpRequest",
    }
    login_response = net.http_request(login_url, method="POST", fields=login_post, cookies_list=COOKIE_INFO, header_list=header_list)
    if login_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        if login_response.data.decode(errors="ignore").find('<a href="/login">登录</a>') == -1:
            return True
    return False


# 关注指定账号
def follow(account_id):
    if "_csrf_token" not in COOKIE_INFO:
        return False
    follow_api_url = "https://bcy.net/weibo/Operate/follow?"
    follow_post_data = {"uid": account_id, "type": "dofollow", "_csrf_token": COOKIE_INFO["_csrf_token"]}
    header_list = {
        "Referer": "https://bcy.net/u/%s" % account_id,
        "X-Requested-With": "XMLHttpRequest",
    }
    follow_response = net.http_request(follow_api_url, method="POST", fields=follow_post_data, cookies_list=COOKIE_INFO, header_list=header_list)
    if follow_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        follow_response_content = follow_response.data.decode(errors="ignore")
        # 0 未登录，11 关注成功，12 已关注
        if crawler.is_integer(follow_response_content) and int(follow_response_content) in [11, 12]:
            return True
    return False


# 取消关注指定账号
def unfollow(account_id):
    unfollow_api_url = "https://bcy.net/weibo/Operate/follow?"
    unfollow_post_data = {"uid": account_id, "type": "unfollow", "_csrf_token": COOKIE_INFO["_csrf_token"]}
    header_list = {
        "Referer": "https://bcy.net/u/%s" % account_id,
        "X-Requested-With": "XMLHttpRequest",
    }
    unfollow_response = net.http_request(unfollow_api_url, method="POST", fields=unfollow_post_data, cookies_list=COOKIE_INFO, header_list=header_list)
    if unfollow_response.status == net.HTTP_RETURN_CODE_SUCCEED:
        unfollow_response_content = unfollow_response.data.decode(errors="ignore")
        if crawler.is_integer(unfollow_response_content) and int(unfollow_response_content) == 1:
            return True
    return False


# 获取指定页数的全部作品
def get_one_page_album(account_id, page_count):
    # https://bcy.net/u/50220/post/cos?&p=1
    album_pagination_url = "https://bcy.net/u/%s/post?&p=%s" % (account_id, page_count)
    query_data = {"p": page_count}
    album_pagination_response = net.http_request(album_pagination_url, method="GET", fields=query_data, cookies_list=COOKIE_INFO)
    result = {
        "album_id_list": [],  # 全部作品id
        "is_over": False,  # 是不是最后一页作品
    }
    if album_pagination_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_pagination_response.status))
    album_pagination_content = album_pagination_response.data.decode(errors="ignore")
    if page_count == 1 and album_pagination_content.find("<h2>用户不存在</h2>") >= 0:
        raise crawler.CrawlerException("账号不存在")
    # 没有作品
    if album_pagination_content.find("<h2>尚未发布作品</h2>") >= 0:
        result["is_over"] = True
        return result
    # 获取作品信息
    if pq(album_pagination_content).find("ul.gridList").length == 0:
        raise crawler.CrawlerException("页面截取作品列表失败\n%s" % album_pagination_content)
    album_list_selector = pq(album_pagination_content).find("ul.gridList li.js-smallCards")
    for album_index in range(0, album_list_selector.length):
        album_selector = album_list_selector.eq(album_index)
        # 获取作品id
        album_url = album_selector.find("a.posr").attr("href")
        if not album_url:
            raise crawler.CrawlerException("作品信息截取作品地址失败\n%s" % album_selector.html())
        album_id = album_url.split("/")[-1]
        if not crawler.is_integer(album_id):
            raise crawler.CrawlerException("作品地址 %s 截取作品id失败\n%s" % (album_url, album_selector.html()))
        result["album_id_list"].append(album_id)
    # 判断是不是最后一页
    last_pagination_selector = pq(album_pagination_content).find("ul.pager li:last a")
    if last_pagination_selector.length == 1:
        max_page_count = int(last_pagination_selector.attr("href").strip().split("&p=")[-1])
        result["is_over"] = page_count >= max_page_count
    else:
        result["is_over"] = True
    return result


# 获取指定id的作品
def get_album_page(album_id):
    # https://bcy.net/item/detail/6383727612803440398
    album_url = "https://bcy.net/item/detail/%s" % album_id
    album_response = net.http_request(album_url, method="GET", cookies_list=COOKIE_INFO)
    result = {
        "photo_url_list": [],  # 全部图片地址
        "is_only_follower": False,  # 是否只对粉丝显示
        "is_only_login": False,  # 是否只对登录用户显示
    }
    if album_response.status != net.HTTP_RETURN_CODE_SUCCEED:
        raise crawler.CrawlerException(crawler.request_failre(album_response.status))
    is_skip = False
    # 问题
    # https://bcy.net/item/detail/6115326868729126670
    if pq(album_response.data).find("div.post__content.js-fullimg").length == 1 and album_response.data.decode(errors="ignore").find('<a href="/group/discover">问答</a>') > 0:
        is_skip = True
    # 文章
    # https://bcy.net/item/detail/6162547130750754574
    elif pq(album_response.data).find("div.post__content h1.title.mt5").length == 1:
        is_skip = True
    # 检测作品是否被管理员锁定
    elif album_response.data.decode(errors="ignore").find("<h2>问题已被锁定，无法查看回答</h2>") >= 0:
        is_skip = True

    # 是不是有报错信息
    if not is_skip:
        error_message = pq(album_response.data.decode("UTF-8")).find("span.l-detail-no-right-to-see__text").text()
        # https://bcy.net/item/detail/5969608017174355726
        if error_message == "该作品已被作者设置为只有粉丝可见":
            result["is_only_follower"] = True
            return result
        # https://bcy.net/item/detail/6363512825238806286
        elif error_message == "该作品已被作者设置为登录后可见":
            if not IS_LOGIN:
                result["is_only_login"] = True
            else:
                raise crawler.CrawlerException("登录状态丢失")
            return result

    # 获取作品页面内的全部图片地址列表
    photo_list_selector = pq(album_response.data).find("div.post__content img.detail_std")
    for photo_index in range(0, photo_list_selector.length):
        photo_selector = photo_list_selector.eq(photo_index)
        # 获取作品id
        photo_url = photo_selector.attr("src")
        if not photo_url:
            raise crawler.CrawlerException("图片信息截取图片地址失败\n%s" % photo_selector.html())
        result["photo_url_list"].append(photo_url)

    if not is_skip and len(result["photo_url_list"]) == 0:
        raise crawler.CrawlerException("页面匹配图片地址失败\n%s" % album_response.data)

    return result


# 禁用指定分辨率
def get_photo_url(photo_url):
    return "/".join(photo_url.split("/")[0:-1])


class Bcy(crawler.Crawler):
    def __init__(self):
        global COOKIE_INFO
        global IS_AUTO_FOLLOW
        global IS_LOCAL_SAVE_SESSION
        global SESSION_DATA_PATH
        
        # 设置APP目录
        crawler.PROJECT_APP_PATH = os.path.abspath(os.path.dirname(__file__))

        # 初始化参数
        sys_config = {
            crawler.SYS_DOWNLOAD_PHOTO: True,
            crawler.SYS_GET_COOKIE: ("bcy.net",),
            crawler.SYS_APP_CONFIG: (
                ("IS_AUTO_FOLLOW", True, crawler.CONFIG_ANALYSIS_MODE_BOOLEAN),
                ("IS_LOCAL_SAVE_SESSION", False, crawler.CONFIG_ANALYSIS_MODE_BOOLEAN)
            ),
        }
        crawler.Crawler.__init__(self, sys_config)

        # 设置全局变量，供子线程调用
        COOKIE_INFO = self.cookie_value
        if "_csrf_token" not in COOKIE_INFO:
            COOKIE_INFO = {}
        IS_AUTO_FOLLOW = self.app_config["IS_AUTO_FOLLOW"]
        IS_LOCAL_SAVE_SESSION = self.app_config["IS_LOCAL_SAVE_SESSION"]
        SESSION_DATA_PATH = self.session_data_path

        # 解析存档文件
        # account_id  last_album_id
        self.account_list = crawler.read_save_data(self.save_data_path, 0, ["", "0"])

        # 生成session信息
        if not init_session():
            log.error("初始化失败")
            tool.process_exit()

        # 检测登录状态
        # 未登录时提示可能无法获取粉丝指定的作品
        if not check_login():
            while True:
                input_str = input(crawler.get_time() + " 没有检测到账号登录状态，可能无法解析那些只对粉丝开放的作品，手动输入账号密码登录(Y)es？或者跳过登录继续程序(C)ontinue？或者退出程序(E)xit？:")
                input_str = input_str.lower()
                if input_str in ["y", "yes"]:
                    if login_from_console():
                        break
                    else:
                        log.step("登录失败！")
                elif input_str in ["e", "exit"]:
                    tool.process_exit()
                elif input_str in ["c", "continue"]:
                    global IS_LOGIN
                    IS_LOGIN = False
                    break

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
        if len(self.account_info) >= 3:
            self.display_name = self.account_info[2]
        else:
            self.display_name = self.account_info[0]
        self.step("开始")

    # 获取所有可下载作品
    def get_crawl_list(self):
        page_count = 1
        unique_list = []
        album_id_list = []
        is_over = False
        while not is_over:
            self.main_thread_check()  # 检测主线程运行状态
            self.step("开始解析第%s页作品" % page_count)

            # 获取一页作品
            try:
                album_pagination_response = get_one_page_album(self.account_id, page_count)
            except crawler.CrawlerException as e:
                self.error("第%s页作品解析失败，原因：%s" % (page_count, e.message))
                raise

            self.trace("第%s页解析的全部作品：%s" % (page_count, album_pagination_response["album_id_list"]))
            self.step("第%s页解析获取%s个作品" % (page_count, len(album_pagination_response["album_id_list"])))

            # 寻找这一页符合条件的作品
            for album_id in album_pagination_response["album_id_list"]:
                # 检查是否达到存档记录
                if int(album_id) > int(self.account_info[1]):
                    # 新增作品导致的重复判断
                    if album_id in unique_list:
                        continue
                    else:
                        album_id_list.append(album_id)
                        unique_list.append(album_id)
                else:
                    is_over = True
                    break

            if not is_over:
                if album_pagination_response["is_over"]:
                    is_over = True
                else:
                    page_count += 1

        return album_id_list

    # 解析单个作品
    def crawl_album(self, album_id):
        self.main_thread_check()  # 检测主线程运行状态
        # 获取作品
        try:
            album_response = get_album_page(album_id)
        except crawler.CrawlerException as e:
            self.error("作品%s解析失败，原因：%s" % (album_id, e.message))
            raise

        # 是不是只对登录账号可见
        if album_response["is_only_login"]:
            self.error("作品%s只对登录账号显示，跳过" % album_id)
            return

        # 是不是只对粉丝可见，并判断是否需要自动关注
        if album_response["is_only_follower"]:
            if not IS_LOGIN or not IS_AUTO_FOLLOW:
                return
            self.step("作品%s是私密作品且账号不是ta的粉丝，自动关注" % album_id)
            if follow(self.account_id):
                self.main_thread_check()  # 检测主线程运行状态
                # 重新获取作品页面
                try:
                    album_response = get_album_page(album_id)
                except crawler.CrawlerException as e:
                    self.error("作品%s解析失败，原因：%s" % (album_id, e.message))
                    raise
            else:
                # 关注失败
                self.error("关注失败，跳过作品%s" % album_id)
                return

        self.trace("作品%s解析的全部图片：%s" % (album_id, album_response["photo_url_list"]))
        self.step("作品%s解析获取%s张图" % (album_id, len(album_response["photo_url_list"])))

        photo_index = 1
        album_path = os.path.join(self.main_thread.photo_download_path, self.display_name, album_id)
        # 设置临时目录
        self.temp_path_list.append(album_path)
        for photo_url in album_response["photo_url_list"]:
            self.main_thread_check()  # 检测主线程运行状态
            # 禁用指定分辨率
            photo_url = get_photo_url(photo_url)
            self.step("作品%s开始下载第%s张图片 %s" % (album_id, photo_index, photo_url))

            file_path = os.path.join(album_path, "%03d.%s" % (photo_index, net.get_file_type(photo_url, "jpg")))
            while True:
                save_file_return = net.save_net_file(photo_url, file_path)
                if save_file_return["status"] == 1:
                    self.step("作品%s第%s张图片下载成功" % (album_id, photo_index))
                    photo_index += 1
                else:
                    # 560报错，重新下载
                    if save_file_return["code"] == 560:
                        time.sleep(5)
                        continue
                    self.error("作品%s第%s张图片 %s，下载失败，原因：%s" % (album_id, photo_index, photo_url, crawler.download_failre(save_file_return["code"])))
                break

        # 作品内图片下全部载完毕
        self.temp_path_list = []  # 临时目录设置清除
        self.total_photo_count += photo_index - 1  # 计数累加
        self.account_info[1] = album_id  # 设置存档记录

    def run(self):
        try:
            # 获取所有可下载作品
            album_id_list = self.get_crawl_list()
            self.step("需要下载的全部作品解析完毕，共%s个" % len(album_id_list))

            # 从最早的作品开始下载
            while len(album_id_list) > 0:
                album_id = album_id_list.pop()
                self.step("开始解析作品%s" % album_id)
                self.crawl_album(album_id)
                self.main_thread_check()  # 检测主线程运行状态
        except SystemExit as se:
            if se.code == 0:
                self.step("提前退出")
            else:
                self.error("异常退出")
            # 如果临时目录变量不为空，表示某个图集正在下载中，需要把下载了部分的内容给清理掉
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
    Bcy().main()
