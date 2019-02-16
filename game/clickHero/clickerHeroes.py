# -*- coding:UTF-8  -*-
"""
clicker heroes窗口处理类
@author: hikaru
email: hikaru870806@hotmail.com
如有问题或建议请联系
"""
from common import windowsApplication

# 窗口标题
WINDOW_TITLE = "Clicker Heroes"
# 每个升级按钮对应的坐标
UPGRADE_BUTTON_POS = {
    1: (100, 230),
    2: (100, 340),
    3: (100, 450),
    4: (100, 550),
}
# 是否关闭自动通关模式需要检测的点（RGB颜色为#FF0000）
PROGRESSION_MODE_CHECK_POSITION = (
    (1099, 235), (1099, 236), (1100, 234), (1100, 235), (1100, 236), (1100, 237), (1101, 235), (1101, 236), (1101, 237),
    (1102, 236), (1102, 237), (1102, 238), (1103, 237), (1103, 238), (1103, 239), (1104, 238), (1104, 239), (1104, 240),
    (1105, 239), (1105, 240), (1105, 241), (1106, 240), (1106, 241), (1106, 242), (1107, 241), (1107, 242), (1107, 243),
    (1108, 242), (1108, 243), (1108, 244), (1109, 243), (1109, 244), (1109, 245), (1110, 243), (1110, 244), (1110, 245),
    (1110, 246), (1111, 244), (1111, 245), (1111, 246), (1111, 247), (1112, 245), (1112, 246), (1112, 247), (1112, 248),
    (1113, 246), (1113, 247), (1113, 248), (1113, 249), (1114, 247), (1114, 248), (1114, 249), (1114, 250), (1115, 248),
    (1115, 249), (1115, 250), (1115, 251), (1116, 249), (1116, 250), (1116, 251), (1117, 250), (1117, 251), (1117, 252),
    (1118, 251), (1118, 252), (1118, 253), (1119, 252), (1119, 253), (1119, 254), (1120, 253), (1120, 254), (1120, 255),
    (1121, 254), (1121, 255), (1121, 256), (1122, 255), (1122, 256), (1122, 257), (1123, 256), (1123, 257), (1123, 258),
    (1124, 257), (1124, 258), (1124, 259), (1125, 257), (1125, 258), (1125, 259), (1125, 260), (1126, 258), (1126, 259),
    (1126, 260), (1126, 261), (1127, 259), (1127, 260), (1127, 261), (1127, 262), (1128, 260), (1128, 261), (1128, 262),
    (1128, 263), (1129, 261), (1129, 262), (1129, 263)
)
MONSTER_CLICK_POSITION = (855, 395)
DEFAULT_WINDOWS_SIZE = (1152, 678)
DEFAULT_CLIENT_SIZE = (1136, 640)


class ClickerHeroes(windowsApplication.WindowsApplication):
    def __init__(self):
        windowsApplication.WindowsApplication.__init__(self, WINDOW_TITLE, DEFAULT_WINDOWS_SIZE)