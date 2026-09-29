# -*- coding: utf-8 -*-
# 黄果短剧 - OK影视/FongMi 兼容版
# 主站 API: https://huangguoai.com
import re
import sys
import json
import time
from base64 import b64encode, b64decode
from urllib.parse import quote, unquote

sys.path.append("..")
try:
    from base.spider import Spider as BaseSpider
except Exception:
    class BaseSpider(object):
        def fetch(self, url, headers=None, timeout=15, verify=False, **kw):
            import urllib.request
            req = urllib.request.Request(url, headers=headers or {})
            try:
                import ssl
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            except Exception:
                resp = urllib.request.urlopen(req, timeout=timeout)
            class R:
                pass
            r = R()
            r.content = resp.read()
            r.text = r.content.decode("utf-8", errors="ignore")
            r.status_code = getattr(resp, "status", 200)
            return r

try:
    from Crypto.Cipher import AES as _AES
except Exception:
    try:
        from Cryptodome.Cipher import AES as _AES
    except Exception:
        _AES = None


class Spider(BaseSpider):
    def getName(self):
        return "黄果短剧"

    def init(self, extend=""):
        self.host = "https://tsgax.kmexvuoz.cc"
        self.hosts = [
        "https://tsgax.kmexvuoz.cc",
        "https://r9ccl0.kmexvuoz.cc",
        ]
        self.ua = (
            "Mozilla/5.0 (Linux; Android 13; Mobile) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Mobile Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "application/json, text/html, */*",
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
        self.filters = {
            "ai-duanju": [{"key": "sort", "name": "排序", "value": [
                {"n": "最新更新", "v": "latest"},
                {"n": "当前热播", "v": "hot"},
                {"n": "随机推荐", "v": "random"},
            ]}],
            "ai-manju": [{"key": "sort", "name": "排序", "value": [
                {"n": "最新更新", "v": "latest"},
                {"n": "当前热播", "v": "hot"},
                {"n": "随机推荐", "v": "random"},
            ]}],
            "ai-huanlian": [{"key": "sort", "name": "排序", "value": [
                {"n": "最新更新", "v": "latest"},
                {"n": "当前热播", "v": "hot"},
                {"n": "随机推荐", "v": "random"},
            ]}],
            "ai-mogai": [{"key": "sort", "name": "排序", "value": [
                {"n": "最新更新", "v": "latest"},
                {"n": "当前热播", "v": "hot"},
                {"n": "随机推荐", "v": "random"},
            ]}],
        }
        self._IMG_KEY = bytes([102, 53, 100, 57, 54, 53, 100, 102, 55, 53, 51, 51, 54, 50, 55, 48])
        self._IMG_IV = bytes([57, 55, 98, 54, 48, 51, 57, 52, 97, 98, 99, 50, 102, 98, 101, 49])
        self._alive_host = None

    def _hdr(self, referer=None):
        h = dict(self.headers)
        h["Referer"] = (referer or self.host) + "/"
        return h

    def _raw_get(self, url, headers=None, timeout=15):
        headers = headers or self._hdr()
        try:
            r = self.fetch(url, headers=headers, timeout=timeout, verify=False)
            if r is not None:
                return r
        except Exception:
            pass
        try:
            import requests
            return requests.get(url, headers=headers, timeout=timeout, verify=False)
        except Exception:
            pass
        try:
            import urllib.request
            import ssl
            req = urllib.request.Request(url, headers=headers)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            resp = urllib.request.urlopen(req, timeout=timeout, context=ctx)
            class R:
                pass
            out = R()
            out.content = resp.read()
            out.text = out.content.decode("utf-8", errors="ignore")
            out.status_code = 200
            return out
        except Exception:
            return None

    def _text(self, r):
        if r is None:
            return ""
        if hasattr(r, "text") and r.text:
            return r.text
        if hasattr(r, "content") and r.content:
            try:
                return r.content.decode("utf-8", errors="ignore")
            except Exception:
                return str(r.content)
        return str(r)

    def _json(self, r):
        try:
            if hasattr(r, "json"):
                return r.json()
            return json.loads(self._text(r))
        except Exception:
            return {}

    def _pick_host(self):
        if self._alive_host:
            return self._alive_host
        for h in self.hosts:
            try:
                r = self._raw_get(
                    h + "/api/videos/category/ai-duanju?page=1&size=1&sort=latest",
                    timeout=10,
                )
                data = self._json(r)
                if isinstance(data, dict) and data.get("data"):
                    self._alive_host = h
                    self.host = h
                    return h
            except Exception:
                continue
        self._alive_host = self.hosts[0]
        self.host = self._alive_host
        return self.host

    def _fetch(self, url, referer=None, asjson=False, raw=False):
        fail = {} if asjson else (b"" if raw else "")
        if not url:
            return fail
        if url.startswith("/"):
            url = self._pick_host() + url
        for _ in range(2):
            try:
                r = self._raw_get(url, headers=self._hdr(referer), timeout=18)
                if r is None:
                    time.sleep(0.3)
                    continue
                if asjson:
                    return self._json(r)
                if raw:
                    return r.content if hasattr(r, "content") else b""
                text = self._text(r)
                if text and len(text) > 50:
                    return text
            except Exception:
                time.sleep(0.3)
        return fail

    def _get_bin(self, url):
        return self._fetch(url, raw=True)

    def _fix(self, u):
        if not u:
            return ""
        if u.startswith("//"):
            return "https:" + u
        if u.startswith("/"):
            return self.host + u
        return u

    def _img_src(self, u):
        u = self._fix(u or "")
        if u.startswith("http") and "?" in u:
            u = re.sub(r"\?.*", "", u)
        return u

    def _proxy_pic(self, u):
        u = self._img_src(u)
        if not u or "placeholder" in u or "data:image" in u:
            return ""
        try:
            enc = quote(b64encode(u.encode("utf-8")).decode("utf-8"), safe="")
            try:
                proxy = self.getProxyUrl()
                if proxy:
                    return f"{proxy}&url={enc}&type=img"
            except Exception:
                pass
            return u
        except Exception:
            return u

    def _decrypt_img(self, raw):
        if not raw or _AES is None or len(raw) % 16 != 0:
            return raw
        try:
            pt = _AES.new(self._IMG_KEY, _AES.MODE_CBC, self._IMG_IV).decrypt(raw)
        except Exception:
            return raw
        if not (
            pt[:2] == b"\xff\xd8"
            or pt[:8] == b"\x89PNG\r\n\x1a\n"
            or pt[:4] == b"RIFF"
            or pt[:6] in (b"GIF87a", b"GIF89a")
        ):
            return raw
        pad = pt[-1]
        if 0 < pad <= 16 and pt[-pad:] == bytes([pad]) * pad:
            pt = pt[:-pad]
        return pt

    def _img_ct(self, data):
        if not data:
            return "image/jpeg"
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if data[:4] == b"RIFF" and len(data) > 12 and data[8:12] == b"WEBP":
            return "image/webp"
        return "image/jpeg"

    def _api_items(self, path):
        host = self._pick_host()
        data = self._fetch(host + path, asjson=True)
        if not isinstance(data, dict):
            return None, None
        body = data.get("data")
        if not isinstance(body, dict):
            return None, None
        items = body.get("items")
        if not isinstance(items, list):
            return None, None
        pag = body.get("pagination") if isinstance(body.get("pagination"), dict) else None
        return items, pag

    @staticmethod
    def _api_remarks(item):
        if not isinstance(item, dict):
            return ""
        if item.get("is_finished"):
            try:
                total = int(item.get("episode_count") or item.get("total_episodes") or 0)
            except Exception:
                total = 0
            return ("全%d集" % total) if total else "已完结"
        try:
            ep = int(item.get("episode_count") or 0)
        except Exception:
            ep = 0
        if ep:
            return "更新至%d集" % ep
        score = item.get("score")
        if score not in (None, ""):
            return str(score) + "分"
        return ""

    def _api_video_item(self, item):
        vid = str(item.get("id") or item.get("video_id") or "")
        if not vid:
            return None
        remarks = self._api_remarks(item)
        tags = item.get("tags")
        if isinstance(tags, list) and tags:
            tag_str = "·".join([str(t) for t in tags[:3] if t])
            if tag_str:
                remarks = (remarks + " " + tag_str).strip() if remarks else tag_str
        return {
            "vod_id": vid,
            "vod_name": item.get("title") or "",
            "vod_pic": self._proxy_pic(item.get("cover") or ""),
            "vod_remarks": remarks,
        }

    def _list_from_api(self, tid, pg=1, sort="latest", size=24):
        path = "/api/videos/category/%s?page=%d&size=%d&sort=%s" % (tid, pg, size, sort)
        items, pag = self._api_items(path)
        lst = []
        if items:
            for it in items:
                v = self._api_video_item(it)
                if v:
                    lst.append(v)
        pages = 1
        total = len(lst)
        if pag:
            try:
                pages = int(pag.get("pages") or 1)
                total = int(pag.get("total") or total)
            except Exception:
                pages = pg + 1 if lst else pg
        elif lst:
            pages = pg + 1
        return {
            "list": lst,
            "page": pg,
            "pagecount": max(pages, 1),
            "limit": size,
            "total": total or 99999,
        }

    def _parse_cards_html(self, html):
        if not html:
            return []
        items, seen = [], set()
        for m in re.finditer(
            r'href=["\'](?:https?://[^"\']+)?(/video/(\d+)/?)["\']',
            html,
            re.I,
        ):
            vid = m.group(2)
            if vid in seen:
                continue
            start = max(0, m.start() - 100)
            chunk = html[start : m.start() + 1500]
            title = ""
            for pat in (
                r'(?:alt|title)=["\']([^"\']{2,100})["\']',
                r"<h[123][^>]*>([\s\S]*?)</h[123]>",
            ):
                tm = re.search(pat, chunk, re.I)
                if tm:
                    title = re.sub(r"<[^>]+>", "", tm.group(1)).strip()
                    title = re.sub(r"\s+", " ", title)
                    if len(title) >= 2:
                        break
            if not title:
                continue
            seen.add(vid)
            pic = ""
            pm = re.search(r'(?:data-src|src)=["\'](https?://[^"\']+)["\']', chunk)
            if pm:
                pic = self._proxy_pic(pm.group(1))
            rem = ""
            rm = re.search(r"((?:更新至|全)\d+集)", chunk)
            if rm:
                rem = rm.group(1)
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_remarks": rem,
            })
        return items

    def homeContent(self, filter):
        result = {"class": self.categories, "filters": self.filters, "list": []}
        try:
            data = self._list_from_api("ai-duanju", 1, "latest", 24)
            result["list"] = data.get("list") or []
        except Exception:
            pass
        if not result["list"]:
            try:
                html = self._fetch(self._pick_host() + "/ai-duanju/")
                result["list"] = self._parse_cards_html(html)
            except Exception:
                pass
        return result

    def homeVideoContent(self):
        try:
            data = self._list_from_api("ai-duanju", 1, "latest", 24)
            if data.get("list"):
                return {"list": data["list"]}
        except Exception:
            pass
        try:
            html = self._fetch(self._pick_host() + "/ai-duanju/")
            return {"list": self._parse_cards_html(html)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        pg = max(int(pg or 1), 1)
        tid = str(tid or "").strip("/")
        ext = extend if isinstance(extend, dict) else {}
        sort = ext.get("sort") or "latest"
        if sort == "original":
            sort = "hot"
        empty = {"list": [], "page": pg, "pagecount": 1, "limit": 24, "total": 0}
        try:
            if tid in ("ranks", "ranks/hot", "rank"):
                items, pag = self._api_items("/api/ranks/hot?page=%d&size=24" % pg)
                lst = []
                if items:
                    for it in items:
                        v = self._api_video_item(it)
                        if v:
                            lst.append(v)
                pages = (pag or {}).get("pages") or (pg + 1 if lst else 1)
                return {
                    "list": lst,
                    "page": pg,
                    "pagecount": int(pages),
                    "limit": 24,
                    "total": (pag or {}).get("total") or 99999,
                }
            data = self._list_from_api(tid, pg, sort, 24)
            if data.get("list"):
                return data
            path = "/%s/" % tid if pg == 1 else "/%s/%d/" % (tid, pg)
            html = self._fetch(self._pick_host() + path)
            cards = self._parse_cards_html(html)
            return {
                "list": cards,
                "page": pg,
                "pagecount": 9999 if cards else pg,
                "limit": 24,
                "total": 99999,
            }
        except Exception:
            return empty

    def detailContent(self, ids):
        vid = str(ids[0]) if ids else ""
        if not vid:
            return {"list": []}
        title, cover, desc = "", "", ""
        episode_count = 0
        host = self._pick_host()
        try:
            data = self._fetch(host + "/api/videos/detail/" + vid, asjson=True)
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                item = data["data"]
                title = item.get("title") or ""
                cover = self._proxy_pic(item.get("cover") or "")
                desc = item.get("description") or ""
                try:
                    episode_count = int(
                        item.get("episode_count") or item.get("total_episodes") or 0
                    )
                except Exception:
                    episode_count = 0
        except Exception:
            pass
        html = ""
        if not title:
            for path in ("/video/%s/" % vid, "/detail/%s/" % vid):
                html = self._fetch(host + path) or ""
                if html and ("<h1" in html or "og:title" in html):
                    break
            if html:
                m = re.search(r"<h1[^>]*>([\s\S]*?)</h1>", html)
                if m:
                    title = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                    title = re.sub(r"\s*第\s*\d+\s*集\s*$", "", title).strip()
                if not title:
                    m = re.search(
                        r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)',
                        html, re.I,
                    )
                    if m:
                        title = m.group(1).strip()
                if not cover:
                    m = re.search(
                        r'property=["\']og:image["\'][^>]*content=["\'](https?://[^"\']+)',
                        html, re.I,
                    )
                    if m:
                        cover = self._proxy_pic(m.group(1))
                if not desc:
                    m = re.search(
                        r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)',
                        html, re.I,
                    )
                    if m:
                        desc = m.group(1).strip()
        if not title:
            title = "视频%s" % vid
        ep_srcs = self._extract_sources(vid, episode_count)
        if ep_srcs:
            segs = [
                "第%s集$%s" % (ep, src)
                for ep, src in sorted(
                    ep_srcs.items(),
                    key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0,
                )
            ]
            play_url = "#".join(segs)
        else:
            n = max(episode_count, 1)
            segs = []
            for i in range(1, n + 1):
                if i == 1:
                    segs.append("第1集$%s/video/%s/" % (host, vid))
                else:
                    segs.append("第%d集$%s/video/%s/ep-%d/" % (i, host, vid, i))
            play_url = "#".join(segs)
        return {
            "list": [{
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": cover,
                "vod_content": desc,
                "vod_play_from": "黄果短剧",
                "vod_play_url": play_url,
                "vod_remarks": ("更新至%d集" % episode_count) if episode_count else "",
            }]
        }

    def _extract_sources(self, vid, max_hint=0):
        ep_srcs = {}
        host = self._pick_host()
        max_check = min(max(max_hint, 1) + 3, 40)
        for check_ep in range(1, max_check + 1):
            url = (
                host + "/video/%s/" % vid
                if check_ep == 1
                else host + "/video/%s/ep-%d/" % (vid, check_ep)
            )
            html = self._fetch(url)
            if not html:
                if check_ep > 1:
                    break
                continue
            found = False
            mm = re.search(
                r'<script[^>]*id=["\']videoInitialData["\'][^>]*>([\s\S]*?)</script>',
                html, re.I,
            )
            if mm:
                try:
                    data = json.loads(mm.group(1))
                    srcs = data.get("epPlaySrcs") or {}
                    if isinstance(srcs, dict):
                        for ep, src in srcs.items():
                            if src and str(ep) not in ep_srcs:
                                src = str(src).replace("\\u0026", "&")
                                if src.startswith("//"):
                                    src = "https:" + src
                                ep_srcs[str(ep)] = src
                                found = True
                    vs = data.get("videoSrc") or ""
                    if vs and str(check_ep) not in ep_srcs:
                        vs = str(vs).replace("\\u0026", "&")
                        if vs.startswith("//"):
                            vs = "https:" + vs
                        ep_srcs[str(check_ep)] = vs
                        found = True
                except Exception:
                    pass
            if not found:
                m3 = re.search(
                    r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', html
                )
                if m3 and str(check_ep) not in ep_srcs:
                    ep_srcs[str(check_ep)] = m3.group(1).replace("\\u0026", "&")
                    found = True
            if check_ep == 1:
                for e in re.findall(r'data-ep-id=["\']?(\d+)', html):
                    try:
                        n = int(e)
                        if n > max_check:
                            max_check = min(n + 1, 40)
                    except Exception:
                        pass
            if not found and check_ep > 1 and str(check_ep) not in ep_srcs:
                break
            if check_ep > 1:
                time.sleep(0.1)
        return ep_srcs

    def searchContent(self, key, quick, pg="1"):
        page = max(int(pg or 1), 1)
        result = {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}
        host = self._pick_host()
        try:
            url = host + "/search/?keyword=%s" % quote(key)
            if page > 1:
                url += "&page=%d" % page
            html = self._fetch(url)
            if not html:
                html = self._fetch(host + "/search/video/%s/" % quote(key))
            if not html:
                return result
            videos, seen = [], set()
            for m in re.finditer(r'data-track-id=["\'](\d+)["\']', html):
                vid = m.group(1)
                if vid in seen:
                    continue
                chunk = html[m.start() : m.start() + 900]
                tm = re.search(r'data-track-title=["\']([^"\']*)["\']', chunk)
                pm = re.search(
                    r'(?:data-src|src)=["\'](https?://[^"\']+)["\']', chunk
                )
                videos.append({
                    "vod_id": vid,
                    "vod_name": tm.group(1) if tm else "",
                    "vod_pic": self._proxy_pic(pm.group(1)) if pm else "",
                    "vod_remarks": "",
                })
                seen.add(vid)
            if not videos:
                videos = self._parse_cards_html(html)
            result["list"] = videos
            pm2 = re.search(r'data-pages=["\'](\d+)["\']', html)
            result["pagecount"] = int(pm2.group(1)) if pm2 else (
                page + 1 if len(videos) >= 20 else page
            )
        except Exception:
            pass
        return result

    def playerContent(self, flag, id, vipFlags):
        header = {"User-Agent": self.ua, "Referer": self.host + "/"}
        result = {"parse": 0, "url": "", "header": header}
        raw = str(id or "").strip()
        if not raw:
            return result
        if raw.startswith("http") and (".m3u8" in raw or ".mp4" in raw):
            result["url"] = raw
            return result
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self._fix(raw)
        elif raw.isdigit():
            url = "%s/video/%s/" % (self._pick_host(), raw)
        else:
            url = self._fix(raw)
        html = self._fetch(url, referer=self.host)
        play = ""
        if html:
            mm = re.search(
                r'<script[^>]*id=["\']videoInitialData["\'][^>]*>([\s\S]*?)</script>',
                html, re.I,
            )
            if mm:
                try:
                    data = json.loads(mm.group(1))
                    em = re.search(r"/ep-(\d+)/", url)
                    ep = str(em.group(1)) if em else "1"
                    srcs = data.get("epPlaySrcs") or {}
                    play = srcs.get(ep) or data.get("videoSrc") or ""
                except Exception:
                    pass
            if play:
                play = str(play).replace("\\u0026", "&")
                if play.startswith("//"):
                    play = "https:" + play
                if not play.startswith("http"):
                    m2 = re.search(r"(https?://[^\s\"']+)", play)
                    play = m2.group(1) if m2 else ""
            if not play:
                m = re.search(
                    r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', html
                )
                if m:
                    play = m.group(1).replace("\\u0026", "&")
        result["url"] = play
        return result

    def localProxy(self, param):
        try:
            url = param.get("url") or ""
            if not url:
                return [404, "text/plain", b""]
            try:
                url = b64decode(unquote(str(url))).decode("utf-8")
            except Exception:
                pass
            url = self._img_src(url)
            raw = self._get_bin(url)
            if not raw:
                return [404, "text/plain", b""]
            data = self._decrypt_img(raw)
            return [200, self._img_ct(data), data]
        except Exception:
            return [404, "text/plain", b""]

    def isVideoFormat(self, url):
        u = (url or "").lower()
        return ".m3u8" in u or ".mp4" in u or ".flv" in u

    def manualVideoCheck(self):
        return False

    def destroy(self):
        pass
