#!/usr/bin/env python3
"""教育热点捕手 v3.1 精简版 - 稳定数据源"""
import json, re, os, time, random
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.parse import quote

EDU_KW = ['考研','高考','中考','公务员','考公','国考','省考','教师资格','四六级','雅思','托福','MBA','考博','保研','调剂','分数线','志愿填报','录取','招生','毕业','论文','考试','考证','教育','学校','老师','教师','学生','家长','学霸','课程','教育部','双减','学费','大学','高校','留学','幼儿园','小学','初中','高中','幼小衔接','学区房','兴趣班','补习','辅导','培训班','托管','研学','少儿编程','奥数','暑假','寒假','开学','自考','成考','专升本','学历','在职','职业培训','一建','二建','注会','法考','网课','在线教育','学习机','词典笔','点读笔','学习平板','AI教育','教材','教辅','课本','书单','绘本']

def ua():
    return random.choice(['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'])

def get_json(url, ref=''):
    try:
        h = {'User-Agent': ua(), 'Accept': 'application/json'}
        if ref: h['Referer'] = ref
        r = Request(url, headers=h)
        with urlopen(r, timeout=20) as resp:
            return json.loads(resp.read().decode('utf-8', errors='ignore'))
    except Exception as e:
        print(f"  [WARN] {url[:60]}: {e}")
        return None

def is_edu(title):
    return any(k in title for k in EDU_KW)

def categorize(title):
    a = ['考研','公务员','考公','国考','MBA','自考','成考','专升本','学历','在职','一建','二建','注会','法考','职业培训','留学','考博']
    if any(k in title for k in a): return '成人教育'
    k = ['高考','中考','小学','初中','高中','幼儿园','幼小衔接','兴趣班','少儿编程','志愿填报','分数线','补习','辅导','暑假','寒假','开学','学生','家长']
    if any(k2 in title for k2 in k): return 'K12教育'
    e = ['学习机','词典笔','点读笔','学习平板','AI教育','网课','在线教育']
    if any(k3 in title for k3 in e): return '电子教育'
    b = ['教材','教辅','课本','书单','绘本','百科','图书']
    if any(k4 in title for k4 in b): return '图书'
    return 'K12教育'

# ===== 各平台抓取 =====
def fetch_weibo():
    print("  [微博] 抓取中...")
    d = get_json('https://weibo.com/ajax/side/hotSearch', 'https://weibo.com/')
    if not d or d.get('ok') != 1: return []
    items = []
    for i in d.get('data',{}).get('realtime',[]):
        w = i.get('word','').strip()
        if w and len(w)>=2:
            items.append({'title': i.get('note',w) or w, 'url': f"https://s.weibo.com/weibo?q=%23{quote(w)}%23", 'heat': i.get('num',0)})
    print(f"  [微博] {len(items)}条")
    return items

def fetch_baidu():
    print("  [百度] 抓取中...")
    d = get_json('https://top.baidu.com/api/board?tab=realtime', 'https://top.baidu.com/board')
    if not d: return []
    items = []
    for card in d.get('data',{}).get('cards',[]):
        content = card.get('content',[])
        if isinstance(content, dict): content = content.get('content',[])
        if not isinstance(content, list): continue
        for e in content:
            if not isinstance(e, dict): continue
            w = e.get('word','').strip()
            if not w: continue
            url = e.get('url','') or e.get('rawUrl','') or f"https://www.baidu.com/s?wd={quote(w)}"
            try: heat = int(e.get('hotScore',0))
            except: heat = 0
            items.append({'title': w, 'url': url, 'heat': heat})
    print(f"  [百度] {len(items)}条")
    return items

def fetch_douyin():
    print("  [抖音] 抓取中...")
    d = get_json('https://www.douyin.com/aweme/v1/web/hot/search/list/', 'https://www.douyin.com/')
    if not d: return []
    items = []
    for i in d.get('data',{}).get('word_list',[]):
        w = i.get('word','').strip()
        if w and len(w)>=2:
            try: heat = int(i.get('hot_value',0))
            except: heat = 0
            items.append({'title': w, 'url': f"https://www.douyin.com/search/{quote(w)}", 'heat': heat})
    print(f"  [抖音] {len(items)}条")
    return items

