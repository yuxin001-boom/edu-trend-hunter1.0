#!/usr/bin/env python3
"""
教育热点捕手 - 数据采集脚本
从 TopHub.today 等公开聚合源抓取教育行业相关热搜 & 电商热销数据
每天由 GitHub Actions 自动执行
"""

import json
import re
import os
import sys
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError

# ============================================================
# 配置：教育行业关键词（用于从全网热搜中筛选教育相关内容）
# ============================================================
EDU_KEYWORDS = [
    # 考试升学
    '考研', '高考', '中考', '公务员', '考公', '国考', '省考', '教师资格',
    '四六级', '雅思', '托福', 'GRE', 'MBA', '考博', '保研', '调剂',
    '分数线', '志愿填报', '录取', '招生', '入学', '毕业', '论文',
    # K12
    '幼儿园', '小学', '初中', '高中', '幼小衔接', '学区房', '课后服务',
    '兴趣班', '补习', '辅导', '培训', '家教', '托管', '研学',
    '少儿编程', '奥数', '作文', '英语学习',
    # 成人教育
    '自考', '成考', '专升本', '学历', '在职', '继续教育', '职业培训',
    '技能培训', '一建', '二建', '注会', 'CPA', '消防工程师', '法考',
    # 在线教育/电子教育
    '网课', '在线教育', '直播课', '学习机', '词典笔', '点读笔',
    '学习平板', 'AI教育', 'AI学习', '智能学习', '教育科技',
    # 图书
    '教材', '教辅', '课本', '书单', '阅读', '图书', '绘本', '百科',
    # 通用教育
    '教育', '学校', '老师', '学生', '家长', '学霸', '学习',
    '知识', '课程', '培训班', '教育部', '双减',
]

# TopHub.today 的各平台节点ID
TOPHUB_NODES = {
    'weibo': 'KqndgxeLl9',      # 微博热搜
    'baidu': 'Jb0vmloB1G',      # 百度热搜
    'quark': 'n6YoVqDeZa',      # 夸克热搜 (UC/夸克)
    'douyin': 'K7GdaMgdQy',     # 抖音热搜
    'so360': 'KMZd7x6erO',      # 360热搜
}

# 电商平台节点
TOPHUB_COMMERCE = {
    'taobao_tmall': 'GOxJBpOArl',  # 淘宝/天猫热销
    'jd': 'Q1Vd5Eo85R',            # 京东热销
    'kuaishou': 'oMGNml765R',       # 快手电商 (热门商品)
}

# ============================================================
# 数据抓取函数
# ============================================================

