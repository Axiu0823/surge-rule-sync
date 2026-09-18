# Surge Rule Sync

This repository downloads the selected Loon rule sets with a Loon user agent and rewrites every rule into Surge rule-set syntax. GitHub Actions checks the sources every six hours and commits only changed outputs.

## Use in Surge

Add the required lines under `[Rule]`:

```
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/okx.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/wechat.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/openai.list,AI
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/claude.list,AI
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/gemini.list,AI
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/twitter.list,新国手动策略
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/telegram.list,加密货币
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/binance.list,加密货币
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/tiktok.list,TikTok
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/ai.list,AI
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/lan.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/cn-region.list,DIRECT
```

The remaining generated files are in [rules/](rules/). Assign each one to the Surge policy you want.

## Add a rule later

Open [config/sources.json](config/sources.json).

Add one object to `sources`, keeping the `id` lowercase and unique:

```json
{
  "id": "discord",
  "name": "Discord",
  "url": "https://rule.kelee.one/Loon/Discord.lsr"
}
```

Commit the change. The workflow runs immediately when `config/sources.json` changes; it also runs every six hours as a fallback.

Add the new generated raw URL to Surge:

```
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/discord.list,你的策略组
```

Every downloaded rule is retained. The converter only normalizes syntax: it removes extra spaces around commas and uppercases the GEOIP country code for Surge.

## Source index

The original Loon-link directory is [luestr/ShuntRules](https://github.com/luestr/ShuntRules). The selected source URLs are fixed in [config/sources.json](config/sources.json), so adding unrelated entries to that upstream README does not change this repository.
