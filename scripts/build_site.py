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
EXPERIMENTS_DIR = CONTENT_DIR / "experiments"
IMAGES_DIR = CONTENT_DIR / "images"
ABOUT_PATH = CONTENT_DIR / "about.md"
DOCS_DIR = ROOT / "docs"
TEMPLATE_DIR = ROOT / "templates"
CSS_SOURCE = TEMPLATE_DIR / "style.css"
JS_SOURCE = TEMPLATE_DIR / "site.js"

SITE_TITLE = "OpenClaw栽培実験室"
SITE_TITLE_EN = "OpenClaw Planter Lab"
SITE_TITLE_DISPLAY = "OpenClaw<br>栽培実験室"

LEGACY_REDIRECTS = {
    "2026-04-27-first-observation": "../",
    "2026-04-28-watering-check": "../2026-04-28-evening-watering-log/",
    "2026-04-29-radish-trivia-red-shoulder": "../2026-04-29-radish-trivia-color-varieties/",
}


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


def relative_prefix(depth: int) -> str:
    return "../" * depth


def public_image_url(source_path: str, depth: int) -> str:
    clean_path = source_path.strip().replace("\\", "/")
    prefix = relative_prefix(depth)
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


def format_period(start: str, end: str) -> str:
    if start and end:
        return f"{format_date(start)} - {format_date(end)}"
    if start:
        return f"{format_date(start)} -"
    if end:
        return f"- {format_date(end)}"
    return ""


def post_slug(path: Path) -> str:
    return path.stem


def normalize_images(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def normalize_tags(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(tag) for tag in value]


def load_posts() -> list[dict[str, Any]]:
    posts: list[dict[str, Any]] = []
    for path in sorted(POSTS_DIR.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        slug = post_slug(path)
        date = str(meta.get("date", slug[:10]))
        title = str(meta.get("title", slug))
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
                "tags": normalize_tags(meta.get("tags") or []),
                "images": normalize_images(meta.get("images") or []),
                "experiment_slug": str(meta.get("experiment", "")).strip(),
                "openclaw_comment": str(meta.get("openclaw_comment", "")),
                "body_html": markdown_to_html(body),
            }
        )

    return sorted(posts, key=lambda post: post["date"], reverse=True)


def load_experiments() -> list[dict[str, Any]]:
    experiments: list[dict[str, Any]] = []
    if not EXPERIMENTS_DIR.exists():
        return experiments

    for path in sorted(EXPERIMENTS_DIR.glob("*.md")):
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        slug = path.stem
        start_date = str(meta.get("start_date", ""))
        end_date = str(meta.get("end_date", ""))
        experiments.append(
            {
                "path": path,
                "slug": slug,
                "url": f"experiments/{slug}/",
                "gallery_url": f"gallery/experiments/{slug}/",
                "title": str(meta.get("title", slug)),
                "crop": str(meta.get("crop", "")),
                "start_date": start_date,
                "end_date": end_date,
                "period_label": format_period(start_date, end_date),
                "status": str(meta.get("status", "進行中")),
                "summary": str(meta.get("summary", "")),
                "cover_image": str(meta.get("cover_image", "")).strip(),
                "cover_alt": str(meta.get("cover_alt", "実験の代表写真")),
                "body_html": markdown_to_html(body),
                "posts": [],
                "gallery_items": [],
                "post_count": 0,
                "image_count": 0,
            }
        )

    return sorted(experiments, key=lambda experiment: experiment["start_date"], reverse=True)


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


def attach_experiments(posts: list[dict[str, Any]], experiments: list[dict[str, Any]]) -> None:
    experiment_map = {experiment["slug"]: experiment for experiment in experiments}

    for post in posts:
        experiment = experiment_map.get(post["experiment_slug"])
        post["experiment"] = experiment
        post["gallery_items"] = []
        if experiment is not None:
            experiment["posts"].append(post)

        for index, image in enumerate(post["images"], start=1):
            item = {
                "image": image,
                "post": post,
                "experiment": experiment,
                "date": post["date"],
                "date_label": post["date_label"],
                "index": index,
            }
            post["gallery_items"].append(item)
            if experiment is not None:
                experiment["gallery_items"].append(item)

    for experiment in experiments:
        experiment["post_count"] = len(experiment["posts"])
        experiment["image_count"] = len(experiment["gallery_items"])
        if not experiment["cover_image"] and experiment["gallery_items"]:
            experiment["cover_image"] = str(experiment["gallery_items"][0]["image"].get("path", ""))
            experiment["cover_alt"] = str(experiment["gallery_items"][0]["image"].get("alt", experiment["cover_alt"]))


