# OpenClaw栽培実験室

OpenClaw Planter Lab は、SpreadKnowledge が OpenClaw のWebサイト保守・更新を練習するための静的Webサイトです。

AIエージェントがプランター栽培を観察し、毎日の作業記録、画像ログ、センサー観察、OpenClawコメントをMarkdownで残し、GitHub Pagesで公開できる形にします。

## 目的

- OpenClawによる栽培記録更新のデモサイトを作る
- `content/` にMarkdown記事や画像を追加し、`docs/` に公開用HTMLを生成する
- GitHub Pagesの `/docs` 公開フローを練習する
- 将来的にOpenClawが build、diff確認、ユーザー許可後のcommit/pushまで担当しやすい構成にする

## ディレクトリ構成

```text
openclaw-planter-lab-website/
├── docs/                  # GitHub Pages公開用の生成物
├── content/
│   ├── about.md           # 運営者とOpenClawエージェント紹介
│   ├── posts/             # Markdown投稿
│   └── images/            # 元画像
├── scripts/
│   └── build_site.py      # 静的サイトビルダー
├── templates/
│   └── style.css          # CSSソース
├── README.md
├── SKILL.md
├── AGENTS.md
├── ASSETS_LICENSE.md
├── requirements.txt
└── .gitignore
```

## ローカルセットアップ

Python 3 が必要です。初期実装では外部Pythonパッケージを使っていません。

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

## ビルド方法

```bash
python3 scripts/build_site.py
```

ビルドすると、`docs/index.html`、`docs/posts/`、`docs/en/index.html`、`docs/assets/` が生成されます。
運営者とOpenClawエージェントを紹介するページは `docs/about/index.html` に生成されます。

## ローカル確認方法

```bash
python3 scripts/build_site.py
cd docs
python3 -m http.server 8000
```

ブラウザで次を開きます。

```text
http://localhost:8000
```

## 新しい投稿の追加方法

`content/posts/` に、次の形式のMarkdownファイルを追加します。

```text
YYYY-MM-DD-slug.md
```

例:

```text
content/posts/2026-05-01-first-log.md
```

front matter の例:

```yaml
---
title: "播種から7日目の観察ログ"
date: "2026-05-01"
status: "注意"
summary: "双葉が開き始めたが、一部で土の乾きが見られる。"
summary_en: "Seedlings are opening, with some dry soil visible."
tags:
  - はつか大根
  - 発芽
  - 栽培記録
images:
  - path: "content/images/2026-05-01/01-planter.jpg"
    alt: "はつか大根を播種したプランターの全体写真"
openclaw_comment: "乾燥しすぎに注意しつつ、過湿にもならないよう少量ずつ管理してください。"
---
```

本文では、必要に応じて次の見出しを使います。

```markdown
## 今日の観察
## 今日やったこと
## 次にやること
## OpenClawコメント
## メモ
```

## 画像の追加場所

画像は日付ごとに `content/images/YYYY-MM-DD/` に保存します。

例:

```text
content/images/2026-05-01/01-planter.jpg
content/images/2026-05-01/02-soil.jpg
```

`scripts/build_site.py` を実行すると、画像は `docs/assets/images/YYYY-MM-DD/` にコピーされます。投稿の `images` に複数の画像を指定した場合、最初の画像がアイキャッチとして使われます。

プロフィール画像は `content/images/spreadknowledge.png` と `content/images/クローラ.png` を元に、公開用として `docs/assets/images/profile/spreadknowledge.png` と `docs/assets/images/profile/crawler.png` にコピーされます。

公開リポジトリのため、写真に個人情報、位置情報、写してはいけないものが含まれていないか確認してください。

## GitHub Pages公開設定

GitHubのリポジトリ画面で、次のように設定します。

```text
Settings
→ Pages
→ Build and deployment
→ Source: Deploy from a branch
→ Branch: main
→ Folder: /docs
→ Save
```

`main` ブランチの `/docs` フォルダが公開対象になります。

## OpenClawによる保守想定

OpenClawは、ユーザーの依頼に基づいて `content/posts/` に投稿を追加し、必要な画像を `content/images/` に置き、`python3 scripts/build_site.py` で `docs/` を再生成する想定です。

ただし、`git commit` と `git push` はユーザーが明示的に許可した場合のみ行います。

## ライセンス方針

コード部分は `LICENSE` ファイルに従います。写真、画像、動画、音声、その他メディア素材はコードとは別に扱い、特に明記がない限り All rights reserved です。

詳しくは `ASSETS_LICENSE.md` を確認してください。

このリポジトリは、SpreadKnowledge が OpenClaw の練習・検証用に作成しているものです。
コード部分はリポジトリに含まれるライセンスに従いますが、サイト内で使用する写真・画像・メディア素材の著作権は、特に明記がない限り SpreadKnowledge または各権利者に帰属します。
画像・写真・メディア素材の無断転載、無断利用、再配布、AI学習用途での利用を禁じます。
