#!/usr/bin/env python3
"""Build a stable Shadowrocket configuration from maintained upstream sources."""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
import urllib.request


CNIP_URL = "https://johnshall.github.io/Shadowrocket-ADBlock-Rules-Forever/sr_cnip_ad.conf"
LAZY_URL = "https://johnshall.github.io/Shadowrocket-ADBlock-Rules-Forever/lazy_group.conf"
CHINA_MAX_URL = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/ChinaMax/ChinaMax.list"

POLICY_MAP = {
    "AI": "AI",
    "YOUTUBE": "YouTube",
    "TELEGRAM": "Telegram",
    "苹果服务": "Apple",
    "谷歌服务": "Google",
    "微软服务": "Microsoft",
    "哔哩哔哩": "DIRECT",
    "NETFLIX": "PROXY",
    "DISNEY+": "PROXY",
    "MAX": "PROXY",
    "SPOTIFY": "PROXY",
    "TWITTER": "PROXY",
    "FACEBOOK": "PROXY",
    "PAYPAL": "PROXY",
    "AMAZON": "PROXY",
    "游戏平台": "PROXY",
    "TIKTOK": "PROXY",
    "DIRECT": "DIRECT",
    "PROXY": "PROXY",
    "REJECT": "REJECT",
    "REJECT-DICT": "REJECT-DICT",
    "REJECT-ARRAY": "REJECT-ARRAY",
    "REJECT-200": "REJECT-200",
    "REJECT-IMG": "REJECT-IMG",
    "REJECT-TINYGIF": "REJECT-TINYGIF",
    "REJECT-VIDEO": "REJECT-VIDEO",
    "REJECT-DROP": "REJECT-DROP",
    "REJECT-NO-DROP": "REJECT-NO-DROP",
}


def read_source(value: str) -> str:
    if value.startswith(("https://", "http://")):
        request = urllib.request.Request(value, headers={"User-Agent": "vitas-shadowrocket-builder/1.0"})
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.read().decode("utf-8-sig")
    return pathlib.Path(value).read_text(encoding="utf-8-sig")


def section(text: str, name: str) -> list[str]:
    match = re.search(rf"(?ms)^\[{re.escape(name)}\]\s*$\n(.*?)(?=^\[|\Z)", text)
    if not match:
        raise ValueError(f"missing [{name}] section")
    return match.group(1).splitlines()


def active_rules(text: str) -> list[str]:
    result: list[str] = []
    for raw_line in section(text, "Rule"):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # 上游个别规则使用空格加 // 作为行尾说明；不能直接按 // 切分，
        # 否则会误伤 RULE-SET 中的 https:// 地址。
        line = re.split(r"\s+(?://|#)", line, maxsplit=1)[0].strip()
        if line:
            result.append(line)
    return result


def replace_policy(line: str) -> str | None:
    parts = [part.strip() for part in line.split(",")]
    for index in range(2, len(parts)):
        policy = parts[index]
        normalized = policy.upper()
        if normalized in POLICY_MAP:
            parts[index] = POLICY_MAP[normalized]
            return ",".join(parts)
    return None


def rule_policy(line: str) -> str | None:
    parts = [part.strip() for part in line.split(",")]
    if line.startswith("FINAL,") and len(parts) >= 2:
        return parts[1]
    if len(parts) < 3:
        return None
    return parts[-2] if parts[-1] == "no-resolve" else parts[-1]


def set_rule_policy(line: str, policy: str) -> str:
    parts = [part.strip() for part in line.split(",")]
    index = -2 if parts[-1] == "no-resolve" else -1
    parts[index] = policy
    return ",".join(parts)


def normalize_ruleset_url(line: str) -> str:
    # lazy_group偶尔引用QuantumultX格式规则。Shadowrocket规则集必须使用
    # DOMAIN-SUFFIX等Shadowrocket字段，不能直接使用HOST-SUFFIX格式。
    return line.replace("/rule/QuantumultX/", "/rule/Shadowrocket/")


