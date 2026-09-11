# -*- coding: utf-8 -*-
import re
import sys
import json
import time
from base64 import b64encode, b64decode
from urllib.parse import quote, unquote
from lxml import etree

try:
    import urllib3
    urllib3.disable_warnings()
except Exception:
    pass

try:
    from Crypto.Cipher import AES as _AES
except Exception:
    _AES = None

sys.path.append('..')
from base.spider import Spider


class Spider(Spider):
    def getName(self):
        return "黄果短剧"

    def init(self, extend=""):
        # 多个备用域名，按顺序自动尝试
        self.hosts = [
            "https://14a.bhefwntk.cc",
            "https://huangguo5.com",
            "https://huangguoai.com",
            "https://huangguoai.pages.dev",
        ]
        self.host = self.hosts[0]
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        ext = extend or ""
        self.pics_direct = "direct=1" in ext or "direct=1" in str(ext)
        self.categories = [
            {"type_id": "ai-duanju", "type_name": "AI成人短剧"},
            {"type_id": "ai-manju", "type_name": "AI成人漫剧"},
            {"type_id": "ai-huanlian", "type_name": "AI换脸"},
            {"type_id": "ai-mogai", "type_name": "AI魔改"},
            {"type_id": "ranks/hot", "type_name": "排行榜"},
        ]

    def _get(self, url, referer=None, asjson=False):
        headers = dict(self.headers)
        if referer:
            headers["Referer"] = referer
        else:
            headers["Referer"] = self.host + "/"

        # 如果是相对路径，补全当前 host
        if url.startswith("/"):
            url = self.host + url

        for i in range(3):
            try:
                r = self.fetch(url, headers=headers, timeout=20, verify=False)
                if r is None:
                    continue
                if not asjson:
                    text = r.text if hasattr(r, "text") else str(r)
                    if text and len(text) > 500:
                        return text
                else:
                    try:
                        return r.json()
                    except Exception:
                        return {}
            except Exception:
                time.sleep(1)
        return {} if asjson else ""

    def _try_hosts(self, path):
        """自动尝试多个域名，返回第一个成功的 HTML 和对应 host"""
        for h in self.hosts:
            self.host = h
            url = h + path if path.startswith("/") else path
            html = self._get(url)
            if html and ("hg-drama-card" in html or "hg-rank-item" in html or "hg-web-detail" in html):
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

    def _img_src(self, u):
        u = self._fix(u or "")
        if u.startswith("http") and "?" in u:
            u = re.sub(r'\?.*', '', u)
        return u

    def _proxy_pic(self, u):
        u = self._img_src(u)
        if not u:
            return ""
        if self.pics_direct:
            return u
        try:
            enc = quote(b64encode(u.encode("utf-8")).decode("utf-8"), safe="")
            return f"{self.getProxyUrl()}&url={enc}&type=img"
        except Exception:
            return u

    _IMG_KEY = bytes([102, 53, 100, 57, 54, 53, 100, 102, 55, 53, 51, 51, 54, 50, 55, 48])
    _IMG_IV = bytes([57, 55, 98, 54, 48, 51, 57, 52, 97, 98, 99, 50, 102, 98, 101, 49])

    def _decrypt_img(self, raw):
        if not raw or len(raw) % 16 != 0 or _AES is None:
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

    def _card(self, card):
        a = card.xpath('.//a[contains(@href,"/detail/")]')
        if not a:
            return None
        a = a[0]
        m = re.search(r'/detail/(\d+)/', a.get("href", ""))
        if not m:
            return None
        img = (card.xpath('.//img/@data-src') or card.xpath('.//img/@src') or [""])[0]
        title = "".join(card.xpath('.//*[contains(@class,"hg-drama-card__title")]//text()')).strip()
        if not title:
            title = a.get("title", "").strip()
        if not title:
            return None
        rem = "".join(card.xpath('.//*[contains(@class,"hg-drama-card__episode")]//text()')).strip()
        score = "".join(card.xpath('.//*[contains(@class,"hg-drama-card__score")]//text()')).strip()
        if rem and score:
            rem = f"{rem} · {score}"
        elif not rem:
            rem = score
        return {
            "vod_id": m.group(1),
            "vod_name": title,
            "vod_pic": self._proxy_pic(img),
            "vod_remarks": rem,
        }

    def _cards(self, html, all_grids=False):
        if not html:
            return []
        try:
            tree = etree.HTML(html)
        except Exception:
            return []
        if all_grids:
            nodes = []
            for g in tree.xpath('//*[contains(@class,"hg-card-grid")]'):
                nodes.extend(g.xpath('.//*[contains(@class,"hg-drama-card")]'))
            if not nodes:
                nodes = tree.xpath('//*[contains(@class,"hg-drama-card")]')
        else:
            grids = tree.xpath('//*[contains(@class,"hg-card-grid")]')
            nodes = grids[0].xpath('.//*[contains(@class,"hg-drama-card")]') if grids else tree.xpath('//*[contains(@class,"hg-drama-card")]')
        out, seen = [], set()
        for card in nodes:
            try:
                item = self._card(card)
                if not item or item["vod_id"] in seen:
                    continue
                seen.add(item["vod_id"])
                out.append(item)
            except Exception:
                continue
        return out

    def _rank_items(self, html):
        if not html:
            return []
        try:
            tree = etree.HTML(html)
        except Exception:
            return []
        lists = tree.xpath('//*[contains(@class,"hg-rank-list")]')
        nodes = lists[0].xpath('.//*[contains(@class,"hg-rank-item")]') if lists else tree.xpath('//*[contains(@class,"hg-rank-item")]')
        out, seen = [], set()
        for item in nodes:
            try:
                a = item.xpath('.//a[contains(@href,"/detail/")]')
                if not a:
                    continue
                m = re.search(r'/detail/(\d+)/', a[0].get("href", ""))
                if not m or m.group(1) in seen:
                    continue
                seen.add(m.group(1))
                img = (item.xpath('.//img/@data-src') or item.xpath('.//img/@src') or [""])[0]
                title = "".join(item.xpath('.//*[contains(@class,"hg-rank-item__title")]//text()')).strip()
                if not title:
                    title = a[0].get("title", "").strip()
                if not title:
                    continue
                out.append({
                    "vod_id": m.group(1),
                    "vod_name": title,
                    "vod_pic": self._proxy_pic(img),
                    "vod_remarks": "".join(item.xpath('.//*[contains(@class,"hg-rank-item__tags")]//text()')).strip(),
                })
            except Exception:
                continue
        return out

    def _panel_total(self, html):
        m = re.search(r'data-panel-total="(\d+)"', html or "")
        return int(m.group(1)) if m else 0

    def homeContent(self, filter):
        html = self._try_hosts("/")
        return {"class": self.categories, "list": self._cards(html, all_grids=True), "filters": {}}

    def homeVideoContent(self):
        html = self._try_hosts("/")
        return {"list": self._cards(html, all_grids=True)}

    def categoryContent(self, tid, pg, filter, extend):
        pg = int(pg or 1)
        tid = str(tid).strip("/")
        if "rank" in tid:
            path = f"/{tid}/" if pg == 1 else f"/{tid}/{pg}/"
            html = self._try_hosts(path)
            return {"page": pg, "pagecount": 9999, "limit": 20, "total": 99999, "list": self._rank_items(html)}
        path = f"/{tid}/" if pg == 1 else f"/{tid}/{pg}/"
        html = self._try_hosts(path)
        cards = self._cards(html)
        total = self._panel_total(html)
        pagecount = max(1, (total + 23) // 24) if total else 9999
        return {"page": pg, "pagecount": pagecount, "limit": 24, "total": total or 99999, "list": cards}

    def detailContent(self, ids):
        vid = str(ids[0])
        html = self._try_hosts(f"/detail/{vid}/")
        result = {"list": []}
        if not html:
            return result
        try:
            tree = etree.HTML(html)
        except Exception:
            return result
        name = "".join(tree.xpath('//h1/text()')).strip()
        if not name:
            return result
        pic_l = tree.xpath('//*[contains(@class,"hg-web-detail__poster")]//img/@data-src')
        if not pic_l:
            pic_l = tree.xpath('//*[contains(@class,"hg-web-detail__poster")]//img/@src')
        pic = pic_l[0].strip() if pic_l else ""
        desc = "".join(tree.xpath('//*[contains(@class,"hg-web-detail__desc")]/text()')).strip()
        remarks = "".join(tree.xpath('//*[contains(@class,"hg-web-detail__poster")]//*[contains(@class,"hg-web-detail__episode")]//text()')).strip()
        score = "".join(tree.xpath('//*[contains(@class,"hg-web-detail__score")]//text()')).strip()
        eps = []
        for a in tree.xpath('//*[contains(@class,"hg-web-detail__ep-grid")]//a'):
            href = a.get("href", "")
            if not href:
                continue
            eid = a.get("data-ep-id", "")
            name_ep = f"第{eid}集" if eid else "".join(a.xpath(".//text()")).strip()
            eps.append(f'{name_ep}${self._fix(href)}')
        if not eps:
            play = tree.xpath('//*[contains(@class,"hg-web-detail__play")]/@href')
            if play:
                eps = [f"第1集${self._fix(play[0])}"]
        if not eps:
            return result
        info = {
            "vod_id": vid,
            "vod_name": name,
            "vod_pic": self._proxy_pic(pic),
            "vod_play_from": "黄果短剧",
            "vod_play_url": "#".join(eps),
            "vod_content": desc,
        }
        if remarks:
            info["vod_remarks"] = remarks
        elif score:
            info["vod_remarks"] = f"{score}分"
        result["list"].append(info)
        return result

    def searchContent(self, key, quick, pg="1"):
        html = self._try_hosts(f"/search/video/{quote(key)}/")
        return {"list": self._cards(html), "page": int(pg or 1)}

    def playerContent(self, flag, id, vipFlags):
        url = self._fix(id)
        play = ""
        html = self._get(url, referer=self.host)
        if html:
            mm = re.search(r'<script id="videoInitialData" type="application/json">(.*?)</script>', html, re.S)
            if mm:
                try:
                    data = json.loads(mm.group(1))
                except Exception:
                    data = {}
                if isinstance(data, dict):
                    em = re.search(r'/ep-(\d+)/', url) or re.search(r'/(\d+)/?$', url)
                    ep = str(em.group(1)) if em else "1"
                    srcs = data.get("epPlaySrcs") or {}
                    play = srcs.get(ep) or data.get("videoSrc") or ""
        if play:
            play = play.replace("\\u0026", "&")
            if not play.startswith("http"):
                mm2 = re.search(r'(https?://[^\s"\']+)', play)
                play = mm2.group(1) if mm2 else ""
        header = {
            "User-Agent": self.headers.get("User-Agent"),
            "Referer": self.host + "/",
        }
        return {"parse": 0, "url": play, "header": header}

    def localProxy(self, param):
        return None

    def isVideoFormat(self, url):
        return True

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass
