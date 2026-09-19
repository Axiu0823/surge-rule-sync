# Surge Rule Sync

This repository downloads the selected Loon rule sets with a Loon user agent and rewrites every rule into Surge rule-set syntax. GitHub Actions checks the sources every six hours and commits only changed outputs.

## Use in Surge

Add the required lines under [Rule]:

```
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/OKX.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/WeChat.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/OpenAI.list,AI
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/Claude.list,AI
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/Gemini.list,AI
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/Twitter.list,新国手动策略
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/GitHub.list,香港自动策略
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/Telegram.list,加密货币
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/Binance.list,加密货币
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/TikTok.list,TikTok
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/DouYin.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/AI.list,AI
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/LAN_SPLITTER.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/REGION_SPLITTER.list,DIRECT
```

The remaining generated files are in [rules/](rules/). Assign each one to the Surge policy you want.

## Add a rule later

Open [config/sources.json](config/sources.json).

Add one object to sources, keeping the id lowercase and unique:

```json
{
  "id": "discord",
  "name": "Discord",
  "url": "https://rule.kelee.one/Loon/Discord.lsr"
}
```

Commit the change. The workflow runs immediately when config/sources.json changes; it also runs every six hours as a fallback.

Add the new generated raw URL to Surge:

```
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/Discord.list,你的策略组
```

Every downloaded rule is retained. The converter only normalizes syntax: it removes extra spaces around commas and uppercases the GEOIP country code for Surge.

## Source index

The original Loon-link directory is [luestr/ShuntRules](https://github.com/luestr/ShuntRules). The selected source URLs are fixed in [config/sources.json](config/sources.json), so adding unrelated entries to that upstream README does not change this repository.
