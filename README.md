# 郊狼惩罚姬插件 - 挨打就电
支持有血条的任何游戏

## 功能
1. 实时截图和ocr检测玩家血量/盾量
2. 判断并输出到郊狼惩罚姬进行电击
3. pyqt6实现的配置gui

## 安装
1. 从 [Releases](https://github.com/thx114/DG-LAB-HitElectric/releases) 下载插件
2. 将插件安装到惩罚姬 (惩罚姬获取：[bilibili](https://space.bilibili.com/383881792))
3. 打开配置工具，`./dist/config_tool.exe` 进行配置 (大概教程：[bilibili](https://www.bilibili.com/video/BV1gPQVBUEQG/))，最好是直接读取卡丘的预设配置 `./预制采样配置-使用配置工具读取`
4. 启动惩罚姬，启动插件，F9打开监测，连接郊狼( [bilibili](https://www.bilibili.com/video/BV11CdaBBEBC/) )

## OCR
1. 插件使用 [Umi-OCR](https://github.com/hiroi-sora/Umi-OCR) 的http接口，启动Umi-OCR后略微配置： 全局设置- 文字识别 - 线程：1
2. 启用配置中的ocr
3. 确保端口和配置中ocr端口一致
