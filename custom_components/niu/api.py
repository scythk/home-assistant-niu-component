from datetime import datetime, timedelta
import hashlib
import json
import math

# from homeassistant.util import Throttle
from time import gmtime, strftime

import requests

from .const import *


class NiuApi:
    def __init__(self, username, password, scooter_id) -> None:
        self.username = username
        self.password = password
        self.scooter_id = int(scooter_id)

        self.dataBat = None
        self.dataMoto = None
        self.dataMotoInfo = None
        self.dataTrackInfo = None

    def initApi(self):
        self.token = self.get_token()
        api_uri = MOTOINFO_LIST_API_URI
        self.sn = self.get_vehicles_info(api_uri)["data"]["items"][self.scooter_id][
            "sn_id"
        ]
        self.sensor_prefix = self.get_vehicles_info(api_uri)["data"]["items"][
            self.scooter_id
        ]["scooter_name"]
        self.updateBat()
        self.updateMoto()
        self.updateMotoInfo()
        self.updateTrackInfo()

    def get_token(self):
        username = self.username
        password = self.password

        url = ACCOUNT_BASE_URL + LOGIN_URI
        md5 = hashlib.md5(password.encode("utf-8")).hexdigest()
        data = {
            "account": username,
            "password": md5,
            "grant_type": "password",
            "scope": "base",
            "app_id": "niu_ktdrr960",
        }
        try:
            r = requests.post(url, data=data)
        except BaseException as e:
            print(e)
            return False
        data = json.loads(r.content.decode())
        return data["data"]["token"]["access_token"]

    def get_vehicles_info(self, path):
        token = self.token

        url = API_BASE_URL + path
        headers = {"token": token}
        try:
            r = requests.get(url, headers=headers, data=[])
        except ConnectionError:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        return data

    def get_info(
        self,
        path,
    ):
        sn = self.sn
        token = self.token
        url = API_BASE_URL + path

        params = {"sn": sn}
        headers = {
            "token": token,
            "user-agent": "manager/4.10.4 (android; IN2020 11);lang=zh-CN;clientIdentifier=Domestic;timezone=Asia/Shanghai;model=IN2020;deviceName=IN2020;ostype=android",
        }
        try:
            r = requests.get(url, headers=headers, params=params)

        except ConnectionError:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        if data["status"] != 0:
            return False
        return data

    def post_info(
        self,
        path,
    ):
        sn, token = self.sn, self.token
        url = API_BASE_URL + path
        params = {}
        headers = {"token": token, "Accept-Language": "en-US"}
        try:
            r = requests.post(url, headers=headers, params=params, data={"sn": sn})
        except ConnectionError:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        if data["status"] != 0:
            return False
        return data

    def post_info_track(self, path):
        sn, token = self.sn, self.token
        url = API_BASE_URL + path
        params = {}
        headers = {
            "token": token,
            "Accept-Language": "en-US",
            "User-Agent": "manager/1.0.0 (identifier);clientIdentifier=identifier",
        }
        try:
            r = requests.post(
                url,
                headers=headers,
                params=params,
                json={"index": "0", "pagesize": 10, "sn": sn},
            )
        except ConnectionError:
            return False
        if r.status_code != 200:
            return False
        data = json.loads(r.content.decode())
        if data["status"] != 0:
            return False
        return data

    def gcj2wgs(lat, lng):
        # Constants used for the conversion
        a = 6378245.0
        ee = 0.00669342162296594323

        def transform_lat(x, y):
            ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * (x ** 0.5)
            ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
            ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
            ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
            return ret

        def transform_lng(x, y):
            ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * (x ** 0.5)
            ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
            ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
            ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
            return ret

        dlat = transform_lat(lng - 105.0, lat - 35.0)
        dlng = transform_lng(lng - 105.0, lat - 35.0)
        radlat = lat / 180.0 * math.pi
        magic = math.sin(radlat)
        magic = 1 - ee * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * math.pi)
        dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * math.pi)
        mglat = lat + dlat
        mglng = lng + dlng
        return lat * 2 - mglat, lng * 2 - mglng

    def getDataBat(self, id_field):
        return self.dataBat["data"]["batteries"]["compartmentA"][id_field]

    def getDataMoto(self, id_field):
        return self.dataMoto["data"][id_field]

    def getDataDist(self, id_field):
        return self.dataMoto["data"]["lastTrack"][id_field]

    def getDataPos(self, id_field):
        return self.dataMoto["data"]["postion"][id_field]

    def getDataPosWGS(self, id_field):
        gcj_lat = self.getDataPos("lat")
        gcj_lng = self.getDataPos("lng")
        wgs_lat, wgs_lng = self.gcj2wgs(gcj_lat, gcj_lng)
        if id_field == "lat":
            return wgs_lat
        else:
            return wgs_lng

    def getDataOverall(self, id_field):
        return self.dataMotoInfo["data"][id_field]

    def getDataTrack(self, id_field):
        if id_field == "startTime" or id_field == "endTime":
            return datetime.fromtimestamp(
                (self.dataTrackInfo["data"][0][id_field]) / 1000
            ).strftime("%Y-%m-%d %H:%M:%S")
        if id_field == "ridingtime":
            return strftime("%H:%M:%S", gmtime(self.dataTrackInfo["data"][0][id_field]))
        if id_field == "track_thumb":
            thumburl = self.dataTrackInfo["data"][0][id_field].replace(
                "app-api.niucache.com", "app-api.niu.com"
            )
            # return thumburl.replace("/track/thumb/", "/track/overseas/thumb/")
            return thumburl
        return self.dataTrackInfo["data"][0][id_field]

    def updateBat(self):
        self.dataBat = self.get_info(MOTOR_BATTERY_API_URI)

    def updateMoto(self):
        self.dataMoto = self.get_info(MOTOR_INDEX_API_URI)

    def updateMotoInfo(self):
        self.dataMotoInfo = self.post_info(MOTOINFO_ALL_API_URI)

    def updateTrackInfo(self):
        self.dataTrackInfo = self.post_info_track(TRACK_LIST_API_URI)