def fetch_url(url, timeout=15):
    """通用URL抓取"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    try:
        req = Request(url, headers=headers)
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"  [WARN] 抓取失败 {url}: {e}")
        return None


def parse_tophub_page(html):
    """
    从 TopHub.today 页面HTML中提取热搜条目
    返回: [{"title": "xxx", "heat": 12345, "url": "xxx"}, ...]
    """
    items = []
    if not html:
        return items
    
    # TopHub 的条目格式: <a href="url" target="_blank">title</a> ... <span class="s">热度数字</span>
    # 使用正则匹配
    pattern = r'<a[^>]*href="([^"]*)"[^>]*target="_blank"[^>]*>([^<]+)</a>'
    heat_pattern = r'<td[^>]*class="al"[^>]*>.*?<a[^>]*>([^<]+)</a>.*?<td[^>]*>(\d[\d.]*万?)</td>'
    
    # 简化版：匹配标题和链接
    matches = re.findall(pattern, html)
    
    for i, (url, title) in enumerate(matches):
        title = title.strip()
        if not title or len(title) < 2:
            continue
        # 过滤掉导航链接等
        if title in ['今日热榜', '全部', '历史', 'TopHub']:
            continue
        
        items.append({
            "title": title,
            "url": url,
            "heat": max(1000000 - i * 50000, 10000),  # 估算热度（按排名递减）
        })
    
    return items[:50]  # 最多取50条


def fetch_tophub_data(node_id):
    """从TopHub获取指定节点的热搜数据"""
    url = f"https://tophub.today/n/{node_id}"
    print(f"  抓取: {url}")
    html = fetch_url(url)
    return parse_tophub_page(html)


def is_edu_related(title):
    """判断一条热搜是否与教育行业相关"""
    title_lower = title.lower()
    for kw in EDU_KEYWORDS:
        if kw in title_lower:
            return True
    return False


def categorize_edu(title):
    """将教育内容分类到四大赛道"""
    title_lower = title.lower()
    
    # 成人教育关键词
    adult_kws = ['考研', '公务员', '考公', '国考', 'MBA', '自考', '成考', '专升本',
                 '学历', '在职', '一建', '二建', '注会', 'CPA', '法考', '消防工程师',
                 '职业培训', '技能培训', '继续教育']
    for kw in adult_kws:
        if kw in title_lower:
            return '成人教育'
    
    # K12关键词
    k12_kws = ['高考', '中考', '小学', '初中', '高中', '幼小衔接', '幼儿园',
               '兴趣班', '少儿编程', '奥数', '研学', '家长', '课后服务',
               '志愿填报', '分数线', '学霸', '补习', '辅导', '托管']
    for kw in k12_kws:
        if kw in title_lower:
            return 'K12教育'
    
    # 电子教育关键词
    elearn_kws = ['学习机', '词典笔', '点读笔', '学习平板', 'AI教育', 'AI学习',
                  '智能学习', '教育科技', '网课', '在线教育', '直播课']
    for kw in elearn_kws:
        if kw in title_lower:
            return '电子教育'
    
    # 图书关键词
    book_kws = ['教材', '教辅', '课本', '书单', '阅读', '图书', '绘本', '百科']
    for kw in book_kws:
        if kw in title_lower:
            return '图书'
    
    # 默认
    return 'K12教育'


# ============================================================
# 营销建议生成（基于关键词匹配规则）
# ============================================================

def generate_marketing_suggestions(hot_searches, hot_products):
    """根据当日热搜和热销数据，自动生成营销建议"""
    
    # 统计各赛道的热词
    category_words = {'成人教育': [], 'K12教育': [], '图书': [], '电子教育': []}
    
    for platform_data in hot_searches.values():
        for item in platform_data:
            cat = categorize_edu(item['title'])
            if cat in category_words:
                category_words[cat].append(item['title'])
    
    for platform_data in hot_products.values():
        for item in platform_data:
            cat = item.get('category', '电子教育')
            if cat in category_words:
                category_words[cat].append(item['title'])
    
    # 基于模板生成建议
    suggestions = []
    
    # 成人教育
    adult_words = category_words.get('成人教育', [])[:9]
    suggestions.append({
        "category": "成人教育",
        "items": [
            {
                "scene": "考证备考季",
                "hot_words": " / ".join(adult_words[:3]) if adult_words else "考研 / 公务员 / MBA",
                "strategy": "投放搜索广告锁定「报名入口」「分数线」等刚需词，搭配落地页免费试听引流，利用考试时间节点制造紧迫感"
            },
            {
                "scene": "职业技能提升",
                "hot_words": " / ".join(adult_words[3:6]) if len(adult_words) > 3 else "AI编程培训 / 学历提升 / 职业认证",
                "strategy": "信息流素材突出「高薪就业」「取证周期短」等痛点，定向25-40岁职场人群，配合限时优惠促转化"
            },
            {
                "scene": "学历焦虑营销",
                "hot_words": " / ".join(adult_words[6:9]) if len(adult_words) > 6 else "自考本科 / 在职研究生 / 专升本",
                "strategy": "短视频投放真人出镜分享上岸经历，评论区引导私信咨询转化，抖音/快手双平台覆盖"
            }
        ]
    })
    
    # K12教育
    k12_words = category_words.get('K12教育', [])[:9]
    suggestions.append({
        "category": "K12教育",
        "items": [
            {
                "scene": "升学季流量高峰",
                "hot_words": " / ".join(k12_words[:3]) if k12_words else "高考志愿 / 幼小衔接 / 中考",
                "strategy": "搜索抢占「分数线预测」「志愿填报工具」等长尾词，落地页提供免费测评工具提升留资率"
            },
            {
                "scene": "暑期培训招生",
                "hot_words": " / ".join(k12_words[3:6]) if len(k12_words) > 3 else "暑期兴趣班 / 研学旅行 / 少儿编程",
                "strategy": "朋友圈广告定向30-45岁家长群体，素材强调「名额有限」「早鸟优惠」制造紧迫感"
            },
            {
                "scene": "学习方法种草",
                "hot_words": " / ".join(k12_words[6:9]) if len(k12_words) > 6 else "学霸笔记 / 高效学习法 / 时间管理",
                "strategy": "抖音达人合作短视频种草，挂载课程商品链接实现短链路转化，配合开学季节点"
            }
        ]
    })
    
    # 图书
    book_words = category_words.get('图书', [])[:9]
    suggestions.append({
        "category": "图书",
        "items": [
            {
                "scene": "教辅刚需旺季",
                "hot_words": " / ".join(book_words[:3]) if book_words else "五三全套 / 考研政治 / 人教版课本",
                "strategy": "电商平台搜索广告竞价「教材全套」「正版书籍」，商品详情页强调发货速度与正品保障"
            },
            {
                "scene": "亲子阅读推广",
                "hot_words": " / ".join(book_words[3:6]) if len(book_words) > 3 else "暑期书单 / DK百科 / 四大名著",
                "strategy": "小红书+抖音种草内容营销，达人晒书单带货，搭配满减促销提升客单价"
            },
            {
                "scene": "知识付费跨界",
                "hot_words": " / ".join(book_words[6:9]) if len(book_words) > 6 else "AI写作 / 读书会 / 知识星球",
                "strategy": "信息流定向考研/自考人群，内容突出「碎片化学习」「名师带读」，引导下单"
            }
        ]
    })
    
    # 电子教育
    elearn_words = category_words.get('电子教育', [])[:9]
    suggestions.append({
        "category": "电子教育",
        "items": [
            {
                "scene": "AI硬件种草",
                "hot_words": " / ".join(elearn_words[:3]) if elearn_words else "AI学习机 / 词典笔 / 智能练习本",
                "strategy": "抖音开箱测评+电商直播组合拳，素材对比传统学习方式突出效率提升200%"
            },
            {
                "scene": "暑期礼物场景",
                "hot_words": " / ".join(elearn_words[3:6]) if len(elearn_words) > 3 else "学习平板 / 点读笔 / 电话手表",
                "strategy": "搜索广告锁定「送孩子礼物」「学习机推荐」等场景词，投放618/暑期节点"
            },
            {
                "scene": "教育科技新品",
                "hot_words": " / ".join(elearn_words[6:9]) if len(elearn_words) > 6 else "AI教育新政 / AI批改 / 智能题库",
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
    print("🎓 教育热点捕手 - 数据采集")
    print(f"⏰ 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 抓取热搜数据
    print("\n📡 [1/4] 抓取各平台热搜...")
    hot_search = {}
    platform_names = {'weibo': '微博', 'baidu': '百度', 'quark': '夸克', 'douyin': '抖音', 'so360': '360'}
    
    for platform, node_id in TOPHUB_NODES.items():
        print(f"  → {platform_names.get(platform, platform)}...")
        all_items = fetch_tophub_data(node_id)
        
        # 筛选教育相关
        edu_items = [item for item in all_items if is_edu_related(item['title'])]
        
        # 如果教育相关不足5条，放宽条件取前5
        if len(edu_items) < 5:
            # 保留已筛选的 + 补充排名靠前的
            remaining = [item for item in all_items if item not in edu_items]
            edu_items = edu_items + remaining[:5 - len(edu_items)]
        
        # 取TOP5
        edu_items = edu_items[:5]
        
        # 添加rank
        for i, item in enumerate(edu_items):
            item['rank'] = i + 1
            item['heat'] = item.get('heat', 1000000 - i * 100000)
        
        hot_search[platform] = edu_items
        print(f"    ✓ 获取 {len(edu_items)} 条教育相关热搜")
    
    # 2. 抓取电商热销数据
    print("\n🛒 [2/4] 抓取电商热销数据...")
    hot_products = {}
    commerce_names = {'taobao_tmall': '淘宝天猫', 'jd': '京东', 'kuaishou': '快手电商'}
    
    for platform, node_id in TOPHUB_COMMERCE.items():
        print(f"  → {commerce_names.get(platform, platform)}...")
        all_items = fetch_tophub_data(node_id)
        
        # 筛选教育相关商品
        edu_items = [item for item in all_items if is_edu_related(item['title'])]
        
        if len(edu_items) < 10:
            remaining = [item for item in all_items if item not in edu_items]
            edu_items = edu_items + remaining[:10 - len(edu_items)]
        
        edu_items = edu_items[:10]
        
        # 格式化为商品格式
        formatted = []
        for i, item in enumerate(edu_items):
            formatted.append({
                "rank": i + 1,
                "title": item['title'],
                "sales": f"热度{item.get('heat', 10000) // 10000}万+",
                "price": "查看详情",
                "category": categorize_edu(item['title'])
            })
        
        hot_products[platform] = formatted
        print(f"    ✓ 获取 {len(formatted)} 条教育商品")
    
    # 3. 生成全平台TOP15
    print("\n🏆 [3/4] 生成全平台 TOP15...")
    all_edu_items = []
    for platform, items in hot_search.items():
        for item in items:
            item['source_platform'] = platform_names.get(platform, platform)
            all_edu_items.append(item)
    
    # 去重（按标题）
    seen_titles = set()
    unique_items = []
    for item in sorted(all_edu_items, key=lambda x: x.get('heat', 0), reverse=True):
        if item['title'] not in seen_titles:
            seen_titles.add(item['title'])
            unique_items.append(item)
    
    # TOP15
    top15 = []
    for i, item in enumerate(unique_items[:15]):
        # 找出该条目出现在哪些平台
        platforms = []
        for platform, items in hot_search.items():
            for it in items:
                if it['title'] == item['title']:
                    platforms.append(platform_names.get(platform, platform))
        
        top15.append({
            "rank": i + 1,
            "title": item['title'],
            "heat": item.get('heat', 500000),
            "platforms": platforms if platforms else [item.get('source_platform', '未知')],
            "category": categorize_edu(item['title'])
        })
    
    print(f"  ✓ 生成 {len(top15)} 条跨平台热点")
    
    # 4. 生成营销建议
    print("\n💡 [4/4] 生成营销建议...")
    marketing = generate_marketing_suggestions(hot_search, hot_products)
    print(f"  ✓ 为 {len(marketing)} 个赛道生成营销建议")
    
    # 5. 组装输出
    now = datetime.now()
    output = {
        "update_time": now.strftime('%Y-%m-%d %H:%M'),
        "issue_no": (now - datetime(2026, 6, 12)).days + 1,
        "hot_search": hot_search,
        "hot_products": hot_products,
        "top15_today": top15,
        "marketing_suggestions": marketing
    }
    
    # 写入 data.json
    output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 数据已写入: {output_path}")
    print(f"📊 本次采集统计:")
    print(f"   - 热搜平台: {len(hot_search)} 个")
    print(f"   - 电商平台: {len(hot_products)} 个")
    print(f"   - 教育热搜: {sum(len(v) for v in hot_search.values())} 条")
    print(f"   - 热销商品: {sum(len(v) for v in hot_products.values())} 条")
    print(f"   - TOP15: {len(top15)} 条")
    print(f"   - 营销建议: {sum(len(c['items']) for c in marketing)} 条")
    print("=" * 60)


if __name__ == '__main__':
    main()
