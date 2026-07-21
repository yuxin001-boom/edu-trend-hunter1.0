#!/usr/bin/env python3
"""
教育热点捕手 - 数据采集脚本 v3.0 (稳定数据源版)
数据源:
  - 微博: weibo.com/ajax/side/hotSearch (官方AJAX接口)
  - 百度: top.baidu.com/api/board (官方热搜API)
  - 抖音: douyin.com/aweme/v1/web/hot/search/list/ (官方Web接口)
  - 夸克: quark.sm.cn 页面解析 + 头条API交叉引用
  - 360:  so.com 页面解析 + 头条API交叉引用
所有链接均为真实可跳转的平台链接。
"""

import json
import re
import os
import time
import random
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import quote, quote_plus

# ============================================================
# 配置
# ============================================================
EDU_KEYWORDS = [
    # 考试升学
    '考研', '高考', '中考', '公务员', '考公', '国考', '省考', '教师资格',
    '四六级', '雅思', '托福', 'GRE', 'MBA', '考博', '保研', '调剂',
    '分数线', '志愿填报', '录取', '招生', '入学', '毕业', '论文',
    '考试', '考证', '考级', '模考', '真题', '答案', '成绩',
    # K12
    '幼儿园', '小学', '初中', '高中', '幼小衔接', '学区房', '课后服务',
    '兴趣班', '补习', '辅导', '培训班', '家教', '托管', '研学',
    '少儿编程', '奥数', '作文', '英语学习', '中小学', '小升初',
    '暑假', '寒假', '开学', '学期', '期末', '期中',
    # 成人教育
    '自考', '成考', '专升本', '学历', '在职', '继续教育', '职业培训',
    '技能培训', '一建', '二建', '注会', 'CPA', '消防工程师', '法考',
    '会计', '司法考试', '执业医师', '护士资格',
    # 在线教育/电子教育
    '网课', '在线教育', '直播课', '学习机', '词典笔', '点读笔',
    '学习平板', 'AI教育', 'AI学习', '智能学习', '教育科技',
    '学习app', '教育app', '知识付费',
    # 图书
    '教材', '教辅', '课本', '书单', '绘本', '百科全书',
    # 通用教育
    '教育', '学校', '老师', '教师', '学生', '家长', '学霸',
    '课程', '教育部', '双减', '学费', '奖学金', '助学',
    '大学', '高校', '院校', '学院', '读研', '读博', '留学',
    '校园', '宿舍', '学位', '文凭', '学籍',
]

# 教育类电商热销关键词
EDU_PRODUCT_KEYWORDS = [
    '学习机', '词典笔', '翻译笔', '点读笔', '学习平板', '学习电脑',
    '教材', '教辅', '课本', '试卷', '真题', '考研', '公务员',
    '课程', '网课', '培训', '辅导', '补习',
    '早教', '启蒙', '绘本', '百科', '儿童书', '少儿',
    '编程', '机器人', '益智', '积木', '拼图',
    '文具', '书包', '笔记本', '铅笔', '钢笔',
    '电子书', '阅读器', '学生', '校园', '考试',
    '练习本', '作业', '智能笔', '错题',
]

# 敏感词过滤
SENSITIVE_KEYWORDS = [
    '政治', '军事', '台湾', '习近平', '领导人', '外交部', '国防', '军队',
    '统一', '主权', '南海', '钓鱼岛',
]

# 平台展示名称
PLATFORM_DISPLAY_NAMES = {
    'weibo': '微博',
    'baidu': '百度',
    'quark': '夸克',
    'douyin': '抖音',
    'so360': '360',
}

# 平台搜索URL模板（用于构造可跳转链接）
PLATFORM_SEARCH_URLS = {
    'weibo': 'https://s.weibo.com/weibo?q={query}',
    'baidu': 'https://www.baidu.com/s?wd={query}',
    'douyin': 'https://www.douyin.com/search/{query}',
    'quark': 'https://quark.sm.cn/s?q={query}',
    'so360': 'https://www.so.com/s?q={query}',
}

# 用户画像与面板配置
USER_PERSONAS = [
    '资深中产', '小镇中老年', '小镇青年', '精致妈妈', '都市银发', '新锐白领',
]

PANEL_PERSONAS = {
    "k12": ['资深中产', '小镇中老年', '小镇青年', '精致妈妈'],
    "adult_edu": ['小镇青年', '都市银发', '新锐白领'],
    "e_edu": ['资深中产', '小镇中老年', '小镇青年', '精致妈妈'],
    "books": ['精致妈妈', '小镇青年', '新锐白领'],
}

PERSONA_KEYWORD_RULES = [
    (['世界杯', 'NBA', '足球', '篮球', '奥运', '比赛', '冠军', '决赛', '联赛', '体育'],
     ['资深中产', '小镇青年', '新锐白领']),
    (['歌手', '乘风', '明星', '演员', '综艺', '电视剧', '热播', '追剧', '演唱会', '电影', '票房'],
     ['精致妈妈', '小镇青年']),
    (['股市', '基金', '新政', '经济', '金融', '房价', '利率', '央行', 'A股', '美联储', '降息'],
     ['新锐白领', '都市银发', '资深中产']),
    (['孩子', '家长', '暑假', '高考', '中考', '亲子', '育儿', '幼儿', '宝宝', '防溺水', '儿童', '婴幼儿'],
     ['精致妈妈', '小镇中老年']),
    (['AI短剧', '热梗', '洗脑', '火了', '出圈', '全网', '刷屏', '网红', '直播'],
     ['小镇青年']),
    (['防暑', '养老', '退休', '广场舞', '保健', '健康', '中老年', '养生', '中医'],
     ['都市银发', '小镇中老年']),
    (['618', '双十一', '优惠', '打折', '手机', '家电', '测评', '推荐', '好物', '种草'],
     ['资深中产', '小镇青年']),
    (['书单', '畅销', '豆瓣', '小说', '绘本', '文案', '情感', '文化', '阅读', '综艺', '知识'],
     ['精致妈妈', '新锐白领']),
    (['考公', '考证', '面试', '简历', '跳槽', '薪资', '裁员', 'AI替代', '就业', '创业'],
     ['新锐白领', '小镇青年']),
    (['AI', '科技', '芯片', '机器人', '数码', '新能源', '电动车', '智能', '5G', '互联网'],
     ['资深中产', '新锐白领']),
    (['暴雨', '高温', '台风', '地震', '防汛', '预警', '洪水'],
     USER_PERSONAS),
]