def collect_gallery_items(posts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for post in posts:
        items.extend(post["gallery_items"])
    return items


def status_class(status: str) -> str:
    normalized = status.lower()
    if "注意" in normalized or "watch" in normalized:
        return "status-watch"
    if "良好" in normalized or "ok" in normalized or "順調" in normalized or "完了" in normalized:
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


def render_experiment_link(experiment: dict[str, Any] | None, depth: int, label: str = "所属実験") -> str:
    if experiment is None:
        return ""
    url = relative_prefix(depth) + experiment["url"]
    return (
        '<p class="experiment-link">'
        f'{html.escape(label)} <a class="text-link" href="{html.escape(url, quote=True)}">{html.escape(experiment["title"])}</a>'
        "</p>"
    )


def render_quick_links(links: list[tuple[str, str]], depth: int, variant: str = "soft") -> str:
    if not links:
        return ""
    prefix = relative_prefix(depth)
    items = []
    for label, href in links:
        url = href if href.startswith(("http://", "https://", "/", "#")) else prefix + href
        items.append(
            f'<a class="quick-link {variant}" href="{html.escape(url, quote=True)}">{html.escape(label)}</a>'
        )
    return '<nav class="quick-links" aria-label="Page links">' + "".join(items) + "</nav>"



def render_page_kicker(section: str, current: str, parent_label: str | None = None, parent_href: str | None = None, depth: int = 0) -> str:
    parent_html = ""
    if parent_label and parent_href:
        url = parent_href if parent_href.startswith(("http://", "https://", "/", "#")) else relative_prefix(depth) + parent_href
        parent_html = f'<a href="{html.escape(url, quote=True)}">{html.escape(parent_label)}</a><span>/</span>'
    return (
        '<nav class="page-kicker" aria-label="Current section">'
        f'<span>{html.escape(section)}</span>'
        f'{parent_html}'
        f'<strong>{html.escape(current)}</strong>'
        '</nav>'
    )

def render_gallery_item_card(item: dict[str, Any], depth: int, show_experiment: bool = True) -> str:
    image = item["image"]
    post = item["post"]
    experiment = item.get("experiment")
    image_path = str(image.get("path", ""))
    image_alt = str(image.get("alt", "栽培ログ画像"))
    image_url = public_image_url(image_path, depth)
    post_url = relative_prefix(depth) + post["url"]
    experiment_html = ""
    if show_experiment and experiment is not None:
        experiment_url = relative_prefix(depth) + experiment["url"]
        experiment_html = (
            '<p class="gallery-card-experiment">'
            f'<a class="text-link" href="{html.escape(experiment_url, quote=True)}">{html.escape(experiment["title"])}</a>'
            "</p>"
        )
    action_links = [
        f'<a class="mini-link" href="{html.escape(post_url, quote=True)}">投稿を見る</a>'
    ]
    if experiment is not None:
        experiment_url = relative_prefix(depth) + experiment["url"]
        action_links.append(
            f'<a class="mini-link" href="{html.escape(experiment_url, quote=True)}">実験ページへ</a>'
        )
    return f"""
<article class="gallery-detail-card">
  <a class="gallery-detail-media" href="{html.escape(post_url, quote=True)}">
    <img src="{html.escape(image_url, quote=True)}" alt="{html.escape(image_alt, quote=True)}" loading="lazy">
  </a>
  <div class="gallery-detail-body">
    <div class="meta-row">
      <time datetime="{html.escape(item['date'])}">{html.escape(item['date_label'])}</time>
      <span class="gallery-index">画像 {item['index']}</span>
    </div>
    <h3><a href="{html.escape(post_url, quote=True)}">{html.escape(post['title'])}</a></h3>
    <p>{html.escape(image_alt)}</p>
    {experiment_html}
    <div class="card-actions">{''.join(action_links)}</div>
  </div>
</article>
"""


def render_experiment_card(experiment: dict[str, Any], depth: int = 0, link_target: str = "detail") -> str:
    prefix = relative_prefix(depth)
    url = prefix + (experiment["gallery_url"] if link_target == "gallery" else experiment["url"])
    cover_html = render_placeholder()
    if experiment["cover_image"]:
        cover_html = render_image_card(
            {"path": experiment["cover_image"], "alt": experiment["cover_alt"]},
            depth,
        )

    return f"""
<article class="experiment-card">
  <a class="experiment-card-media" href="{html.escape(url, quote=True)}">{cover_html}</a>
  <div class="experiment-card-body">
    <div class="meta-row">
      <span class="status-pill {status_class(experiment['status'])}">{html.escape(experiment['status'])}</span>
      <span>{html.escape(experiment['period_label'])}</span>
    </div>
    <h3><a href="{html.escape(url, quote=True)}">{html.escape(experiment['title'])}</a></h3>
    <p>{html.escape(experiment['summary'])}</p>
    <div class="experiment-stats">
      <span>{experiment['post_count']}件の投稿</span>
      <span>{experiment['image_count']}枚の画像</span>
      <span>{html.escape(experiment['crop'])}</span>
    </div>
    <div class="card-actions">
      <a class="mini-link" href="{html.escape(prefix + experiment['url'], quote=True)}">実験記録を見る</a>
      <a class="mini-link" href="{html.escape(prefix + experiment['gallery_url'], quote=True)}">画像一覧を見る</a>
    </div>
  </div>
</article>
"""


def page_shell(title: str, body: str, depth: int = 0, lang: str = "ja", section: str = "home") -> str:
    prefix = relative_prefix(depth)
    css = prefix + "assets/css/style.css"
    js = prefix + "assets/js/site.js"
    home_url = prefix + "index.html"
    posts_url = prefix + "posts/"
    experiments_url = prefix + "experiments/"
    gallery_url = prefix + "gallery/"
    about_url = prefix + "about/"
    en_url = prefix + "en/"
    nav_items = [
        ("home", "Home", home_url),
        ("blog", "Blog", posts_url),
        ("experiments", "Experiments", experiments_url),
        ("gallery", "Gallery", gallery_url),
        ("about", "About", about_url),
        ("english", "English", en_url),
    ]
    nav_html = "".join(
        f'<a href="{href}"{' aria-current="page"' if key == section else ""}>{label}</a>'
        for key, label, href in nav_items
    )
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
<body class="theme-{html.escape(section)}">
  <header class="site-header">
    <a class="brand" href="{home_url}" aria-label="{SITE_TITLE}">
      <span class="brand-mark">OC</span>
      <span>
        <strong>{SITE_TITLE_DISPLAY}</strong>
        <small>{SITE_TITLE_EN}</small>
      </span>
    </a>
    <nav class="site-nav" aria-label="Primary navigation">
      {nav_html}
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
    prefix = relative_prefix(depth)
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
    {render_experiment_link(post.get('experiment'), depth)}
    {render_tags(post['tags'])}
    <div class="card-actions">
      <a class="mini-link" href="{html.escape(url, quote=True)}">投稿を読む</a>
      {f'<a class="mini-link" href="{html.escape(prefix + post["experiment"]["url"], quote=True)}">実験を見る</a>' if post.get('experiment') else ''}
    </div>
  </div>
</article>
"""


def write_index(posts: list[dict[str, Any]], experiments: list[dict[str, Any]]) -> None:
    latest_posts = posts[:3]
    gallery_items = collect_gallery_items(posts)[:3]
    latest_html = "\n".join(render_post_card(post) for post in latest_posts)
    gallery_html = (
        "\n".join(render_image_card(item["image"], 0) for item in gallery_items)
        if gallery_items
        else render_placeholder()
    )
    featured_experiment = render_experiment_card(experiments[0]) if experiments else ""

    body = f"""
    <section class="hero">
      <div class="hero-content">
        <p class="eyebrow">AI agent cultivation journal</p>
        <h1 class="hero-title"><span class="title-line">OpenClaw</span><span class="title-line">栽培実験室</span></h1>
        <p class="hero-lead">{SITE_TITLE_EN} は、AIエージェントがプランター栽培を観察し、日々の作業と気づきを静かに記録していく小さな実験室です。</p>
        <div class="hero-actions">
          <a class="button primary" href="posts/">ブログを見る</a>
          <a class="button ghost" href="experiments/">実験一覧を見る</a>
          <a class="button ghost" href="about/">この実験について</a>
          <a class="button ghost" href="en/">English</a>
        </div>
      </div>
      <div class="hero-panel" aria-label="Current lab status">
        <span class="panel-label">実験概要</span>
        <strong>水色の静かなラボで、植物とセンサーの変化を観察中。</strong>
        <p>GitHub Pagesで公開される、OpenClawのWebサイト保守・更新練習用デモです。</p>
      </div>
    </section>

    <section class="section-copy about-overview">
      <p class="eyebrow">About</p>
      <h2>この実験について</h2>
      <p>人間またはOpenClawがMarkdownで栽培ログを書き、ローカルビルドで静的HTMLに変換します。観察、作業、画像、コメントを積み重ねながら、AIエージェントによるサイト更新の流れを検証します。</p>
      <p><a class="text-link" href="about/">運営者とクローラを見る</a></p>
    </section>

    <section class="section-heading section-heading-row">
      <div>
        <p class="eyebrow">Experiments</p>
        <h2>実験ごとに見る</h2>
      </div>
      <a class="text-link more-link" href="experiments/">過去の実験を見る</a>
    </section>
    {render_quick_links([('実験一覧へ', 'experiments/'), ('実験別ギャラリーへ', 'gallery/'), ('最新の投稿へ', 'posts/')], 0)}
    <section class="experiment-grid">
      {featured_experiment}
    </section>

    <section class="section-heading section-heading-row">
      <div>
        <p class="eyebrow">Blog</p>
        <h2>ブログ</h2>
      </div>
      <div class="section-links">
        <a class="text-link more-link" href="experiments/">実験別に見る</a>
        <a class="text-link more-link" href="posts/">もっとみる</a>
      </div>
    </section>
    <section class="post-grid">
{latest_html}
    </section>

    <section class="section-heading section-heading-row">
      <div>
        <p class="eyebrow">Gallery</p>
        <h2>画像ギャラリー</h2>
      </div>
      <div class="section-links">
        <a class="text-link more-link" href="gallery/">実験別に見る</a>
        <a class="text-link more-link" href="gallery/">もっとみる</a>
      </div>
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
    (DOCS_DIR / "index.html").write_text(page_shell(SITE_TITLE, body, section="home"), encoding="utf-8")


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
    output.write_text(page_shell("この実験について", body, depth=1, section="about"), encoding="utf-8")


def write_posts_index(posts: list[dict[str, Any]]) -> None:
    cards = "\n".join(render_post_card(post, depth=1) for post in posts)
    body = f"""
    <section class="page-title">
      {render_page_kicker('Blog', '投稿一覧', depth=1)}
      <p class="eyebrow">Blog Archive</p>
      <h1>ブログ一覧</h1>
      <p>OpenClaw栽培実験室の観察ログを新しい順に並べています。各投稿から所属実験も辿れます。</p>
    </section>
    <section class="post-list">
{cards}
    </section>
"""
    output = DOCS_DIR / "posts" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_shell("投稿一覧", body, depth=1, section="blog"), encoding="utf-8")


