#!/usr/bin/env python3
"""Turn a built site into GitHub Pages redirect stubs.

The site lives on another host now. For every HTML page in SITE_DIR this
writes a stub at the same path in OUT_DIR that sends the visitor to the same
path on TARGET (canonical link, meta refresh, and a script that keeps the
query and fragment). 404.html forwards any other path under PREFIX the same
way, so paths that never had a page still land on the new host.

    python3 scripts/pages-redirect.py SITE_DIR OUT_DIR TARGET PREFIX

    TARGET  https://quantum.litkhai.dev
    PREFIX  the Pages path the stubs are served under, e.g. /notes-on-quantum
"""
import html
import pathlib
import sys

STUB = """<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex" />
    <title>{title}</title>
    <link rel="canonical" href="{url}" />
    <meta http-equiv="refresh" content="0; url={url}" />
    <script>location.replace({url_js} + location.search + location.hash);</script>
  </head>
  <body>
    <p>이 페이지는 <a href="{url}">{url}</a>로 옮겼습니다. · This page moved to <a href="{url}">{url}</a>.</p>
  </body>
</html>
"""

NOT_FOUND = """<!doctype html>
<html lang="ko">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex" />
    <title>Moved to {host}</title>
    <link rel="canonical" href="{target}/" />
    <meta http-equiv="refresh" content="0; url={target}/" />
    <script>
      // Keep the path below the Pages prefix, the query and the fragment
      var p = location.pathname;
      var prefix = {prefix_js};
      if (p.indexOf(prefix) === 0) p = p.slice(prefix.length);
      if (p.charAt(0) !== "/") p = "/" + p;
      location.replace({target_js} + p + location.search + location.hash);
    </script>
  </head>
  <body>
    <p>이 사이트는 <a href="{target}/">{host}</a>로 옮겼습니다. · This site moved to <a href="{target}/">{host}</a>.</p>
  </body>
</html>
"""


def js(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def main(site_dir, out_dir, target, prefix):
    site, out = pathlib.Path(site_dir), pathlib.Path(out_dir)
    target, prefix = target.rstrip("/"), "/" + prefix.strip("/")
    host = target.split("://", 1)[-1]
    count = 0
    for page in sorted(site.rglob("*.html")):
        rel = page.relative_to(site).as_posix()
        if rel == "404.html":
            continue
        path = rel[: -len("index.html")] if rel.endswith("index.html") else rel
        url = html.escape(f"{target}/{path}", quote=True)
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(STUB.format(title=f"Moved to {host}", url=url, url_js=js(f"{target}/{path}")))
        count += 1
    out.mkdir(parents=True, exist_ok=True)
    (out / "404.html").write_text(
        NOT_FOUND.format(host=host, target=target, target_js=js(target), prefix_js=js(prefix))
    )
    (out / ".nojekyll").write_text("")
    print(f"{count} redirect stubs + 404.html -> {target} (prefix {prefix})")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    main(*sys.argv[1:])
