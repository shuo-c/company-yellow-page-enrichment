# yellow-page-translator — Skill Brief (Step 1)

## 要解决的问题
这个技能用于把黄页数据库中的公司简介/描述等文本，从英文批量翻译成中文或其他语言，并经过行业视角审校后输出可回写/可交付的最终文件，替代手工“逐条导出→复制粘贴翻译→人工校对→再拼回文件”的流程。

## 目标用户
- 主要用户：你自己（负责翻译脚本与内容更新的人）
- 次要用户：团队内运营/内容编辑（需要快速获得可发布的多语言内容）
- 潜在用户：工程同事（需要标准化产出文件用于回写 DB 或上线）

## 触发语句（示例）
1. “用 .env.prod 把 records 里这些 company keys 的 intro 和 description 从英文翻译成中文，10条一批，翻译+审校后合并输出。”
2. “只跑翻译阶段：把 batches/batch_0003.jsonl 翻译成 zh-CN，保留公司名、地址、网址不翻。”
3. “翻译都完成了，帮我跑一遍审校（行业口吻）并生成 final 合并文件。”
4. “把同一批 keys 额外生成西语（es）版本，并输出 diff 报告标注哪些字段被跳过/保留。”
5. “从上次中断处继续：跳过 done 的 batch，只处理 pending/error 的 batch。”

## 输入
- 配置来源
  - env_file: .env 路径（默认 .env）
  - records_file: key 记录文件路径（jsonl/csv/json）
- 语言参数
  - source_lang: 默认 en
  - target_lang: zh-CN / zh-TW / es / ja 等
- 字段选择
  - fields: 要翻译的字段列表（如 intro, description, services）
- 批处理
  - batch_size: 默认 10
  - start_batch / end_batch：只处理某个范围（可选）
  - resume: 是否断点续跑（默认 true）
- 专有名词保护
  - no_translate_fields: 明确永不翻译的字段（如 company_name, address）
  - glossary_file: 术语表/固定译法（可选）
- 输出格式
  - output_format: jsonl / csv / sql（默认 jsonl）
  - output_dir: 输出目录（默认 ./out）

## 输出
- 原始拉取缓存
  - out/raw/*.json 或 out/raw.jsonl
- 分批产物
  - out/batches/batch_0001.input.jsonl
  - out/batches/batch_0001.translated.jsonl
  - out/batches/batch_0001.reviewed.jsonl
- Todo / 状态跟踪
  - out/todo/batch_0001.json（记录状态、错误、完成时间、条目数）
- 最终合并文件
  - out/final/companies_i18n.<target_lang>.<ext>
- 报告（推荐）
  - out/report/summary.md（统计、跳过项、失败原因、术语命中）

## 边界
- 不直接写回数据库（除非显式授权 + API 文档 + --enable_writeback）
- 不翻译专有名词/特指信息（公司名、地址、人名、电话、邮箱、网址）
- 不做夸张营销创作，不虚构资质/荣誉/数据
- 不做权限绕过，不猜测 API 能力

## 验收标准
- 正确性
  - 每条 key 在输出中可追踪（result 或 skipped/error）
  - 专有名词保护生效
  - 审校结果相对直译有可解释优化
- 可用性
  - 支持断点续跑，不重复处理 done batch
  - 失败可定位，todo 与 summary.md 有明确原因和建议
- 效率
  - 按 batch_size=10 产物稳定输出
- 交付
  - final 文件格式符合约定（jsonl/csv/sql），字段完整可用于回写/上线
