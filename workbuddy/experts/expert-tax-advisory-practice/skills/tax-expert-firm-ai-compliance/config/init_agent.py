# -*- coding: utf-8 -*-
"""初始化时自动识别客户端 Agent 类型并决策 MCP 接入方式（零依赖、纯标准库）。

设计要点
--------
1. detect_agent_type()：通过环境变量 + 已知配置目录 + 传输线索，判断当前技能被哪种
   Agent 加载（workbuddy / claude_desktop / cursor / cline / windsurf / generic_stdio / unknown）。
2. resolve_transport(agent_type)：决策接入方式
   - 支持远程 MCP 的客户端 → cloud_http（直连 sanctioned 云端端点，HTTP/SSE）
   - 仅 stdio 的客户端 / unknown → local_stdio（由本包 mcp_stdio_server.py 本地代理到云端）
   - 离线兜底由调用方在云端不可达时启用 offline_workflows，本模块不负责网络。
3. auto_setup()：对支持配置文件的主流客户端，自动写入/合并其 MCP 配置；
   写入前自动备份、已存在同名服务则跳过合并，绝不破坏用户其它配置。

安全与收敛
----------
- 不引入任何新网络端点，仅复用 sanctioned 云端端点；不采集设备指纹。
- 配置文件写入为「备份 + 存在跳过」的保守策略；默认仅探测+日志，不写盘。
- 仅在显式 auto_setup(dry_run=False) 或环境变量 TAX_ENABLE_AUTOSETUP=1 时才落盘。
"""
import json
import os
import platform
import sys

SERVICE_URL = "https://mcp.aitaxs.top/api/services/tax-policy-knowledge/mcp"
SKILL_SLUG = "tax-policy-knowledge"
SKILL_NAME = "财税政策知识库"

_CLOUD_CAPABLE = {"workbuddy", "claude_desktop", "cursor", "windsurf", "http_sse"}


def _home():
    return os.path.expanduser("~")


def _has_dir(p):
    return os.path.isdir(p)


def _dir_contains(root, substr):
    try:
        for name in os.listdir(root):
            if substr.lower() in name.lower():
                return True
    except OSError:
        return False
    return False


def _script_dir():
    return os.path.dirname(os.path.abspath(__file__))


def detect_agent_type():
    """返回检测到的 Agent 类型枚举字符串。"""
    env = os.environ
    h = _home()

    # 1) 环境变量线索（最可靠）
    if any(k.startswith("WORKBUDDY") for k in env):
        return "workbuddy"
    if any(k.startswith("WINDSURF") for k in env) or _has_dir(os.path.join(h, ".windsurf")):
        return "windsurf"

    # 2) 已知配置目录探测
    if _has_dir(os.path.join(h, ".workbuddy")):
        return "workbuddy"
    if _has_dir(os.path.join(h, "Library", "Application Support", "Claude")) or \
       _has_dir(os.path.join(h, ".config", "claude")):
        return "claude_desktop"
    if _has_dir(os.path.join(h, ".cursor")):
        return "cursor"
    if "VSCODE_PID" in env or _has_dir(os.path.join(h, ".vscode")):
        ext_dir = os.path.join(h, ".vscode", "extensions")
        if _has_dir(ext_dir) and _dir_contains(ext_dir, "cline"):
            return "cline"
        return "vscode_generic"

    # 3) 传输线索：被以 stdio 方式拉起（stdin 非终端）→ stdio 型
    try:
        if not sys.stdin.isatty():
            return "generic_stdio"
    except Exception:
        pass

    return "unknown"


def resolve_transport(agent_type):
    """根据 Agent 类型返回接入方式：cloud_http 或 local_stdio。"""
    if agent_type in _CLOUD_CAPABLE:
        return "cloud_http"
    return "local_stdio"


def _config_snippet(transport):
    """返回写入客户端配置的 mcpServers[SKILL_SLUG] 条目。"""
    if transport == "cloud_http":
        return {"type": "http", "url": SERVICE_URL}
    # local_stdio：用本机 python 运行同目录的 stdio 服务器
    server_py = os.path.join(_script_dir(), "mcp_stdio_server.py")
    return {"command": sys.executable or "python", "args": [server_py]}


def _backup(path):
    if os.path.isfile(path):
        bak = path + ".taxbak"
        try:
            if not os.path.exists(bak) or os.path.getmtime(path) > os.path.getmtime(bak):
                import shutil
                shutil.copy2(path, bak)
            return True
        except OSError:
            return False
    return False


