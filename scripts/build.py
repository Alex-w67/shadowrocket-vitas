#!/usr/bin/env python3
"""Build a stable Shadowrocket configuration from maintained upstream sources."""

from __future__ import annotations

import argparse
import datetime as dt
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
        line = re.split(r"\s+//", line, maxsplit=1)[0].strip()
        if line:
            result.append(line)
    return result


def replace_policy(line: str) -> str | None:
    parts = [part.strip() for part in line.split(",")]
    for index in range(2, len(parts)):
        policy = parts[index]
        if policy in POLICY_MAP:
            parts[index] = POLICY_MAP[policy]
            return ",".join(parts)
    return None


def deduplicate(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            result.append(line)
    return result


def build(cnip: str, lazy: str) -> list[str]:
    lazy_rules: list[str] = []
    for line in active_rules(lazy):
        if line.startswith(("GEOIP,", "FINAL,")):
            continue
        mapped = replace_policy(line)
        if mapped:
            lazy_rules.append(mapped)

    cnip_rules = [
        line for line in active_rules(cnip)
        if not line.startswith(("GEOIP,", "FINAL,"))
    ]

    rules = [
        "# 一、精细服务分流（来自懒人配置的持续维护规则源）",
        *lazy_rules,
        "",
        "# 二、CNIP手工代理与完整广告规则；保持上游原有顺序",
        *cnip_rules,
        "",
        "# 三、中国域名和IP双重直连，未知国外请求统一代理",
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

    groups = set()
    for line in section(config, "Proxy Group"):
        if "=" in line and not line.lstrip().startswith("#"):
            groups.add(line.split("=", 1)[0].strip())

    builtins = {
        "DIRECT", "PROXY", "REJECT", "REJECT-DICT", "REJECT-ARRAY",
        "REJECT-200", "REJECT-IMG", "REJECT-TINYGIF", "REJECT-VIDEO",
        "REJECT-DROP", "REJECT-NO-DROP", "TAILSCALE",
    }
    undefined = set()
    rule_count = 0
    for line in active_rules(config):
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
    if undefined:
        raise ValueError(f"undefined policies: {sorted(undefined)}")
    if rule_count < 50000:
        raise ValueError(f"unexpectedly small rule set: {rule_count}")


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
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = (
        f"# Generated: {timestamp}\n"
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
