#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据去标识化脚本 (de-identification)
====================================
生成可公开上传的匿名化版本，供论文数据仓库使用：

  1) 美国案例 (us_cases.json)
     - 删除 full_text 字段（含大量真实当事人姓名 / 医生 / 案号 / 医院，属可识别原文）
     - 仅保留 source_url（指向公开 CourtListener 记录，保证溯源与可复现）
     - 结构化字段 (clinical_facts / malpractice_details / organ_system_mapping / case_metadata) 本就脱敏，原样保留

  2) 中国案例 (cn_medical_cases.json)
     - 高置信 PII 掩码：手机号 / 座机 / 身份证
     - 未匿名化的当事人称谓（原告/被告/...后紧跟且不含"某"字的人名/机构名）
       统一替换为「某某」，满足去标识化要求

输入为原始大文件（被 .gitignore 排除，不上传）；
输出为 *_deidentified.json（新文件名，不在排除列表，可纳入仓库上传）。

运行: python src/deidentify.py
"""
import json
import re

# ---------- 通用掩码 ----------
PHONE = re.compile(
    r'(?<!\d)(?:1[3-9]\d{9}|0\d{2,3}-?\d{7,8}|400-?\d{3}-?\d{4}|800-?\d{3}-?\d{4})(?!\d)'
)
IDCD = re.compile(r'\b\d{17}[\dXx]\b')

# ---------- 中国当事人称谓去实名 ----------
ROLE = re.compile(
    r'(原告|被告|上诉人|被上诉人|申请人|被申请人|第三人)\s*[:：]?\s*([^，。；：:（()\s]{1,6})'
)
# 叙述性 / 机构性词汇黑名单：命中则视为非"具体人名"，不替换
BLACK = set(
    '向本院 起诉 主张 认为 不服 诉称 辩称 提供 申请 答辩 代理人 委托 出庭 缺席 '
    '查明 审理 判决 赔偿 质证 举证 证实 承认 同意 撤回 调解 上诉 证据 医院 公司 '
    '保险 中心 学校 政府 协会 合伙 企业 门诊 诊所 卫生 药店 药房 医生 护士 患者 '
    '科室 主任 院长 原告 被告'.split()
)


def mask_text(s: str) -> str:
    s = PHONE.sub('[PHONE]', s)
    s = IDCD.sub('[ID]', s)
    return s


def _role_repl(m, stats: dict) -> str:
    role = m.group(1)
    ent = m.group(2).strip()
    if not ent:
        return m.group(0)
    if '某' in ent:          # 已匿名化，保留
        return m.group(0)
    if ent in BLACK:         # 叙述/机构词，保留
        return m.group(0)
    if re.search(r'[A-Za-z0-9]', ent):  # 含字母数字，不处理
        return m.group(0)
    stats['role_replaced'] += 1
    return role + '某某'


def deid_cn_value(v, stats: dict):
    if isinstance(v, str):
        s = mask_text(v)
        s = ROLE.sub(lambda m: _role_repl(m, stats), s)
        return s
    if isinstance(v, dict):
        return {k: deid_cn_value(val, stats) for k, val in v.items()}
    if isinstance(v, list):
        return [deid_cn_value(x, stats) for x in v]
    return v


def deidentify_cn(src: str, dst: str):
    with open(src, encoding='utf-8') as f:
        data = json.load(f)
    stats = {'role_replaced': 0}
    out = deid_cn_value(data, stats)
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[CN] {src} -> {dst}")
    print(f"     records={len(data)}  role_entities_anonymized={stats['role_replaced']}")


def deidentify_us(src: str, dst: str):
    with open(src, encoding='utf-8') as f:
        data = json.load(f)
    out = []
    kept_url = 0
    for rec in data:
        r = {k: v for k, v in rec.items() if k != 'full_text'}
        if r.get('source_url'):
            kept_url += 1
        out.append(r)
    with open(dst, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"[US] {src} -> {dst}")
    print(f"     records={len(data)}  full_text_dropped={len(data)}  source_url_kept={kept_url}")


if __name__ == '__main__':
    base = 'data'
    deidentify_cn(f'{base}/cn_medical_cases.json',
                  f'{base}/cn_medical_cases_deidentified.json')
    deidentify_us(f'{base}/us_cases.json',
                  f'{base}/us_cases_deidentified.json')
