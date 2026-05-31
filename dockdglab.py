import requests

class DockDGLab:
    """
    设备控制后端 API 客户端
    适配：通用波形接口 / 郊狼蓝牙设备控制接口
    所有请求均为 POST，支持 JSON 传参
    """
    def __init__(self, base_url="http://127.0.0.1:5000"):
        """
        初始化客户端
        :param base_url: 服务基础地址，默认 http://127.0.0.1:5000
        """
        self.base_url = base_url
        self.session = requests.Session()  # 使用会话提升请求效率

    def _post(self, endpoint, data):
        """
        内部通用 POST 请求方法
        :param endpoint: 接口路径（如 /websocket /coyote）
        :param data: 请求参数字典
        :return: 响应JSON / 状态码
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.post(url, json=data)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": f"请求失败：{str(e)}"}, -1
    def _get(self, endpoint):
        """
        内部通用 GET 请求方法
        :param endpoint: 接口路径（如 /websocket /coyote）
        :return: 响应JSON / 状态码
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.get(url)
            return response.json(), response.status_code
        except Exception as e:
            return {"error": f"请求失败：{str(e)}"}, -1

    def get_config(self,name):
        json,code = self._get(f"/config/{name}")
        return json

    def get_active(self):
        """
        Websocket/Coyote状态查询
        :param endpoint: 接口路径（如 /websocket /coyote）
        :param data: 请求参数字典
        :return: 响应JSON / 状态码
        """
        json,code = self._get(f"/active")
        return json

    def log(self,log_type,msg):
        data = {"type": log_type, "text": msg}
        return self._post(f"/add_log", data)

    # ==================== 1. 通用波形强度控制（/websocket）====================
    def get_strength(self):
        data = {
            "action": "get_strength"
        }
        json, code = self._post("/websocket", data)
        return json

    def add_strength(self, channel="All", strength=1):
        """增加指定通道强度"""
        data = {
            "action": "add_strength",
            "channel": channel,
            "strength": strength
        }
        json, code = self._post("/websocket", data)
        return json

    def reduce_strength(self, channel="All", strength=1):
        """减小指定通道强度"""
        data = {
            "action": "reduce_strength",
            "channel": channel,
            "strength": strength
        }
        json, code = self._post("/websocket", data)
        return json

    def set_strength(self, strength, channel="All"):
        """直接设置通道绝对强度"""
        data = {
            "action": "set_strength",
            "channel": channel,
            "strength": strength
        }
        json, code = self._post("/websocket", data)
        return json

    def send_waveform(self, select=None, waveform=None, channel="All"):
        """
        发送波形
        :param select: 预设波形名称（优先）
        :param waveform: 自定义波形（select为空时生效）
        :param channel: 通道
        """
        data = {
            "action": "send_waveform",
            "channel": channel
        }
        if select is not None:
            data["select"] = select
        if waveform is not None:
            data["waveform"] = waveform
        json, code = self._post("/websocket", data)
        return json

    def clear_waveform(self, channel="All"):
        """清空指定通道波形"""
        data = {
            "action": "clear_waveform",
            "channel": channel
        }
        json, code = self._post("/websocket", data)
        return json

    # ==================== 2. 郊狼蓝牙设备控制（/coyote）====================
    def coyote_connect(self):
        """扫描蓝牙并自动连接首个设备"""
        data = {"action": "connect"}
        json, code = self._post("/coyote", data)
        return json

    def coyote_battery(self):
        """获取设备当前电量"""
        data = {"action": "battery"}
        json, code = self._post("/coyote", data)
        return json

    def coyote_strength(self, option, channel, strength):
        """
        调整通道强度
        :param option: add 增量 / reduce 减量 / set 绝对值
        :param channel: 通道
        :param strength: 强度值
        """
        data = {
            "action": "strength",
            "option": option,
            "channel": channel,
            "strength": strength
        }
        json, code = self._post("/coyote", data)
        return json

    def coyote_get_strength(self):
        """
        获取通道强度
        """
        data = {
            "action": "get_strength"
        }
        json,code = self._post("/coyote", data)
        return json

    def coyote_set_waveform(self, select=None, waveform=None):
        """
        设置设备波形
        :param select: 预设波形（优先）
        :param waveform: 自定义波形
        """
        data = {"action": "set_waveform"}
        if select is not None:
            data["select"] = select
        if waveform is not None:
            data["waveform"] = waveform
        json, code = self._post("/coyote", data)
        return json

    def coyote_start_punish(self):
        """开始自动播放波形"""
        data = {"action": "start_punish"}
        json, code = self._post("/coyote", data)
        return json

    def coyote_stop_punish(self):
        """停止播放波形"""
        data = {"action": "stop_punish"}
        json, code = self._post("/coyote", data)
        return json

    def coyote_disconnect(self):
        """断开蓝牙连接"""
        data = {"action": "disconnect"}
        json, code = self._post("/coyote", data)
        return json