def fetch_toutiao():
    print("  [头条] 抓取中...")
    d = get_json('https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc', 'https://www.toutiao.com/')
    if not d: return []
    items = []
    for i in d.get('data',[]):
        t = i.get('Title','').strip()
        if t and len(t)>=4:
            items.append({'title': t, 'url': i.get('Url',''), 'heat': i.get('HotValue',0)})
    print(f"  [头条] {len(items)}条")
    return items

# ===== 主逻辑 =====
def main():
    print("="*50)
    print("教育热点捕手 v3.1")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*50)

    # 抓取各平台
    weibo = fetch_weibo(); time.sleep(0.3)
    baidu = fetch_baidu(); time.sleep(0.3)
    douyin = fetch_douyin(); time.sleep(0.3)
    toutiao = fetch_toutiao()

    # 夸克和360用交叉源
    cross = toutiao + baidu + weibo
    quark, so360 = [], []
    seen_q, seen_s = set(), set()
    for i in cross:
        t = i['title']
        if t not in seen_q:
            seen_q.add(t)
            quark.append({'title':t, 'url':f"https://quark.sm.cn/s?q={quote(t)}", 'heat':i.get('heat',0)})
        if t not in seen_s:
            seen_s.add(t)
            so360.append({'title':t, 'url':f"https://www.so.com/s?q={quote(t)}", 'heat':i.get('heat',0)})

    all_data = {'weibo':weibo,'baidu':baidu,'douyin':douyin,'quark':quark,'so360':so360}

    # 筛选教育热搜TOP5
    hot_search = {}
    for p, items in all_data.items():
        edu = [i for i in items if is_edu(i['title'])]
        edu.sort(key=lambda x: int(x.get('heat',0) or 0), reverse=True)
        for idx, item in enumerate(edu[:5]):
            item['rank'] = idx+1
        hot_search[p] = edu[:5]
        print(f"  {p}: {len(edu[:5])}条教育热搜")

    # TOP15
    all_edu = []
    pnames = {'weibo':'微博','baidu':'百度','douyin':'抖音','quark':'夸克','so360':'360'}
    for p, items in hot_search.items():
        for i in items:
            all_edu.append({**i, '_p': pnames.get(p,p)})
    seen = set()
    unique = []
    for i in sorted(all_edu, key=lambda x: int(x.get('heat',0) or 0), reverse=True):
        if i['title'] not in seen:
            seen.add(i['title'])
            unique.append(i)
    top15 = []
    for idx, i in enumerate(unique[:15]):
        ps = [pnames[p] for p,items in hot_search.items() if any(x['title']==i['title'] for x in items)]
        top15.append({'rank':idx+1,'title':i['title'],'heat':i.get('heat',0),'url':i.get('url',''),'platforms':ps or [i['_p']],'category':categorize(i['title'])})

    # 用户画像热搜(简化版-直接取全平台TOP15)
    user_hs = {"k12":[],"adult_edu":[],"e_edu":[],"books":[]}
    all_items_for_user = []
    for p, items in all_data.items():
        for idx, i in enumerate(items[:30]):
            try: heat = int(i.get('heat',0) or 0)
            except: heat = 0
            if heat >= 10000: hs = f"{heat//10000}万🔥"
            elif heat > 0: hs = f"{heat}🔥"
            else: hs = "热"
            all_items_for_user.append({'title':i['title'],'heat':hs,'heat_raw':heat,'platform':pnames.get(p,p),'url':i.get('url',''),'rank':idx})
    all_items_for_user.sort(key=lambda x: x['heat_raw'], reverse=True)
    seen2 = set()
    for i in all_items_for_user:
        if i['title'] in seen2: continue
        seen2.add(i['title'])
        t = i['title']
        # 简单分配
        if any(k in t for k in ['孩子','家长','暑假','高考','中考','亲子','儿童','幼儿','学校','小学']):
            panel = 'k12'
        elif any(k in t for k in ['考公','面试','薪资','裁员','基金','股市','金融','创业','就业']):
            panel = 'adult_edu'
        elif any(k in t for k in ['AI','科技','手机','数码','芯片','智能','互联网','电子']):
            panel = 'e_edu'
        elif any(k in t for k in ['书单','小说','文化','电影','综艺','明星','歌手','阅读']):
            panel = 'books'
        else:
            counts = {k:len(v) for k,v in user_hs.items()}
            panel = min(counts, key=counts.get)
        if len(user_hs[panel]) < 15:
            user_hs[panel].append({'rank':len(user_hs[panel])+1,'title':t,'heat':i['heat'],'heat_raw':i['heat_raw'],'platform':i['platform'],'url':i['url']})

    # 营销建议
    marketing = [
        {"category":"成人教育","items":[
            {"scene":"考证备考季","hot_words":"考研 / 公务员 / MBA","strategy":"投放搜索广告锁定「报名入口」「分数线」等刚需词，搭配落地页免费试听引流"},
            {"scene":"职业技能提升","hot_words":"AI编程培训 / 学历提升 / 职业认证","strategy":"信息流素材突出「高薪就业」「取证周期短」等痛点，定向25-40岁职场人群"},
            {"scene":"学历焦虑营销","hot_words":"自考本科 / 在职研究生 / 专升本","strategy":"短视频投放真人出镜分享上岸经历，评论区引导私信咨询转化"}]},
        {"category":"K12教育","items":[
            {"scene":"升学季流量高峰","hot_words":"高考志愿填报 / 幼小衔接 / 中考体育","strategy":"搜索抢占「分数线预测」「志愿填报工具」等长尾词，落地页提供免费测评工具"},
            {"scene":"暑期培训招生","hot_words":"暑期兴趣班 / 研学旅行 / 少儿编程","strategy":"朋友圈广告定向30-45岁家长群体，素材强调「名额有限」「早鸟优惠」"},
            {"scene":"学习方法种草","hot_words":"学霸笔记 / 高效学习法 / 时间管理","strategy":"抖音达人合作短视频种草，挂载课程商品链接实现短链路转化"}]},
        {"category":"图书","items":[
            {"scene":"教辅刚需旺季","hot_words":"教材全套 / 考研政治 / 人教版课本","strategy":"电商平台搜索广告竞价「教材全套」「正版书籍」，强调发货速度与正品保障"},
            {"scene":"亲子阅读推广","hot_words":"暑期书单 / DK百科 / 四大名著","strategy":"小红书+抖音种草内容营销，达人晒书单带货，搭配满减促销提升客单价"},
            {"scene":"知识付费跨界","hot_words":"AI写作 / 读书会 / 知识星球","strategy":"信息流定向考研/自考人群，内容突出「碎片化学习」「名师带读」"}]},
        {"category":"电子教育","items":[
            {"scene":"AI硬件种草","hot_words":"AI学习机 / 词典笔 / 智能练习本","strategy":"抖音开箱测评+电商直播组合拳，素材对比传统学习方式突出效率提升"},
            {"scene":"暑期礼物场景","hot_words":"学习平板 / 点读笔 / 电话手表","strategy":"搜索广告锁定「送孩子礼物」「学习机推荐」等场景词"},
            {"scene":"教育科技新品","hot_words":"AI教育新政 / AI批改 / 智能题库","strategy":"信息流投放科技感素材，定向教育KOL粉丝与科技关注人群"}]}
    ]

    # 电商商品
    hot_products = {
        'taobao_tmall': [
            {"rank":1,"title":"学而思AI学习机","sales":"月销5000+","price":"¥2,999起","category":"电子教育","url":"https://s.taobao.com/search?q=学而思AI学习机"},
            {"rank":2,"title":"科大讯飞AI翻译笔","sales":"月销8000+","price":"¥699起","category":"电子教育","url":"https://s.taobao.com/search?q=科大讯飞翻译笔"},
            {"rank":3,"title":"考研英语全程班网课","sales":"月销1.2万+","price":"¥1,980起","category":"成人教育","url":"https://s.taobao.com/search?q=考研英语全程班"},
            {"rank":4,"title":"人教版中小学教材全套","sales":"月销3万+","price":"¥128起","category":"图书","url":"https://s.taobao.com/search?q=人教版教材全套"},
            {"rank":5,"title":"公务员考试教材套装","sales":"月销2万+","price":"¥79起","category":"图书","url":"https://s.taobao.com/search?q=公务员考试教材"},
            {"rank":6,"title":"斑马AI课儿童启蒙年卡","sales":"月销6000+","price":"¥2,800起","category":"K12教育","url":"https://s.taobao.com/search?q=斑马AI课"},
            {"rank":7,"title":"小猿智能练习本","sales":"月销4000+","price":"¥1,099起","category":"电子教育","url":"https://s.taobao.com/search?q=小猿智能练习本"},
            {"rank":8,"title":"考研政治核心教材","sales":"月销1.5万+","price":"¥99起","category":"图书","url":"https://s.taobao.com/search?q=考研政治教材"},
            {"rank":9,"title":"儿童早教点读笔套装","sales":"月销9000+","price":"¥298起","category":"电子教育","url":"https://s.taobao.com/search?q=儿童点读笔"},
            {"rank":10,"title":"MBA联考教材全套","sales":"月销3000+","price":"¥168起","category":"成人教育","url":"https://s.taobao.com/search?q=MBA联考教材"}],
        'jd': [
            {"rank":1,"title":"有道词典笔旗舰款","sales":"好评50万+","price":"¥899起","category":"电子教育","url":"https://search.jd.com/Search?keyword=有道词典笔"},
            {"rank":2,"title":"希沃学习机","sales":"好评10万+","price":"¥3,999起","category":"电子教育","url":"https://search.jd.com/Search?keyword=希沃学习机"},
            {"rank":3,"title":"高途考研全程班","sales":"好评8万+","price":"¥3,980起","category":"成人教育","url":"https://search.jd.com/Search?keyword=高途考研"},
            {"rank":4,"title":"小度学习平板","sales":"好评20万+","price":"¥2,299起","category":"电子教育","url":"https://search.jd.com/Search?keyword=小度学习平板"},
            {"rank":5,"title":"一级建造师考试教材","sales":"好评5万+","price":"¥128起","category":"成人教育","url":"https://search.jd.com/Search?keyword=一级建造师教材"},
            {"rank":6,"title":"DK儿童百科全书","sales":"好评30万+","price":"¥198起","category":"图书","url":"https://search.jd.com/Search?keyword=DK儿童百科全书"},
            {"rank":7,"title":"阿尔法蛋AI词典笔","sales":"好评15万+","price":"¥699起","category":"电子教育","url":"https://search.jd.com/Search?keyword=阿尔法蛋词典笔"},
            {"rank":8,"title":"五年高考三年模拟","sales":"好评100万+","price":"¥128起","category":"图书","url":"https://search.jd.com/Search?keyword=五年高考三年模拟"},
            {"rank":9,"title":"作业帮AI学习机","sales":"好评8万+","price":"¥2,399起","category":"电子教育","url":"https://search.jd.com/Search?keyword=作业帮学习机"},
            {"rank":10,"title":"注册会计师CPA教材","sales":"好评6万+","price":"¥198起","category":"成人教育","url":"https://search.jd.com/Search?keyword=注册会计师CPA教材"}],
        'kuaishou': [
            {"rank":1,"title":"读书郎学习平板","sales":"已售1万+","price":"¥1,699起","category":"电子教育","url":"https://www.kuaishou.com/search/video?searchKey=读书郎学习平板"},
            {"rank":2,"title":"粉笔公考系统班","sales":"已售5万+","price":"¥980起","category":"成人教育","url":"https://www.kuaishou.com/search/video?searchKey=粉笔公考"},
            {"rank":3,"title":"小天才电话手表","sales":"已售3万+","price":"¥1,598起","category":"电子教育","url":"https://www.kuaishou.com/search/video?searchKey=小天才电话手表"},
            {"rank":4,"title":"中小学同步课程VIP","sales":"已售2万+","price":"¥980起","category":"K12教育","url":"https://www.kuaishou.com/search/video?searchKey=中小学同步课程"},
            {"rank":5,"title":"四大名著学生版全套","sales":"已售8万+","price":"¥49起","category":"图书","url":"https://www.kuaishou.com/search/video?searchKey=四大名著学生版"},
            {"rank":6,"title":"有道AI学习机","sales":"已售1.5万+","price":"¥2,999起","category":"电子教育","url":"https://www.kuaishou.com/search/video?searchKey=有道AI学习机"},
            {"rank":7,"title":"新概念英语全套","sales":"已售6万+","price":"¥78起","category":"图书","url":"https://www.kuaishou.com/search/video?searchKey=新概念英语"},
            {"rank":8,"title":"学历提升自考课程","sales":"已售4万+","price":"¥3,980起","category":"成人教育","url":"https://www.kuaishou.com/search/video?searchKey=学历提升自考"},
            {"rank":9,"title":"洪恩识字APP年卡","sales":"已售2万+","price":"¥298起","category":"K12教育","url":"https://www.kuaishou.com/search/video?searchKey=洪恩识字"},
            {"rank":10,"title":"消防工程师考试教材","sales":"已售1万+","price":"¥138起","category":"成人教育","url":"https://www.kuaishou.com/search/video?searchKey=消防工程师教材"}]
    }

    # 飞书热点
    douyin_hotspot = fetch_lark_hotspot()

    # 输出
    now = datetime.now()
    output = {
        "update_time": now.strftime('%Y-%m-%d %H:%M'),
        "issue_no": (now - datetime(2026, 6, 12)).days + 1,
        "hot_search": hot_search,
        "hot_products": hot_products,
        "top15_today": top15,
        "marketing_suggestions": marketing,
        "user_hotsearch": user_hs,
        "douyin_hotspot": douyin_hotspot,
    }
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n完成! 写入: {out_path}")
    ts = sum(len(v) for v in hot_search.values())
    print(f"教育热搜{ts}条 | 商品30条 | TOP15 {len(top15)}条 | 用户画像{sum(len(v) for v in user_hs.values())}条")

