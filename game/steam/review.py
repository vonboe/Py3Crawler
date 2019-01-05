# -*- coding:UTF-8  -*-
"""
获取steam可以发布评测的游戏
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
import json
import os
from common import crawler, file, output, tool
from game.steam import steamCommon


# 保存评测记录到文件
def save_discount_list(cache_file_path, review_data):
    file.write_file(json.dumps(review_data), cache_file_path, file.WRITE_FILE_TYPE_REPLACE)


# 获取历史评测记录
def load_review_list(cache_file_path):
    review_data = {
        "can_review_lists": [],
        "dlc_in_game": {},
        "review_list": [],
        "learning_list": [],
        "deleted_list": [],
    }
    if not os.path.exists(cache_file_path):
        return review_data
    review_data = tool.json_decode(file.read_file(cache_file_path), review_data)
    return review_data


# 打印列表
# print_type  0 全部游戏
# print_type  1 只要本体
# print_type  2 只要DLC
# print_type  3 只要本体已评测的DLC
def print_list(cache_file_path, print_type=0):
    review_data = load_review_list(cache_file_path)
    for game_id in review_data["can_review_lists"]:
        # 是DLC
        if game_id in review_data["dlc_in_game"]:
            if print_type == 1:
                continue
            # 本体没有评测过
            if review_data["dlc_in_game"][game_id] in review_data["can_review_lists"]:
                if print_type == 3:
                    continue
        else:
            if print_type == 2 or print_type == 3:
                continue
        output.print_msg("https://store.steampowered.com/app/%s" % game_id)


def main():
    # 获取登录状态
    steam_class = steamCommon.Steam(need_login=True)
    cache_file_path = os.path.abspath(os.path.join(steam_class.cache_data_path, "review.txt"))

    # 历史记录
    review_data = load_review_list(cache_file_path)
    # 获取自己的全部玩过的游戏列表
    try:
        played_game_list = steamCommon.get_account_owned_app_list(steam_class.account_id, True)
    except crawler.CrawlerException as e:
        output.print_msg("个人游戏主页解析失败，原因：%s" % e.message)
        raise
    
    for game_id in played_game_list:
        if game_id in review_data["deleted_list"]:
            continue

        # 获取游戏信息
        try:
            game_data = steamCommon.get_game_store_index(game_id)
        except crawler.CrawlerException as e:
            output.print_msg("游戏%s解析失败，原因：%s" % (game_id, e.message))
            raise

        # 已删除
        if game_data["deleted"]:
            review_data["deleted_list"].append(game_id)
        else:
            # 有DLC的话，遍历每个DLC
            for dlc_id in game_data["dlc_list"]:
                # 已经评测过了，跳过检查
                if dlc_id in review_data["review_list"]:
                    continue

                # DLC和游戏本体关系字典
                review_data["dlc_in_game"][dlc_id] = game_id

                # 获取DLC信息
                try:
                    dlc_data = steamCommon.get_game_store_index(dlc_id)
                except crawler.CrawlerException as e:
                    output.print_msg("游戏%s解析失败，原因：%s" % (dlc_id, e.message))
                    raise

                if dlc_data["owned"]:
                    # 已经评测过了
                    if dlc_data["reviewed"]:
                        # 从待评测列表中删除
                        if dlc_id in review_data["can_review_lists"]:
                            review_data["can_review_lists"].remove(dlc_id)
                        # 增加已评测记录
                        if dlc_id not in review_data["review_list"]:
                            review_data["review_list"].append(dlc_id)
                    # 新的可以评测游戏
                    else:
                        if dlc_id not in review_data["can_review_lists"]:
                            review_data["can_review_lists"].append(dlc_id)

            # 已经评测过了
            if game_data["reviewed"]:
                # 从待评测列表中删除
                if game_id in review_data["can_review_lists"]:
                    review_data["can_review_lists"].remove(game_id)
                # 增加已评测记录
                if game_id not in review_data["review_list"]:
                    review_data["review_list"].append(game_id)
            # 新的可以评测游戏
            else:
                if game_id not in review_data["can_review_lists"]:
                    review_data["can_review_lists"].append(game_id)

            # 需要了解
            if game_data["learning"]:
                if game_id not in review_data["learning_list"]:
                    review_data["learning_list"].append(game_id)

        # 增加检测标记
        save_discount_list(cache_file_path, review_data)

    # 输出
    print_list(cache_file_path)


if __name__ == "__main__":
    main()
