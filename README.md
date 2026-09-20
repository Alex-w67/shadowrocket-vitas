# Vitas Shadowrocket 自动更新配置

这是一份面向 iPhone 日常使用的 Shadowrocket 混合配置：保留 CNIP 配置“国内直连、国外代理、强广告过滤”的可靠性，同时加入 AI、Telegram、YouTube、Apple、Google、Microsoft 独立策略组。

## 同时运行多个应用时如何分流

Shadowrocket按每条连接独立匹配规则。ChatGPT、Telegram和YouTube可以同时使用美国、日本和香港节点，不会互相抢占或覆盖。它们只共享手机的底层 Wi-Fi/蜂窝网络，各自的代理出口相互独立。

策略默认设计：

- AI：优先美国地区组；可进入“AI固定节点”选择一个具体节点。
- Telegram：优先日本地区组；建议进入“Telegram固定节点”选择一个具体节点并长期保持。
- YouTube：香港、日本、新加坡、美国地区组自动测速。
- Apple、Microsoft：默认直连。
- Google：默认代理。
- 中国域名和中国IP：直连。
- 其他未识别的国外连接：代理。

## 自动更新

GitHub Actions每天北京时间08:20抓取并合并：

- Johnshall `sr_cnip_ad.conf` 的完整广告和手工代理规则；
- Johnshall `lazy_group.conf` 当前引用的服务规则；
- Blackmatrix7 `ChinaMax` 国内域名规则。

构建过程会检查策略组引用、模板占位符、`FINAL`数量以及最低规则数量。任何检查失败都不会发布损坏的配置，手机继续使用上一次正常版本。

Shadowrocket订阅地址为：

```text
https://raw.githubusercontent.com/你的GitHub用户名/shadowrocket-vitas/main/vitas_shadowrocket.conf
```

首次导入后，在“配置 → 本地文件”选中本配置。建议通过iOS快捷指令在每天08:30触发一次配置更新。

## 与现有模块配合

可以继续使用：广告拦截与净化、HTTPDNS拦截、YouTube Enhance。模块规则优先于主配置规则，因此不再叠加其他大规模 DIRECT/PROXY/REJECT 模块。

## 上游来源

- https://github.com/Johnshall/Shadowrocket-ADBlock-Rules-Forever
- https://github.com/blackmatrix7/ios_rule_script

本仓库不保存节点、订阅链接、证书或任何账号信息。
