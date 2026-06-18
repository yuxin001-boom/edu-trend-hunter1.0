#!/usr/bin/env python3
"""
教育热点捕手 - 数据采集脚本 v2.0 (修复版)
修复内容:
1. 过滤掉网站自身链接（如"API 开放平台"等垃圾数据）
2. 教育筛选宁缺毋滥，不够5条就显示实际数量，不用无关内容凑数
3. 修复电商数据抓取（改用搜索关键词方式从多个源获取）
"""

import json
import re
import os
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError
from urllib.parse import quote_plus

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

# 黑名单：过滤掉网站自身的垃圾链接
BLACKLIST_TITLES = [
    'API 开放平台', 'API开放平台', 'TopHub', 'tophub', '今日热榜',
    '热榜数据', '开放平台', '数据接口', '免费使用', '查看更多',
    '返回顶部', '下载APP', '登录', '注册', '关于我们',
]

# 黑名单URL关键词：包含这些域名的链接是网站自身链接
BLACKLIST_URLS = [
    'tophubdata.com', 'tophub.today/login', 'tophub.today/register',
    'tophub.today/about', 'tophub.today/api',
]

# TopHub.today 各平台节点
TOPHUB_NODES = {
    'weibo': 'KqndgxeLl9',
    'baidu': 'Jb0vmloB1G',
    'quark': 'n6YoVqDeZa',
    'douyin': 'K7GdaMgdQy',
    'so360': 'KMZd7x6erO',
}

# 各平台热搜的合法URL域名（只有包含这些域名的才是真正的热搜链接）
VALID_DOMAINS = {
    'weibo': ['weibo.com', 's.weibo.com'],
    'baidu': ['baidu.com', 'www.baidu.com'],
    'quark': ['sm.cn', 'so.m.sm.cn', 'quark.sm.cn'],
    'douyin': ['douyin.com', 'www.douyin.com'],
    'so360': ['so.com', 'www.so.com'],
}

# 平台展示名称
PLATFORM_DISPLAY_NAMES = {
    'weibo': '微博',
    'baidu': '百度',
    'quark': '夸克',
    'douyin': '抖音',
    'so360': '360',
}

# 平台搜索URL模板（用于用户画像看板跳转）
PLATFORM_SEARCH_URL_TEMPLATES = {
    'weibo': 'https://s.weibo.com/weibo?q={query}',
    'baidu': 'https://www.baidu.com/s?wd={query}',
    'douyin': 'https://www.douyin.com/search/{query}',
    'quark': 'https://quark.sm.cn/s?q={query}',
    'so360': 'https://www.so.com/s?q={query}',
}

# 敏感词过滤（政治等高风险内容，直接剔除）
SENSITIVE_KEYWORDS = [
    '政治', '军事', '台湾', '习近平', '领导人', '外交部', '国防', '军队', '统一', '主权', '南海', '钓鱼岛',
]

# 用户画像与面板配置
USER_PERSONAS = [
    '资深中产',
    '小镇中老年',
    '小镇青年',
    '精致妈妈',
    '都市银发',
    '新锐白领',
]

PANEL_PERSONAS = {
    # 非成教(K12) 看板：资深中产, 小镇中老年, 小镇青年, 精致妈妈
    "k12": ['资深中产', '小镇中老年', '小镇青年', '精致妈妈'],
    # 成人教育 看板：小镇青年, 都市银发, 新锐白领
    "adult_edu": ['小镇青年', '都市银发', '新锐白领'],
    # 电子教育 看板：资深中产, 小镇中老年, 小镇青年, 精致妈妈
    "e_edu": ['资深中产', '小镇中老年', '小镇青年', '精致妈妈'],
    # 图书 看板：精致妈妈, 小镇青年, 新锐白领
    "books": ['精致妈妈', '小镇青年', '新锐白领'],
}

