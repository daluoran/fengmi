# -*- coding: utf-8 -*-
# Jable - 影视仓/蜂蜜用（需能访问站点；无法内置WebView过CF）
import re
import sys
from urllib.parse import quote

sys.path.append("..")
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "Jable"

    def init(self, extend=""):
        # 多镜像：哪个通就用哪个（和阅读源思路类似）
        self.hosts = [
            "https://jable.tv",
            "https://jable.com",
        ]
        self.host = self.hosts[0]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 13; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": self.host + "/",
        }

    def _get(self, url):
        for h in self.hosts:
            try:
                if url.startswith("http"):
                    u = url
                else:
                    u = h + url
                r = self.fetch(u, headers={**self.headers, "Referer": h + "/"}, timeout=20, verify=False)
                if r is None:
                    continue
                text = r.text if hasattr(r, "text") else str(r)
                # CF 拦截页
                if "cf_chl" in text or "Just a moment" in text or "Checking your browser" in text:
                    continue
                if "video-img-box" in text or "/videos/" in text or "hlsUrl" in text:
                    self.host = h
                    return text
            except Exception:
                continue
        return ""

    def homeContent(self, filter):
        classes = [
            {"type_id": "latest-updates", "type_name": "最近更新"},
            {"type_id": "hot", "type_name": "热门"},
            {"type_id": "categories/chinese-subtitle", "type_name": "中文字幕"},
            {"type_id": "categories/uncensored-leak", "type_name": "无码流出"},
            {"type_id": "categories/lesbian", "type_name": "女同"},
            {"type_id": "categories/roleplay", "type_name": "角色剧情"},
        ]
        return {"class": classes, "filters": {}}

    def homeVideoContent(self):
        return self._list(self._get("/latest-updates/"))

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid).strip("/")
        path = f"/{tid}/" if pg == 1 else f"/{tid}/{pg}/"
        return {
            "page": pg,
            "pagecount": 9999,
            "limit": 24,
            "total": 99999,
            "list": self._list(self._get(path)).get("list", []),
        }

    def searchContent(self, key, quick, pg="1"):
        pg = int(pg or 1)
        q = quote(key)
        path = f"/search/{q}/" if pg == 1 else f"/search/{q}/{pg}/"
        return self._list(self._get(path))

    def _list(self, html):
        items = []
        if not html:
            return {"list": items}
        blocks = html.split("video-img-box")[1:]
        seen = set()
        for block in blocks:
            try:
                m = re.search(r'href=["\']([^"\']*?/videos/[^"\']+)["\']', block)
                if not m:
                    continue
                href = m.group(1)
                if not href.startswith("http"):
                    href = self.host + href
                vid = href.rstrip("/").split("/")[-1] or href
                if vid in seen:
                    continue
                seen.add(vid)
                tm = re.search(r'<h6[^>]*>\s*<a[^>]*>([\s\S]*?)</a>', block)
                title = re.sub(r"<[^>]+>", "", tm.group(1)).strip() if tm else vid
                pm = re.search(r'data-src=["\']([^"\']+)["\']', block) or re.search(
                    r'src=["\']([^"\']+)["\']', block
                )
                pic = pm.group(1) if pm else ""
                if pic.startswith("//"):
                    pic = "https:" + pic
                rem = ""
                rm = re.search(r'class="[^"]*label[^"]*"[^>]*>([\s\S]*?)<', block)
                if rm:
                    rem = re.sub(r"<[^>]+>", "", rm.group(1)).strip()
                items.append(
                    {
                        "vod_id": href,
                        "vod_name": title,
                        "vod_pic": pic,
                        "vod_remarks": rem,
                    }
                )
            except Exception:
                continue
        return {"list": items}

    def detailContent(self, ids):
        url = ids[0]
        if not url.startswith("http"):
            url = self.host + url
        html = self._get(url)
        result = {"list": []}
        if not html:
            return result
        name = ""
        m = re.search(r"<h4[^>]*>([\s\S]*?)</h4>", html)
        if m:
            name = re.sub(r"<[^>]+>", "", m.group(1)).strip()
        if not name:
            m = re.search(r"<title>([^<]+)</title>", html)
            name = m.group(1).strip() if m else "Jable"
        pic = ""
        pm = re.search(r'og:image["\'][^>]*content=["\']([^"\']+)["\']', html)
        if pm:
            pic = pm.group(1)
        # 播放：页面里的 hlsUrl
        play = ""
        hm = re.search(r"hlsUrl\s*=\s*['\"]([^'\"]+)['\"]", html)
        if hm:
            play = hm.group(1).replace("\\u0026", "&")
        if not play:
            return result
        result["list"].append(
            {
                "vod_id": url,
                "vod_name": name,
                "vod_pic": pic,
                "vod_play_from": "Jable",
                "vod_play_url": f"正片${play}",
            }
        )
        return result

    def playerContent(self, flag, id, vipFlags):
        # id 已是 m3u8
        return {
            "parse": 0,
            "url": id,
            "header": {
                "User-Agent": self.headers["User-Agent"],
                "Referer": self.host + "/",
            },
        }

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass
