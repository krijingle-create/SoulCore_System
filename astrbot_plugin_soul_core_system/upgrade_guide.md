# 双意识角色扮演插件 - 升级指南

## 🎯 新功能

### 1. 多角色支持
- 可配置多个角色，通过指令切换
- 每个角色有独立的 conscious_prompt 和 subconscious_prompt

### 2. 模型分离
- 主意识层可使用指定模型（如 GPT-4）
- 潜意识层可使用不同模型（如 GPT-3.5-turbo）
- 支持留空使用默认模型

### 3. 情绪调制方式选择
- **regex**：正则表达式替换（快速，规则明确）
- **llm**：使用 LLM 智能调制（需实现）

---

## 📦 安装步骤

### 步骤 1：备份原有配置
```bash
# 备份原有配置
cp config_schema.json config_schema_backup.json
```

### 步骤 2：替换文件
```bash
# 替换主文件
cp main_refactored.py main.py

# 替换配置 schema
cp config_schema_refactored.json config_schema.json
```

### 步骤 3：重载插件
在 AstrBot WebUI → 插件管理 → 双意识角色插件 → `...` → 重载插件

---

## ⚙️ 配置说明

### 配置角色（roles）

```json
{
  "aira": {
    "name": "艾拉",
    "conscious_prompt": "# Identity for 艾拉\n末世幸存者，23岁...",
    "subconscious_prompt": "基于情绪状态调制：\n- anxious: 语速快...",
    "personality": "理性克制，必要时果断",
    "style": "简洁直接",
    "boundaries": "不说脏话，不暴露脆弱"
  }
}
```

### 配置模型

- **conscious_model**: 主意识层模型（如 `gpt-4`）
- **subconscious_model**: 潜意识层模型（如 `gpt-3.5-turbo`）

**注意**：
- 留空则使用 AstrBot 默认模型
- 目前仅实现了 conscious_model 的支持（需要验证 ProviderRequest）
- subconscious_model 需要实现 LLM 调制功能后生效

### 配置情绪系统

```json
{
  "primary_emotion": "normal",
  "emotion_triggers": {
    "": "affectionate",
    "": "sad",
    "": "angry"
  },
  "emotion_modulation": {
    "happy": [
      {"pattern": "。", "replacement": "！"}
    ],
    "sad": [
      {"pattern": "。", "replacement": "……"}
    ]
  },
  "modulation_method": "regex"
}
```

---

## 🎮 使用指令

### 角色管理

| 指令 | 说明 | 示例 |
|------|------|------|
| `/role` | 查看所有角色 | `/role` |
| `/role_switch <name>` | 切换角色 | `/role_switch aira` |
| `/role_add <name>` | 添加新角色 | `/role_add test` |
| `/persona` | 查看当前角色信息 | `/persona` |

### 情绪管理

| 指令 | 说明 | 示例 |
|------|------|------|
| `/persona_emotion [emotion]` | 查看/切换情绪 | `/persona_emotion happy` |
| `/persona_test <text>` | 测试调制效果 | `/persona_test 你是傻逼吗` |
| `/persona_add_trigger <word> <emotion>` | 添加触发词 | `/persona_add_trigger 游戏 happy` |

---

## 🚀 使用示例

### 配置第一个角色

在 WebUI → 插件配置 → 双意识角色插件 → 配置中：

1. **roles** - 填入角色配置（JSON）
2. **active_role** - 设置为 `default`
3. **conscious_model** - 留空或填写 `gpt-4`
4. **subconscious_model** - 留空（目前无效）
5. **emotion_triggers** - 配置情绪触发词
6. **emotion_modulation** - 配置调制规则

### 切换角色

```
用户：/role
Bot：Available roles: default, aira
     Active: default

用户：/role_switch aira
Bot：Switched to role: aira
     Name: 艾拉
     Personality: 理性克制，必要时果断
```

### 查看角色信息

```
用户：/persona
Bot：
=== Current Role ====
Name: 
Personality: 
Style: 
Boundaries: 

=== Emotion System ====
Default emotion: normal
Current emotion: normal
Triggers: 7
Modulation rules: 4

=== Model Config ====
Conscious model: (default)
Subconscious model: (default)
Modulation method: regex
```

---

## ⚠️ 限制和注意事项

### 当前限制

1. **conscious_model 支持不确定**
   - 代码尝试设置 `req.model`，但需要验证 ProviderRequest 是否支持
   - 如果不支持，模型配置会被忽略

2. **subconscious_model 暂未实现**
   - 需要实现 `_llm_modulation()` 方法
   - 需要访问 AstrBot 的 LLM 提供者 API
   - 目前回退到 regex 调制

3. **LLM 调制功能未完成**
   - 需要实现在插件中主动调用 LLM 的方法
   - 需要研究 AstrBot 的 provider API

### 验证模型切换

要验证 `conscious_model` 是否生效：

1. 配置 conscious_model 为 `gpt-4`
2. 开启调试日志 `show_debug_log: true`
3. 查看日志中是否有 `Model override: gpt-4`

### 如何实现 LLM 调制

如果需要实现 `modulation_method=llm`：

1. 研究 AstrBot 的 provider API
2. 找到如何在插件中主动调用 LLM
3. 实现 `_llm_modulation()` 方法
4. 更新 `modulate()` 方法调用逻辑

---

## 🔧 故障排查

### 问题 1：角色切换失败
**症状**：`/role_switch` 提示 "Role not found"

**解决**：
1. 检查 WebUI 配置中的 `roles` JSON 格式是否正确
2. 确认角色名称拼写正确
3. 重载插件后重试

### 问题 2：模型切换无效
**症状**：设置了 conscious_model 但没有生效

**解决**：
1. 开启 `show_debug_log: true`
2. 查看日志中是否有 `Model override`
3. 如果没有，说明 ProviderRequest 不支持 model 字段

### 问题 3：调制规则不生效
**症状**：情绪切换了，但输出没有变化

**解决**：
1. 检查 `emotion_modulation` JSON 格式
2. 确认正则表达式语法正确
3. 使用 `/persona_test` 测试调制效果

---

## 📝 开发计划

### 阶段 1：验证和修复
- [ ] 验证 ProviderRequest 是否支持 model 字段
- [ ] 修复模型切换功能（如支持）
- [ ] 完善错误处理

### 阶段 2：实现 LLM 调制
- [ ] 研究 AstrBot 的 provider API
- [ ] 实现 `_llm_modulation()` 方法
- [ ] 测试 LLM 调制效果

### 阶段 3：优化和文档
- [ ] 性能优化
- [ ] 完善用户文档
- [ ] 添加更多示例角色

---

## 🤝 贡献

本插件灵感来源于：
- 基于AstrBot的SubAgent的，可解释内心活动：https://jiupamiao.asia/market?id=555
- Goal-Driven 框架：https://github.com/lidangzzz/goal-driven

如果你：
- 实现了 LLM 调制功能
- 修复了模型切换问题
- 发现了其他改进点

欢迎提交 Issue 或 PR！

---

## 📄 许可证

MIT License