PANEL_AFFINITY_KEYWORDS = {
    "k12": ['孩子', '家长', '暑假', '亲子', '育儿', '幼儿', '宝宝', '防溺水', '儿童',
            '学校', '玩具', '游乐', '动画', '暴雨', '高温', '预警', '安全', '防汛',
            '婴幼儿', '中考', '高考', '小学', '中学'],
    "adult_edu": ['职场', '考公', '面试', '薪资', '裁员', '跳槽', '基金', '股市',
                  '金融', '房价', '养老', '退休', '创业', '就业', '经济', '利率',
                  '央行', '美联储', '降息', '新政', 'A股', '社保'],
    "e_edu": ['AI', '科技', '手机', '数码', '测评', '电子', '充电', '机器人', '芯片',
              '互联网', '5G', '智能', '新能源', '电动车', '618', '打折', '优惠',
              '好物', '种草', '家电', '推荐', '双十一'],
    "books": ['书单', '豆瓣', '文案', '情感', '小说', '文化', '艺术', '阅读', '知识',
              '综艺', '电影', '影视', '追剧', '明星', '演唱会', '歌手', '票房',
              '热播', '网红', '直播', '火了', '出圈'],
}


# ============================================================
# 通用工具函数
# ============================================================

def get_random_ua():
    """随机User-Agent"""
    uas = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    ]
    return random.choice(uas)


def fetch_json(url, headers=None, timeout=20):
    """通用JSON抓取"""
    if headers is None:
        headers = {}
    headers.setdefault('User-Agent', get_random_ua())
    headers.setdefault('Accept', 'application/json, text/plain, */*')
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8', errors='ignore'))
    except Exception as e:
        print(f"    [WARN] fetch_json 失败 {url[:80]}: {e}")
        return None


def fetch_html(url, headers=None, timeout=20):
    """通用HTML抓取"""
    if headers is None:
        headers = {}
    headers.setdefault('User-Agent', get_random_ua())
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"    [WARN] fetch_html 失败 {url[:80]}: {e}")
        return None


def build_search_url(platform, query):
    """构造平台搜索URL（确保真实可跳转）"""
    template = PLATFORM_SEARCH_URLS.get(platform, '')
    if not template:
        return ''
    return template.format(query=quote(query, safe=''))


def is_edu_related(title):
    """判断一条内容是否与教育行业相关"""
    for kw in EDU_KEYWORDS:
        if kw in title:
            return True
    return False


def is_edu_product(title):
    """判断是否为教育类商品"""
    for kw in EDU_PRODUCT_KEYWORDS:
        if kw in title:
            return True
    return False


def is_sensitive_title(title):
    """敏感词过滤"""
    for kw in SENSITIVE_KEYWORDS:
        if kw in title:
            return True
    return False


def categorize_edu(title):
    """将教育内容分类到四大赛道"""
    adult_kws = ['考研', '公务员', '考公', '国考', 'MBA', '自考', '成考', '专升本',
                 '学历', '在职', '一建', '二建', '注会', 'CPA', '法考', '消防工程师',
                 '职业培训', '技能培训', '继续教育', '读研', '读博', '考博',
                 '会计', '司法考试', '执业', '护士', '留学']
    for kw in adult_kws:
        if kw in title:
            return '成人教育'
    k12_kws = ['高考', '中考', '小学', '初中', '高中', '幼小衔接', '幼儿园',
               '兴趣班', '少儿编程', '奥数', '研学', '家长', '课后服务',
               '志愿填报', '分数线', '学霸', '补习', '辅导', '托管',
               '小升初', '暑假', '寒假', '开学', '学期', '中小学', '学生']
    for kw in k12_kws:
        if kw in title:
            return 'K12教育'
    elearn_kws = ['学习机', '词典笔', '点读笔', '学习平板', 'AI教育', 'AI学习',
                  '智能学习', '教育科技', '网课', '在线教育', '直播课', '教育app']
    for kw in elearn_kws:
        if kw in title:
            return '电子教育'
    book_kws = ['教材', '教辅', '课本', '书单', '绘本', '百科', '图书']
    for kw in book_kws:
        if kw in title:
            return '图书'
    return 'K12教育'


# ============================================================
# 各平台热搜抓取（真实数据源）
# ============================================================

def fetch_weibo_hot():
    """微博热搜 - 官方AJAX接口"""
    print("    → 调用微博官方接口...")
    data = fetch_json('https://weibo.com/ajax/side/hotSearch', headers={
        'Referer': 'https://weibo.com/',
    })
    if not data or data.get('ok') != 1:
        print("    ✗ 微博接口返回异常")
        return []

    realtime = data.get('data', {}).get('realtime', [])
    items = []
    for item in realtime:
        word = item.get('word', '').strip()
        if not word or len(word) < 2:
            continue
        # 微博提供的真实跳转URL
        url = f"https://s.weibo.com/weibo?q=%23{quote(word)}%23"
        # 有些item有note字段是完整标题
        note = item.get('note', word)
        items.append({
            'title': note if note else word,
            'url': url,
            'heat': item.get('num', 0),
        })
    print(f"    ✓ 获取到 {len(items)} 条微博热搜")
    return items


def fetch_baidu_hot():
    """百度热搜 - 官方Board API"""
    print("    → 调用百度官方接口...")
    data = fetch_json('https://top.baidu.com/api/board?tab=realtime', headers={
        'Referer': 'https://top.baidu.com/board',
    })
    if not data:
        print("    ✗ 百度接口返回异常")
        return []

    cards = data.get('data', {}).get('cards', [])
    items = []
    for card in cards:
        content = card.get('content', [])
        if isinstance(content, dict):
            # nested structure
            content = content.get('content', [])
        if not isinstance(content, list):
            continue
        for entry in content:
            if not isinstance(entry, dict):
                continue
            word = entry.get('word', '').strip()
            if not word:
                continue
            # 百度提供的真实跳转URL
            url = entry.get('url', '') or entry.get('rawUrl', '')
            if not url:
                url = f"https://www.baidu.com/s?wd={quote(word)}"
            heat = entry.get('hotScore', 0)
            try:
                heat = int(heat)
            except (ValueError, TypeError):
                heat = 0
            items.append({
                'title': word,
                'url': url,
                'heat': heat,
            })
    print(f"    ✓ 获取到 {len(items)} 条百度热搜")
    return items


def fetch_douyin_hot():
    """抖音热搜 - 官方Web接口"""
    print("    → 调用抖音官方接口...")
    data = fetch_json('https://www.douyin.com/aweme/v1/web/hot/search/list/', headers={
        'Referer': 'https://www.douyin.com/',
    })
    if not data:
        print("    ✗ 抖音接口返回异常")
        return []

    word_list = data.get('data', {}).get('word_list', [])
    items = []
    for item in word_list:
        word = item.get('word', '').strip()
        if not word or len(word) < 2:
            continue
        # 抖音搜索真实URL
        url = f"https://www.douyin.com/search/{quote(word)}"
        heat = item.get('hot_value', 0)
        try:
            heat = int(heat)
        except (ValueError, TypeError):
            heat = 0
        items.append({
            'title': word,
            'url': url,
            'heat': heat,
        })
    print(f"    ✓ 获取到 {len(items)} 条抖音热搜")
    return items


def fetch_toutiao_hot():
    """今日头条热搜 - 用作360/夸克的数据交叉源"""
    print("    → 调用头条热搜接口（交叉数据源）...")
    data = fetch_json('https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc', headers={
        'Referer': 'https://www.toutiao.com/',
    })
    if not data:
        return []
    items = data.get('data', [])
    result = []
    for item in items:
        title = item.get('Title', '').strip()
        url = item.get('Url', '')
        heat = item.get('HotValue', 0)
        if title and len(title) >= 4:
            result.append({'title': title, 'url': url, 'heat': heat})
    print(f"    ✓ 获取到 {len(result)} 条头条热搜")
    return result


def fetch_quark_hot():
    """夸克热搜 - 多重尝试"""
    print("    → 尝试夸克数据源...")
    items = []

    # 方式1: 尝试夸克搜索热词API
    try:
        html = fetch_html('https://quark.sm.cn/', headers={
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        }, timeout=10)
        if html:
            # 尝试从页面script中提取热搜数据
            # 夸克首页通常在__NEXT_DATA__或内联JSON中嵌入热搜
            json_blocks = re.findall(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
            for block in json_blocks:
                try:
                    jdata = json.loads(block)
                    # 递归查找含有hotwords之类的字段
                    items = _extract_quark_from_json(jdata)
                    if items:
                        break
                except json.JSONDecodeError:
                    pass

            if not items:
                # 尝试提取页面中的关键词列表
                words = re.findall(r'"word"\s*:\s*"([^"]{2,30})"', html)
                seen = set()
                for w in words:
                    if w not in seen and not w.startswith('http'):
                        seen.add(w)
                        items.append({
                            'title': w,
                            'url': f"https://quark.sm.cn/s?q={quote(w)}",
                            'heat': 0,
                        })
    except Exception as e:
        print(f"    [WARN] 夸克页面解析失败: {e}")

    if items:
        print(f"    ✓ 从夸克获取到 {len(items)} 条热搜")
    else:
        print("    ⚠ 夸克原始数据不可用，将使用交叉源")
    return items


def _extract_quark_from_json(obj, depth=0):
    """递归从JSON结构中提取夸克热搜词"""
    if depth > 5:
        return []
    items = []
    if isinstance(obj, dict):
        # 查找含有热搜关键字段
        for key in ['hotWords', 'hotList', 'trendingList', 'hotSearch', 'words']:
            if key in obj and isinstance(obj[key], list):
                for entry in obj[key]:
                    if isinstance(entry, str) and len(entry) >= 2:
                        items.append({
                            'title': entry,
                            'url': f"https://quark.sm.cn/s?q={quote(entry)}",
                            'heat': 0,
                        })
                    elif isinstance(entry, dict):
                        word = entry.get('word', '') or entry.get('title', '') or entry.get('query', '')
                        if word and len(word) >= 2:
                            items.append({
                                'title': word,
                                'url': f"https://quark.sm.cn/s?q={quote(word)}",
                                'heat': entry.get('heat', 0) or entry.get('score', 0),
                            })
        if not items:
            for v in obj.values():
                items = _extract_quark_from_json(v, depth + 1)
                if items:
                    break
    elif isinstance(obj, list):
        for item in obj:
            items = _extract_quark_from_json(item, depth + 1)
            if items:
                break
    return items


def fetch_so360_hot():
    """360热搜 - 多重尝试"""
    print("    → 尝试360数据源...")
    items = []

    # 方式1: 尝试360搜索首页热词
    try:
        html = fetch_html('https://www.so.com/', headers={
            'Referer': 'https://www.so.com/',
        }, timeout=10)
        if html:
            # 360首页通常有热搜推荐词
            words = re.findall(r'"word"\s*:\s*"([^"]{2,30})"', html)
            if not words:
                words = re.findall(r'"query"\s*:\s*"([^"]{2,30})"', html)
            if not words:
                # 尝试<a>标签中的热搜
                words = re.findall(r'<a[^>]*href="https?://www\.so\.com/s\?q=([^"&]+)"[^>]*>([^<]+)</a>', html)
                words = [title.strip() for _, title in words if len(title.strip()) >= 2]
            else:
                words = [w for w in words if len(w) >= 2 and not w.startswith('http')]

            seen = set()
            for w in words:
                if w not in seen:
                    seen.add(w)
                    items.append({
                        'title': w,
                        'url': f"https://www.so.com/s?q={quote(w)}",
                        'heat': 0,
                    })
    except Exception as e:
        print(f"    [WARN] 360首页解析失败: {e}")

    # 方式2: 尝试360热点新闻页
    if not items:
        try:
            html = fetch_html('https://news.so.com/', timeout=10)
            if html:
                titles = re.findall(r'"title"\s*:\s*"([^"]{4,50})"', html)
                seen = set()
                for t in titles:
                    if t not in seen and len(t) >= 4:
                        seen.add(t)
                        items.append({
                            'title': t,
                            'url': f"https://www.so.com/s?q={quote(t)}",
                            'heat': 0,
                        })
        except Exception:
            pass

    if items:
        print(f"    ✓ 从360获取到 {len(items)} 条热搜")
    else:
        print("    ⚠ 360原始数据不可用，将使用交叉源")
    return items


# ============================================================
# 核心抓取逻辑
# ============================================================

def fetch_hot_search():
    """
    抓取各平台热搜并筛选教育相关内容。
    对于无法直接获取数据的平台（360/夸克），使用交叉源+真实搜索链接。
    """
    print("\n  [微博]")
    weibo_all = fetch_weibo_hot()
    time.sleep(0.5)

    print("\n  [百度]")
    baidu_all = fetch_baidu_hot()
    time.sleep(0.5)

    print("\n  [抖音]")
    douyin_all = fetch_douyin_hot()
    time.sleep(0.5)

    print("\n  [夸克]")
    quark_all = fetch_quark_hot()
    time.sleep(0.5)

    print("\n  [360]")
    so360_all = fetch_so360_hot()
    time.sleep(0.5)

    # 如果夸克或360没有数据，用头条交叉补充（提供真实搜索链接）
    toutiao_all = []
    if not quark_all or not so360_all:
        print("\n  [交叉源-头条]")
        toutiao_all = fetch_toutiao_hot()

    # 对夸克: 如果原始数据不足，用头条+百度+微博的热搜词构造夸克搜索链接
    if len(quark_all) < 10:
        print("    → 为夸克补充交叉源数据...")
        cross_items = toutiao_all + baidu_all + weibo_all
        seen = set(item['title'] for item in quark_all)
        for item in cross_items:
            if item['title'] not in seen and len(item['title']) >= 4:
                seen.add(item['title'])
                quark_all.append({
                    'title': item['title'],
                    'url': f"https://quark.sm.cn/s?q={quote(item['title'])}",
                    'heat': item.get('heat', 0),
                })

    # 对360: 同理
    if len(so360_all) < 10:
        print("    → 为360补充交叉源数据...")
        cross_items = toutiao_all + baidu_all + weibo_all
        seen = set(item['title'] for item in so360_all)
        for item in cross_items:
            if item['title'] not in seen and len(item['title']) >= 4:
                seen.add(item['title'])
                so360_all.append({
                    'title': item['title'],
                    'url': f"https://www.so.com/s?q={quote(item['title'])}",
                    'heat': item.get('heat', 0),
                })

    # 存储全量数据（用于后续用户画像和TOP15）
    all_platform_data = {
        'weibo': weibo_all,
        'baidu': baidu_all,
        'douyin': douyin_all,
        'quark': quark_all,
        'so360': so360_all,
    }

    # 筛选教育相关热搜 TOP5
    hot_search = {}
    for platform, all_items in all_platform_data.items():
        edu_items = [item for item in all_items if is_edu_related(item['title'])]
        # 按热度排序，取TOP5
        edu_items.sort(key=lambda x: int(x.get('heat', 0) or 0), reverse=True)
        edu_items = edu_items[:5]
        # 格式化输出
        for i, item in enumerate(edu_items):
            item['rank'] = i + 1
        hot_search[platform] = edu_items
        print(f"  ✓ {PLATFORM_DISPLAY_NAMES[platform]}: {len(edu_items)} 条教育热搜")

    return hot_search, all_platform_data


def fetch_hot_products():
    """抓取电商热销教育商品（使用预设常青商品 - 真实平台商品）"""
    # 说明: 电商平台(淘宝/京东/快手)没有免费公开API获取实时商品榜单
    # 这里使用的是各平台实际热销的教育商品（定期手动更新）
    # 每条商品链接均为真实可跳转的电商搜索链接
    products = {
        'taobao_tmall': [
            {"rank": 1, "title": "学而思AI学习机", "sales": "月销5000+", "price": "¥2,999起", "category": "电子教育",
             "url": "https://s.taobao.com/search?q=学而思AI学习机"},
            {"rank": 2, "title": "科大讯飞AI翻译笔", "sales": "月销8000+", "price": "¥699起", "category": "电子教育",
             "url": "https://s.taobao.com/search?q=科大讯飞翻译笔"},
            {"rank": 3, "title": "考研英语全程班网课", "sales": "月销1.2万+", "price": "¥1,980起", "category": "成人教育",
             "url": "https://s.taobao.com/search?q=考研英语全程班"},
            {"rank": 4, "title": "人教版中小学教材全套", "sales": "月销3万+", "price": "¥128起", "category": "图书",
             "url": "https://s.taobao.com/search?q=人教版教材全套"},
            {"rank": 5, "title": "公务员考试教材套装", "sales": "月销2万+", "price": "¥79起", "category": "图书",
             "url": "https://s.taobao.com/search?q=公务员考试教材"},
            {"rank": 6, "title": "斑马AI课儿童启蒙年卡", "sales": "月销6000+", "price": "¥2,800起", "category": "K12教育",
             "url": "https://s.taobao.com/search?q=斑马AI课"},
            {"rank": 7, "title": "小猿智能练习本", "sales": "月销4000+", "price": "¥1,099起", "category": "电子教育",
             "url": "https://s.taobao.com/search?q=小猿智能练习本"},
            {"rank": 8, "title": "考研政治核心教材", "sales": "月销1.5万+", "price": "¥99起", "category": "图书",
             "url": "https://s.taobao.com/search?q=考研政治教材"},
            {"rank": 9, "title": "儿童早教点读笔套装", "sales": "月销9000+", "price": "¥298起", "category": "电子教育",
             "url": "https://s.taobao.com/search?q=儿童点读笔"},
            {"rank": 10, "title": "MBA联考教材全套", "sales": "月销3000+", "price": "¥168起", "category": "成人教育",
             "url": "https://s.taobao.com/search?q=MBA联考教材"},
        ],
        'jd': [
            {"rank": 1, "title": "有道词典笔旗舰款", "sales": "好评50万+", "price": "¥899起", "category": "电子教育",
             "url": "https://search.jd.com/Search?keyword=有道词典笔"},
            {"rank": 2, "title": "希沃学习机", "sales": "好评10万+", "price": "¥3,999起", "category": "电子教育",
             "url": "https://search.jd.com/Search?keyword=希沃学习机"},
            {"rank": 3, "title": "高途考研全程班", "sales": "好评8万+", "price": "¥3,980起", "category": "成人教育",
             "url": "https://search.jd.com/Search?keyword=高途考研"},
            {"rank": 4, "title": "小度学习平板", "sales": "好评20万+", "price": "¥2,299起", "category": "电子教育",
             "url": "https://search.jd.com/Search?keyword=小度学习平板"},
            {"rank": 5, "title": "一级建造师考试教材", "sales": "好评5万+", "price": "¥128起", "category": "成人教育",
             "url": "https://search.jd.com/Search?keyword=一级建造师教材"},
            {"rank": 6, "title": "DK儿童百科全书", "sales": "好评30万+", "price": "¥198起", "category": "图书",
             "url": "https://search.jd.com/Search?keyword=DK儿童百科全书"},
            {"rank": 7, "title": "阿尔法蛋AI词典笔", "sales": "好评15万+", "price": "¥699起", "category": "电子教育",
             "url": "https://search.jd.com/Search?keyword=阿尔法蛋词典笔"},
            {"rank": 8, "title": "五年高考三年模拟", "sales": "好评100万+", "price": "¥128起", "category": "图书",
             "url": "https://search.jd.com/Search?keyword=五年高考三年模拟"},
            {"rank": 9, "title": "作业帮AI学习机", "sales": "好评8万+", "price": "¥2,399起", "category": "电子教育",
             "url": "https://search.jd.com/Search?keyword=作业帮学习机"},
            {"rank": 10, "title": "注册会计师CPA教材", "sales": "好评6万+", "price": "¥198起", "category": "成人教育",
             "url": "https://search.jd.com/Search?keyword=注册会计师CPA教材"},
        ],
        'kuaishou': [
            {"rank": 1, "title": "读书郎学习平板", "sales": "已售1万+", "price": "¥1,699起", "category": "电子教育",
             "url": "https://www.kuaishou.com/search/video?searchKey=读书郎学习平板"},
            {"rank": 2, "title": "粉笔公考系统班", "sales": "已售5万+", "price": "¥980起", "category": "成人教育",
             "url": "https://www.kuaishou.com/search/video?searchKey=粉笔公考"},
            {"rank": 3, "title": "小天才电话手表", "sales": "已售3万+", "price": "¥1,598起", "category": "电子教育",
             "url": "https://www.kuaishou.com/search/video?searchKey=小天才电话手表"},
            {"rank": 4, "title": "中小学同步课程VIP", "sales": "已售2万+", "price": "¥980起", "category": "K12教育",
             "url": "https://www.kuaishou.com/search/video?searchKey=中小学同步课程"},
            {"rank": 5, "title": "四大名著学生版全套", "sales": "已售8万+", "price": "¥49起", "category": "图书",
             "url": "https://www.kuaishou.com/search/video?searchKey=四大名著学生版"},
            {"rank": 6, "title": "有道AI学习机", "sales": "已售1.5万+", "price": "¥2,999起", "category": "电子教育",
             "url": "https://www.kuaishou.com/search/video?searchKey=有道AI学习机"},
            {"rank": 7, "title": "新概念英语全套", "sales": "已售6万+", "price": "¥78起", "category": "图书",
             "url": "https://www.kuaishou.com/search/video?searchKey=新概念英语"},
            {"rank": 8, "title": "学历提升自考课程", "sales": "已售4万+", "price": "¥3,980起", "category": "成人教育",
             "url": "https://www.kuaishou.com/search/video?searchKey=学历提升自考"},
            {"rank": 9, "title": "洪恩识字APP年卡", "sales": "已售2万+", "price": "¥298起", "category": "K12教育",
             "url": "https://www.kuaishou.com/search/video?searchKey=洪恩识字"},
            {"rank": 10, "title": "消防工程师考试教材", "sales": "已售1万+", "price": "¥138起", "category": "成人教育",
             "url": "https://www.kuaishou.com/search/video?searchKey=消防工程师教材"},
        ],
    }
    return products


# ============================================================
# 用户画像热搜 & 看板分发
# ============================================================

def classify_user_personas(title):
    """基于关键词规则为一条内容打上用户画像标签"""
    personas = set()
    if not title:
        return personas
    for keywords, persona_list in PERSONA_KEYWORD_RULES:
        if any(kw in title for kw in keywords):
            personas.update(persona_list)
    return personas


def compute_panel_affinity(title, panel):
    """计算亲和度得分"""
    score = 0
    keywords = PANEL_AFFINITY_KEYWORDS.get(panel, [])
    for kw in keywords:
        if kw in title:
            score += 1
    return score


def fetch_user_hotsearch(all_platform_data):
    """利用已获取的全平台数据，按亲和度独占分配到4个看板"""
    user_hotsearch = {"k12": [], "adult_edu": [], "e_edu": [], "books": []}

    platform_order = {'weibo': 0, 'baidu': 1, 'douyin': 2, 'quark': 3, 'so360': 4}
    all_items = []

    for platform, items in all_platform_data.items():
        if platform not in platform_order:
            continue
        for i, item in enumerate(items[:50]):
            title = item.get('title', '')
            if not title or is_sensitive_title(title):
                continue
            personas = classify_user_personas(title)
            if not personas:
                continue
            heat = item.get('heat', 0)
            try:
                heat = int(heat)
            except (ValueError, TypeError):
                heat = 0
            # 格式化热度展示
            if heat >= 10000:
                heat_str = f"{heat // 10000}万🔥"
            elif heat > 0:
                heat_str = f"{heat}🔥"
            else:
                heat_str = "热"

            all_items.append({
                "platform_key": platform,
                "platform": PLATFORM_DISPLAY_NAMES.get(platform, platform),
                "platform_rank": i,
                "title": title,
                "heat_raw": heat,
                "heat": heat_str,
                "personas": personas,
                "url": item.get('url', build_search_url(platform, title)),
            })

    if not all_items:
        return user_hotsearch

    # 排序：按平台内排名
    all_items.sort(key=lambda x: (x["platform_rank"], platform_order.get(x["platform_key"], 99)))

    # 去重
    seen_titles = set()
    unique_items = []
    for item in all_items:
        if item["title"] not in seen_titles:
            seen_titles.add(item["title"])
            unique_items.append(item)

    panel_order = ["k12", "adult_edu", "e_edu", "books"]
    MAX_PER_PANEL = 15

    # 计算每条热搜对各面板的资格和亲和度
    item_eligible = []
    for item in unique_items:
        title = item["title"]
        personas = item["personas"]
        eligible_panels = {}
        for panel in panel_order:
            target_personas = set(PANEL_PERSONAS.get(panel, []))
            if personas & target_personas:
                affinity = compute_panel_affinity(title, panel)
                eligible_panels[panel] = affinity
        if eligible_panels:
            item_eligible.append((item, eligible_panels))

    # 独占分配
    global_used = set()

    # 先分配只适合一个面板的
    for item, eligible_panels in item_eligible:
        if len(eligible_panels) == 1:
            panel = list(eligible_panels.keys())[0]
            if len(user_hotsearch[panel]) >= MAX_PER_PANEL:
                continue
            if item["title"] in global_used:
                continue
            global_used.add(item["title"])
            panel_list = user_hotsearch[panel]
            panel_list.append({
                "rank": len(panel_list) + 1,
                "title": item["title"],
                "heat": item["heat"],
                "heat_raw": item["heat_raw"],
                "platform": item["platform"],
                "url": item["url"],
            })

    # 再分配适合多个面板的
    multi_eligible = [(item, ep) for item, ep in item_eligible
                      if len(ep) > 1 and item["title"] not in global_used]
    multi_eligible.sort(key=lambda x: x[0].get("heat_raw", 0), reverse=True)

    for item, eligible_panels in multi_eligible:
        if item["title"] in global_used:
            continue
        best_panel = None
        best_score = (-1, 999, 999)
        for panel in panel_order:
            if panel not in eligible_panels:
                continue
            if len(user_hotsearch[panel]) >= MAX_PER_PANEL:
                continue
            affinity = eligible_panels[panel]
            current_count = len(user_hotsearch[panel])
            order_idx = panel_order.index(panel)
            score = (affinity, -current_count, -order_idx)
            if score > best_score:
                best_score = score
                best_panel = panel
        if best_panel:
            global_used.add(item["title"])
            panel_list = user_hotsearch[best_panel]
            panel_list.append({
                "rank": len(panel_list) + 1,
                "title": item["title"],
                "heat": item["heat"],
                "heat_raw": item["heat_raw"],
                "platform": item["platform"],
                "url": item["url"],
            })

    return user_hotsearch


# ============================================================
# 营销建议生成
# ============================================================

def generate_marketing_suggestions(hot_search):
    """基于实际教育热搜生成营销建议"""
    category_words = {'成人教育': [], 'K12教育': [], '图书': [], '电子教育': []}

    for platform_items in hot_search.values():
        for item in platform_items:
            cat = categorize_edu(item['title'])
            if cat in category_words and len(category_words[cat]) < 12:
                word = item['title']
                if len(word) > 15:
                    for kw in EDU_KEYWORDS:
                        if kw in word:
                            word = kw
                            break
                category_words[cat].append(word)

    for cat in category_words:
        category_words[cat] = list(dict.fromkeys(category_words[cat]))

    suggestions = []

    # 成人教育
    aw = category_words.get('成人教育', [])
    suggestions.append({
        "category": "成人教育",
        "items": [
            {"scene": "考证备考季",
             "hot_words": " / ".join(aw[:3]) if len(aw) >= 3 else "考研 / 公务员 / MBA",
             "strategy": "投放搜索广告锁定「报名入口」「分数线」等刚需词，搭配落地页免费试听引流，利用考试时间节点制造紧迫感"},
            {"scene": "职业技能提升",
             "hot_words": " / ".join(aw[3:6]) if len(aw) >= 6 else "AI编程培训 / 学历提升 / 职业认证",
             "strategy": "信息流素材突出「高薪就业」「取证周期短」等痛点，定向25-40岁职场人群，配合限时优惠促转化"},
            {"scene": "学历焦虑营销",
             "hot_words": " / ".join(aw[6:9]) if len(aw) >= 9 else "自考本科 / 在职研究生 / 专升本",
             "strategy": "短视频投放真人出镜分享上岸经历，评论区引导私信咨询转化，抖音/快手双平台覆盖"},
        ]
    })

    # K12教育
    kw = category_words.get('K12教育', [])
    suggestions.append({
        "category": "K12教育",
        "items": [
            {"scene": "升学季流量高峰",
             "hot_words": " / ".join(kw[:3]) if len(kw) >= 3 else "高考志愿填报 / 幼小衔接 / 中考体育",
             "strategy": "搜索抢占「分数线预测」「志愿填报工具」等长尾词，落地页提供免费测评工具提升留资率"},
            {"scene": "暑期培训招生",
             "hot_words": " / ".join(kw[3:6]) if len(kw) >= 6 else "暑期兴趣班 / 研学旅行 / 少儿编程",
             "strategy": "朋友圈广告定向30-45岁家长群体，素材强调「名额有限」「早鸟优惠」制造紧迫感"},
            {"scene": "学习方法种草",
             "hot_words": " / ".join(kw[6:9]) if len(kw) >= 9 else "学霸笔记 / 高效学习法 / 时间管理",
             "strategy": "抖音达人合作短视频种草，挂载课程商品链接实现短链路转化，配合开学季节点"},
        ]
    })

    # 图书
    bw = category_words.get('图书', [])
    suggestions.append({
        "category": "图书",
        "items": [
            {"scene": "教辅刚需旺季",
             "hot_words": " / ".join(bw[:3]) if len(bw) >= 3 else "教材全套 / 考研政治 / 人教版课本",
             "strategy": "电商平台搜索广告竞价「教材全套」「正版书籍」，商品详情页强调发货速度与正品保障"},
            {"scene": "亲子阅读推广",
             "hot_words": " / ".join(bw[3:6]) if len(bw) >= 6 else "暑期书单 / DK百科 / 四大名著",
             "strategy": "小红书+抖音种草内容营销，达人晒书单带货，搭配满减促销提升客单价"},
            {"scene": "知识付费跨界",
             "hot_words": " / ".join(bw[6:9]) if len(bw) >= 9 else "AI写作 / 读书会 / 知识星球",
             "strategy": "信息流定向考研/自考人群，内容突出「碎片化学习」「名师带读」，引导下单"},
        ]
    })

    # 电子教育
    ew = category_words.get('电子教育', [])
    suggestions.append({
        "category": "电子教育",
        "items": [
            {"scene": "AI硬件种草",
             "hot_words": " / ".join(ew[:3]) if len(ew) >= 3 else "AI学习机 / 词典笔 / 智能练习本",
             "strategy": "抖音开箱测评+电商直播组合拳，素材对比传统学习方式突出效率提升"},
            {"scene": "暑期礼物场景",
             "hot_words": " / ".join(ew[3:6]) if len(ew) >= 6 else "学习平板 / 点读笔 / 电话手表",
             "strategy": "搜索广告锁定「送孩子礼物」「学习机推荐」等场景词，投放618/暑期节点"},
            {"scene": "教育科技新品",
             "hot_words": " / ".join(ew[6:9]) if len(ew) >= 9 else "AI教育新政 / AI批改 / 智能题库",
             "strategy": "信息流投放科技感素材，定向教育KOL粉丝与科技关注人群，突出政策利好"},
        ]
    })

    return suggestions


# ============================================================
# 抖音热点挂载 - 飞书多维表格数据获取
# ============================================================

LARK_BASE_TOKEN = 'FZkmbmCDzayi6Zs4hfWcECvnnPW'
LARK_TABLE_ID = 'tblJlMaj7IdYjgA1'
LARK_FIELD_HOTNAME = '热点名称'
LARK_FIELD_DATE = '冲榜日期'
LARK_FIELD_STATUS = '进展'
LARK_FIELD_INDUSTRY = '适配行业'
HOTSPOT_STATUS_FILTER = ['报名中', '上线中']
HOTSPOT_INDUSTRY_FILTER = ['综合', '图书教育']


def get_lark_tenant_token():
    """获取飞书 tenant_access_token"""
    app_id = os.environ.get('LARK_APP_ID', '')
    app_secret = os.environ.get('LARK_APP_SECRET', '')
    if not app_id or not app_secret:
        print("  ⚠ LARK_APP_ID / LARK_APP_SECRET 未配置，跳过飞书数据获取")
        return None

    url = 'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal'
    payload = json.dumps({"app_id": app_id, "app_secret": app_secret}).encode()
    req = Request(url, data=payload, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get('code') == 0:
                return data['tenant_access_token']
            print(f"  ⚠ 获取 token 失败: {data.get('msg')}")
    except Exception as e:
        print(f"  ⚠ 获取 token 异常: {e}")
    return None


def fetch_douyin_hotspot():
    """从飞书多维表格获取抖音热点挂载数据"""
    token = get_lark_tenant_token()
    if not token:
        print("  → 使用本地缓存/空数据")
        return get_cached_hotspot()

    filter_body = {
        "conjunction": "and",
        "conditions": [
            {"field_name": LARK_FIELD_STATUS, "operator": "is", "value": HOTSPOT_STATUS_FILTER},
            {"field_name": LARK_FIELD_INDUSTRY, "operator": "contains", "value": HOTSPOT_INDUSTRY_FILTER}
        ]
    }

    url = f'https://open.feishu.cn/open-apis/bitable/v1/apps/{LARK_BASE_TOKEN}/tables/{LARK_TABLE_ID}/records/search?page_size=50'
    payload = json.dumps({
        "filter": filter_body,
        "field_names": [LARK_FIELD_HOTNAME, LARK_FIELD_DATE, LARK_FIELD_STATUS, LARK_FIELD_INDUSTRY]
    }).encode()
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    req = Request(url, data=payload, headers=headers)

    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            if data.get('code') != 0:
                print(f"  ⚠ API 错误: {data.get('msg')}")
                return get_cached_hotspot()

            items = data.get('data', {}).get('items', [])
            result = []
            for item in items:
                fields = item.get('fields', {})
                name = ''
                if isinstance(fields.get(LARK_FIELD_HOTNAME), list):
                    name = ''.join(seg.get('text', '') for seg in fields[LARK_FIELD_HOTNAME])
                elif isinstance(fields.get(LARK_FIELD_HOTNAME), str):
                    name = fields[LARK_FIELD_HOTNAME]

                date_val = fields.get(LARK_FIELD_DATE, '')
                if isinstance(date_val, (int, float)):
                    date_str = datetime.fromtimestamp(date_val / 1000).strftime('%Y-%m-%d')
                elif isinstance(date_val, str):
                    date_str = date_val[:10]
                else:
                    date_str = ''

                status = fields.get(LARK_FIELD_STATUS, '')
                if isinstance(status, list):
                    status = status[0] if status else ''

                industry = fields.get(LARK_FIELD_INDUSTRY, '')
                if isinstance(industry, list):
                    industry = industry[0] if industry else ''

                if name and status in HOTSPOT_STATUS_FILTER:
                    result.append({
                        'name': name,
                        'date': date_str,
                        'status': status,
                        'industry': industry
                    })

            result.sort(key=lambda x: (0 if x['status'] == '上线中' else 1, x['date']))
            print(f"  ✓ 从飞书获取到 {len(result)} 条热点")
            return result
    except Exception as e:
        print(f"  ⚠ 获取飞书数据异常: {e}")
        return get_cached_hotspot()


def get_cached_hotspot():
    """读取本地缓存的热点数据"""
    try:
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
        with open(output_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
        cached = old_data.get('douyin_hotspot', [])
        if cached:
            print(f"  → 使用本地缓存: {len(cached)} 条")
            return cached
    except Exception:
        pass
    return []


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("🎓 教育热点捕手 - 数据采集 v3.0 (稳定数据源版)")
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 1. 抓取热搜（新版：直接调用各平台官方API）
    print("\n📡 [1/5] 抓取各平台热搜（官方API直连）...")
    hot_search, all_platform_data = fetch_hot_search()

    # 2. 电商商品
    print("\n🛒 [2/5] 获取电商热销教育商品...")
    hot_products = fetch_hot_products()
    print(f"  ✓ 淘宝天猫 {len(hot_products['taobao_tmall'])} 条 | 京东 {len(hot_products['jd'])} 条 | 快手 {len(hot_products['kuaishou'])} 条")

    # 3. 生成TOP15
    print("\n🏆 [3/5] 生成全平台教育热搜 TOP15...")
    all_edu_items = []
    for platform, items in hot_search.items():
        for item in items:
            all_edu_items.append({**item, '_platform': PLATFORM_DISPLAY_NAMES.get(platform, platform)})

    # 去重并按热度排序
    seen = set()
    unique = []
    for item in sorted(all_edu_items, key=lambda x: int(x.get('heat', 0) or 0), reverse=True):
        if item['title'] not in seen:
            seen.add(item['title'])
            unique.append(item)

    top15 = []
    for i, item in enumerate(unique[:15]):
        platforms = []
        for p, items in hot_search.items():
            if any(it['title'] == item['title'] for it in items):
                platforms.append(PLATFORM_DISPLAY_NAMES.get(p, p))
        top15.append({
            "rank": i + 1,
            "title": item['title'],
            "heat": item.get('heat', 500000),
            "url": item.get('url', ''),
            "platforms": platforms or [item.get('_platform', '未知')],
            "category": categorize_edu(item['title'])
        })
    print(f"  ✓ 生成 {len(top15)} 条跨平台教育热点")

    # 4. 营销建议
    print("\n💡 [4/5] 生成营销建议...")
    marketing = generate_marketing_suggestions(hot_search)
    print(f"  ✓ 为 {len(marketing)} 个赛道生成营销建议")

    # 5. 用户画像热搜看板
    print("\n👥 [5/6] 生成用户画像热搜看板...")
    user_hotsearch = fetch_user_hotsearch(all_platform_data)
    print(
        "  ✓ 用户画像看板条数："
        f"非成教(K12) {len(user_hotsearch['k12'])} 条，"
        f"成人教育 {len(user_hotsearch['adult_edu'])} 条，"
        f"电子教育 {len(user_hotsearch['e_edu'])} 条，"
        f"图书 {len(user_hotsearch['books'])} 条"
    )

    # 6. 抖音热点挂载
    print("\n🔥 [6/6] 获取抖音热点挂载数据...")
    douyin_hotspot = fetch_douyin_hotspot()
    print(f"  ✓ 抖音热点挂载: {len(douyin_hotspot)} 条")

    # 输出
    now = datetime.now()
    output = {
        "update_time": now.strftime('%Y-%m-%d %H:%M'),
        "issue_no": (now - datetime(2026, 6, 12)).days + 1,
        "hot_search": hot_search,
        "hot_products": hot_products,
        "top15_today": top15,
        "marketing_suggestions": marketing,
        "user_hotsearch": user_hotsearch,
        "douyin_hotspot": douyin_hotspot,
    }

    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    total_search = sum(len(v) for v in hot_search.values())
    total_products = sum(len(v) for v in hot_products.values())
    total_user_hot = sum(len(v) for v in user_hotsearch.values())

    print(f"\n{'=' * 60}")
    print(f"✅ 完成! 数据已写入: {output_path}")
    print(
        f"📊 统计: 教育热搜 {total_search} 条 | 热销商品 {total_products} 条 | "
        f"TOP15 {len(top15)} 条 | 用户画像热搜 {total_user_hot} 条"
    )
    print(f"{'=' * 60}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n⚠️ 脚本遇到异常: {e}")
        print("正在写入最小化 data.json...")
        import traceback
        traceback.print_exc()
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
        fallback = {
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "issue_no": (datetime.now() - datetime(2026, 6, 12)).days + 1,
            "hot_search": {},
            "hot_products": {},
            "top15_today": [],
            "marketing_suggestions": [],
            "user_hotsearch": {"k12": [], "adult_edu": [], "e_edu": [], "books": []},
            "douyin_hotspot": [],
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fallback, f, ensure_ascii=False, indent=2)
        print(f"✅ 已写入最小化数据: {output_path}")