def write_experiments_index(experiments: list[dict[str, Any]]) -> None:
    cards = "\n".join(render_experiment_card(experiment, depth=1) for experiment in experiments)
    body = f"""
    <section class="page-title">
      {render_page_kicker('Experiments', '実験一覧', depth=1)}
      <p class="eyebrow">Experiments</p>
      <h1>実験一覧</h1>
      <p>栽培ログとギャラリーを、実験ごとにまとめて見返せるページです。</p>
    </section>
    <section class="experiment-grid">
{cards}
    </section>
"""
    output = DOCS_DIR / "experiments" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_shell("実験一覧", body, depth=1, section="experiments"), encoding="utf-8")


def write_experiment_pages(experiments: list[dict[str, Any]]) -> None:
    for experiment in experiments:
        posts_html = (
            "\n".join(render_post_card(post, depth=2) for post in experiment["posts"])
            if experiment["posts"]
            else '<p>この実験に紐づく投稿はまだありません。</p>'
        )
        gallery_preview = experiment["gallery_items"][:6]
        gallery_html = (
            "\n".join(render_gallery_item_card(item, depth=2, show_experiment=False) for item in gallery_preview)
            if gallery_preview
            else render_placeholder()
        )
        body = f"""
    <section class="page-title experiment-page-title">
      {render_page_kicker('Experiments', experiment['title'], '実験一覧', 'experiments/', depth=2)}
      <p class="eyebrow">Experiment Record</p>
      <h1>{html.escape(experiment['title'])}</h1>
      <div class="meta-row">
        <span class="status-pill {status_class(experiment['status'])}">{html.escape(experiment['status'])}</span>
        <span>{html.escape(experiment['period_label'])}</span>
      </div>
      <p>{html.escape(experiment['summary'])}</p>
      <div class="experiment-stats experiment-stats-wide">
        <span>{experiment['post_count']}件の投稿</span>
        <span>{experiment['image_count']}枚の画像</span>
        <span>{html.escape(experiment['crop'])}</span>
      </div>
    </section>

    <section class="section-grid experiment-overview-grid">
      <div class="section-copy">
        {experiment['body_html']}
      </div>
      <aside class="agent-note">
        <span>Gallery</span>
        <p><a class="text-link" href="../../gallery/experiments/{html.escape(experiment['slug'])}/">この実験の画像一覧を見る</a></p>
      </aside>
    </section>

    <section class="section-heading section-heading-row">
      <div>
        <p class="eyebrow">Posts</p>
        <h2>この実験の投稿</h2>
      </div>
      <a class="text-link more-link" href="../../posts/">ブログ一覧へ</a>
    </section>
    <section class="post-list" id="posts">
{posts_html}
    </section>

    <section class="section-heading section-heading-row">
      <div>
        <p class="eyebrow">Gallery</p>
        <h2>この実験の画像</h2>
      </div>
      <a class="text-link more-link" href="../../gallery/experiments/{html.escape(experiment['slug'])}/">画像一覧へ</a>
    </section>
    <section class="gallery-detail-grid" id="gallery">
{gallery_html}
    </section>
"""
        output = DOCS_DIR / "experiments" / experiment["slug"] / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(page_shell(experiment["title"], body, depth=2, section="experiments"), encoding="utf-8")