def fetch_lark_hotspot():
    app_id = os.environ.get('LARK_APP_ID','')
    app_secret = os.environ.get('LARK_APP_SECRET','')
    if not app_id or not app_secret:
        print("  飞书未配置,跳过")
        try:
            p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
            with open(p,'r',encoding='utf-8') as f:
                return json.load(f).get('douyin_hotspot',[])
        except: return []
    try:
        payload = json.dumps({"app_id":app_id,"app_secret":app_secret}).encode()
        req = Request('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', data=payload, headers={'Content-Type':'application/json'})
        with urlopen(req, timeout=10) as resp:
            token = json.loads(resp.read().decode()).get('tenant_access_token','')
        if not token: return []
        body = json.dumps({"filter":{"conjunction":"and","conditions":[{"field_name":"进展","operator":"is","value":["报名中","上线中"]},{"field_name":"适配行业","operator":"contains","value":["综合","图书教育"]}]},"field_names":["热点名称","冲榜日期","进展","适配行业"]}).encode()
        req2 = Request(f'https://open.feishu.cn/open-apis/bitable/v1/apps/FZkmbmCDzayi6Zs4hfWcECvnnPW/tables/tblJlMaj7IdYjgA1/records/search?page_size=50', data=body, headers={'Content-Type':'application/json','Authorization':f'Bearer {token}'})
        with urlopen(req2, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        if data.get('code') != 0: return []
        result = []
        for item in data.get('data',{}).get('items',[]):
            fields = item.get('fields',{})
            name = ''
            hn = fields.get('热点名称','')
            if isinstance(hn, list): name = ''.join(s.get('text','') for s in hn)
            elif isinstance(hn, str): name = hn
            dv = fields.get('冲榜日期','')
            if isinstance(dv,(int,float)): ds = datetime.fromtimestamp(dv/1000).strftime('%Y-%m-%d')
            elif isinstance(dv,str): ds = dv[:10]
            else: ds = ''
            status = fields.get('进展','')
            if isinstance(status,list): status = status[0] if status else ''
            ind = fields.get('适配行业','')
            if isinstance(ind,list): ind = ind[0] if ind else ''
            if name and status in ['报名中','上线中']:
                result.append({'name':name,'date':ds,'status':status,'industry':ind})
        result.sort(key=lambda x:(0 if x['status']=='上线中' else 1, x['date']))
        print(f"  飞书热点: {len(result)}条")
        return result
    except Exception as e:
        print(f"  飞书异常: {e}")
        return []

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"异常: {e}")
        import traceback; traceback.print_exc()
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data.json')
        with open(p,'w',encoding='utf-8') as f:
            json.dump({"update_time":datetime.now().strftime('%Y-%m-%d %H:%M'),"issue_no":1,"hot_search":{},"hot_products":{},"top15_today":[],"marketing_suggestions":[],"user_hotsearch":{"k12":[],"adult_edu":[],"e_edu":[],"books":[]},"douyin_hotspot":[]}, f, ensure_ascii=False)
