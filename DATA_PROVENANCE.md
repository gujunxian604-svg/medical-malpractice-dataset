# 数据来源与合规说明 (Data Provenance & Compliance)

> 本文件说明仓库内数据集的**来源、去标识化方法、上传范围与合规依据**，供论文评审、机构审查（IRB）与数据使用者参考。
> 注：以下为基于数据特征与通用规范的合规分析，非正式法律意见；正式发表前建议由所在机构 IRB / 法务做最终确认。

---

## 1. 数据来源

| 数据集 | 数量 | 来源 | 法律属性 |
|--------|------|------|----------|
| 美国医疗过失案例 | 490 例 | CourtListener REST API v4（基于美国各州/联邦法院**公开司法意见** public court opinions） | 美国联邦司法记录原则上属**公共领域**（sealed 案件除外） |
| 中国医疗损害责任案例 | 612 例 | 中国公开裁判文书（如中国裁判文书网） | 依法公开的司法文书；发布时当事人姓名已作匿名化处理（"张某"式） |

---

## 2. 去标识化方法（可复现，见 `src/deidentify.py`）

- **美国案例**：删除 `full_text` 完整判决书原文（含真实当事人姓名、医生姓名、案号、医院名称），**仅保留 `source_url`** 指向公开 CourtListener 记录。结构化字段（`clinical_facts` / `malpractice_details` / `organ_system_mapping`）本就脱敏，原样保留。
- **中国案例**：掩码电话号码与身份证号；将未匿名化的当事人称谓（原告/被告/…后紧跟且不含"某"字者）统一替换为"某某"。

---

## 3. 仓库上传范围

| 文件 | 上传 | 说明 |
|------|------|------|
| `data/case_database.json` | ✅ | 25 例 OLD CARTS 结构化精选（含 `final_diagnosis` 金标准，实验用 gold 集） |
| `data/selected_cases.json` | ✅ | 21 例代表性脱敏精选（不同 schema，无 OLD CARTS 结构） |
| `data/cn_medical_cases_deidentified.json` | ✅ | 612 例，已去标识化 |
| `data/us_cases_deidentified.json` | ✅ | 490 例，`full_text` 已删、仅留 `source_url` |
| `data/cn_medical_cases.json`（原始） | ❌ | 被 `.gitignore` 排除 |
| `data/us_cases.json`（原始，含 `full_text`） | ❌ | 被 `.gitignore` 排除 |
| `config.py`（含 API keys） | ❌ | 被 `.gitignore` 排除 |

---

## 4. 合规要点

### 美国数据
- 来源为**公开司法记录**，属公共领域；本仓库**不二次分发**含个人姓名 / 受保护健康信息（PHI）的完整原文，仅提供公开来源的引用链接（`source_url`），符合**数据最小化**原则。
- 结构化元数据可溯源、可复现（任何研究者可凭 `source_url` 合法访问原始公开记录）。

### 中国数据
- 来源为**依法公开的裁判文书**；本仓库进一步做去标识化（掩码直接标识符 + 当事人称谓匿名化），符合《中华人民共和国个人信息保护法》关于**去标识化 / 匿名化**处理的要求。
- 经去标识化后的信息不再属于可直接识别的个人信息，处理与共享风险极低。

---

## 5. 使用限制与许可建议

- 数据**仅供学术研究、非商业用途**。
- 建议配套 `LICENSE`（如 `CC-BY-4.0` 或 `CC0`）。
- 若研究涉及人类受试者（human subjects），公开司法 / 文书记录通常属 **IRB 豁免（exempt）** 范畴；如机构要求，可说明数据已去标识化且源于公开记录。

---

## 6. 复现命令

```bash
pip install -r requirements.txt
python src/deidentify.py   # 由原始文件生成 *_deidentified.json
```