"""class NiuDataBridge(object):
    async def __init__(self, api):
    #  hass, username, password, country, scooter_id):

        self.api = api
        # await hass.async_add_executor_job(lambda : NiuDataBridge(username, password, country, scooter_id))
        # NiuApi(username, password, country, scooter_id)
        sn, token = self.api.sn, self.api.token

        self._dataBat = None
        self._dataMoto = None
        self._dataMotoInfo = None
        self._dataTrackInfo = None
        self._sn = sn
        self._token = token

    def token(self):
        return self.api.token
    
    def sn(self):
        return self.api.sn

    def sensor_prefix(self):
        return self.api.sensor_prefix

    def dataBat(self, id_field):
        return self._dataBat["data"]["batteries"]["compartmentA"][id_field]

    def dataMoto(self, id_field):
        return self._dataMoto["data"][id_field]

    def dataDist(self, id_field):
        return self._dataMoto["data"]["lastTrack"][id_field]

    def dataPos(self, id_field):
        return self._dataMoto["data"]["postion"][id_field]

    def dataOverall(self, id_field):
        return self._dataMotoInfo["data"][id_field]

    def dataTrack(self, id_field):
        if id_field == "startTime" or id_field == "endTime":
            return datetime.fromtimestamp(
                (self._dataTrackInfo["data"][0][id_field]) / 1000
            ).strftime("%Y-%m-%d %H:%M:%S")
        if id_field == "ridingtime":
            return strftime(
                "%H:%M:%S", gmtime(self._dataTrackInfo["data"][0][id_field])
            )
        if id_field == "track_thumb":
            thumburl = self._dataTrackInfo["data"][0][id_field].replace(
                "app-api.niucache.com", "app-api.niu.com"
            )
            return thumburl.replace("/track/thumb/", "/track/overseas/thumb/")
        return self._dataTrackInfo["data"][0][id_field]

    @Throttle(timedelta(seconds=1))
    def updateBat(self):
        self._dataBat = self.api.get_info(MOTOR_BATTERY_API_URI)

    @Throttle(timedelta(seconds=1))
    def updateMoto(self):
        self._dataMoto = self.api.get_info(MOTOR_INDEX_API_URI)

    @Throttle(timedelta(seconds=1))
    def updateMotoInfo(self):
        self._dataMotoInfo = self.api.post_info(MOTOINFO_ALL_API_URI)

    @Throttle(timedelta(seconds=1))
    def updateTrackInfo(self):
        self._dataTrackInfo = self.api.post_info_track(TRACK_LIST_API_URI)"""
