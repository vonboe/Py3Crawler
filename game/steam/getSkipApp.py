# -*- coding:UTF-8  -*-
"""
获取缓存文件中所有无效的steam游戏
https://store.steampowered.com/
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import output
from game.steam import steamCommon, review


def main():
    # 获取登录状态
    steam_class = steamCommon.Steam(need_login=False)

    # 历史记录
    apps_cache_data = steam_class.load_cache_apps_info()
    output.print_msg(apps_cache_data["learning_list"] + apps_cache_data["deleted_list"])


if __name__ == "__main__":
    main()