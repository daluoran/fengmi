# -*- coding: utf-8 -*-
# 黄果短剧 - 推荐仅短剧 + 新域名
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
            "https://oimjl.mvbessfgf.cc",
            "https://14a.bhefwntk.cc",
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
        headers = {
            "User-Agent": self.headers["User-Agent"],
            "Referer": self.host + "/",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
        for _ in range(2):
            try:
                r = self.fetch(url, headers=headers, timeout=15, verify=False)
                if r is None:
                    continue
                content = r.content if hasattr(r, "content") else None
                if content and len(content) > 100:
                    return content
            except Exception:
                time.sleep(0.3)
        return None

    def _get_html(self, path):
        for h in self.hosts:
            self.host = h
            url = path if path.startswith("http") else (h + path)
            html = self._fetch(url)
            if html and ("/detail/" in html or "hg-drama-card" in html):
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
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', s)).strip()

    def _decrypt_img(self, raw):
        if not raw or _AES is None or len(raw) % 16 != 0:
            return raw
        try:
            pt = _AES.new(self._IMG_KEY, _AES.MODE_CBC, self._IMG_IV).decrypt(raw)
        except Exception:
            return raw
        if not (pt[:2] == b"\xff\xd8" or pt[:8] == b"\x89PNG\r\n\x1a\n"
                or pt[:4] == b"RIFF" or pt[:6] in (b"GIF87a", b"GIF89a")):
            return raw
        pad = pt[-1]
        if 0 < pad <= 16 and pt[-pad:] == bytes([pad]) * pad:
            pt = pt[:-pad]
        return pt

    def _proxy_pic(self, u):
        u = self._fix(u or "")
        if not u or "placeholder" in u or "data:image" in u:
            return ""
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
        for m in re.finditer(r'<div class="hg-drama-card"[^>]*>', html):
            start = m.start()
            chunk = html[start:start + 1200]
            if "hg-search-suggest" in chunk or "hot-item" in chunk:
                continue
            mid = re.search(r'/detail/(\d+)/', chunk)
            if not mid:
                continue
            vid = mid.group(1)
            if vid in seen:
                continue
            seen.add(vid)
            title = ""
            am = re.search(r'alt=["\']([^"\']{1,80})["\']', chunk)
            if am:
                title = self._clean(am.group(1))
            if not title:
                tm = re.search(r'hg-drama-card__title[^>]*>\s*<a[^>]*>([^<]+)</a>', chunk)
                if tm:
                    title = self._clean(tm.group(1))
            if not title:
                continue
            pic = ""
            pm = re.search(r'data-src=["\'](https?://[^"\']+)["\']', chunk)
            if pm:
                pic = self._proxy_pic(pm.group(1))
            rem = ""
            rm = re.search(r'hg-drama-card__episode[^>]*>[\s\S]*?((?:更新至|全)\d+集)', chunk)
            if rm:
                rem = rm.group(1)
            sm = re.search(r'hg-drama-card__score[^>]*>([\d.]+分?)', chunk)
            if sm:
                score = sm.group(1)
                rem = f"{rem} · {score}" if rem else score
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": rem,
            })
        return items

    def _parse_rank(self, html):
        return self._parse_cards(html)

    def homeContent(self, filter):
        # 方案A：推荐只显示 AI 成人短剧
        html = self._get_html("/ai-duanju/")
        return {"class": self.categories, "list": self._parse_cards(html), "filters": {}}

    def homeVideoContent(self):
        html = self._get_html("/ai-duanju/")
        return {"list": self._parse_cards(html)}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid).strip("/")
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
            r'data-src=["\'](https?://pic\.[^"\']+)["\']',
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
                    ep = "1"
                    m_ep = re.search(r'/ep-(\d+)/?', url)
                    if m_ep:
                        ep = m_ep.group(1)
                    else:
                        cur = data.get("ep")
                        if cur is not None:
                            ep = str(cur)
                    play = srcs.get(ep) or data.get("videoSrc") or ""
                    if not play and srcs:
                        play = srcs.get(ep) or list(srcs.values())[0]
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
