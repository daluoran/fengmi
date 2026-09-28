# -*- coding: utf-8 -*-
# 黄果短剧 - 适配当前站点 (API优先 + HTML回退)
# 主站: https://huangguoai.com
import re
import sys
import json
import time
from base64 import b64encode, b64decode
from urllib.parse import quote, unquote

sys.path.append("..")
from base.spider import Spider

try:
    from Crypto.Cipher import AES as _AES
except Exception:
    try:
        from Cryptodome.Cipher import AES as _AES
    except Exception:
        _AES = None

try:
    from lxml import etree
except Exception:
    etree = None


class Spider(Spider):
    def getName(self):
        return "黄果短剧"

    def init(self, extend=""):
        self.host = "https://huangguoai.com"
        self.hosts = [
            "https://huangguoai.com",
            "https://mhtl9n.hwqlgzvsk.cc",
            "https://v7u6.fejivxks.cc",
            "https://ro6o3.fejivxks.cc",
        ]
        self.ua = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
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
        # AES-128-CBC 封面解密密钥
        self._IMG_KEY = bytes([102, 53, 100, 57, 54, 53, 100, 102, 55, 53, 51, 51, 54, 50, 55, 48])
        self._IMG_IV = bytes([57, 55, 98, 54, 48, 51, 57, 52, 97, 98, 99, 50, 102, 98, 101, 49])

    # ---------- 基础请求 ----------
    def _hdr(self, referer=None):
        h = dict(self.headers)
        h["Referer"] = (referer or self.host) + "/"
        return h

    def _fetch(self, url, referer=None, asjson=False, raw=False):
        fail = {} if asjson else (b"" if raw else "")
        if not url:
            return fail
        for _ in range(3):
            try:
                r = self.fetch(url, headers=self._hdr(referer), timeout=18, verify=False)
                if r is None:
                    time.sleep(0.4)
                    continue
                if asjson:
                    try:
                        if hasattr(r, "json"):
                            return r.json()
                        text = r.text if hasattr(r, "text") else str(r)
                        return json.loads(text)
                    except Exception:
                        return {}
                if raw:
                    return r.content if hasattr(r, "content") else b""
                text = r.text if hasattr(r, "text") else str(r)
                if text and len(text) > 100:
                    return text
            except Exception:
                time.sleep(0.4)
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

    def _clean(self, s):
        if not s:
            return ""
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s)).strip()

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
            return f"{self.getProxyUrl()}&url={enc}&type=img"
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
        if pt[:2] == b"\xff\xd8":
            i = pt.rfind(b"\xff\xd9")
            if i >= 0:
                pt = pt[: i + 2]
        elif pt[:8] == b"\x89PNG\r\n\x1a\n":
            i = pt.rfind(b"IEND")
            if i >= 0:
                pt = pt[: i + 8]
        return pt

    def _img_ct(self, data):
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if data[:4] == b"RIFF" and len(data) > 12 and data[8:12] == b"WEBP":
            return "image/webp"
        if data[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        return "image/jpeg"

    # ---------- API ----------
    def _api_items(self, path):
        data = self._fetch(self.host + path, asjson=True)
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

    def _api_rank_item(self, item):
        vid = str(item.get("video_id") or item.get("id") or "")
        if not vid:
            return None
        try:
            rank = item.get("rank")
            label = item.get("metric_label") or ""
            value = item.get("metric_value")
            remarks = ("#%s %s%s" % (rank, label, value)).strip() if rank else ""
        except Exception:
            remarks = ""
        if not remarks:
            remarks = self._api_remarks(item)
        return {
            "vod_id": vid,
            "vod_name": item.get("title") or "",
            "vod_pic": self._proxy_pic(item.get("cover") or ""),
            "vod_remarks": remarks,
        }

    # ---------- HTML 卡片解析 (回退) ----------
    def _parse_cards_html(self, html):
        if not html:
            return []
        items, seen = [], set()
        # 新结构: /video/ID/
        for m in re.finditer(
            r'href=["\'](/video/(\d+)/?)["\'][^>]*>[\s\S]{0,800}?(?:data-src|src)=["\'](https?://[^"\']+)["\']',
            html,
            re.I,
        ):
            vid, pic = m.group(2), m.group(3)
            if vid in seen:
                continue
            chunk = html[max(0, m.start() - 200) : m.start() + 1200]
            title = ""
            tm = re.search(r"(?:alt|title)=[\"']([^\"']{2,80})[\"']", chunk)
            if tm:
                title = self._clean(tm.group(1))
            if not title:
                tm2 = re.search(r"<h[23][^>]*>([\s\S]*?)</h[23]>", chunk)
                if tm2:
                    title = self._clean(tm2.group(1))
            if not title:
                continue
            seen.add(vid)
            rem = ""
            rm = re.search(r"((?:更新至|全)\d+集)", chunk)
            if rm:
                rem = rm.group(1)
            sm = re.search(r"([\d.]+)\s*分", chunk)
            if sm:
                rem = (rem + " · " + sm.group(1) + "分") if rem else (sm.group(1) + "分")
            items.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": self._proxy_pic(pic),
                "vod_remarks": rem,
            })
        if items:
            return items
        # 旧结构: hg-drama-card + /detail/
        if etree is not None:
            try:
                tree = etree.HTML(html)
                nodes = tree.xpath('//*[contains(@class,"hg-drama-card")]')
                for card in nodes:
                    a = card.xpath('.//a[contains(@href,"/detail/") or contains(@href,"/video/")]')
                    if not a:
                        continue
                    href = a[0].get("href", "")
                    m = re.search(r"/(?:detail|video)/(\d+)/?", href)
                    if not m or m.group(1) in seen:
                        continue
                    img = (card.xpath(".//img/@data-src") or card.xpath(".//img/@src") or [""])[0]
                    title = "".join(
                        card.xpath('.//*[contains(@class,"hg-drama-card__title")]//text()')
                    ).strip()
                    if not title:
                        title = a[0].get("title", "").strip()
                    if not title:
                        continue
                    seen.add(m.group(1))
                    rem = "".join(
                        card.xpath('.//*[contains(@class,"hg-drama-card__episode")]//text()')
                    ).strip()
                    score = "".join(
                        card.xpath('.//*[contains(@class,"hg-drama-card__score")]//text()')
                    ).strip()
                    if rem and score:
                        rem = rem + " · " + score
                    elif not rem:
                        rem = score
                    items.append({
                        "vod_id": m.group(1),
                        "vod_name": title,
                        "vod_pic": self._proxy_pic(img),
                        "vod_remarks": rem,
                    })
            except Exception:
                pass
        return items

    # ---------- 入口 ----------
    def homeContent(self, filter):
        return {"class": self.categories, "filters": self.filters, "list": []}

    def homeVideoContent(self):
        items, _ = self._api_items("/api/videos/category/ai-duanju?page=1&size=24&sort=latest")
        if items:
            vids, seen = [], set()
            for it in items:
                v = self._api_video_item(it)
                if v and v["vod_id"] not in seen:
                    seen.add(v["vod_id"])
                    vids.append(v)
            if vids:
                return {"list": vids}
        html = self._fetch(self.host + "/ai-duanju/")
        return {"list": self._parse_cards_html(html)}

    def categoryContent(self, tid, pg, filter, extend):
        pg = max(int(pg or 1), 1)
        tid = str(tid or "").strip("/")
        ext = extend if isinstance(extend, dict) else {}
        sort = ext.get("sort", "latest") or "latest"
        if sort == "original":
            sort = "hot"

        # 排行榜
        if tid in ("ranks", "ranks/hot", "rank"):
            items, pag = self._api_items("/api/ranks/hot?page=%d&size=24" % pg)
            lst = []
            if items:
                for it in items:
                    v = self._api_rank_item(it)
                    if v:
                        lst.append(v)
            pages = (pag or {}).get("pages") or (pg + 1 if lst else pg)
            return {
                "page": pg,
                "pagecount": int(pages),
                "limit": 24,
                "total": (pag or {}).get("total") or 99999,
                "list": lst,
            }

        # 分类 API
        path = "/api/videos/category/%s?page=%d&size=24&sort=%s" % (tid, pg, sort)
        items, pag = self._api_items(path)
        if items:
            lst = []
            for it in items:
                v = self._api_video_item(it)
                if v:
                    lst.append(v)
            pages = (pag or {}).get("pages") or (pg + 1 if lst else pg)
            return {
                "page": pg,
                "pagecount": int(pages),
                "limit": 24,
                "total": (pag or {}).get("total") or 99999,
                "list": lst,
            }

        # HTML 回退
        path_html = "/%s/" % tid if pg == 1 else "/%s/%d/" % (tid, pg)
        html = self._fetch(self.host + path_html)
        cards = self._parse_cards_html(html)
        return {
            "page": pg,
            "pagecount": 9999 if cards else pg,
            "limit": 24,
            "total": 99999,
            "list": cards,
        }

    def detailContent(self, ids):
        vid = str(ids[0]) if ids else ""
        if not vid:
            return {"list": []}
        result = {"list": []}
        title, cover, desc = "", "", ""
        episode_count = 0

        # 1) API 详情
        data = self._fetch(self.host + "/api/videos/detail/" + vid, asjson=True)
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            item = data["data"]
            title = item.get("title") or ""
            cover = self._proxy_pic(item.get("cover") or "")
            desc = item.get("description") or ""
            try:
                episode_count = int(item.get("episode_count") or item.get("total_episodes") or 0)
            except Exception:
                episode_count = 0

        # 2) HTML 补全标题/封面
        html = ""
        if not title or not cover:
            for path in ("/video/%s/" % vid, "/detail/%s/" % vid):
                html = self._fetch(self.host + path) or ""
                if html and ("<h1" in html or "og:title" in html):
                    break
            if html:
                if not title:
                    m = re.search(r'<h1[^>]*>([\s\S]*?)</h1>', html)
                    if m:
                        title = re.sub(r"\s*第\s*\d+\s*集\s*$", "", self._clean(m.group(1))).strip()
                    if not title:
                        m = re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html, re.I)
                        if m:
                            title = self._clean(m.group(1))
                if not cover:
                    for pat in (
                        r'property=["\']og:image["\'][^>]*content=["\'](https?://[^"\']+)',
                        r'data-src=["\'](https?://[^"\']+)["\']',
                        r'src=["\'](https?://pic\.[^"\']+)["\']',
                    ):
                        pm = re.search(pat, html, re.I)
                        if pm:
                            cover = self._proxy_pic(pm.group(1))
                            break
                if not desc:
                    m = re.search(r'property=["\']og:description["\'][^>]*content=["\']([^"\']+)', html, re.I)
                    if m:
                        desc = self._clean(m.group(1))

        if not title:
            title = "视频%s" % vid

        # 3) 提取集数播放地址
        ep_srcs = self._extract_sources(vid, episode_count)
        if ep_srcs:
            segs = ["第%s集$%s" % (ep, src) for ep, src in sorted(ep_srcs.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0)]
            play_url = "#".join(segs)
        else:
            # 最后回退：把详情页当第1集入口，由 playerContent 再解析
            play_url = "第1集$%s/video/%s/" % (self.host, vid)

        result["list"].append({
            "vod_id": vid,
            "vod_name": title,
            "vod_pic": cover,
            "vod_content": desc,
            "vod_play_from": "黄果短剧",
            "vod_play_url": play_url,
            "vod_remarks": ("更新至%d集" % episode_count) if episode_count else "",
        })
        return result

    def _extract_sources(self, vid, max_hint=0):
        """从 /video/ID/ 与 /video/ID/ep-N/ 提取各集直链"""
        ep_srcs = {}
        max_check = max(max_hint, 1) + 5
        if max_check > 80:
            max_check = 80
        check_ep = 1
        while check_ep <= max_check:
            url = "/video/%s/" % vid if check_ep == 1 else "/video/%s/ep-%d/" % (vid, check_ep)
            html = self._fetch(self.host + url)
            if not html:
                if check_ep > 1:
                    break
                check_ep += 1
                continue
            found = False
            # videoInitialData JSON
            mm = re.search(
                r'<script[^>]*id=["\']videoInitialData["\'][^>]*>([\s\S]*?)</script>',
                html,
                re.I,
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
            # 正则兜底
            if not found:
                for m in re.finditer(r'"epPlaySrcs"\s*:\s*(\{[^}]+\})', html):
                    try:
                        raw = m.group(1).replace("\\u0026", "&")
                        eps = json.loads(raw)
                        for ep, src in eps.items():
                            if src and str(ep) not in ep_srcs:
                                if str(src).startswith("//"):
                                    src = "https:" + src
                                ep_srcs[str(ep)] = str(src)
                                found = True
                    except Exception:
                        pass
                vs_m = re.search(r'"videoSrc"\s*:\s*"((?:https?:)?//[^"]+)"', html)
                if vs_m and str(check_ep) not in ep_srcs:
                    src = vs_m.group(1).replace("\\u0026", "&")
                    if src.startswith("//"):
                        src = "https:" + src
                    ep_srcs[str(check_ep)] = src
                    found = True
                m3 = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', html)
                if m3 and str(check_ep) not in ep_srcs:
                    ep_srcs[str(check_ep)] = m3.group(1).replace("\\u0026", "&")
                    found = True

            # 从页面集数链接推断总数
            if check_ep == 1:
                eids = re.findall(r'data-ep-id=["\']?(\d+)', html)
                for e in eids:
                    try:
                        n = int(e)
                        if n > max_check:
                            max_check = min(n + 2, 80)
                    except Exception:
                        pass
                # 集数网格链接
                for a in re.finditer(r'href=["\']([^"\']*(?:/ep-(\d+)/|/video/\d+/)?)["\'][^>]*data-ep-id=["\']?(\d+)', html):
                    eid = a.group(3) or a.group(2)
                    href = self._fix(a.group(1))
                    if eid and eid not in ep_srcs and href:
                        # 暂存页面入口，player 再解析
                        ep_srcs[eid] = href

            if not found and check_ep > 1 and str(check_ep) not in ep_srcs:
                break
            check_ep += 1
            if check_ep > 1:
                time.sleep(0.12)
        return ep_srcs

    def searchContent(self, key, quick, pg="1"):
        page = max(int(pg or 1), 1)
        result = {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}
        url = self.host + "/search/?keyword=%s" % quote(key)
        if page > 1:
            url += "&page=%d" % page
        html = self._fetch(url)
        if not html:
            # 备用搜索路径
            html = self._fetch(self.host + "/search/video/%s/" % quote(key))
        if not html:
            return result
        videos, seen = [], set()
        for m in re.finditer(r'data-track-id=["\'](\d+)["\']', html):
            vid = m.group(1)
            if vid in seen:
                continue
            chunk = html[m.start() : m.start() + 900]
            tm = re.search(r'data-track-title=["\']([^"\']*)["\']', chunk)
            pm = re.search(r'(?:data-src|src)=["\'](https?://[^"\']+)["\']', chunk)
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
        tm2 = re.search(r'data-track-search-total=["\'](\d+)["\']', html)
        if tm2:
            result["total"] = int(tm2.group(1))
        result["pagecount"] = int(pm2.group(1)) if pm2 else (page + 1 if len(videos) >= 20 else page)
        return result

    def playerContent(self, flag, id, vipFlags):
        header = {
            "User-Agent": self.ua,
            "Referer": self.host + "/",
        }
        result = {"parse": 0, "url": "", "header": header}
        raw = str(id or "").strip()
        if not raw:
            return result

        # 已是直链
        if raw.startswith("http") and (".m3u8" in raw or ".mp4" in raw):
            result["url"] = raw
            return result

        # 页面 URL 或纯 ID
        if raw.startswith("http"):
            url = raw
        elif raw.startswith("/"):
            url = self._fix(raw)
        elif raw.isdigit():
            url = "%s/video/%s/" % (self.host, raw)
        else:
            url = self._fix(raw)

        html = self._fetch(url, referer=self.host)
        play = ""
        if html:
            mm = re.search(
                r'<script[^>]*id=["\']videoInitialData["\'][^>]*>([\s\S]*?)</script>',
                html,
                re.I,
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
                m = re.search(r'(https?://[^\s"\'<>]+\.(?:m3u8|mp4)[^\s"\'<>]*)', html)
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
                url = b64decode(unquote(url)).decode("utf-8")
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
        pass

    def destroy(self):
        pass
