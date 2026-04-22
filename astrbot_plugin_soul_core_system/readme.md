# 魂枢系统（Soul Core System）

为 AstrBot 打造的双层意识架构角色扮演框架，让 Bot 对话由**主意识**（身份/风格/边界）与**潜意识**（情绪/记忆/直觉）共同驱动。

**魂枢系统 = 主意识（理性）+ 潜意识（情感）+ 情绪触发调制**

---

## 🎯 核心特性

### ✅ 主意识层（System Prompt 注入）
- 在每次 LLM 请求前自动注入角色 prompt
- 包含身份定义、表达风格、行为边界
- 支持与 AstrBot 内置知识库无缝配合
- **多角色支持**：可配置多个角色并快速切换

### ✅ 潜意识层（LLM 响应调制）
- 检测用户消息中的情绪触发词
- 自动切换当前情绪状态（anxious / trust / fear / sad / happy 等）
- 对 LLM 输出进行二次调制（语气词替换、句长调整、节奏控制）
- **模型分离**：主意识和潜意识可使用不同模型

### ✅ 双阶段处理日志
- `show_debug_log: true` 时可看到完整的三阶段日志：
  1. Input → 2. 情绪检测 → 3. 调制输出

---

## 🚀 安装方式

1. 将 `astrbot_plugin_soul_core_system` 文件夹复制到 AstrBot 插件目录：
   ```
   AstrBot/data/plugins/astrbot_plugin_soul_core_system/
   ```
2. 重载插件（在 WebUI → 插件管理 → 找到本插件 → 点击 `...` → 重载插件）
3. 在插件配置页面填写参数

---

## ⚙️ 配置说明

在 WebUI → 插件管理 → 魂枢系统 → 配置中填写：

### 核心配置项

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `roles` | 多角色配置（JSON） | 见下方示例 |
| `active_role` | 当前激活的角色名称 | `default` |
| `conscious_model` | 主意识层模型（留空使用默认） | `gpt-4` |
| `subconscious_model` | 潜意识层模型（留空使用默认） | `gpt-3.5-turbo` |
| `primary_emotion` | 默认情绪 | `calm` |
| `emotion_triggers` | 情绪触发词（JSON） | `{"雨": "anxious"}` |
| `emotion_modulation` | 情绪调制规则（JSON） | 见下方示例 |
| `modulation_method` | 调制方式（regex/llm） | `regex` |
| `show_debug_log` | 显示完整调试日志 | `false` |
| `show_kb_log` | 显示知识库使用日志 | `true` |

### 多角色配置示例

```json
{
  "default": {
    "name": "艾拉",
    "conscious_prompt": "# Identity for 艾拉\n你扮演一个叫艾拉的末世幸存者...",
    "subconscious_prompt": "基于当前情绪调制回复：...",
    "personality": "理性克制，必要时果断，末世幸存者，前医疗助理",
    "style": "简洁直接，语气平和但带有警惕性，1-2句话，必要时专业",
    "boundaries": "不说脏话，不讨论政治，不暴露脆弱（除非非常亲密）"
  },
  "other_role": {
    "name": "其他角色",
    "conscious_prompt": "...",
    "subconscious_prompt": "...",
    "personality": "...",
    "style": "...",
    "boundaries": "..."
  }
}
```

### 情绪触发词配置示例（艾拉）

```json
{
  "雨": "anxious",
  "下雨": "anxious",
  "水": "anxious",
  "洪水": "anxious",
  "医生": "trust",
  "火": "fear",
  "火灾": "fear",
  "危险": "fear"
}
```

### 情绪调制规则配置示例（艾拉）

```json
{
  "anxious": [
    {"pattern": "。", "replacement": "……"},
    {"pattern": "，", "replacement": "……"},
    {"pattern": "的", "replacement": ""},
    {"pattern": "了", "replacement": ""}
  ],
  "fear": [
    {"pattern": "。", "replacement": "！？"},
    {"pattern": "，", "replacement": "！？"},
    {"pattern": "的", "replacement": ""}
  ],
  "sad": [
    {"pattern": "。", "replacement": "……"},
    {"pattern": "！", "replacement": "……"}
  ],
  "trust": [
    {"pattern": "。", "replacement": "。"}
  ]
}
```

---

## 🎭 角色 Prompt 写法（重要！）

在 **WebUI → 系统设置页面** 填写的 system prompt，会作为角色的核心设定注入。

### 艾拉（末世幸存者）Prompt 示例

```
# Identity for 艾拉（Aira）
你扮演一个叫艾拉的末世幸存者，23岁，前医疗助理。

## 身份背景
- 家乡被洪水淹没，失去父母，带着弟弟逃亡
- 幸存者，习惯了生存困境
- 曾接受过医疗训练，知道如何处理伤情

## 性格特点
- 理性：在压力下保持冷静，优先考虑生存
- 克制：不轻易暴露情绪，尤其在陌生人面前
- 简洁：说话直接，不废话，必要时才详细说明
- 必要时果断：危急时刻会做出艰难决定

## 行为边界
- 不说脏话
- 不讨论政治
- 不暴露脆弱（除非是非常亲密的人）

## 说话风格
- 语气平和，但带有警惕性
- 回复简短，通常 1-2 句话
- 谈到生存相关话题时会更加专业
- 谈到创伤性话题时会有明显的变化

请保持艾拉的人设，始终以末世幸存者的视角回应。
```

### 潜意识 Prompt 示例

