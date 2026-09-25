# Loon Rule Sync

把同一批 Loon 规则源自动转换为 Surge 规则集和 Clash/Mihomo classical rule provider。

## 生成目录

```text
rules/
├── surge/                  # Surge RULE-SET 使用
│   ├── OKX.list
│   └── manifest.json
├── clash/                  # Clash/Mihomo rule-providers 使用
│   ├── OKX.yaml
│   └── manifest.json
└── conversion-report.json  # 每次转换的规则数、类型、来源与校验和
```

文件名始终继承源 Loon 文件名；仅扩展名分别改为 `.list` 和 `.yaml`。

## Use in Surge

在 Surge 配置的 `[Rule]` 下引用 `rules/surge/` 中的文件。例如：

```ini
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/GitHub.list,香港自动策略,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/OKX.list,加密货币,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/WeChat.list,DIRECT,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/Telegram.list,加密货币,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/Binance.list,加密货币,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/TikTok.list,TikTok,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/DouYin.list,DIRECT,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/OpenAI.list,AI,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/Claude.list,AI,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/Gemini.list,AI,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/Twitter.list,X
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/AI.list,AI,extended-matching
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/LAN_SPLITTER.list,DIRECT
RULE-SET,https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/surge/REGION_SPLITTER.list,DIRECT
FINAL,兜底后备策略,dns-failed
```

TikTok 应放在 DouYin 前面：两者目前只有 `pstatp.com` 重叠，因此它会优先走 TikTok 策略。

## Use in Clash / Mihomo

在配置中定义 provider，再在 `rules:` 里引用它。策略名称由你自己的 Clash/Mihomo 配置决定。

```yaml
rule-providers:
  okx:
    type: http
    behavior: classical
    format: yaml
    url: https://raw.githubusercontent.com/Axiu0823/surge-rule-sync/main/rules/clash/OKX.yaml
    path: ./ruleset/OKX.yaml
    interval: 21600

rules:
  - RULE-SET,okx,加密货币
```

其他规则只需把 URL 的文件名替换为相应的源名，例如 `OpenAI.yaml`、`TikTok.yaml`、`DouYin.yaml`。

## 转换原则

- 下载时伪装为 Loon 客户端；Action 每 6 小时执行一次，也可手动运行。
- 用语义解析器处理逗号、引号、括号和嵌套的 `AND` / `OR` / `NOT`，不会用简单分割破坏逻辑规则。
- 支持当前 Loon 官方规则类型：域名、URL/UA、IPv4/IPv6、GEOIP、IP-ASN、源/目的端口、协议及逻辑规则。
- Surge 直接保留规则语义；Clash/Mihomo 将 Loon 的 `DEST-PORT` 改写为其规则名 `DST-PORT`。
- 规则 provider 只包含匹配条件，策略由你的 Surge/Clash 配置指定。源文件若混入末尾策略、出现未知类型、格式错误或无法无损表达的规则，Action 会失败并保留上一次已生成的文件，绝不静默丢弃规则。
- 每次生成都会更新 `rules/conversion-report.json`，可查看每个源的规则数量、类型、校验和与输出路径。

## 添加新规则源

编辑 [config/sources.json](config/sources.json)，在 `sources` 数组里增加一项：

```json
{
  "id": "example",
  "name": "Example",
  "url": "https://rule.kelee.one/Loon/Example.lsr"
}
```

提交后 Action 会自动生成：

- `rules/surge/Example.list`
- `rules/clash/Example.yaml`

然后按需要在 Surge 或 Clash/Mihomo 配置中为它分配策略即可。