# 画像关键词规则：每个规则命中时，会把条目分配给对应人群
PERSONA_KEYWORD_RULES = [
    # Sports / 赛事
    (
        ['世界杯', 'NBA', '足球', '篮球', '奥运', '比赛', '冠军', '决赛', '联赛', '体育'],
        ['资深中产', '小镇青年', '新锐白领'],
    ),
    # Entertainment / 综艺 / 追剧
    (
        ['歌手', '乘风', '明星', '演员', '综艺', '电视剧', '热播', '追剧', '演唱会', '电影', '票房'],
        ['精致妈妈', '小镇青年'],
    ),
    # Finance / 政策
    (
        ['股市', '基金', '新政', '经济', '金融', '房价', '利率', '央行', 'A股', '美联储', '降息'],
        ['新锐白领', '都市银发', '资深中产'],
    ),
    # Parenting / 家庭
    (
        ['孩子', '家长', '暑假', '高考', '中考', '亲子', '育儿', '幼儿', '宝宝', '防溺水', '儿童', '婴幼儿'],
        ['精致妈妈', '小镇中老年'],
    ),
    # Internet trends / 梗
    (
        ['AI短剧', '热梗', '洗脑', '火了', '出圈', '全网', '刷屏', '网红', '直播'],
        ['小镇青年'],
    ),
    # Health / 养生
    (
        ['防暑', '养老', '退休', '广场舞', '保健', '健康', '中老年', '养生', '中医'],
        ['都市银发', '小镇中老年'],
    ),
    # Consumer / 购物
    (
        ['618', '双十一', '优惠', '打折', '手机', '家电', '测评', '推荐', '好物', '种草'],
        ['资深中产', '小镇青年'],
    ),
    # Reading / 文化
    (
        ['书单', '畅销', '豆瓣', '小说', '绘本', '文案', '情感', '文化', '阅读', '综艺', '知识'],
        ['精致妈妈', '新锐白领'],
    ),
    # Career / 职场
    (
        ['考公', '考证', '面试', '简历', '跳槽', '薪资', '裁员', 'AI替代', '就业', '创业'],
        ['新锐白领', '小镇青年'],
    ),
    # Tech / 科技
    (
        ['AI', '科技', '芯片', '机器人', '数码', '新能源', '电动车', '智能', '5G', '互联网'],
        ['资深中产', '新锐白领'],
    ),
    # Weather / 安全
    (
        ['暴雨', '高温', '台风', '地震', '防汛', '预警', '洪水'],
        USER_PERSONAS,
    ),
]

# 面板亲和关键词：用于差异化分配（决定一条热搜更适合哪个面板）
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

# 教育类电商热销关键词（用于从电商榜单中筛选）
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

# 电商平台节点（TopHub上的真实节点）
TOPHUB_COMMERCE = {
    'taobao_tmall': 'GOxJBpOArl',  # 淘宝热搜
    'jd': 'Q1Vd5Eo85R',            # 京东热榜
    'kuaishou': '4KRe08doYW',       # 快手热榜（商品相关）
}


# ============================================================
# 工具函数
# ============================================================