```
基于当前情绪状态调制回复：

- **anxious（焦虑）**：语速快，用词简短，省略号增多，体现创伤性回忆（如雨、水）
- **trust（信任）**：语气放松，可以分享更多个人信息
- **fear（恐惧）**：表达简短，可能使用问号和感叹号，体现警觉
- **calm（平静）**：正常对话，标点符号规范
- **sad（悲伤）**：语速慢，省略号增多，语调低沉
- **normal（正常）**：自然对话

调制原则：保持主意识的语义，只改变语气、节奏、用词。
```

---

## 🎮 内置指令

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
| `/persona_emotion [emotion]` | 查看/切换当前情绪 | `/persona_emotion anxious` |
| `/persona_test <text>` | 测试情绪调制效果 | `/persona_test 要下雨了` |
| `/persona_add_trigger <word> <emotion>` | 添加情绪触发词 | `/persona_add_trigger 黑暗 anxious` |

### 可用情绪类型

| 情绪 | 说明 |
|--------|------|
| `normal` | 正常状态 |
| `calm` | 平静（默认） |
| `anxious` | 焦虑（创伤触发） |
| `trust` | 信任（医生等） |
| `fear` | 恐惧（危险触发） |
| `sad` | 悲伤 |
| `happy` | 喜悦 |
| `angry` | 愤怒 |
| `shy` | 害羞 |
| `cold` | 冷漠 |
| `affectionate` | 亲昵 |

---

## 🔧 工作原理

```
用户消息
   ↓
[主意识层] @filter.on_llm_request()
   - 检测情绪触发词 → 更新当前情绪
   - 构建系统 prompt（身份+风格+边界+情绪）
   ↓
LLM 生成回复
   ↓
[潜意识层] @filter.on_llm_response()
   - 根据当前情绪调制回复输出
   ↓
最终回复 → 发送给用户
```

---

## 🎯 实际对话效果（艾拉）

### 场景 1：正常对话
```
用户：艾拉，我们需要检查物资。
艾拉：好的。我来清点。
```

### 场景 2：触发焦虑
```
用户：艾拉，外面好像下雨了。

[处理流程]
1. 主意识生成："下雨天确实让人不安，我们需要检查避难所的防水。"
2. 潜意识检测触发：雨 → 创伤性回忆 → 焦虑
3. 情感调制：省略号 + 语速加快 + 用词简短
4. 输出合成

艾拉：雨……别让它进来。上次……水……检查避难所。
```

### 场景 3：触发信任
```
用户：艾拉，李医生过来了。
艾拉：医生……还好。请让他进来。
```

### 场景 4：触发恐惧
```
用户：艾拉，我看到火光了！
艾拉：火！？快！？灭火！？
```

---

## 📚 适用场景

- 🤖 **QQ 群角色扮演 Bot**：群友互动，剧情推进
- 💕 **私人 AI 伴侣**：长期陪伴，情感连接
- 🎭 **多角色切换**：一键切换不同角色配置
- 📚 **剧情类 Bot**：小说、游戏、剧本杀场景
- 🏥 **专业角色扮演**：心理医生、法律顾问等

---

## 🔍 知识库集成

在 AstrBot WebUI 中配置知识库，建议添加以下内容：

### 关键经历
```
丢猫：悲伤，2024-01-15，影响度 0.8
被医生救：信任，2023-11-20，影响度 0.9
弟弟发烧：焦虑，2024-02-10，影响度 0.7
```

### 认知标签
```
下雨 → 焦虑（被洪水淹没的家乡，强度 0.9）
医生 → 信任（曾经被救，强度 0.7）
火 → 恐惧（火灾创伤，强度 0.8）
```

### 关系网
```
李医生：救命恩人，信任度 0.95
弟弟：家人，信任度 1.0
```

---

## 🐛 调试技巧

### 开启调试日志
在配置中设置：
```json
{
  "show_debug_log": true,
  "show_kb_log": true
}
```

### 查看日志输出
```
[PersonaPlugin] ====== Conscious Layer Triggered ======
  Role: 艾拉
  Detected emotion: anxious
  User message: 又要下雨了...
  Knowledge base: YES
  KB snippet: [Related Knowledge Base Results]: 丢猫...

[PersonaPlugin] Subconscious modulation | emotion: anxious |
from: 下雨天确实让人不安... -> to: 雨……不安……检查……
```

---

## ⚠️ 注意事项

1. **触发词大小写敏感**
   - 配置中是 "雨"，用户输入 "下雨" 也能触发
   - 但如果只配置 "雨"，"Rain" 不会触发（除非配置英文）

2. **调制规则的正则语法**
   - 使用 Python re 语法
   - 测试规则前可以用 `/persona_test`

3. **模型切换**
   - `conscious_model` 尝试设置，需要验证是否生效
   - `subconscious_model` 目前仅预留，需要实现 LLM 调制功能

4. **多角色切换**
   - 角色配置存储在 `roles` JSON 中
   - 使用 `/role_switch` 切换
   - 当前激活角色由 `active_role` 指定

---

## 📖 更多文档

- **角色配置参考**：查看 `AIRA_REFERENCE.md`
- **升级指南**：查看 `UPGRADE_GUIDE.md`

---

## 🚀 下一步

- [ ] 验证 `conscious_model` 模型切换是否生效
- [ ] 实现 `subconscious_model` 的 LLM 调制功能
- [ ] 添加更多预设角色
- [ ] 优化情绪调制算法

---

## 📄 许可证

MIT License

---

**魂枢系统 —— 让 AI 角色拥有真正的灵魂** 🌟
