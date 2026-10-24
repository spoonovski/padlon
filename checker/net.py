"""Malý HTTP klient nad standardní knihovnou (cookies, JSON, timeouty)."""
import gzip
import http.cookiejar
import json
import urllib.parse
import urllib.request

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")


class Session:
    def __init__(self, timeout=25):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.timeout = timeout

    def request(self, method, url, *, headers=None, data=None, json_body=None, form=None):
        h = {"User-Agent": UA, "Accept-Encoding": "gzip", "Accept-Language": "cs,en;q=0.8"}
        body = None
        if json_body is not None:
            body = json.dumps(json_body).encode()
            h["Content-Type"] = "application/json"
        elif form is not None:
            body = urllib.parse.urlencode(form).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        elif data is not None:
            body = data.encode() if isinstance(data, str) else data
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, data=body, headers=h, method=method)
        with self.opener.open(req, timeout=self.timeout) as r:
            raw = r.read()
            if r.headers.get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            return raw.decode(r.headers.get_content_charset() or "utf-8", "replace")

    def get(self, url, **kw):
        return self.request("GET", url, **kw)

    def post(self, url, **kw):
        return self.request("POST", url, **kw)

    def get_json(self, url, **kw):
        return json.loads(self.get(url, **kw))

    def post_json(self, url, **kw):
        return json.loads(self.post(url, **kw))

    def cookie(self, name):
        for c in self.jar:
            if c.name == name:
                return c.value
        return None
