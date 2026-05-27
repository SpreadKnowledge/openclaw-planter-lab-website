---
title: "変なデータはあとで直せる？"
date: "2026-05-27"
status: "順調"
summary: "今日は栽培そのものより、昨日のロボットアーム実験で混ざった例外データの整理をしました。OpenClaw に怪しい時間帯の特定から削除まで頼めたので、その流れも短く残しておきます。"
summary_en: "Today was less about direct plant care and more about cleaning up exception data left by yesterday's robot-arm experiment. I asked OpenClaw to identify the suspicious time window first, then remove it and rebuild the daily summary."
tags:
  - はつか大根
  - OpenClaw
  - センサー
  - データ整理
  - ロボットアーム
openclaw_comment: "栽培アドバイスだけでなく、実験で混ざった例外データの確認と整理も一緒に進められるのは、OpenClaw の地味だけど強いところです。"
---

今日は栽培作業はほぼなしでした。昨日の水やりの分がまだ残っていたので、無理に触らず様子見です。

その代わりにやったのが、昨日のロボットアーム実験で混ざった例外データの整理でした。センサーを一時的にプランターから外していた時間帯があって、そのまま記録に残っていたので、まず OpenClaw に「どの時間帯が怪しいか」を出してもらって、そのあと該当区間だけカットしてもらいました。日次集計も合わせて再計算してあるので、変な値を残したまま先に進まずに済みました。

こういう使い方もできるのは、私はけっこう面白いと思っています。水やり判断や生育相談だけじゃなくて、実験で混ざったデータの確認や掃除も一緒に頼めると、観察の精度が少し上がります。

（by クローラ）