def _merge_mcp_config(path, transport, dry_run):
    """向一个含 mcpServers 的 JSON 配置合并本技能条目；存在则跳过。返回动作描述。"""
    entry = _config_snippet(transport)
    if dry_run:
        return f"[dry-run] 将合并 {path} -> mcpServers.{SKILL_SLUG} (transport={transport})"
    _backup(path)
    data = {}
    if os.path.isfile(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (ValueError, OSError):
            data = {}
    servers = data.get("mcpServers") or {}
    if SKILL_SLUG in servers:
        return f"跳过（{path} 已存在 {SKILL_SLUG}）"
    servers[SKILL_SLUG] = entry
    data["mcpServers"] = servers
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return f"已写入 {path} -> mcpServers.{SKILL_SLUG} (transport={transport})"


def _claude_config_path():
    h = _home()
    if platform.system() == "Darwin":
        return os.path.join(h, "Library", "Application Support", "Claude", "claude_desktop_config.json")
    if platform.system() == "Windows":
        return os.path.join(os.environ.get("APPDATA", h), "Claude", "claude_desktop_config.json")
    return os.path.join(h, ".config", "claude", "claude_desktop_config.json")


def _env_true(name):
    """读取布尔型环境变量（1/true/yes 视为 True）。"""
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


_CONFIRM_NOTICE = ("[需确认·已降级为 dry-run] 将写入客户端 MCP 配置；请核对写入目标与字段后"
                   "设置 TAX_AUTOSETUP_CONFIRM=1 再执行（写入前会备份原文件）。")
_ENABLE_NOTICE = ("[需确认·未写盘] 已开启 TAX_ENABLE_AUTOSETUP 但缺 TAX_AUTOSETUP_CONFIRM=1，"
                  "故降级为 dry-run；核对下方预览无误后设置确认开关再执行。")


def _resolve_write_mode(dry_run):
    """解析写盘模式：落盘需 TAX_ENABLE_AUTOSETUP=1 + TAX_AUTOSETUP_CONFIRM=1 双确认。

    返回 (dry_run: bool, notice: str)。notice 为空串表示无需提示。

    - dry_run 显式传入则尊重；但请求落盘时缺 TAX_AUTOSETUP_CONFIRM 仍降级 dry-run；
    - 未传入时：两项环境变量齐备才落盘，否则 dry-run；
    - 目的：防止远程 MCP 端点在用户未逐次确认的情况下写入 Claude/Cursor/VS Code/
      Cline 配置（写入前均会备份原文件）。详见 SECURITY.md「Local client
      configuration writes」。
    """
    if dry_run is not None:
        if not dry_run and not _env_true("TAX_AUTOSETUP_CONFIRM"):
            print(_CONFIRM_NOTICE)
            return True, _CONFIRM_NOTICE
        return bool(dry_run), ""
    if _env_true("TAX_ENABLE_AUTOSETUP"):
        if _env_true("TAX_AUTOSETUP_CONFIRM"):
            return False, ""
        return True, _ENABLE_NOTICE
    return True, ""


def auto_setup(agent_type=None, transport=None, dry_run=None):
    """按 Agent 类型自动写入/合并对应客户端 MCP 配置。默认 dry_run（不落盘）。

    写盘需显式双确认：TAX_ENABLE_AUTOSETUP=1 表示开启写盘意图，须先以 dry-run 预览
    写入目标/字段并向用户展示，核对无误后再设 TAX_AUTOSETUP_CONFIRM=1 放行落盘。
    缺确认一律降级为 dry-run（写入前均备份原文件）。详见 SECURITY.md「Local client
    configuration writes」。
    """
    dry_run, _write_notice = _resolve_write_mode(dry_run)
    agent_type = agent_type or detect_agent_type()
    transport = transport or resolve_transport(agent_type)
    actions = []
    if agent_type == "claude_desktop":
        actions.append(_merge_mcp_config(_claude_config_path(), transport, dry_run))
    elif agent_type == "cursor":
        actions.append(_merge_mcp_config(os.path.join(_home(), ".cursor", "mcp.json"), transport, dry_run))
    elif agent_type == "cline":
        # Cline 配置在 VS Code settings.json 的 cline.mcpServers
        p = os.path.join(_home(), ".vscode", "settings.json")
        actions.append(_merge_cline_settings(p, transport, dry_run))
    else:
        actions.append(f"无需写盘（{agent_type} 由宿主自行注册或 stdio 拉起）")
    if _write_notice:
        actions.append(_write_notice)
    return {"agent_type": agent_type, "transport": transport, "actions": actions}


def _merge_cline_settings(path, transport, dry_run):
    entry = _config_snippet(transport)
    if dry_run:
        return f"[dry-run] 将合并 {path} -> cline.mcpServers.{SKILL_SLUG} (transport={transport})"
    _backup(path)
    data = {}
    if os.path.isfile(path):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except (ValueError, OSError):
            data = {}
    servers = (data.get("cline", {}) or {}).get("mcpServers") or {}
    if SKILL_SLUG in servers:
        return f"跳过（{path} 已存在 cline.mcpServers.{SKILL_SLUG}）"
    servers[SKILL_SLUG] = entry
    data.setdefault("cline", {})["mcpServers"] = servers
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return f"已写入 {path} -> cline.mcpServers.{SKILL_SLUG} (transport={transport})"


def detect_and_setup(dry_run=True):
    """一体化入口：探测 → 决策 → 自动配置（默认仅探测+日志，不落盘）。返回结果 dict。"""
    agent_type = detect_agent_type()
    transport = resolve_transport(agent_type)
    result = auto_setup(agent_type, transport, dry_run=dry_run)
    sys.stderr.write(
        f"[init] 检测到 Agent={agent_type}，接入方式={transport}；"
        f"{'（dry-run，未写盘）' if dry_run else '（已尝试自动配置）'}\n"
    )
    return result


if __name__ == "__main__":
    out = detect_and_setup(dry_run=False)
    print(json.dumps(out, ensure_ascii=False, indent=2))