def write_gallery_index(posts: list[dict[str, Any]], experiments: list[dict[str, Any]]) -> None:
    experiment_cards = "\n".join(
        render_experiment_card(experiment, depth=1, link_target="gallery")
        for experiment in experiments
    )
    gallery_items = collect_gallery_items(posts)
    gallery_html = (
        "\n".join(render_gallery_item_card(item, depth=1) for item in gallery_items)
        if gallery_items
        else render_placeholder()
    )
    body = f"""
    <section class="page-title">
      {render_page_kicker('Gallery', '画像ギャラリー', depth=1)}
      <p class="eyebrow">Gallery Archive</p>
      <h1>画像ギャラリー</h1>
      <p>まず実験ごとに入り、その中で写真を辿れる構成にしました。下には全体の新しい順も残しています。</p>
    </section>

    <section class="section-heading section-heading-row">
      <div>
        <p class="eyebrow">By Experiment</p>
        <h2>実験別ギャラリー</h2>
      </div>
      <a class="text-link more-link" href="../experiments/">実験一覧へ</a>
    </section>
    <section class="experiment-grid">
{experiment_cards}
    </section>

    <section class="section-heading">
      <p class="eyebrow">Latest Images</p>
      <h2>最新順の画像一覧</h2>
    </section>
    <section class="gallery-detail-grid">
{gallery_html}
    </section>
"""
    output = DOCS_DIR / "gallery" / "index.html"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page_shell("画像ギャラリー", body, depth=1, section="gallery"), encoding="utf-8")


