# OpenClaw Planter Lab Skill

このファイルは、OpenClawが `openclaw-planter-lab-website` を保守・更新するときの作業手順です。

## OpenClawがやってよいこと

- `content/posts/` への投稿追加
- `content/images/YYYY-MM-DD/` への画像追加
- `scripts/build_site.py` の実行
- `docs/` の再生成
- `git diff` の確認
- ユーザー許可後の `git commit`
- ユーザー許可後の `git push`

## OpenClawが原則触る場所

- `content/posts/`
- `content/about.md`
- `content/images/`
- `scripts/build_site.py`
- `templates/`
- `docs/`

`docs/` はビルド生成物として扱います。手動で直接編集するより、原則として `content/`、`templates/`、`scripts/build_site.py` を編集して再生成してください。

## OpenClawが勝手にやってはいけないこと

- APIキーやトークンを作成・保存・変更しない
- `.env`、`.env.*`、ローカル設定ファイル、credentials、secrets、秘密鍵をリポジトリへ追加しない
- リポジトリ外のファイルを変更しない
- `.git/config` や認証情報を変更しない
- 既存記事を勝手に削除しない
- public公開に不適切な個人情報や位置情報を含めない
- ユーザー確認なしに大規模な設計変更をしない
- ユーザー確認なしに `git commit` や `git push` をしない

## 新しい栽培ログを追加する手順

1. 日付を確認する
2. `content/posts/YYYY-MM-DD-slug.md` を作る
3. 画像がある場合は `content/images/YYYY-MM-DD/` に置く
4. 画像を追加したら `python3 scripts/sanitize_image_metadata.py` を実行してメタデータを除去する
5. front matter を書く
6. Markdown本文を書く
7. `python3 scripts/build_site.py` を実行する
8. `docs/` の生成結果を確認する
9. `python3 scripts/public_safety_check.py` を実行する
10. `git diff` を確認する
11. ユーザーに変更内容を要約して確認する
12. ユーザーが許可したら commit する
13. ユーザーが許可したら push する

## front matter の基本形

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

## 投稿本文の見出し

必要に応じて、次の見出しを使います。

```markdown
## 今日の観察
## 今日やったこと
## 次にやること
## OpenClawコメント
## メモ
```

## ビルド方法

venv がある場合:

```bash
source .venv/bin/activate
```

依存関係の確認:

```bash
python3 -m pip install -r requirements.txt
```

ビルド:

```bash
python3 scripts/build_site.py
```

公開前チェック:

```bash
python3 scripts/sanitize_image_metadata.py
python3 scripts/public_safety_check.py
```

ローカル確認:

```bash
cd docs
python3 -m http.server 8000
```

ブラウザで `http://localhost:8000` を開きます。

## コミットとpushの方法

commit と push は、必ずユーザーの明示的な許可を得てから実行します。

```bash
git status
git diff
git add content docs
git add README.md SKILL.md AGENTS.md ASSETS_LICENSE.md scripts templates requirements.txt .gitignore
git commit -m "add planter log for YYYY-MM-DD"
git push origin main
```

## Discord経由の依頼を受けた想定の処理ルール

- 投稿依頼文からタイトル、日付、本文、作業内容、観察内容、次の作業、OpenClawコメントを整理する
- 画像が添付されている場合は日付フォルダに保存する想定で処理する
- 添付画像や追加画像は、公開前にEXIF/GPSなどのメタデータを除去する
- 本番反映前に必ず変更内容を要約する
- 自動pushは、ユーザーが明示的に許可した場合のみ行う
- 画像に個人情報や位置情報が含まれていないか注意喚起する

## メディア素材の扱い

写真、画像、動画、音声、その他メディア素材は、特に明記がない限り All rights reserved です。無断転載、無断利用、再配布、AI学習用途での利用は禁止されています。

プロフィール画像を扱う場合も同じ方針です。`content/images/spreadknowledge.png` と `content/images/クローラ.png` は公開用に `docs/assets/images/profile/` へコピーされますが、画像の無断利用は禁止です。公開前に、画像の内容や権利上の扱いに問題がないか確認してください。
