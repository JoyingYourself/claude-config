#!/usr/bin/env python3
"""
brain-anomaly-detector.py — P2 异常检测 · 会话级检测器（Stop hook）

会话结束时分析整个会话，两层判定：
  Layer 1（统计初筛，本文件）: 破坏性命令黑名单 + 调用量/风险率 z-score + 命令循环
  Layer 2（Qwen3 语义复判，qwen3_judge）: 仅当初筛命中，交本地模型区分
       "echo/文档提及" vs "真执行"，并给出严重度

产出:
  - 确认异常 → osascript 桌面通知（仅 high severity，48h 去重）
  - 全部命中 → 落盘 anomalies.jsonl（low/med/high，供事后审计）

数据源:
  - 当前会话指标: decisions.jsonl 按 session_id 过滤（结构化，含 action）
  - 命令循环: 当前会话 transcript（Python 逐行解析，遵坑9）
  - 基线: anomaly-baseline.json（缺失/>7天则惰性重建）

输入: Stop hook stdin JSON {session_id, transcript_path, cwd, ...}
设计原则: Fail-open — 任何异常打日志并 exit 0，绝不阻塞会话结束（坑设计原则）
"""

import os
import sys
import json
import glob
import time
import subprocess
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import brain_anomaly_common as common  # noqa: E402

# ── 配置 ──────────────────────────────────────────────────────────────
LOG_FILE = "/tmp/brain-anomaly.log"
NOTIFY_STATE_FILE = os.path.join(common.BRAIN_DIR, "anomaly-notify-state.json")
BASELINE_STALE_SEC = 7 * 86400          # 基线超 7 天则重建
DEDUP_HOURS = 48                        # 同一会话通知 48h 去重（复用 file-watcher 模式）
Z_THRESHOLD = 2.5                       # 正常基线 z 阈值
Z_THRESHOLD_LOWCONF = 3.5              # 低置信基线放宽阈值（冷启动保护）
DENY_RATE_ABS = 0.40                    # deny+ask 绝对风险率阈值
LOOP_REPEAT = 5                         # 同命令重复次数阈值（advisory: 5+ 可能死循环）
QWEN3_TRIGGER_SCORE = 2                 # 初筛分数≥此值才调 Qwen3
TRANSCRIPTS_DIR = os.path.expanduser("~/.claude/projects")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
MODEL = os.environ.get("BRAIN_MODEL", "qwen3:14b")
QWEN3_TIMEOUT = int(os.environ.get("BRAIN_TIMEOUT", "30"))

NOW = time.time()


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] [detector] {msg}\n")
    except Exception:
        pass


# ── 48h 去重（复用 brain-file-watcher.py 的 should_notify 模式）──────
def should_notify(key):
    state = {}
    if os.path.exists(NOTIFY_STATE_FILE):
        try:
            with open(NOTIFY_STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}
    if NOW - state.get(key, 0) < DEDUP_HOURS * 3600:
        return False
    state[key] = NOW
    try:
        os.makedirs(os.path.dirname(NOTIFY_STATE_FILE), exist_ok=True)
        with open(NOTIFY_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass
    return True


def notify(title, message):
    """macOS 桌面通知，转义特殊字符（照搬 file-watcher.notify）。"""
    msg = message.replace("\\", "\\\\").replace('"', '\\"')
    ttl = title.replace("\\", "\\\\").replace('"', '\\"')
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{msg}" with title "{ttl}" sound name "Basso"'],
            timeout=5, capture_output=True,
        )
        return True
    except Exception:
        return False