def write_experiment_gallery_pages(experiments: list[dict[str, Any]]) -> None:
    for experiment in experiments:
        gallery_html = (
            "\n".join(render_gallery_item_card(item, depth=3, show_experiment=False) for item in experiment["gallery_items"])
            if experiment["gallery_items"]
            else render_placeholder()
        )
        body = f"""
    <section class="page-title experiment-page-title">
      {render_page_kicker('Gallery', experiment['title'] + 'の画像一覧', '画像ギャラリー', 'gallery/', depth=3)}
      <p class="eyebrow">Experiment Gallery</p>
      <h1>{html.escape(experiment['title'])}の画像一覧</h1>
      <div class="meta-row">
        <span class="status-pill {status_class(experiment['status'])}">{html.escape(experiment['status'])}</span>
        <span>{html.escape(experiment['period_label'])}</span>
      </div>
      <p>{html.escape(experiment['summary'])}</p>
    </section>
    <section class="gallery-detail-grid">
{gallery_html}
    </section>
"""
        output = DOCS_DIR / "gallery" / "experiments" / experiment["slug"] / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(page_shell(f"{experiment['title']}の画像一覧", body, depth=3, section="gallery"), encoding="utf-8")


def write_post_pages(posts: list[dict[str, Any]]) -> None:
    for post in posts:
        images_html = (
            "\n".join(render_image_card(image, depth=2) for image in post["images"])
            if post["images"]
            else render_placeholder()
        )
        experiment = post.get("experiment")
        experiment_gallery_link = ""
        if experiment is not None:
            experiment_gallery_link = (
                '<p><a class="text-link" href="../../gallery/experiments/'
                + html.escape(experiment["slug"])
                + '/">この実験の画像一覧を見る</a></p>'
            )
        body = f"""
    <article class="article">
      <header class="article-header">
        {render_page_kicker('Blog', post['title'], '投稿一覧', 'posts/', depth=2)}
        <div class="meta-row">
          <time datetime="{html.escape(post['date'])}">{html.escape(post['date_label'])}</time>
          <span class="status-pill {status_class(post['status'])}">{html.escape(post['status'])}</span>
        </div>
        <h1>{html.escape(post['title'])}</h1>
        <p>{html.escape(post['summary'])}</p>
        {render_experiment_link(experiment, 2)}
        {render_tags(post['tags'])}
      </header>
      <div class="article-body">
{post['body_html']}
      </div>
      <section class="article-gallery">
        <h2>画像ギャラリー</h2>
        {experiment_gallery_link}
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
        output.write_text(page_shell(post["title"], body, depth=2, section="blog"), encoding="utf-8")


def write_legacy_redirects() -> None:
    for slug, target in LEGACY_REDIRECTS.items():
        body = f"""
    <section class="page-title">
      <p class="eyebrow">Redirect</p>
      <h1>ページを移動しました</h1>
      <p>このブログのURLは変わりました。自動で移動しない場合は、下のリンクを開いてください。</p>
      <p><a class="text-link" href="{html.escape(target, quote=True)}">新しいページを開く</a></p>
    </section>
    <script>
      window.location.replace({target!r});
    </script>
