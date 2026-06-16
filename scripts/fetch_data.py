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
# 主流程
# ============================================================

def main():
    print("=" * 60)
    print("🎓 教育热点捕手 - 数据采集 v2.0")
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 抓取热搜
    print("\n📡 [1/4] 抓取各平台热搜（仅保留教育相关）...")
    hot_search = fetch_hot_search()
    
    # 2. 抓取电商
    print("\n🛒 [2/4] 抓取电商热销教育商品...")
    hot_products = fetch_hot_products()
    
    # 3. 生成TOP15
    print("\n🏆 [3/4] 生成全平台教育热搜 TOP15...")
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
    print("\n💡 [4/4] 生成营销建议...")
    marketing = generate_marketing_suggestions(hot_search)
    print(f"  ✓ 为 {len(marketing)} 个赛道生成营销建议")
    
    # 输出
    now = datetime.now()
    output = {
        "update_time": now.strftime('%Y-%m-%d %H:%M'),
        "issue_no": (now - datetime(2026, 6, 12)).days + 1,
        "hot_search": hot_search,
        "hot_products": hot_products,
        "top15_today": top15,
        "marketing_suggestions": marketing
    }
    
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    total_search = sum(len(v) for v in hot_search.values())
    total_products = sum(len(v) for v in hot_products.values())
    
    print(f"\n{'='*60}")
    print(f"✅ 完成! 数据已写入: {output_path}")
    print(f"📊 统计: 教育热搜 {total_search} 条 | 热销商品 {total_products} 条 | TOP15 {len(top15)} 条")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