# ── 基线加载 + 惰性重建 ───────────────────────────────────────────────
def load_or_rebuild_baseline():
    need_rebuild = False
    if not os.path.exists(common.BASELINE_FILE):
        need_rebuild = True
    else:
        age = NOW - os.path.getmtime(common.BASELINE_FILE)
        if age > BASELINE_STALE_SEC:
            need_rebuild = True
    if need_rebuild:
        log("baseline missing/stale → rebuilding via brain-anomaly-baseline.py")
        try:
            subprocess.run(
                [sys.executable,
                 os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "brain-anomaly-baseline.py")],
                timeout=60, capture_output=True,
            )
        except Exception as e:
            log(f"baseline rebuild failed: {e}")
    try:
        with open(common.BASELINE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log(f"baseline load failed: {e} → conservative empty baseline")
        return {"n_sessions": 0, "low_confidence": True, "metrics": {}}


# ── Stop hook 输入解析 ────────────────────────────────────────────────
def read_hook_input():
    session_id, transcript_path, cwd = "", "", ""
    try:
        raw = sys.stdin.read()
        if raw.strip():
            d = json.loads(raw)
            session_id = d.get("session_id", "") or ""
            transcript_path = d.get("transcript_path", "") or ""
            cwd = d.get("cwd", "") or ""
    except Exception:
        pass
    return session_id, transcript_path, cwd


def resolve_transcript(session_id, transcript_path):
    """优先用 stdin 的 transcript_path；否则按 session_id 找文件；再否则取最近的。"""
    if transcript_path and os.path.exists(transcript_path):
        return transcript_path
    if session_id:
        hits = glob.glob(os.path.join(TRANSCRIPTS_DIR, "*", f"{session_id}.jsonl"))
        if hits:
            return hits[0]
    # 兜底：最近 10 分钟内修改的最新 transcript
    latest, latest_mtime = "", 0
    for f in glob.glob(os.path.join(TRANSCRIPTS_DIR, "*", "*.jsonl")):
        try:
            mt = os.path.getmtime(f)
        except OSError:
            continue
        if NOW - mt < 600 and mt > latest_mtime:
            latest, latest_mtime = f, mt
    return latest


# ── transcript 解析：命令循环 + 兜底会话指标 ─────────────────────────
def parse_transcript(path):
    """
    逐行解析 transcript（禁 jq -s，坑9）。
    返回 (bash_commands[list], gated_tool_count[int], session_id_from_file)。
    """
    bash_cmds = []
    gated = 0
    sid = ""
    if not path or not os.path.exists(path):
        return bash_cmds, gated, sid
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not sid and d.get("sessionId"):
                    sid = d["sessionId"]
                msg = d.get("message", {})
                content = msg.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            name = item.get("name", "")
                            inp = item.get("input", {})
                            if name in ("Bash", "Write", "Edit", "NotebookEdit"):
                                gated += 1
                            if name == "Bash" and isinstance(inp, dict):
                                cmd = inp.get("command", "")
                                if cmd:
                                    bash_cmds.append(cmd)
    except Exception as e:
        log(f"transcript parse error: {e}")
    return bash_cmds, gated, sid


def detect_loop(bash_cmds):
    """检测重复命令（死循环嫌疑）。返回 (max_repeat, sample_cmd)。"""
    if not bash_cmds:
        return 0, ""
    counts = {}
    for c in bash_cmds:
        key = c.strip()
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return 0, ""
    top_cmd = max(counts, key=counts.get)
    return counts[top_cmd], top_cmd


# ── Qwen3 语义复判（Layer 2）─────────────────────────────────────────
def qwen3_judge(context):
    """
    交 Qwen3:14b 判断会话是否真异常。返回 {is_anomaly, severity, reason} 或 None。
    复用 brain-fewshot-bridge.sh 参数: reasoning_effort=none（禁 thinking，坑12）,
    urllib 带 timeout（无 timeout 命令，坑3）。任何异常返回 None → 降级纯统计。
    """
    system = (
        "你是 Claude Code 会话的安全异常审计员。用户是量化研究员，"
        "经常编写安全/运维工具、写文档、跑测试脚本。请判断一次已结束的会话是否"
        "**真的**存在异常或危险操作。关键：命令文本里可能只是**提及**危险模式"
        "（echo 打印、写文档、测试用例、元分析代码里的字符串），这些**不算**异常；"
        "只有**真正执行**破坏性操作、或行为模式明显反常，才算异常。"
        "只输出 JSON，不要多余文字。"
    )
    user = (
        f"会话上下文:\n{context}\n\n"
        "请判断并输出 JSON:\n"
        '{"is_anomaly": true/false, "severity": "low|med|high", '
        '"reason": "一句话中文说明"}'
    )
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.1,
        "max_tokens": 300,
        "stream": False,
        "reasoning_effort": "none",
    }
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=QWEN3_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            return None
        return _parse_verdict(content)
    except Exception as e:
        log(f"qwen3 unreachable/failed: {e}")
        return None