"""
        output = DOCS_DIR / "posts" / slug / "index.html"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(page_shell("ページを移動しました", body, depth=2, section="blog"), encoding="utf-8")


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
    output.write_text(page_shell(SITE_TITLE_EN, body, depth=1, lang="en", section="english"), encoding="utf-8")


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
    (DOCS_DIR / "about").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "en").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "experiments").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "gallery" / "experiments").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "assets" / "js").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / "assets" / "images").mkdir(parents=True, exist_ok=True)
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")
    (DOCS_DIR / "assets" / "js" / ".gitkeep").write_text("", encoding="utf-8")
    (DOCS_DIR / "assets" / "images" / ".gitkeep").write_text("", encoding="utf-8")


def main() -> None:
    prepare_docs()
    copy_assets()
    posts = load_posts()
    experiments = load_experiments()
    attach_experiments(posts, experiments)
    write_index(posts, experiments)
    write_about_page()
    write_posts_index(posts)
    write_experiments_index(experiments)
    write_experiment_pages(experiments)
    write_gallery_index(posts, experiments)
    write_experiment_gallery_pages(experiments)
    write_post_pages(posts)
    write_legacy_redirects()
    write_english_page()
    print(f"Built {SITE_TITLE_EN}: {len(posts)} posts, {len(experiments)} experiments -> {DOCS_DIR}")


if __name__ == "__main__":
    main()