def deduplicate(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            result.append(line)
    return result


def build(cnip: str, lazy: str) -> list[str]:
    priority_rules: list[str] = []
    service_rules: list[str] = []
    for line in active_rules(lazy):
        if line.startswith(("GEOIP,", "FINAL,")):
            continue
        mapped = replace_policy(normalize_ruleset_url(line))
        if not mapped:
            raise ValueError(f"unrecognized lazy policy: {line}")

        # CNIP已经采用ChinaMax + GEOIP + FINAL完成国内外兜底，继续加载
        # Global/China大规则集既重复又会抢在广告规则前匹配，因此剔除。
        if "/Global/Global.list" in mapped or "/China/China.list" in mapped:
            continue
        if "/SteamCN/SteamCN.list" in mapped:
            mapped = set_rule_policy(mapped, "DIRECT")

        if rule_policy(mapped) in {"AI", "Telegram"}:
            priority_rules.append(mapped)
        else:
            service_rules.append(mapped)

    cnip_proxy_rules: list[str] = []
    cnip_reject_rules: list[str] = []
    for line in active_rules(cnip):
        if line.startswith(("GEOIP,", "FINAL,")):
            continue
        mapped = replace_policy(line)
        if not mapped:
            raise ValueError(f"unrecognized CNIP policy: {line}")
        policy = rule_policy(mapped)
        if policy == "PROXY":
            cnip_proxy_rules.append(mapped)
        elif policy and policy.startswith("REJECT"):
            cnip_reject_rules.append(mapped)
        else:
            raise ValueError(f"unexpected CNIP rule policy: {mapped}")

    rules = [
        "# 一、AI与Telegram优先使用独立固定出口",
        *priority_rules,
        "",
        "# 二、保留CNIP原有代理白名单，避免误杀必要服务",
        *cnip_proxy_rules,
        "",
        "# 三、完整广告与恶意域名拦截；置于宽泛服务规则之前",
        *cnip_reject_rules,
        "",
        "# 四、按服务细分流量；来源统一转换为Shadowrocket规则格式",
        *service_rules,
        "",
        "# 五、中国域名和IP双重直连，未知国外请求统一代理",
        f"RULE-SET,{CHINA_MAX_URL},DIRECT",
        "GEOIP,CN,DIRECT",
        "FINAL,PROXY",
    ]
    return deduplicate(rules)


def validate(config: str) -> None:
    if "__UPDATE_URL__" in config or "__RULES__" in config:
        raise ValueError("unresolved template token")
    if config.count("FINAL,") != 1:
        raise ValueError("configuration must contain exactly one FINAL rule")
    for required_section in ("General", "Proxy", "Proxy Group", "Rule", "Host"):
        if config.count(f"[{required_section}]") != 1:
            raise ValueError(f"configuration must contain one [{required_section}] section")
    if "/rule/QuantumultX/" in config:
        raise ValueError("QuantumultX rule-set URL is not valid for this configuration")

    groups = set()
    for line in section(config, "Proxy Group"):
        if "=" in line and not line.lstrip().startswith("#"):
            groups.add(line.split("=", 1)[0].strip())

    required_groups = {
        "AI", "AI固定节点", "Telegram", "Telegram固定节点", "YouTube",
        "Apple", "Google", "Microsoft", "香港节点", "台湾节点", "日本节点",
        "新加坡节点", "美国节点",
    }
    missing_groups = required_groups - groups
    if missing_groups:
        raise ValueError(f"missing policy groups: {sorted(missing_groups)}")

    builtins = {
        "DIRECT", "PROXY", "REJECT", "REJECT-DICT", "REJECT-ARRAY",
        "REJECT-200", "REJECT-IMG", "REJECT-TINYGIF", "REJECT-VIDEO",
        "REJECT-DROP", "REJECT-NO-DROP", "TAILSCALE",
    }
    undefined = set()
    rule_count = 0
    reject_count = 0
    parsed_rules = active_rules(config)
    for line in parsed_rules:
        rule_count += 1
        parts = [part.strip() for part in line.split(",")]
        if line.startswith("FINAL,"):
            policy = parts[1]
        elif len(parts) >= 3:
            policy = parts[-2] if parts[-1] == "no-resolve" else parts[-1]
        else:
            continue
        if policy not in builtins and policy not in groups:
            undefined.add(policy)
        if policy.startswith("REJECT"):
            reject_count += 1
        if line.startswith("RULE-SET,"):
            if len(parts) < 3 or not parts[1].startswith("https://"):
                raise ValueError(f"invalid remote rule set: {line}")
    if undefined:
        raise ValueError(f"undefined policies: {sorted(undefined)}")
    if rule_count < 50000:
        raise ValueError(f"unexpectedly small rule set: {rule_count}")
    if reject_count < 50000:
        raise ValueError(f"unexpectedly small reject set: {reject_count}")
    if not parsed_rules[-1].startswith("FINAL,"):
        raise ValueError("FINAL must be the last active rule")

    group_members = set()
    for line in section(config, "Proxy Group"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        _, value = stripped.split("=", 1)
        tokens = [token.strip() for token in value.split(",")]
        for token in tokens[1:]:
            if "=" not in token:
                group_members.add(token)
    undefined_members = group_members - groups - builtins
    if undefined_members:
        raise ValueError(f"undefined policy-group members: {sorted(undefined_members)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnip", default=CNIP_URL)
    parser.add_argument("--lazy", default=LAZY_URL)
    parser.add_argument("--repository", required=True, help="GitHub owner/repository")
    parser.add_argument("--output", default="vitas_shadowrocket.conf")
    args = parser.parse_args()

    root = pathlib.Path(__file__).resolve().parents[1]
    template = (root / "config" / "base.conf").read_text(encoding="utf-8")
    rules = build(read_source(args.cnip), read_source(args.lazy))
    update_url = f"https://raw.githubusercontent.com/{args.repository}/main/vitas_shadowrocket.conf"
    header = (
        "# Generated automatically; local edits will be replaced.\n"
        f"# Upstream CNIP: {CNIP_URL}\n"
        f"# Upstream policy skeleton: {LAZY_URL}\n"
    )
    config = header + template.replace("__UPDATE_URL__", update_url).replace("__RULES__", "\n".join(rules))
    validate(config)
    output = root / args.output
    output.write_text(config, encoding="utf-8", newline="\n")
    print(f"built {output} with {len(active_rules(config))} active rules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
