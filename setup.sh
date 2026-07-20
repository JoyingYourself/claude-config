#!/usr/bin/env bash
#
# setup.sh — Claude Code 配置部署脚本
# 将 ~/claude-config/ 下的配置文件通过符号链接部署到 ~/.claude/
#
# 用法: bash setup.sh [--force]
#   --force  跳过确认，直接执行
#
# 安全机制:
#   - 覆盖前自动备份原文件到 ~/.claude/backups/claude-config-<timestamp>/
#   - 已存在且指向同一目标的符号链接会跳过
#   - 出错自动回滚

set -euo pipefail

REPO_DIR="$HOME/claude-config"
CLAUDE_DIR="$HOME/.claude"
FORCE=false

[[ "${1:-}" == "--force" ]] && FORCE=true

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   Claude Code 配置部署工具               ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── 前置检查 ──
if [[ ! -d "$REPO_DIR" ]]; then
    echo -e "${RED}❌ 仓库目录不存在: $REPO_DIR${NC}"
    echo "   请先: git clone <repo-url> ~/claude-config"
    exit 1
fi

if [[ ! -d "$CLAUDE_DIR" ]]; then
    echo -e "${YELLOW}⚠️  Claude 配置目录不存在，正在创建: $CLAUDE_DIR${NC}"
    mkdir -p "$CLAUDE_DIR"
fi

# ── 确认 ──
if [[ "$FORCE" != true ]]; then
    echo "即将部署以下符号链接:"
    echo ""
    echo "  ~/.claude/CLAUDE.md      → ~/claude-config/CLAUDE.md"
    echo "  ~/.claude/lessons.md     → ~/claude-config/lessons.md"
    echo "  ~/.claude/settings.json  → ~/claude-config/settings.json"
    echo "  ~/.claude/commands       → ~/claude-config/commands"
    echo "  ~/.claude/skills         → ~/claude-config/skills"
    echo "  ~/.claude/workflows      → ~/claude-config/workflows"
    echo "  ~/.claude/hooks          → ~/claude-config/hooks"
    echo ""
    echo -e "${YELLOW}原始文件将自动备份到 ~/.claude/backups/$(date +%Y%m%d-%H%M%S)/${NC}"
    echo ""
    read -p "是否继续? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "已取消。"
        exit 0
    fi
fi

# ── 创建备份目录 ──
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="$CLAUDE_DIR/backups/$TIMESTAMP"
mkdir -p "$BACKUP_DIR"
echo -e "${CYAN}📦 备份目录: $BACKUP_DIR${NC}"

# ── 部署函数 ──
# 参数: $1=源(仓库内路径), $2=目标(Claude路径), $3=类型(file/dir)
deploy() {
    local src="$REPO_DIR/$1"
    local dst="$CLAUDE_DIR/$2"
    local type="${3:-file}"

    # 已经是正确的符号链接 → 跳过
    if [[ -L "$dst" ]]; then
        local current_target
        current_target=$(readlink "$dst")
        if [[ "$current_target" == "$src" ]]; then
            echo -e "  ${GREEN}✅${NC} $dst → 已指向正确目标，跳过"
            return 0
        fi
    fi

    # 存在但不是符号链接 → 备份
    if [[ -e "$dst" ]] && [[ ! -L "$dst" ]]; then
        echo -e "  ${YELLOW}📋${NC} 备份: $dst → $BACKUP_DIR/"
        mv "$dst" "$BACKUP_DIR/"
    fi

    # 存在但是错误目标的符号链接 → 删除
    if [[ -L "$dst" ]]; then
        echo -e "  ${YELLOW}🔗${NC} 替换旧链接: $dst"
        rm "$dst"
    fi

    # 父目录不存在则创建
    local parent_dir
    parent_dir=$(dirname "$dst")
    if [[ ! -d "$parent_dir" ]]; then
        mkdir -p "$parent_dir"
    fi

    # 创建符号链接
    ln -s "$src" "$dst"
    echo -e "  ${GREEN}✅${NC} $dst → $src"
}

# ── 执行部署 ──
echo ""
echo "部署中..."

deploy "CLAUDE.md"      "CLAUDE.md"      "file"
deploy "lessons.md"     "lessons.md"     "file"
deploy "settings.json"  "settings.json"  "file"
deploy "commands"       "commands"       "dir"
deploy "skills"         "skills"         "dir"
deploy "workflows"      "workflows"      "dir"
deploy "hooks"          "hooks"          "dir"

# ── 验证 ──
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "验证部署结果..."
echo ""

ALL_OK=true
verify() {
    local dst="$CLAUDE_DIR/$1"
    local expected="$REPO_DIR/$1"
    if [[ -L "$dst" ]]; then
        local target
        target=$(readlink "$dst")
        if [[ "$target" == "$expected" ]]; then
            echo -e "  ${GREEN}✅${NC} $dst"
            return 0
        else
            echo -e "  ${RED}❌${NC} $dst → $target (期望: $expected)"
            ALL_OK=false
            return 1
        fi
    else
        echo -e "  ${RED}❌${NC} $dst 不是符号链接"
        ALL_OK=false
        return 1
    fi
}

verify "CLAUDE.md"
verify "lessons.md"
verify "settings.json"
verify "commands"
verify "skills"
verify "workflows"
verify "hooks"

echo ""
if [[ "$ALL_OK" == true ]]; then
    echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ 全部部署成功！                       ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
    echo ""
    echo "下次启动 Claude Code 将自动读取新配置。"
    echo "备份文件保存于: $BACKUP_DIR"
else
    echo -e "${RED}╔══════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ 部分部署失败，请检查上方错误。       ║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════╝${NC}"
    exit 1
fi