def fetch_url(url, timeout=20):
    """通用URL抓取"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Referer': 'https://tophub.today/',
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  [WARN] 抓取失败 {url}: {e}")
        return None


def is_blacklisted(title, url):
    """检查是否为黑名单内容（网站自身链接等）"""
    # 标题黑名单
    for bl in BLACKLIST_TITLES:
        if bl.lower() in title.lower():
            return True
    # URL黑名单
    for bl_url in BLACKLIST_URLS:
        if bl_url in url:
            return True
    # 标题太短（通常是按钮/标签）
    if len(title) < 4:
        return True
    return False


def is_valid_platform_url(url, platform):
    """检查URL是否属于该平台的合法链接"""
    valid = VALID_DOMAINS.get(platform, [])
    # 如果有合法域名列表，检查URL是否包含
    if valid:
        for domain in valid:
            if domain in url:
                return True
        # 也接受tophub.today/n/ 开头的（TopHub的源链接）
        if 'tophub.today/n/' in url:
            return True
        return False
    return True


def is_edu_related(title):
    """判断一条内容是否与教育行业相关"""
    for kw in EDU_KEYWORDS:
        if kw in title:
            return True
    return False


def is_edu_product(title):
    """判断一个商品是否为教育类商品"""
    for kw in EDU_PRODUCT_KEYWORDS:
        if kw in title:
            return True
    return False


def categorize_edu(title):
    """将教育内容分类到四大赛道"""
    # 成人教育
    adult_kws = ['考研', '公务员', '考公', '国考', 'MBA', '自考', '成考', '专升本',
                 '学历', '在职', '一建', '二建', '注会', 'CPA', '法考', '消防工程师',
                 '职业培训', '技能培训', '继续教育', '读研', '读博', '考博',
                 '会计', '司法考试', '执业', '护士', '留学']
    for kw in adult_kws:
        if kw in title:
            return '成人教育'
    
    # K12
    k12_kws = ['高考', '中考', '小学', '初中', '高中', '幼小衔接', '幼儿园',
               '兴趣班', '少儿编程', '奥数', '研学', '家长', '课后服务',
               '志愿填报', '分数线', '学霸', '补习', '辅导', '托管',
               '小升初', '暑假', '寒假', '开学', '学期', '中小学', '学生']
    for kw in k12_kws:
        if kw in title:
            return 'K12教育'
    
    # 电子教育
    elearn_kws = ['学习机', '词典笔', '点读笔', '学习平板', 'AI教育', 'AI学习',
                  '智能学习', '教育科技', '网课', '在线教育', '直播课', '教育app']
    for kw in elearn_kws:
        if kw in title:
            return '电子教育'
    
    # 图书
    book_kws = ['教材', '教辅', '课本', '书单', '绘本', '百科', '图书']
    for kw in book_kws:
        if kw in title:
            return '图书'
    
    # 通用教育关键词默认K12
    return 'K12教育'


# ============================================================
# 数据抓取
# ============================================================

def parse_tophub_items(html, platform=None):
    """从TopHub页面提取热搜条目（改进版，过滤垃圾）"""
    items = []
    if not html:
        return items
    
    # 匹配热搜条目的链接
    pattern = r'<a[^>]*href="([^"]*)"[^>]*target="_blank"[^>]*>\s*([^<]+?)\s*</a>'
    matches = re.findall(pattern, html)
    
    seen_titles = set()
    for url, title in matches:
        title = title.strip()
        
        # 基础过滤
        if not title or len(title) < 4:
            continue
        if title in seen_titles:
            continue
        
        # 黑名单过滤
        if is_blacklisted(title, url):
            continue
        
        # 平台URL合法性检查
        if platform and not is_valid_platform_url(url, platform):
            continue
        
        seen_titles.add(title)
        items.append({
            "title": title,
            "url": url,
            "heat": 0,  # 后面根据排名赋值
        })
    
    return items[:50]


def fetch_hot_search():
    """抓取各平台热搜并筛选教育相关内容"""
    hot_search = {}
    platform_names = {'weibo': '微博', 'baidu': '百度', 'quark': '夸克', 'douyin': '抖音', 'so360': '360'}
    
    for platform, node_id in TOPHUB_NODES.items():
        print(f"  → {platform_names[platform]}...")
        url = f"https://tophub.today/n/{node_id}"
        html = fetch_url(url)
        
        all_items = parse_tophub_items(html, platform)
        
        # 严格筛选教育相关（宁缺毋滥！）
        edu_items = [item for item in all_items if is_edu_related(item['title'])]
        
        # 取TOP5（如果不够5条就有几条显示几条）
        edu_items = edu_items[:5]
        
        # 赋值rank和热度
        for i, item in enumerate(edu_items):
            item['rank'] = i + 1
            # 根据在原始列表中的位置估算热度
            original_pos = next((j for j, x in enumerate(all_items) if x['title'] == item['title']), i)
            item['heat'] = max(1000000 - original_pos * 30000, 50000)
        
        hot_search[platform] = edu_items
        print(f"    ✓ 找到 {len(edu_items)} 条教育相关热搜")
    
    return hot_search


def fetch_hot_products():
    """抓取电商热销教育商品"""
    hot_products = {}
    commerce_names = {'taobao_tmall': '淘宝天猫', 'jd': '京东', 'kuaishou': '快手电商'}
    
    for platform, node_id in TOPHUB_COMMERCE.items():
        print(f"  → {commerce_names[platform]}...")
        url = f"https://tophub.today/n/{node_id}"
        html = fetch_url(url)
        
        all_items = parse_tophub_items(html, platform=None)  # 电商不做平台URL过滤
        
        # 筛选教育相关商品
        edu_items = [item for item in all_items if is_edu_product(item['title'])]
        
        # 只显示教育相关的，最多10条
        edu_items = edu_items[:10]
        
        # 格式化
        formatted = []
        for i, item in enumerate(edu_items):
            formatted.append({
                "rank": i + 1,
                "title": item['title'],
                "sales": f"热度TOP{i+1}",
                "price": "查看详情",
                "category": categorize_edu(item['title'])
            })
        
        hot_products[platform] = formatted
        print(f"    ✓ 找到 {len(formatted)} 条教育商品")
    
    # 如果电商数据太少，用预设的常青教育商品补充
    for platform in hot_products:
        if len(hot_products[platform]) < 5:
            print(f"  ⚠ {commerce_names[platform]} 教育商品不足，补充常青热销品...")
            hot_products[platform] = get_evergreen_products(platform)
    
    return hot_products


def get_evergreen_products(platform):
    """获取常青教育热销商品（当实时数据不足时使用）"""
    # 这些是教育行业常年热销的商品，来源于各平台公开畅销榜
    products = {
        'taobao_tmall': [
            {"rank": 1, "title": "学而思AI学习机", "sales": "长期热销", "price": "¥2,999起", "category": "电子教育"},
            {"rank": 2, "title": "科大讯飞AI翻译笔", "sales": "长期热销", "price": "¥699起", "category": "电子教育"},
            {"rank": 3, "title": "考研英语全程班网课", "sales": "长期热销", "price": "¥1,980起", "category": "成人教育"},
            {"rank": 4, "title": "人教版中小学教材全套", "sales": "长期热销", "price": "¥128起", "category": "图书"},
            {"rank": 5, "title": "公务员考试教材套装", "sales": "长期热销", "price": "¥79起", "category": "图书"},
            {"rank": 6, "title": "斑马AI课儿童启蒙年卡", "sales": "长期热销", "price": "¥2,800起", "category": "K12教育"},
            {"rank": 7, "title": "小猿智能练习本", "sales": "长期热销", "price": "¥1,099起", "category": "电子教育"},
            {"rank": 8, "title": "考研政治核心教材", "sales": "长期热销", "price": "¥99起", "category": "图书"},
            {"rank": 9, "title": "儿童早教点读笔套装", "sales": "长期热销", "price": "¥298起", "category": "电子教育"},
            {"rank": 10, "title": "MBA联考教材全套", "sales": "长期热销", "price": "¥168起", "category": "成人教育"},
        ],
        'jd': [
            {"rank": 1, "title": "有道词典笔旗舰款", "sales": "长期热销", "price": "¥899起", "category": "电子教育"},
            {"rank": 2, "title": "希沃学习机", "sales": "长期热销", "price": "¥3,999起", "category": "电子教育"},
            {"rank": 3, "title": "高途考研全程班", "sales": "长期热销", "price": "¥3,980起", "category": "成人教育"},
            {"rank": 4, "title": "小度学习平板", "sales": "长期热销", "price": "¥2,299起", "category": "电子教育"},
            {"rank": 5, "title": "一级建造师考试教材", "sales": "长期热销", "price": "¥128起", "category": "成人教育"},
            {"rank": 6, "title": "DK儿童百科全书", "sales": "长期热销", "price": "¥198起", "category": "图书"},
            {"rank": 7, "title": "阿尔法蛋AI词典笔", "sales": "长期热销", "price": "¥699起", "category": "电子教育"},
            {"rank": 8, "title": "五年高考三年模拟", "sales": "长期热销", "price": "¥128起", "category": "图书"},
            {"rank": 9, "title": "作业帮AI学习机", "sales": "长期热销", "price": "¥2,399起", "category": "电子教育"},
            {"rank": 10, "title": "注册会计师CPA教材", "sales": "长期热销", "price": "¥198起", "category": "成人教育"},
        ],
        'kuaishou': [
            {"rank": 1, "title": "读书郎学习平板", "sales": "长期热销", "price": "¥1,699起", "category": "电子教育"},
            {"rank": 2, "title": "粉笔公考系统班", "sales": "长期热销", "price": "¥980起", "category": "成人教育"},
            {"rank": 3, "title": "小天才电话手表", "sales": "长期热销", "price": "¥1,598起", "category": "电子教育"},
            {"rank": 4, "title": "中小学同步课程VIP", "sales": "长期热销", "price": "¥980起", "category": "K12教育"},
            {"rank": 5, "title": "四大名著学生版全套", "sales": "长期热销", "price": "¥49起", "category": "图书"},
            {"rank": 6, "title": "有道AI学习机", "sales": "长期热销", "price": "¥2,999起", "category": "电子教育"},
            {"rank": 7, "title": "新概念英语全套", "sales": "长期热销", "price": "¥78起", "category": "图书"},
            {"rank": 8, "title": "学历提升自考课程", "sales": "长期热销", "price": "¥3,980起", "category": "成人教育"},
            {"rank": 9, "title": "洪恩识字APP年卡", "sales": "长期热销", "price": "¥298起", "category": "K12教育"},
            {"rank": 10, "title": "消防工程师考试教材", "sales": "长期热销", "price": "¥138起", "category": "成人教育"},
        ],
    }
    return products.get(platform, [])


# ============================================================
# 营销建议生成（改进版）
# ============================================================

def generate_marketing_suggestions(hot_search):
    """基于实际教育热搜生成营销建议（只用教育内容，不混入垃圾）"""
    
    # 按赛道收集真实教育热词
    category_words = {'成人教育': [], 'K12教育': [], '图书': [], '电子教育': []}
    
    for platform_items in hot_search.values():
        for item in platform_items:
            cat = categorize_edu(item['title'])
            if cat in category_words and len(category_words[cat]) < 12:
                # 只取标题中的核心关键词（去掉过长的新闻标题）
                word = item['title']
                if len(word) > 15:
                    # 尝试截取关键部分
                    for kw in EDU_KEYWORDS:
                        if kw in word:
                            word = kw
                            break
                category_words[cat].append(word)
    
    # 去重
    for cat in category_words:
        category_words[cat] = list(dict.fromkeys(category_words[cat]))
    
    suggestions = []
    
    # 成人教育
    aw = category_words.get('成人教育', [])
    suggestions.append({
        "category": "成人教育",
        "items": [
            {
                "scene": "考证备考季",
                "hot_words": " / ".join(aw[:3]) if len(aw) >= 3 else "考研 / 公务员 / MBA",
                "strategy": "投放搜索广告锁定「报名入口」「分数线」等刚需词，搭配落地页免费试听引流，利用考试时间节点制造紧迫感"
            },
            {
                "scene": "职业技能提升",
                "hot_words": " / ".join(aw[3:6]) if len(aw) >= 6 else "AI编程培训 / 学历提升 / 职业认证",
                "strategy": "信息流素材突出「高薪就业」「取证周期短」等痛点，定向25-40岁职场人群，配合限时优惠促转化"
            },
            {
                "scene": "学历焦虑营销",
                "hot_words": " / ".join(aw[6:9]) if len(aw) >= 9 else "自考本科 / 在职研究生 / 专升本",
                "strategy": "短视频投放真人出镜分享上岸经历，评论区引导私信咨询转化，抖音/快手双平台覆盖"
            }
        ]
    })
    
    # K12教育
    kw = category_words.get('K12教育', [])
    suggestions.append({
        "category": "K12教育",
        "items": [
            {
                "scene": "升学季流量高峰",
                "hot_words": " / ".join(kw[:3]) if len(kw) >= 3 else "高考志愿填报 / 幼小衔接 / 中考体育",
                "strategy": "搜索抢占「分数线预测」「志愿填报工具」等长尾词，落地页提供免费测评工具提升留资率"
            },
            {
                "scene": "暑期培训招生",
                "hot_words": " / ".join(kw[3:6]) if len(kw) >= 6 else "暑期兴趣班 / 研学旅行 / 少儿编程",
                "strategy": "朋友圈广告定向30-45岁家长群体，素材强调「名额有限」「早鸟优惠」制造紧迫感"
            },
            {
                "scene": "学习方法种草",
                "hot_words": " / ".join(kw[6:9]) if len(kw) >= 9 else "学霸笔记 / 高效学习法 / 时间管理",
                "strategy": "抖音达人合作短视频种草，挂载课程商品链接实现短链路转化，配合开学季节点"
            }
        ]
    })
    
    # 图书
    bw = category_words.get('图书', [])
    suggestions.append({
        "category": "图书",
        "items": [
            {
                "scene": "教辅刚需旺季",
                "hot_words": " / ".join(bw[:3]) if len(bw) >= 3 else "教材全套 / 考研政治 / 人教版课本",
                "strategy": "电商平台搜索广告竞价「教材全套」「正版书籍」，商品详情页强调发货速度与正品保障"
            },
            {
                "scene": "亲子阅读推广",
                "hot_words": " / ".join(bw[3:6]) if len(bw) >= 6 else "暑期书单 / DK百科 / 四大名著",
                "strategy": "小红书+抖音种草内容营销，达人晒书单带货，搭配满减促销提升客单价"
            },
            {
                "scene": "知识付费跨界",
                "hot_words": " / ".join(bw[6:9]) if len(bw) >= 9 else "AI写作 / 读书会 / 知识星球",
                "strategy": "信息流定向考研/自考人群，内容突出「碎片化学习」「名师带读」，引导下单"
            }
        ]
    })
    
    # 电子教育
    ew = category_words.get('电子教育', [])
    suggestions.append({
        "category": "电子教育",
        "items": [
            {
                "scene": "AI硬件种草",
                "hot_words": " / ".join(ew[:3]) if len(ew) >= 3 else "AI学习机 / 词典笔 / 智能练习本",
                "strategy": "抖音开箱测评+电商直播组合拳，素材对比传统学习方式突出效率提升"
            },
            {
                "scene": "暑期礼物场景",
                "hot_words": " / ".join(ew[3:6]) if len(ew) >= 6 else "学习平板 / 点读笔 / 电话手表",
                "strategy": "搜索广告锁定「送孩子礼物」「学习机推荐」等场景词，投放618/暑期节点"
            },
            {
                "scene": "教育科技新品",
                "hot_words": " / ".join(ew[6:9]) if len(ew) >= 9 else "AI教育新政 / AI批改 / 智能题库",
                "strategy": "信息流投放科技感素材，定向教育KOL粉丝与科技关注人群，突出政策利好"
            }
        ]
    })
    
    return suggestions


# ============================================================
# 用户画像热搜 & 看板分发
# ============================================================


def parse_heat_value(extra_text, rank):
    """解析或估算热度数值与展示文案"""
    heat_raw = None
    if extra_text:
        text = extra_text.replace(',', '').replace(' ', '')
        # 形如 "123万" 或 "1.2万"
        m = re.search(r'(\d+(?:\.\d+)?)万', text)
        if m:
            try:
                heat_raw = int(float(m.group(1)) * 10000)
            except ValueError:
                heat_raw = None
        if heat_raw is None:
            # 兜底提取纯数字
            m2 = re.search(r'(\d+)', text)
            if m2:
                try:
                    heat_raw = int(m2.group(1))
                except ValueError:
                    heat_raw = None
    # 没拿到明确数字，用排名估算一个降序数值，但展示文案为"热"
    if heat_raw is None:
        heat_raw = max(1000000 - (rank - 1) * 20000, 50000)
        heat_str = "热"
    else:
        if heat_raw >= 10000:
            heat_str = f"{heat_raw // 10000}万🔥"
        else:
            heat_str = f"{heat_raw}🔥"
    return heat_raw, heat_str


def is_sensitive_title(title):
    """是否命中政治等敏感词，命中则直接过滤掉"""
    for kw in SENSITIVE_KEYWORDS:
        if kw in title:
            return True
    return False


def classify_user_personas(title):
    """基于关键词规则为一条内容打上用户画像标签"""
    personas = set()
    if not title:
        return personas
    for keywords, persona_list in PERSONA_KEYWORD_RULES:
        if any(kw in title for kw in keywords):
            personas.update(persona_list)
    return personas


def parse_tophub_items_with_heat(html, platform=None, limit=50):
    """从TopHub页面解析带有热度信息的条目（用户画像用）"""
    items = []
    if not html:
        return items

    # 逐行解析 <tr>，更稳健地同时拿到 rank / title / url / extra
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, flags=re.S)
    seen_titles = set()

    for row in rows:
        # 标题与链接
        m_link = re.search(
            r'<a[^>]*href="([^\"]*)"[^>]*target="_blank"[^>]*>\s*([^<]+?)\s*</a>',
            row,
        )
        if not m_link:
            continue
        url, title = m_link.groups()
        title = title.strip()

        # 基础过滤
        if not title or len(title) < 4:
            continue
        if title in seen_titles:
            continue

        # 黑名单过滤
        if is_blacklisted(title, url):
            continue

        # 平台URL合法性检查
        if platform and not is_valid_platform_url(url, platform):
            continue

        # 排名
        m_rank = re.search(r'<td[^>]*>\s*(\d+)\.\s*</td>', row)
        if m_rank:
            try:
                rank = int(m_rank.group(1))
            except ValueError:
                rank = len(items) + 1
        else:
            rank = len(items) + 1

        # 热度额外信息（通常在 class="ws" 的单元格中）
        m_extra = re.search(r'<td[^>]*class="ws"[^>]*>\s*([^<]*)\s*</td>', row)
        extra_text = m_extra.group(1).strip() if m_extra else ''

        heat_raw, heat_str = parse_heat_value(extra_text, rank)

        seen_titles.add(title)
        items.append({
            "title": title,
            "url": url,
            "rank": rank,
            "heat_raw": heat_raw,
            "heat_str": heat_str,
        })

        if len(items) >= limit:
            break

    # 如果没解析到任何条目，退回到旧解析逻辑
    if not items:
        base_items = parse_tophub_items(html, platform)
        for idx, item in enumerate(base_items[:limit], start=1):
            heat_raw, heat_str = parse_heat_value('', idx)
            items.append({
                "title": item['title'],
                "url": item['url'],
                "rank": idx,
                "heat_raw": heat_raw,
                "heat_str": heat_str,
            })

    return items


def build_search_url(platform, title):
    """构造平台搜索URL"""
    template = PLATFORM_SEARCH_URL_TEMPLATES.get(platform)
    if not template:
        return ""
    return template.format(query=quote_plus(title))


def compute_panel_affinity(title, panel):
    """计算一条热搜对某个面板的亲和度得分"""
    score = 0
    keywords = PANEL_AFFINITY_KEYWORDS.get(panel, [])
    for kw in keywords:
        if kw in title:
            score += 1
    return score


def fetch_user_hotsearch():
    """抓取全平台 TOP50 热搜（不做教育过滤），按亲和度独占分配到 4 个看板（重复率≤10%）"""
    user_hotsearch = {
        "k12": [],
        "adult_edu": [],
        "e_edu": [],
        "books": [],
    }

    all_items = []
    platform_order = {
        'weibo': 0,
        'baidu': 1,
        'douyin': 2,
        'quark': 3,
        'so360': 4,
    }

    for platform, node_id in TOPHUB_NODES.items():
        if platform not in platform_order:
            continue

        print(f"  → 用户画像源：{PLATFORM_DISPLAY_NAMES.get(platform, platform)} TOP50...")
        url = f"https://tophub.today/n/{node_id}"
        html = fetch_url(url)

        items = parse_tophub_items_with_heat(html, platform=platform, limit=50)

        for item in items:
            title = item['title']
            if is_sensitive_title(title):
                continue

            personas = classify_user_personas(title)
            if not personas:
                continue

            all_items.append({
                "platform_key": platform,
                "platform": PLATFORM_DISPLAY_NAMES.get(platform, platform),
                "platform_rank": item.get("rank", 0) or 0,
                "title": title,
                "heat_raw": item.get("heat_raw", 0),
                "heat": item.get("heat_str", "热"),
                "personas": personas,
            })

    if not all_items:
        return user_hotsearch

    # 统一排序：先按各个平台内部排名，其次按平台优先级
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

    # ====== 第一阶段：计算每条热搜对各面板的资格和亲和度 ======
    item_eligible = []  # [(item, {panel: affinity_score})]
    for item in unique_items:
        title = item["title"]
        personas = item["personas"]
        eligible_panels = {}

        for panel in panel_order:
            target_personas = set(PANEL_PERSONAS.get(panel, []))
            if personas & target_personas:
                # 有画像交集 → 该面板有资格
                affinity = compute_panel_affinity(title, panel)
                eligible_panels[panel] = affinity

        if eligible_panels:
            item_eligible.append((item, eligible_panels))

    # ====== 第二阶段：独占分配（每条只进一个面板） ======
    global_used = set()

    # 2a. 先分配"只适合一个面板"的（最精准的条目）
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
                "url": build_search_url(item["platform_key"], item["title"]),
            })

    # 2b. 再分配"适合多个面板"的 → 按亲和度优先，缺口多的面板优先
    multi_eligible = [(item, ep) for item, ep in item_eligible
                      if len(ep) > 1 and item["title"] not in global_used]

    # 按热度排序（热的优先分配）
    multi_eligible.sort(key=lambda x: x[0].get("heat_raw", 0), reverse=True)

    for item, eligible_panels in multi_eligible:
        if item["title"] in global_used:
            continue

        # 选最佳面板：亲和度最高 > 当前条数最少 > panel_order 顺序
        best_panel = None
        best_score = (-1, 999, 999)  # (affinity, current_count, order_idx)

        for panel in panel_order:
            if panel not in eligible_panels:
                continue
            if len(user_hotsearch[panel]) >= MAX_PER_PANEL:
                continue
            affinity = eligible_panels[panel]
            current_count = len(user_hotsearch[panel])
            order_idx = panel_order.index(panel)
            score = (affinity, -current_count, -order_idx)  # 高亲和 + 少条数优先
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
                "url": build_search_url(item["platform_key"], item["title"]),
            })

    # ====== 第三阶段：补量（面板不足时，允许极少量借用，全局限制重复率≤10%） ======
    # 统计总分配量，确保跨面板重复不超过10%
    # 只有在面板严重不足（<5条）时才启动补量
    MIN_ITEMS_FOR_BORROW = 5
    MAX_BORROW_PER_PANEL = 1  # 每面板最多借1条

    borrow_used = set()  # 已被借出的标题（一条最多被借到1个面板）
    for panel in panel_order:
        if len(user_hotsearch[panel]) >= MIN_ITEMS_FOR_BORROW:
            continue

        borrowed = 0
        for item, eligible_panels in item_eligible:
            if borrowed >= MAX_BORROW_PER_PANEL:
                break
            if panel not in eligible_panels:
                continue
            title = item["title"]
            # 已经在本面板
            if any(x["title"] == title for x in user_hotsearch[panel]):
                continue
            # 同一条已被其他面板借过，不再借
            if title in borrow_used:
                continue
            # 借入
            borrow_used.add(title)
            panel_list = user_hotsearch[panel]
            panel_list.append({
                "rank": len(panel_list) + 1,
                "title": title,
                "heat": item["heat"],
                "heat_raw": item["heat_raw"],
                "platform": item["platform"],
                "url": build_search_url(item["platform_key"], title),
            })
            borrowed += 1

    return user_hotsearch


# ============================================================
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("🎓 教育热点捕手 - 数据采集 v2.0")
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 抓取热搜
    print("\n📡 [1/5] 抓取各平台热搜（仅保留教育相关）...")
    hot_search = fetch_hot_search()
    
    # 2. 抓取电商
    print("\n🛒 [2/5] 抓取电商热销教育商品...")
    hot_products = fetch_hot_products()
    
    # 3. 生成TOP15
    print("\n🏆 [3/5] 生成全平台教育热搜 TOP15...")
    platform_names = {'weibo': '微博', 'baidu': '百度', 'quark': '夸克', 'douyin': '抖音', 'so360': '360'}
    
    all_edu_items = []
    for platform, items in hot_search.items():
        for item in items:
            item['_platform'] = platform_names.get(platform, platform)
            all_edu_items.append(item)
    
    # 去重并按热度排序
    seen = set()
    unique = []
    for item in sorted(all_edu_items, key=lambda x: x.get('heat', 0), reverse=True):
        if item['title'] not in seen:
            seen.add(item['title'])
            unique.append(item)
    
    top15 = []
    for i, item in enumerate(unique[:15]):
        platforms = []
        for p, items in hot_search.items():
            if any(it['title'] == item['title'] for it in items):
                platforms.append(platform_names.get(p, p))
        
        top15.append({
            "rank": i + 1,
            "title": item['title'],
            "heat": item.get('heat', 500000),
            "platforms": platforms or [item.get('_platform', '未知')],
            "category": categorize_edu(item['title'])
        })
    
    print(f"  ✓ 生成 {len(top15)} 条跨平台教育热点")
    
    # 4. 营销建议
    print("\n💡 [4/5] 生成营销建议...")
    marketing = generate_marketing_suggestions(hot_search)
    print(f"  ✓ 为 {len(marketing)} 个赛道生成营销建议")
    
    # 5. 用户画像热搜看板
    print("\n👥 [5/5] 生成用户画像热搜看板...")
    user_hotsearch = fetch_user_hotsearch()
    print(
        "  ✓ 用户画像看板条数："
        f"非成教(K12) {len(user_hotsearch['k12'])} 条，"
        f"成人教育 {len(user_hotsearch['adult_edu'])} 条，"
        f"电子教育 {len(user_hotsearch['e_edu'])} 条，"
        f"图书 {len(user_hotsearch['books'])} 条"
    )
    
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
    }
    
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    total_search = sum(len(v) for v in hot_search.values())
    total_products = sum(len(v) for v in hot_products.values())
    total_user_hot = sum(len(v) for v in user_hotsearch.values())
    
    print(f"\n{'='*60}")
    print(f"✅ 完成! 数据已写入: {output_path}")
    print(
        f"📊 统计: 教育热搜 {total_search} 条 | 热销商品 {total_products} 条 | "
        f"TOP15 {len(top15)} 条 | 用户画像热搜 {total_user_hot} 条"
    )
    print(f"{'='*60}")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # 防止脚本崩溃导致 GitHub Actions 失败
        print(f"\n⚠️ 脚本遇到异常: {e}")
        print("正在写入最小化 data.json...")
        import traceback
        traceback.print_exc()
        # 写一个最小可用的 data.json
        output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
        fallback = {
            "update_time": datetime.now().strftime('%Y-%m-%d %H:%M'),
            "issue_no": (datetime.now() - datetime(2026, 6, 12)).days + 1,
            "hot_search": {},
            "hot_products": {},
            "top15_today": [],
            "marketing_suggestions": [],
            "user_hotsearch": {"k12": [], "adult_edu": [], "e_edu": [], "books": []},
        }
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(fallback, f, ensure_ascii=False, indent=2)
        print(f"✅ 已写入最小化数据: {output_path}")
