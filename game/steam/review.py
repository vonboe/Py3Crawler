# -*- coding:UTF-8  -*-
"""
获取steam可以发布评测的游戏
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import os
from common import crawler, file, output
from game.steam.lib import steam


# 打印列表
# print_type  0 全部游戏
# print_type  1 只要本体
# print_type  2 只要DLC
# print_type  3 只要本体已评测的DLC
def print_list(apps_cache_data, print_type=0):
    for game_id in apps_cache_data["can_review_lists"]:
        # 是DLC
        if game_id in apps_cache_data["dlc_in_game"]:
            if print_type == 1:
                continue
            # 本体没有评测过
            if apps_cache_data["dlc_in_game"][game_id] in apps_cache_data["can_review_lists"]:
                if print_type == 3:
                    continue
        else:
            if print_type == 2 or print_type == 3:
                continue
        output.print_msg("https://store.steampowered.com/app/%s" % game_id)


def main():
    # 获取登录状态
    steam_class = steam.Steam(need_login=True)

    # 历史记录
    apps_cache_data = steam_class.load_cache_apps_info()
    # 已检测过的游戏列表
    checked_apps_file_path = os.path.join(steam_class.cache_data_path, "review_checked.txt")
    checked_apps_string = file.read_file(checked_apps_file_path)
    if checked_apps_string:
        checked_apps_list = checked_apps_string.split(",")
    else:
        checked_apps_list = []
    # 已删除的游戏
    deleted_app_list = steam_class.load_deleted_app_list()
    # 已资料受限制的游戏
    restricted_app_list = steam_class.load_restricted_app_list()

    # 获取自己的全部玩过的游戏列表
    try:
        played_game_list = steam.get_account_owned_app_list(steam_class.account_id, True)
    except crawler.CrawlerException as e:
        output.print_msg("个人游戏主页解析失败，原因：%s" % e.message)
        raise

    for game_id in played_game_list:
        if game_id in deleted_app_list:
            continue
        if game_id in checked_apps_list:
            continue

        output.print_msg("开始解析游戏%s" % game_id)

        # 获取游戏信息
        try:
            game_data = steam.get_game_store_index(game_id)
        except crawler.CrawlerException as e:
            output.print_msg("游戏%s解析失败，原因：%s" % (game_id, e.message))
            continue

        # 已删除
        if game_data["deleted"]:
            deleted_app_list.append(game_id)
            # 保存数据
            steam_class.save_deleted_app_list(deleted_app_list)
        else:
            # 有DLC的话，遍历每个DLC
            for dlc_id in game_data["dlc_list"]:
                # 已经评测过了，跳过检查
                if dlc_id in apps_cache_data["review_list"]:
                    continue

                # DLC和游戏本体关系字典
                apps_cache_data["dlc_in_game"][dlc_id] = game_id

                # 获取DLC信息
                try:
                    dlc_data = steam.get_game_store_index(dlc_id)
                except crawler.CrawlerException as e:
                    output.print_msg("游戏%s解析失败，原因：%s" % (dlc_id, e.message))
                    continue

                if dlc_data["owned"]:
                    # 已经评测过了
                    if dlc_data["reviewed"]:
                        # 从待评测列表中删除
                        if dlc_id in apps_cache_data["can_review_lists"]:
                            apps_cache_data["can_review_lists"].remove(dlc_id)
                        # 增加已评测记录
                        if dlc_id not in apps_cache_data["review_list"]:
                            apps_cache_data["review_list"].append(dlc_id)
                    # 新的可以评测游戏
                    else:
                        if dlc_id not in apps_cache_data["can_review_lists"]:
                            apps_cache_data["can_review_lists"].append(dlc_id)

            # 已经评测过了
            if game_data["reviewed"]:
                # 从待评测列表中删除
                if game_id in apps_cache_data["can_review_lists"]:
                    apps_cache_data["can_review_lists"].remove(game_id)
                # 增加已评测记录
                if game_id not in apps_cache_data["review_list"]:
                    apps_cache_data["review_list"].append(game_id)
            # 新的可以评测游戏
            else:
                if game_id not in apps_cache_data["can_review_lists"]:
                    apps_cache_data["can_review_lists"].append(game_id)

            # 需要了解
            if game_data["learning"]:
                if game_id not in restricted_app_list:
                    restricted_app_list.append(game_id)
                    # 保存数据
                    steam_class.save_restricted_app_list(restricted_app_list)

        # 增加检测标记
        steam_class.save_cache_apps_info(apps_cache_data)
        # 保存数据
        checked_apps_list.append(game_id)
        file.write_file(",".join(checked_apps_list), checked_apps_file_path, file.WRITE_FILE_TYPE_REPLACE)

    # 输出
    print_list(apps_cache_data)


if __name__ == "__main__":
    main()
