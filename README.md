# Surge Rule Sync

This repository downloads the selected Loon rule sets with a Loon user agent and rewrites every rule into Surge rule-set syntax. GitHub Actions checks the sources every six hours and commits only changed outputs.

## Use in Surge

Add the required lines under [Rule]:

```ini
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/okx.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/telegram.list,加密货币
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/binance.list,加密货币
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/tiktok.list,TikTok
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/ai.list,AI
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/lan.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/cn-region.list,DIRECT
```

The remaining generated files are in [rules/](rules/). Assign each one to the Surge policy you want.

## Add a rule later

1. Open [config/sources.json](config/sources.json).
2. Add one object to sources, keeping the id lowercase and unique:

   ```json
   {
     "id": "discord",
     "name": "Discord",
     "url": "https://rule.kelee.one/Loon/Discord.lsr"
   }
   ```

3. Commit the change. The workflow runs immediately when config/sources.json changes; it also runs every six hours as a fallback.
4. Add the new generated raw URL to Surge:

   ```ini
   RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/discord.list,你的策略组
   ```

Every downloaded rule is retained. The converter only normalizes syntax: it removes extra spaces around commas and uppercases the GEOIP country code for Surge.

## Source index

The original Loon-link directory is [luestr/ShuntRules](https://github.com/luestr/ShuntRules). The 14 selected source URLs are fixed in config/sources.json, so adding unrelated entries to that upstream README does not change this repository.
