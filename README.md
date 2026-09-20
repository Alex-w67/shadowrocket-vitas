# Vitas Shadowrocket 自动更新配置

面向 iPhone 日常使用的 Shadowrocket 混合配置。它保留 CNIP 配置的国内直连、国外代理、广告与恶意域名拦截，同时吸收懒人配置的服务策略组能力。仓库只保存规则和构建程序，不保存节点、机场订阅、证书、账号或密钥。

## 主要功能

- 约 5.8 万条有效规则，其中 5.7 万余条为广告或恶意域名拦截规则。
- AI、Telegram、YouTube、Apple、Google、Microsoft 独立分流。
- 香港、台湾、日本、新加坡、美国地区节点自动测速，每 30 分钟复测，50 ms 容差避免频繁跳节点。
- AI 与 Telegram 可锁定具体节点，防止登录期间出口国家反复变化。
- 国内域名和中国 IP 直连，未识别的境外请求代理。
- 国内 DoH、DNS 劫持保护、私有地址应答和代理流量 QUIC 回退。
- 每天自动拉取上游、构建、校验；失败时保留上一份正常配置。

## 订阅地址

```text
https://raw.githubusercontent.com/Alex-w67/shadowrocket-vitas/main/vitas_shadowrocket.conf
```

## 首次使用

1. 先在 Shadowrocket 中添加自己的节点订阅并确认至少一个节点可用。本配置不包含节点。
2. 打开“配置”，点击右上角“+”，粘贴上面的订阅地址并下载。
3. 在“配置 → 本地文件”中点击 `vitas_shadowrocket.conf`，让其出现勾选标记。
4. 回到首页，把“全局路由”设为“配置”。不要使用“代理”或“直连”模式，否则分流规则不会生效。
5. 首次导入时 AI、Telegram、YouTube 都继承当前 `PROXY` 节点，保证即使机场没有某个地区节点也能先正常联网。

## 建议的策略组设置

### AI

1. 打开“AI固定节点”。
2. 从日本、台湾、美国或新加坡中选择一个能稳定打开 ChatGPT、Claude、Gemini 等服务的具体节点。
3. 返回上一级，把“AI”设为“AI固定节点”。

优先看节点是否干净、稳定以及是否长期保持同一出口，其次才是国家。对中国大陆用户，日本或台湾通常延迟更低；美国并非必选，只在某些服务、账号区域或节点质量明显更好时更合适。不要频繁切换 AI 出口国家。

### Telegram

1. 打开“Telegram固定节点”并选择一个稳定、支持 UDP 的具体节点。
2. 返回上一级，把“Telegram”设为“Telegram固定节点”。

Telegram 与 AI 可以同时使用不同节点。Shadowrocket按每条连接分别匹配，不会互相抢占。

### YouTube

可选择香港、台湾、日本、新加坡或美国地区组。地区组会在本地区节点内自动测速；追求中文内容与低延迟可优先香港或台湾，追求稳定可根据实际线路选择日本。

### 其他策略

- Apple：默认 `DIRECT`，减少系统服务延迟。
- Google：默认 `PROXY`。
- Microsoft：默认 `DIRECT`；如果 Copilot 或海外服务受限，再手动改为代理地区组。
- `PROXY`：继承 Shadowrocket 首页当前选择的通用节点，是所有专用组的安全初始值。

如果某个地区组为空，说明机场节点名称不包含对应国旗、英文缩写或中文地区名。此时可以选 `PROXY`，或将节点重命名为包含“日本、台湾、美国、新加坡、香港”等可识别文字。

## 自动更新原理

GitHub Actions 每天北京时间 08:20 执行以下流程：

1. 下载 Johnshall 的 CNIP 广告配置与 lazy_group 策略规则。
2. 把误用的 QuantumultX 规则地址转换为 Shadowrocket 格式。
3. 合并规则并保持“必要白名单 → 广告拦截 → 服务分流 → 国内直连 → 国外代理”的顺序。
4. 检查策略组引用、规则数量、广告规则数量、规则集格式、唯一 `FINAL` 以及模板占位符。
5. 只有内容发生变化且全部检查通过，才提交新的 `vitas_shadowrocket.conf`；失败时不覆盖旧版本。

配置中的 `update-url` 会指向本仓库最新版。要让手机也无人值守更新，可在 iPhone“快捷指令 → 自动化”中建立每天 08:30 的个人自动化，运行 Shadowrocket 的“更新配置”，并关闭“运行前询问”。

## 模块配合

可以继续使用广告净化、HTTPDNS 拦截和 YouTube Enhance。模块规则优先于主配置规则，因此不要再叠加其他大规模 DIRECT、PROXY 或 REJECT 规则包，否则可能覆盖本配置的策略组和分流顺序。

## 上游来源

- https://github.com/Johnshall/Shadowrocket-ADBlock-Rules-Forever
- https://github.com/blackmatrix7/ios_rule_script
- https://github.com/iab0x00/ProxyRules
