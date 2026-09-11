# -*- coding: utf-8 -*-
# 黄果短剧 - 封面+简介最终修复版
import re
import sys
import json
import time
from base64 import b64encode, b64decode
from urllib.parse import quote, unquote

sys.path.append('..')
from base.spider import Spider

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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Connection": "keep-alive",
        }
        # 是否强制直链图片（一般不建议，容易没封面）
        ext = extend or ""
        self.pics_direct = "direct=1" in str(ext)
        self.categories = [
            {"type_id": "ai-duanju", "type_name": "AI成人短剧"},
            {"type_id": "ai-manju", "type_name": "AI成人漫剧"},
            {"type_id": "ai-huanlian", "type_name": "AI换脸"},
            {"type_id": "ai-mogai", "type_name": "AI魔改"},
            {"type_id": "ranks/hot", "type_name": "排行榜"},
        ]

    def _fetch(self, url, referer=None):
        headers = dict(self.headers)
        headers["Referer"] = referer or (self.host + "/")
        for _ in range(3):
            try:
                r = self.fetch(url, headers=headers, timeout=20, verify=False)
                if r is None:
                    time.sleep(0.6)
                    continue
                text = r.text if hasattr(r, "text") else str(r)
                if text and len(text) > 300:
                    return text
            except Exception:
                time.sleep(0.6)
        return ""

    def _get_html(self, path):
        for h in self.hosts:
            self.host = h
            url = path if path.startswith("http") else (h + path)
            html = self._fetch(url)
            if html and ("hg-drama-card" in html or "detail/" in html or "hg-web-detail" in html or "og:description" in html):
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

    def _proxy_pic(self, u):
        """通过本地代理加载图片，解决防盗链/过期问题"""
        u = self._fix(u or "")
        if not u:
            return ""
        if self.pics_direct:
            # 直链模式：去掉 auth_key 有时反而更稳
            if "?" in u:
                u = u.split("?")[0]
            return u
        try:
            enc = quote(b64encode(u.encode("utf-8")).decode("utf-8"), safe="")
            return f"{self.getProxyUrl()}&url={enc}&type=img"
        except Exception:
            return u

    def _parse_rank(self, html):
        if not html:
            return []
        items = []
        seen = set()
        blocks = re.split(r'class="[^"]*hg-rank-item[^"]*"', html)[1:]
        for block in blocks:
            try:
                m = re.search(r'href=["\'](/detail/(\d+)/)["\']', block)
                if not m:
                    continue
                vid = m.group(2)
                if vid in seen:
                    continue
                seen.add(vid)
                title = ""
                tm = re.search(r'hg-rank-item__title[^>]*>(.*?)</', block, re.S)
                if tm:
                    title = re.sub(r'<[^>]+>', '', tm.group(1)).strip()
                if not title:
                    continue
                pic = ""
                pm = re.search(r'data-src=["\']([^"\']+)["\']', block) or re.search(r'src=["\']([^"\']+)["\']', block)
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

        # 标题
        name = ""
        m = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.S)
        if m:
            name = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        if not name:
            return result

        # 封面
        pic = ""
        pm = re.search(r'hg-web-detail__poster[\s\S]{0,500}?(?:data-src|src)=["\']([^"\']+)["\']', html)
        if pm:
            pic = self._proxy_pic(pm.group(1))
        if not pic or "placeholder" in pic:
            # 备用 og:image
            om = re.search(r'<meta[^>]*property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
            if om:
                pic = self._proxy_pic(om.group(1))

        # ★简介：优先 og:description / meta description（最稳）
        desc = ""
        for pat in [
            r'<meta[^>]*property=["\']og:description["\'][^>]*content=["\']([^"\']+)["\']',
            r'<meta[^>]*name=["\']description["\'][^>]*content=["\']([^"\']+)["\']',
            r'class="[^"]*hg-web-detail__desc[^"]*"[^>]*>([\s\S]*?)</div>',
        ]:
            dm = re.search(pat, html, re.I)
            if dm:
                desc = re.sub(r'<[^>]+>', '', dm.group(1)).strip()
                if len(desc) > 15:
                    break

        # 分集
        eps = []
        for am in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*data-ep-id=["\']?(\d+)["\']?', html):
            href = self._fix(am.group(1))
            eid = am.group(2)
            eps.append(f"第{eid}集${href}")
        if not eps:
            pm = re.search(r'hg-web-detail__play[^>]*href=["\']([^"\']+)["\']', html)
            if pm:
                eps = [f"第1集${self._fix(pm.group(1))}"]
        if not eps:
            return result

        info = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": pic,
            "vod_play_from": "黄果短剧",
            "vod_play_url": "#".join(eps),
            "vod_content": desc,
        }
        result["list"].append(info)
        return result

    def searchContent(self, key, quick, pg="1"):
        from urllib.parse import quote as q
        html = self._get_html(f"/search/video/{q(key)}/")
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
        """图片代理：带正确 Referer 拉取封面"""
        try:
            url = param.get("url") or ""
            if not url:
                return [404, "text/plain", b""]
            # base64 解码
            try:
                url = b64decode(unquote(url)).decode("utf-8")
            except Exception:
                pass
            headers = {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            }
            r = self.fetch(url, headers=headers, timeout=15, verify=False)
            if r is None:
                return [404, "text/plain", b""]
            content = r.content if hasattr(r, "content") else b""
            ctype = "image/jpeg"
            if content[:8] == b"\x89PNG\r\n\x1a\n":
                ctype = "image/png"
            elif content[:4] == b"RIFF":
                ctype = "image/webp"
            elif content[:6] in (b"GIF87a", b"GIF89a"):
                ctype = "image/gif"
            return [200, ctype, content]
        except Exception:
            return [404, "text/plain", b""]

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass
