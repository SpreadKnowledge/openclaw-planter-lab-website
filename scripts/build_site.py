#!/usr/bin/env python3
"""Build the OpenClaw Planter Lab static site.

The builder intentionally uses only the Python standard library so OpenClaw can
update the site from a small, predictable environment.
"""

from __future__ import annotations

import html
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
POSTS_DIR = CONTENT_DIR / "posts"
IMAGES_DIR = CONTENT_DIR / "images"
ABOUT_PATH = CONTENT_DIR / "about.md"
DOCS_DIR = ROOT / "docs"
TEMPLATE_DIR = ROOT / "templates"
CSS_SOURCE = TEMPLATE_DIR / "style.css"
JS_SOURCE = TEMPLATE_DIR / "site.js"

SITE_TITLE = "OpenClaw栽培実験室"
SITE_TITLE_EN = "OpenClaw Planter Lab"
SITE_TITLE_DISPLAY = "OpenClaw<br>栽培実験室"


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    return value


def parse_front_matter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text

    lines = text.splitlines()
    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, text

    meta: dict[str, Any] = {}
    current_key: str | None = None
    current_item: dict[str, Any] | None = None

    for raw_line in lines[1:end_index]:
        if not raw_line.strip():
            continue
        if not raw_line.startswith(" "):
            key, _, raw_value = raw_line.partition(":")
            current_key = key.strip()
            current_item = None
            value = raw_value.strip()
            meta[current_key] = parse_scalar(value) if value else []
            continue

        if current_key is None:
            continue

        stripped = raw_line.strip()
        if stripped.startswith("- "):
            item_text = stripped[2:].strip()
            if ":" in item_text:
                key, _, raw_value = item_text.partition(":")
                current_item = {key.strip(): parse_scalar(raw_value)}
                meta.setdefault(current_key, []).append(current_item)
            else:
                current_item = None
                meta.setdefault(current_key, []).append(parse_scalar(item_text))
        elif current_item is not None and ":" in stripped:
            key, _, raw_value = stripped.partition(":")
            current_item[key.strip()] = parse_scalar(raw_value)

    body = "\n".join(lines[end_index + 1 :]).strip()
    return meta, body


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: f'<a href="{html.escape(match.group(2), quote=True)}">{match.group(1)}</a>',
        escaped,
    )
    return escaped


def markdown_to_html(markdown: str) -> str:
    blocks: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_list() -> None:
        if list_items:
            blocks.append("<ul>" + "".join(list_items) + "</ul>")
            list_items.clear()

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        heading_match = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading_match:
            flush_paragraph()
            flush_list()
            level = len(heading_match.group(1))
            blocks.append(
                f"<h{level}>{inline_markdown(heading_match.group(2))}</h{level}>"
            )
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            list_items.append(f"<li>{inline_markdown(stripped[2:].strip())}</li>")
            continue

        flush_list()
        paragraph.append(stripped)

    flush_paragraph()
    flush_list()
    return "\n".join(blocks)


def public_image_url(source_path: str, depth: int) -> str:
    clean_path = source_path.strip().replace("\\", "/")
    prefix = "../" * depth
    marker = "content/images/"
    if clean_path.startswith(marker):
        return prefix + "assets/images/" + clean_path[len(marker) :]
    if clean_path.startswith("/"):
        return clean_path
    return prefix + "assets/images/" + clean_path


def format_date(value: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y.%m.%d")
    except ValueError:
        return value


def post_slug(path: Path) -> str:
    return path.stem


def load_posts() -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        slug = post_slug(path)
        date = str(meta.get("date", slug[:10]))
        title = str(meta.get("title", slug))
        images = meta.get("images") or []
        if not isinstance(images, list):
            images = []
        tags = meta.get("tags") or []
        if not isinstance(tags, list):
            tags = []
        posts.append(
            {
                "path": path,
                "slug": slug,
                "url": f"posts/{slug}/",
                "title": title,
                "date": date,
                "date_label": format_date(date),
                "status": str(meta.get("status", "観察中")),
                "summary": str(meta.get("summary", "")),
                "tags": [str(tag) for tag in tags],
                "images": images,
                "openclaw_comment": str(meta.get("openclaw_comment", "")),
                "body_html": markdown_to_html(body),
            }
        )

    return sorted(posts, key=lambda post: post["date"], reverse=True)


def load_about_content() -> dict[str, Any]:
    defaults = {
        "title": "この実験をしている人と、見守るAI",
        "lead": "OpenClaw栽培実験室は、プランター栽培の記録をAIエージェントと一緒に残していく小さな実験サイトです。",
        "profiles": [],
        "activities": [],
        "body_html": "",
    }
    if not ABOUT_PATH.exists():
        return defaults

    meta, body = parse_front_matter(ABOUT_PATH.read_text(encoding="utf-8"))
    profiles = meta.get("profiles") or []
    activities = meta.get("activities") or []
    if not isinstance(profiles, list):
        profiles = []
    if not isinstance(activities, list):
        activities = []
    defaults.update(
        {
            "title": str(meta.get("title", defaults["title"])),
            "lead": str(meta.get("lead", defaults["lead"])),
            "profiles": profiles,
            "activities": activities,
            "body_html": markdown_to_html(body),
        }
    )
    return defaults


def status_class(status: str) -> str:
    normalized = status.lower()
    if "注意" in normalized or "watch" in normalized:
        return "status-watch"
    if "良好" in normalized or "ok" in normalized:
        return "status-good"
    return "status-neutral"


def render_tags(tags: list[str]) -> str:
    if not tags:
        return ""
    return '<div class="tags">' + "".join(
        f"<span>#{html.escape(tag)}</span>" for tag in tags
    ) + "</div>"


def render_image_card(image: dict[str, Any], depth: int) -> str:
    path = str(image.get("path", ""))
    alt = str(image.get("alt", "栽培ログ画像"))
    src = public_image_url(path, depth)
    return (
        '<figure class="image-card">'
        f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" loading="lazy">'
        f"<figcaption>{html.escape(alt)}</figcaption>"
        "</figure>"
    )


def render_profile_card(profile: dict[str, Any]) -> str:
    label = str(profile.get("label", "Profile"))
    name = str(profile.get("name", "Profile"))
    role = str(profile.get("role", ""))
    body = str(profile.get("body", ""))
    image = str(profile.get("image", ""))
    alt = str(profile.get("alt", f"{name}のアイコン"))
    src = "../assets/images/profile/" + image
    return f"""
      <article class="profile-card">
        <img class="profile-avatar" src="{html.escape(src, quote=True)}" alt="{html.escape(alt, quote=True)}" loading="lazy">
        <div>
          <p class="eyebrow">{html.escape(label)}</p>
          <h2>{html.escape(name)}</h2>
          <p class="profile-role">{html.escape(role)}</p>
          <p>{html.escape(body)}</p>
        </div>
      </article>
"""


def render_placeholder() -> str:
    return (
        '<div class="image-placeholder">'
        '<span class="placeholder-mark">Observation</span>'
        "<p>画像はまだありません。次回の観察写真をここに追加できます。</p>"
        "</div>"
    )


def page_shell(title: str, body: str, depth: int = 0, lang: str = "ja") -> str:
    prefix = "../" * depth
    css = prefix + "assets/css/style.css"
    js = prefix + "assets/js/site.js"
    home_url = prefix + "index.html"
    posts_url = prefix + "posts/"
    about_url = prefix + "about/"
    en_url = prefix + "en/"
    return f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{html.escape(title)} | {SITE_TITLE}</title>
  <link rel="stylesheet" href="{css}">
  <script src="{js}" defer></script>
</head>
<body>
  <header class="site-header">
    <a class="brand" href="{home_url}" aria-label="{SITE_TITLE}">
      <span class="brand-mark">OC</span>
      <span>
        <strong>{SITE_TITLE_DISPLAY}</strong>
        <small>{SITE_TITLE_EN}</small>
      </span>
    </a>
    <nav class="site-nav" aria-label="Primary navigation">
      <a href="{home_url}">Home</a>
      <a href="{posts_url}">Blog</a>
      <a href="{about_url}">About</a>
      <a href="{en_url}">English</a>
    </nav>
  </header>
  <main>
{body}
  </main>
  <footer class="site-footer">
    <p>{SITE_TITLE_EN} is a GitHub Pages demo maintained for OpenClaw website update practice.</p>
    <p>Photos, images, and media are not covered by the MIT License unless explicitly stated.</p>
  </footer>
</body>
</html>
"""


def render_post_card(post: dict[str, Any], depth: int = 0) -> str:
    prefix = "../" * depth
    url = prefix + post["url"]
    image_html = render_placeholder()
    if post["images"]:
        image_html = render_image_card(post["images"][0], depth)

    return f"""
<article class="post-card">
  <a class="post-card-media" href="{url}">{image_html}</a>
  <div class="post-card-body">
    <div class="meta-row">
      <time datetime="{html.escape(post['date'])}">{html.escape(post['date_label'])}</time>
      <span class="status-pill {status_class(post['status'])}">{html.escape(post['status'])}</span>
    </div>
    <h3><a href="{url}">{html.escape(post['title'])}</a></h3>
    <p>{html.escape(post['summary'])}</p>
    {render_tags(post['tags'])}
  </div>
</article>
"""


def write_index(posts: list[dict[str, Any]]) -> None:
    latest = posts[:5]

    gallery_items: list[str] = []
    for post in posts:
        for image in post["images"]:
            gallery_items.append(render_image_card(image, 0))
            if len(gallery_items) >= 6:
                break
        if len(gallery_items) >= 6:
            break
    gallery_html = "\n".join(gallery_items) if gallery_items else render_placeholder()

    latest_html = "\n".join(render_post_card(post) for post in latest)

    body = f"""
    <section class="hero">
      <div class="hero-content">
        <p class="eyebrow">AI agent cultivation journal</p>
        <h1 class="hero-title"><span class="title-line">OpenClaw</span><span class="title-line">栽培実験室</span></h1>
        <p class="hero-lead">{SITE_TITLE_EN} は、AIエージェントがプランター栽培を観察し、日々の作業と気づきを静かに記録していく小さな実験室です。</p>
        <div class="hero-actions">
          <a class="button primary" href="posts/">ブログを見る</a>
          <a class="button ghost" href="about/">この実験について</a>
          <a class="button ghost" href="en/">English</a>
        </div>
      </div>
      <div class="hero-panel" aria-label="Current lab status">
        <span class="panel-label">Today</span>
        <strong>水色の静かなラボで、植物とセンサーの変化を観察中。</strong>
        <p>GitHub Pagesで公開される、OpenClawのWebサイト保守・更新練習用デモです。</p>
      </div>
    </section>

    <section class="section-grid">
      <div class="section-copy">
        <p class="eyebrow">About</p>
        <h2>この実験について</h2>
        <p>人間またはOpenClawがMarkdownで栽培ログを書き、ローカルビルドで静的HTMLに変換します。観察、作業、画像、コメントを積み重ねながら、AIエージェントによるサイト更新の流れを検証します。</p>
        <p><a class="text-link" href="about/">運営者とクローラを見る</a></p>
      </div>
      <div class="lab-stats">
        <div><span>{len(posts)}</span><small>logs</small></div>
        <div><span>{sum(len(post['images']) for post in posts)}</span><small>images</small></div>
        <div><span>Pages</span><small>GitHub /docs</small></div>
      </div>
    </section>

    <section class="section-heading">
      <p class="eyebrow">Blog</p>
      <h2>ブログ</h2>
    </section>
    <section class="post-grid">
{latest_html}
    </section>

    <section class="section-heading">
      <p class="eyebrow">Gallery</p>
      <h2>画像ギャラリー</h2>
    </section>
    <section class="gallery-grid">
{gallery_html}
    </section>

    <section class="section-grid">
      <div class="section-copy">
        <p class="eyebrow">OpenClaw</p>
        <h2>OpenClawとは何か</h2>
        <p>OpenClawは、観察記録の整理、Markdown投稿の作成、静的サイトのビルド、差分確認などを支援するAIエージェントとして扱います。このサイトは、その保守フローを公開リポジトリで練習するための実験場です。</p>
      </div>
      <a class="repo-card" href="https://github.com/" rel="noreferrer">
        <span>Demo Site</span>
        <strong>GitHub Pagesで公開される静的サイト</strong>
        <p>公開対象は main ブランチの /docs フォルダです。</p>
      </a>
    </section>
"""
    (DOCS_DIR / "index.html").write_text(page_shell(SITE_TITLE, body), encoding="utf-8")


def write_about_page() -> None:
    about = load_about_content()
    about_title = str(about["title"])
    if about_title == "この実験をしている人と、見守るAI":
        about_title_html = (
            '<span class="title-line">この実験をしている人と</span>'
            '<span class="title-line">見守るAI</span>'
        )
    else:
        about_title_html = html.escape(about_title)
    profile_cards = "\n".join(
        render_profile_card(profile)
        for profile in about["profiles"]
        if isinstance(profile, dict)
    )
    activity_items = "\n".join(
        f"<div>{html.escape(str(activity))}</div>" for activity in about["activities"]
    )
    body = f"""
    <section class="page-title about-title">
      <p class="eyebrow">About This Lab</p>
      <h1 class="about-heading">{about_title_html}</h1>
      <p>{html.escape(about['lead'])}</p>
    </section>

    <section class="profile-grid" aria-label="運営者とOpenClawエージェント">
{profile_cards}
    </section>

    <section class="section-grid about-note">
      <div class="section-copy">
{about['body_html']}
      </div>
      <aside class="agent-note">
        <span>Small Experiment</span>
        <p>身近な題材を使いながら、AIエージェントがWebサイト更新をどこまで手伝えるかを確かめるための公開デモです。</p>
      </aside>
    </section>

    <section class="section-heading">
      <p class="eyebrow">What We Track</p>
      <h2>このサイトでやっていること</h2>
    </section>
    <section class="activity-grid">
{activity_items}
    </section>
"""
    output = DOCS_DIR / "about" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_shell("この実験について", body, depth=1), encoding="utf-8")


def write_posts_index(posts: list[dict[str, Any]]) -> None:
    cards = "\n".join(render_post_card(post, depth=1) for post in posts)
    body = f"""
    <section class="page-title">
      <p class="eyebrow">Blog Archive</p>
      <h1>ブログ一覧</h1>
      <p>OpenClaw栽培実験室の観察ログを新しい順に並べています。</p>
    </section>
    <section class="post-list">
{cards}
    </section>
"""
    output = DOCS_DIR / "posts" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_shell("投稿一覧", body, depth=1), encoding="utf-8")


def write_post_pages(posts: list[dict[str, Any]]) -> None:
    for post in posts:
        images_html = (
            "\n".join(render_image_card(image, depth=2) for image in post["images"])
            if post["images"]
            else render_placeholder()
        )
        body = f"""
    <article class="article">
      <header class="article-header">
        <a class="text-link" href="../">投稿一覧へ</a>
        <div class="meta-row">
          <time datetime="{html.escape(post['date'])}">{html.escape(post['date_label'])}</time>
          <span class="status-pill {status_class(post['status'])}">{html.escape(post['status'])}</span>
        </div>
        <h1>{html.escape(post['title'])}</h1>
        <p>{html.escape(post['summary'])}</p>
        {render_tags(post['tags'])}
      </header>
      <div class="article-body">
{post['body_html']}
      </div>
      <section class="article-gallery">
        <h2>画像ギャラリー</h2>
        <div class="gallery-grid">
{images_html}
        </div>
      </section>
      <section class="openclaw-comment">
        <span>OpenClaw Comment</span>
        <p>{html.escape(post['openclaw_comment'])}</p>
      </section>
    </article>
"""
        output = DOCS_DIR / "posts" / post["slug"] / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(page_shell(post["title"], body, depth=2), encoding="utf-8")


def write_english_page() -> None:
    body = f"""
    <section class="hero compact">
      <div class="hero-content">
        <p class="eyebrow">English Overview</p>
        <h1>{SITE_TITLE_EN}</h1>
        <p class="hero-lead">This is a small static website for observing planter cultivation with OpenClaw. It demonstrates how an AI agent can maintain cultivation notes, image logs, sensor observations, and comments through Markdown and GitHub Pages.</p>
        <div class="hero-actions">
          <a class="button primary" href="../index.html">Japanese</a>
          <a class="button ghost" href="../about/">About</a>
          <a class="button ghost" href="../posts/">Log archive</a>
        </div>
      </div>
      <div class="hero-panel">
        <span class="panel-label">Static Workflow</span>
        <strong>Markdown in content/, generated HTML in docs/.</strong>
        <p>The public GitHub Pages target is the /docs folder on the main branch.</p>
      </div>
    </section>
    <section class="section-grid">
      <div class="section-copy">
        <p class="eyebrow">Purpose</p>
        <h2>A public demo for agent-maintained updates</h2>
        <p>SpreadKnowledge uses this repository to practice OpenClaw website maintenance. Daily posts are currently written in Japanese, with the structure kept ready for future English summaries.</p>
      </div>
      <a class="repo-card" href="../index.html">
        <span>OpenClaw栽培実験室</span>
        <strong>日本語トップページへ戻る</strong>
        <p>See the latest observation state, recent logs, and gallery.</p>
      </a>
    </section>
"""
    output = DOCS_DIR / "en" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_shell(SITE_TITLE_EN, body, depth=1, lang="en"), encoding="utf-8")


def copy_assets() -> None:
    css_dest = DOCS_DIR / "assets" / "css"
    css_dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CSS_SOURCE, css_dest / "style.css")

    js_dest = DOCS_DIR / "assets" / "js"
    js_dest.mkdir(parents=True, exist_ok=True)
    if JS_SOURCE.exists():
        shutil.copy2(JS_SOURCE, js_dest / "site.js")

    image_dest = DOCS_DIR / "assets" / "images"
    image_dest.mkdir(parents=True, exist_ok=True)
    if IMAGES_DIR.exists():
        for source in IMAGES_DIR.rglob("*"):
            if source.is_file():
                if source.parent == IMAGES_DIR and source.name in {
                    "spreadknowledge.png",
                    "クローラ.png",
                }:
                    continue
                relative = source.relative_to(IMAGES_DIR)
                target = image_dest / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)

    profile_dest = image_dest / "profile"
    profile_dest.mkdir(parents=True, exist_ok=True)
    profile_sources = {
        "spreadknowledge.png": IMAGES_DIR / "spreadknowledge.png",
        "crawler.png": IMAGES_DIR / "クローラ.png",
    }
    for filename, source in profile_sources.items():
        if source.exists():
            shutil.copy2(source, profile_dest / filename)


def prepare_docs() -> None:
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    (DOCS_DIR / "posts").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "en").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "about").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "assets" / "js").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS_DIR / "assets" / "js" / ".gitkeep").write_text("", encoding="utf-8")
    (DOCS_DIR / "assets" / "images" / ".gitkeep").write_text("", encoding="utf-8")


def main() -> None:
    prepare_docs()
    copy_assets()
    posts = load_posts()
    write_index(posts)
    write_about_page()
    write_posts_index(posts)
    write_post_pages(posts)
    write_english_page()
    print(f"Built {SITE_TITLE_EN}: {len(posts)} posts -> {DOCS_DIR}")


if __name__ == "__main__":
    main()
