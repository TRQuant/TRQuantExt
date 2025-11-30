#!/bin/bash
# -*- coding: utf-8 -*-
# 韬睿量化启动脚本

# 获取脚本所在目录（绝对路径）
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# 日志文件
LOG_FILE="$SCRIPT_DIR/logs/trquant_startup.log"
mkdir -p "$SCRIPT_DIR/logs"

# 记录启动信息
echo "$(date '+%Y-%m-%d %H:%M:%S') - 启动脚本执行" >> "$LOG_FILE"
echo "工作目录: $SCRIPT_DIR" >> "$LOG_FILE"

# 检查虚拟环境
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    error_msg="错误: 未找到虚拟环境 'venv'"
    echo "$error_msg" >> "$LOG_FILE"
    notify-send "韬睿量化启动失败" "$error_msg" 2>/dev/null || echo "$error_msg"
    exit 1
fi

# 检查Python主程序
if [ ! -f "$SCRIPT_DIR/TRQuant.py" ]; then
    error_msg="错误: 未找到主程序 'TRQuant.py'"
    echo "$error_msg" >> "$LOG_FILE"
    notify-send "韬睿量化启动失败" "$error_msg" 2>/dev/null || echo "$error_msg"
    exit 1
fi

# 检查是否已经在运行
if pgrep -f "python.*TRQuant.py" > /dev/null; then
    echo "韬睿量化已经在运行中。" >> "$LOG_FILE"
    notify-send "韬睿量化" "应用已在运行中" 2>/dev/null || echo "韬睿量化已经在运行中。"
    exit 0
fi

# 激活虚拟环境并启动
echo "启动韬睿量化..." >> "$LOG_FILE"
cd "$SCRIPT_DIR"

# 使用绝对路径启动，避免环境变量问题
"$SCRIPT_DIR/venv/bin/python" "$SCRIPT_DIR/TRQuant.py" --fast >> "$LOG_FILE" 2>&1 &

# 等待一下确认启动
sleep 1

# 检查是否启动成功
if pgrep -f "python.*TRQuant.py" > /dev/null; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - 启动成功" >> "$LOG_FILE"
    notify-send "韬睿量化" "启动成功" 2>/dev/null || echo "✅ 韬睿量化已启动"
else
    error_msg="启动失败，请查看日志: $LOG_FILE"
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $error_msg" >> "$LOG_FILE"
    notify-send "韬睿量化启动失败" "$error_msg" 2>/dev/null || echo "❌ $error_msg"
    exit 1
fi