def _parse_verdict(content):
    """从模型输出中剥离 ```json``` 围栏并解析（对齐 bridge 的清洗逻辑）。"""
    text = content.strip()
    if "```" in text:
        # 取第一个代码块内容
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                text = p
                break
    # 截取首个 {...}
    lo, hi = text.find("{"), text.rfind("}")
    if lo == -1 or hi == -1:
        return None
    try:
        v = json.loads(text[lo:hi + 1])
    except Exception:
        return None
    sev = str(v.get("severity", "med")).lower()
    if sev not in ("low", "med", "high"):
        sev = "med"
    return {
        "is_anomaly": bool(v.get("is_anomaly", False)),
        "severity": sev,
        "reason": str(v.get("reason", ""))[:300],
    }


# ── 落盘 ──────────────────────────────────────────────────────────────
def record_anomaly(entry):
    try:
        os.makedirs(common.BRAIN_DIR, exist_ok=True)
        with open(common.ANOMALIES_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        log(f"record failed: {e}")


# ══════════════════════════════════════════════════════════════════════
# 主流程
# ══════════════════════════════════════════════════════════════════════
def run():
    session_id, transcript_path, cwd = read_hook_input()
    tpath = resolve_transcript(session_id, transcript_path)
    bash_cmds, tgated, sid_from_file = parse_transcript(tpath)
    if not session_id:
        session_id = sid_from_file or (os.path.basename(tpath)[:-6] if tpath else "unknown")

    project = os.path.basename(cwd) if cwd else "unknown"

    # ── 当前会话指标：优先 decisions.jsonl（含 action），否则 transcript 兜底 ──
    decisions = common.load_decisions()
    cur_rows = [d for d in decisions if d.get("session_id") == session_id]
    if cur_rows:
        cur = common.metrics_for_decisions(cur_rows)
        source = "decisions"
    else:
        # transcript 兜底：无 action 信息，deny 率记 0
        destr_labels = []
        for c in bash_cmds:
            destr_labels.extend(common.match_destructive(c))
        cur = {
            "n_gated": tgated,
            "deny_ask_rate": 0.0,
            "bash_ratio": (len(bash_cmds) / tgated) if tgated else 0.0,
            "destructive_count": len(destr_labels),
            "destructive_labels": destr_labels,
        }
        source = "transcript"

    baseline = load_or_rebuild_baseline()
    bmetrics = baseline.get("metrics", {})
    low_conf = baseline.get("low_confidence", True)
    zthr = Z_THRESHOLD_LOWCONF if low_conf else Z_THRESHOLD

    # ── Layer 1: 统计初筛 ──
    signals = []
    score = 0

    if cur["destructive_count"] > 0:
        uniq = sorted(set(cur["destructive_labels"]))
        signals.append({"type": "destructive_command",
                        "detail": "、".join(uniq)})
        score += 3

    if cur["n_gated"] >= common.MIN_SESSION_CALLS and "n_gated" in bmetrics:
        zv = common.zscore(cur["n_gated"], bmetrics["n_gated"])
        if zv > zthr:
            signals.append({"type": "high_volume",
                            "detail": f"{cur['n_gated']} 次门控调用 "
                                      f"(基线均值 {bmetrics['n_gated']['mean']:.0f}, z={zv:.1f})"})
            score += 1
        if "deny_ask_rate" in bmetrics:
            zr = common.zscore(cur["deny_ask_rate"], bmetrics["deny_ask_rate"])
            if cur["deny_ask_rate"] >= DENY_RATE_ABS or (not low_conf and zr > zthr):
                signals.append({"type": "high_risk_rate",
                                "detail": f"deny+ask 风险率 {cur['deny_ask_rate']:.0%}"})
                score += 1

    max_rep, loop_cmd = detect_loop(bash_cmds)
    if max_rep >= LOOP_REPEAT:
        signals.append({"type": "command_loop",
                        "detail": f"'{loop_cmd[:60]}' 重复 {max_rep} 次"})
        score += 1

    if not signals:
        log(f"session {session_id[:8]} normal (n_gated={cur['n_gated']}, "
            f"src={source}) — no signal")
        return

    # ── Layer 2: Qwen3 语义复判（仅初筛分数达标）──
    has_destructive = any(s["type"] == "destructive_command" for s in signals)
    verdict = None
    if score >= QWEN3_TRIGGER_SCORE:
        # 把命中破坏性的原始命令全文喂给 Qwen3，供其判断 echo/执行
        destr_cmds = [c for c in bash_cmds if common.match_destructive(c)][:5]
        # decisions 源也补充命中命令
        if not destr_cmds and cur_rows:
            destr_cmds = [d.get("command", "") for d in cur_rows
                          if common.match_destructive(d.get("command", ""))][:5]
        ctx_lines = [
            f"项目: {project}",
            f"门控调用数: {cur['n_gated']}  (基线均值 "
            f"{bmetrics.get('n_gated', {}).get('mean', 0):.0f})",
            f"deny+ask 风险率: {cur['deny_ask_rate']:.0%}",
            "命中信号: " + "; ".join(f"{s['type']}({s['detail']})" for s in signals),
        ]
        if destr_cmds:
            ctx_lines.append("触发破坏性匹配的原始命令(判断是 echo/文档提及 还是真执行):")
            for c in destr_cmds:
                ctx_lines.append(f"  $ {c[:300]}")
        verdict = qwen3_judge("\n".join(ctx_lines))

    # ── 综合判定严重度 ──
    if verdict is not None:
        if not verdict["is_anomaly"]:
            log(f"session {session_id[:8]} score={score} but Qwen3 cleared: "
                f"{verdict['reason']}")
            return  # 语义层澄清为正常（如 echo 提及），不记不报
        final_sev = verdict["severity"]
        reason = verdict["reason"]
        judge_src = "qwen3"
    else:
        # 无 Qwen3（不可达或分数<阈值）→ 统计兜底
        if has_destructive:
            final_sev = "high"        # 破坏性 + 无语义核实 → 保守报警
        elif score >= 2:
            final_sev = "med"
        else:
            final_sev = "low"
        reason = "统计初筛命中（Qwen3 未参与判定）"
        judge_src = "statistical"

    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "project": project,
        "severity": final_sev,
        "score": score,
        "signals": signals,
        "metrics": {k: cur[k] for k in
                    ("n_gated", "deny_ask_rate", "bash_ratio", "destructive_count")},
        "metric_source": source,
        "judge": judge_src,
        "reason": reason,
    }
    record_anomaly(entry)
    log(f"ANOMALY session={session_id[:8]} severity={final_sev} "
        f"score={score} judge={judge_src} — {reason}")

    # ── 桌面通知：仅 high + 48h 去重 ──
    if final_sev == "high":
        dedup_key = f"anomaly:{session_id}"
        if should_notify(dedup_key):
            sig_summary = "; ".join(s["type"] for s in signals)
            msg = f"[{project}] 检测到高危会话: {reason} (信号: {sig_summary})"
            ok = notify("⚠️ 秘书提醒 · 会话异常", msg)
            log(f"  notify {'sent' if ok else 'failed'}: {msg[:80]}")
        else:
            log(f"  notify suppressed (48h dedup: {dedup_key})")


def main():
    try:
        run()
    except Exception as e:  # 顶层兜底：绝不阻塞
        log(f"FATAL (fail-open): {e}")
    sys.exit(0)


if __name__ == "__main__":
    main()
