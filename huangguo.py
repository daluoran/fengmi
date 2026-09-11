# -*- coding: utf-8 -*-
# 黄果短剧 - 封面AES解密最终版
import re
import sys
import json
import time
from base64 import b64encode, b64decode
from urllib.parse import quote, unquote

sys.path.append('..')
from base.spider import Spider

try:
    from Crypto.Cipher import AES as _AES
except Exception:
    _AES = None

class Spider(Spider):
    def getName(self):
        return "黄果短剧"

    def init(self, extend=""):
        self.hosts = [
            "https://14a.bhefwntk.cc",
            "https://huangguo5.com",
            "https://huangguoai.com",
        ]
        self.host = self.hosts[0]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Connection": "keep-alive",
        }
        self.categories = [
            {"type_id": "ai-duanju", "type_name": "AI成人短剧"},
            {"type_id": "ai-manju", "type_name": "AI成人漫剧"},
            {"type_id": "ai-huanlian", "type_name": "AI换脸"},
            {"type_id": "ai-mogai", "type_name": "AI魔改"},
            {"type_id": "ranks/hot", "type_name": "排行榜"},
        ]
        # 图片AES密钥（站点前端 crypto-worker.js）
        self._IMG_KEY = bytes([102, 53, 100, 57, 54, 53, 100, 102, 55, 53, 51, 51, 54, 50, 55, 48])
        self._IMG_IV = bytes([57, 55, 98, 54, 48, 51, 57, 52, 97, 98, 99, 50, 102, 98, 101, 49])

    def _fetch(self, url, referer=None):
        headers = dict(self.headers)
        headers["Referer"] = referer or (self.host + "/")
        for _ in range(2):
            try:
                r = self.fetch(url, headers=headers, timeout=18, verify=False)
                if r is None:
                    time.sleep(0.5)
                    continue
                text = r.text if hasattr(r, "text") else str(r)
                if text and len(text) > 400:
                    return text
            except Exception:
                time.sleep(0.5)
        return ""

    def _get_bin(self, url):
        headers = dict(self.headers)
        headers["Referer"] = self.host + "/"
        headers["Accept"] = "image/webp,image/apng,image/*,*/*;q=0.8"
        for _ in range(2):
            try:
                r = self.fetch(url, headers=headers, timeout=15, verify=False)
                if r is None:
                    continue
                content = r.content if hasattr(r, "content") else None
                if content and len(content) > 100:
                    return content
            except Exception:
                time.sleep(0.4)
        return None

    def _get_html(self, path):
        for h in self.hosts:
            self.host = h
            url = path if path.startswith("http") else (h + path)
            html = self._fetch(url)
            if html and ("hg-drama-card" in html or "/detail/" in html):
                return html
        return ""

    def _fix(self, u):
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return self.host + u
        return u

    def _clean(self, s):
        if not s:
            return ""
        s = re.sub(r'<[^>]+>', '', s)
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    def _decrypt_img(self, raw):
        if not raw or _AES is None:
            return raw
        if len(raw) % 16 != 0:
            return raw
        try:
            pt = _AES.new(self._IMG_KEY, _AES.MODE_CBC, self._IMG_IV).decrypt(raw)
        except Exception:
            return raw
        # 校验是否解密成图片
        if not (pt[:2] == b"\xff\xd8" or pt[:8] == b"\x89PNG\r\n\x1a\n"
                or pt[:4] == b"RIFF" or pt[:6] in (b"GIF87a", b"GIF89a")):
            return raw
        pad = pt[-1]
        if 0 < pad <= 16 and pt[-pad:] == bytes([pad]) * pad:
            pt = pt[:-pad]
        return pt

    def _proxy_pic(self, u):
        """走本地代理 + AES解密"""
        u = self._fix(u or "")
        if not u or "placeholder" in u or "data:image" in u:
            return ""
        # 保留完整url（含auth_key更稳）
        try:
            enc = quote(b64encode(u.encode("utf-8")).decode("utf-8"), safe="")
            return f"{self.getProxyUrl()}&url={enc}&type=img"
        except Exception:
            return u

    def _parse_cards(self, html):
        if not html:
            return []
        items = []
        seen = set()
        blocks = re.split(r'hg-drama-card', html)[1:]
        for block in blocks:
            try:
                m = re.search(r'/detail/(\d+)/', block)
                if not m:
                    continue
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)

                title = ""
                for pat in [
                    r'hg-drama-card__title[^>]*>([\s\S]*?)</',
                    r'title=["\']([^"\']{2,80})["\']',
                    r'alt=["\']([^"\']{2,80})["\']',
                ]:
                    tm = re.search(pat, block)
                    if tm:
                        title = self._clean(tm.group(1))
                        if title and title not in ("未知", "null", "undefined"):
                            break
                if not title:
                    title = f"剧集{vid}"

                pic = ""
                pm = re.search(r'data-src=["\'](https?://[^"\']+)["\']', block)
                if not pm:
                    pm = re.search(r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|webp)[^"\']*)["\']', block, re.I)
                if pm:
                    pic = self._proxy_pic(pm.group(1))

                rem = ""
                rm = re.search(r'hg-drama-card__episode[^>]*>([\s\S]*?)</', block)
                if rm:
                    rem = self._clean(rm.group(1))
                sm = re.search(r'hg-drama-card__score[^>]*>([\s\S]*?)</', block)
                if sm:
                    score = self._clean(sm.group(1))
                    rem = f"{rem} · {score}" if rem else score

                items.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": rem,
                })
            except Exception:
                continue
        return items

    def _parse_rank(self, html):
        if not html:
            return []
        items = []
        seen = set()
        blocks = re.split(r'hg-rank-item', html)[1:]
        for block in blocks:
            try:
                m = re.search(r'/detail/(\d+)/', block)
                if not m:
                    continue
                vid = m.group(1)
                if vid in seen:
                    continue
                seen.add(vid)
                title = ""
                for pat in [
                    r'hg-rank-item__title[^>]*>([\s\S]*?)</',
                    r'title=["\']([^"\']{2,80})["\']',
                ]:
                    tm = re.search(pat, block)
                    if tm:
                        title = self._clean(tm.group(1))
                        if title:
                            break
                if not title:
                    continue
                pic = ""
                pm = re.search(r'data-src=["\'](https?://[^"\']+)["\']', block) or re.search(r'src=["\'](https?://[^"\']+)["\']', block)
                if pm:
                    pic = self._proxy_pic(pm.group(1))
                items.append({
                    "vod_id": vid,
                    "vod_name": title,
                    "vod_pic": pic,
                    "vod_remarks": "",
                })
            except Exception:
                continue
        return items

    def homeContent(self, filter):
        html = self._get_html("/")
        return {"class": self.categories, "list": self._parse_cards(html), "filters": {}}

    def homeVideoContent(self):
        html = self._get_html("/")
        return {"list": self._parse_cards(html)}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid).strip("/")
        if "rank" in tid:
            path = f"/{tid}/" if pg == 1 else f"/{tid}/{pg}/"
            html = self._get_html(path)
            return {"page": pg, "pagecount": 9999, "limit": 20, "total": 99999, "list": self._parse_rank(html)}
        path = f"/{tid}/" if pg == 1 else f"/{tid}/{pg}/"
        html = self._get_html(path)
        cards = self._parse_cards(html)
        return {"page": pg, "pagecount": 9999 if cards else pg, "limit": 24, "total": 99999, "list": cards}

    def detailContent(self, ids):
        vid = str(ids[0])
        html = self._get_html(f"/detail/{vid}/")
        result = {"list": []}
        if not html:
            return result

        name = ""
        m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html)
        if m:
            name = self._clean(m.group(1))
        if not name:
            return result

        pic = ""
        for pat in [
            r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']',
            r'hg-web-detail__poster[\s\S]{0,600}?(?:data-src|src)=["\']([^"\']+)["\']',
        ]:
            pm = re.search(pat, html, re.I)
            if pm:
                pic = self._proxy_pic(pm.group(1))
                if pic:
                    break

        desc = ""
        for pat in [
            r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
            r'name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
        ]:
            dm = re.search(pat, html, re.I)
            if dm:
                desc = self._clean(dm.group(1))
                if len(desc) > 10:
                    break

        eps = []
        for am in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*data-ep-id=["\']?(\d+)', html):
            href = self._fix(am.group(1))
            eid = am.group(2)
            eps.append(f"第{eid}集${href}")
        if not eps:
            pm = re.search(r'hg-web-detail__play[^>]*href=["\']([^"\']+)["\']', html)
            if pm:
                eps = [f"第1集${self._fix(pm.group(1))}"]
        if not eps:
            return result

        result["list"].append({
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_play_from": "黄果短剧",
            "vod_play_url": "#".join(eps),
            "vod_content": desc,
        })
        return result

    def searchContent(self, key, quick, pg="1"):
        html = self._get_html(f"/search/video/{quote(key)}/")
        return {"list": self._parse_cards(html), "page": int(pg or 1)}

    def playerContent(self, flag, id, vipFlags):
        url = self._fix(id)
        play = ""
        html = self._fetch(url, referer=self.host)
        if html:
            mm = re.search(r'<script id="videoInitialData" type="application/json">(.*?)</script>', html, re.S)
            if mm:
                try:
                    data = json.loads(mm.group(1))
                    srcs = data.get("epPlaySrcs") or {}
                    play = srcs.get("1") or data.get("videoSrc") or ""
                    if not play and srcs:
                        play = list(srcs.values())[0]
                except Exception:
                    pass
        if play:
            play = play.replace("\\u0026", "&")
            if not play.startswith("http"):
                m2 = re.search(r'(https?://[^\s"\']+)', play)
                play = m2.group(1) if m2 else ""
        return {
            "parse": 0,
            "url": play,
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
            }
        }

    def localProxy(self, param):
        """图片代理：下载 + AES解密后返回真正图片"""
        try:
            url = param.get("url") or ""
            if not url:
                return [404, "text/plain", b""]
            try:
                url = b64decode(unquote(url)).decode("utf-8")
            except Exception:
                pass
            raw = self._get_bin(url)
            if not raw:
                return [404, "text/plain", b""]
            data = self._decrypt_img(raw)
            if data[:8] == b"\x89PNG\r\n\x1a\n":
                ctype = "image/png"
            elif data[:2] == b"\xff\xd8":
                ctype = "image/jpeg"
            elif data[:4] == b"RIFF":
                ctype = "image/webp"
            elif data[:6] in (b"GIF87a", b"GIF89a"):
                ctype = "image/gif"
            else:
                ctype = "image/jpeg"
            return [200, ctype, data]
        except Exception:
            return [404, "text/plain", b""]

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass
