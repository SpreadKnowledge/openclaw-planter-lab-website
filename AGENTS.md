# Repository Agent Guidelines

このリポジトリは、SpreadKnowledge が OpenClaw のWebサイト保守・更新を練習するための public repository です。目的は「OpenClaw栽培実験室」というGitHub Pages向け静的Webサイトを、MarkdownとPythonビルドで継続更新できるようにすることです。

## 優先順位

1. 保守しやすいこと
2. 更新しやすいこと
3. GitHub Pagesで安定動作すること
4. スマホで見やすいこと
5. 見た目が良いこと
6. 将来OpenClawが半自動更新しやすいこと

## ディレクトリ構成

- `content/posts/`: Markdown投稿を置く場所
- `content/about.md`: 運営者とOpenClawエージェント紹介の生成元
- `content/images/`: 元画像を日付別に置く場所
- `scripts/build_site.py`: 静的サイト生成スクリプト
- `templates/`: CSSなど、生成元のテンプレート素材
- `docs/`: GitHub Pages公開用の生成物
- `README.md`: 人間向けの説明
- `SKILL.md`: OpenClaw向けの具体的な作業手順
- `ASSETS_LICENSE.md`: 画像・メディア素材のライセンス方針

## デザイン方針

- モバイルファーストで作る
- 白、淡い水色、薄い青灰色を基調にする
- 補助色として淡い緑を少し使う
- 清潔感、観察ノート感、小さな栽培ラボ感を大切にする
- 古い個人ホームページ風、WordPress初期テーマ風、過度に派手な表現は避ける
- 写真が追加されたときにきれいに見える余白、角丸、薄い影を使う
- CSS変数を使い、将来のダークモードや色調整をしやすくする

## 投稿ルール

- 投稿は `content/posts/YYYY-MM-DD-slug.md` に追加する
- front matter には `title`、`date`、`status`、`summary`、`tags`、`images`、`openclaw_comment` を書く
- 将来の英語対応のため、必要に応じて `summary_en` を追加する
- 投稿本文では、必要に応じて `## 今日の観察`、`## 今日やったこと`、`## 次にやること`、`## OpenClawコメント`、`## メモ` を使う
- 既存記事を削除または大きく書き換える場合は、ユーザー確認を取る

## 画像ルール

- 画像は `content/images/YYYY-MM-DD/` に保存する
- 投稿の `images` には、画像パスとaltテキストを書く
- 画像がない投稿でもページが崩れないようにする
- 公開前に、個人情報、位置情報、写してはいけないものが含まれていないか注意する
- ビルド時に `content/images/` から `docs/assets/images/` にコピーする
- プロフィール画像は公開用に `docs/assets/images/profile/spreadknowledge.png` と `docs/assets/images/profile/crawler.png` へ英数字ファイル名でコピーする
- 公開画像の扱いには注意し、画像の無断利用禁止方針を維持する

## ライセンス・メディア利用ルール

- コード部分は `LICENSE` ファイルに従う
- 写真、画像、動画、音声、その他メディア素材はコードとは別に扱う
- メディア素材は、特に明記がない限り All rights reserved とする
- 無断転載、無断利用、再配布、AI学習用途での利用は禁止
- 画像やメディア素材をMIT License対象として扱わない

## Git運用ルール

- 作業後は `git status` と `git diff` を確認する
- `docs/` はビルド生成物として扱う
- `git commit` と `git push` はユーザーが明示的に許可した場合のみ行う
- `.git/config` や認証情報は変更しない
- 既存の未追跡ファイルやユーザー作業を勝手に削除しない

## 禁止事項

- APIキー、GitHub token、Discord tokenなどの秘密情報を作成・保存・変更しない
- リポジトリ外のファイルを変更しない
- WordPress、Node.js、npm、React、Astro、Next.jsを初期実装に導入しない
- 不要に複雑なフレームワークを導入しない
- ユーザー確認なしに大規模な設計変更をしない
- ユーザー確認なしに `git commit` や `git push` をしない
- public公開に不適切な個人情報や位置情報を含めない
