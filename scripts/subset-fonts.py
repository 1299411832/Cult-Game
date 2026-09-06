#!/usr/bin/env python3
"""把 Ma Shan Zheng 与 Noto Serif SC 子集化并转成 woff2，供本地自托管。

字集来源：项目内所有 .ts/.tsx/.html/.json 的实际用字 + 拉丁/数字/标点 +
一份人名与修仙题材常用字补充集。玩家输入的道号若用到生僻字，会由 CSS
字体栈回退到系统衬线体，不影响可用性。

用法：python scripts/subset-fonts.py
"""

import pathlib
import re
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
FONTS = ROOT / "src" / "assets" / "fonts"
CACHE = ROOT / ".font-cache"

# jsdelivr 对超过 20MB 的文件返回 403，Noto Serif SC 走 GitHub raw
SOURCES = {
    "MaShanZheng": "https://cdn.jsdelivr.net/gh/google/fonts@main/ofl/mashanzheng/MaShanZheng-Regular.ttf",
    "NotoSerifSC": "https://raw.githubusercontent.com/notofonts/noto-cjk/main/Serif/Variable/TTF/Subset/NotoSerifSC-VF.ttf",
}

# 首屏必须立刻可见的文案用字，单独出一个极小的关键子集做 preload，
# 完整子集后台异步加载，避免 1MB 书法体阻塞 LCP
CRITICAL_CHARS = (
    "修仙模拟器天道渺渺仙途漫漫踏入仙途道号出身今日天命先天道体修仙志"
    "抉择属性修炼乾坤袋剧情线修为寿元回合根骨悟性气运因果心魔灵石"
    "坊市小憩灵机缘命道"
    "CultivationSimulator"
    "0123456789"
    "，。、：·—「」《》"
)

# 人名与修仙题材常用字补充：玩家道号是自由输入，项目文本覆盖不到的部分靠这里兜底
EXTRA_CHARS = (
    "赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜"
    "戚谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳酆鲍史唐"
    "费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄"
    "和穆萧尹姚邵湛汪祁毛禹狄米贝明臧计伏成戴谈宋茅庞熊纪舒屈项祝董梁"
    "杜阮蓝闵席季麻强贾路娄危江童颜郭梅盛林刁钟徐邱骆高夏蔡田樊胡凌霍"
    "虞万支柯昝管卢莫经房裘缪干解应宗丁宣贲邓郁单杭洪包诸左石崔吉钮龚"
    "程嵇邢滑裴陆荣翁荀羊於惠甄曲家封芮羿储靳汲邴糜松井段富巫乌焦巴弓"
    "牧隗山谷车侯宓蓬全郗班仰秋仲伊宫宁仇栾暴甘钭厉戎祖武符刘景詹束龙"
    "叶幸司韶郜黎蓟薄印宿白怀蒲邰从鄂索咸籍赖卓蔺屠蒙池乔阴鬱胥能苍双"
    "闻莘党翟谭贡劳逄姬申扶堵冉宰郦雍卻璩桑桂濮牛寿通边扈燕冀郏浦尚农"
    "温别庄晏柴瞿阎充慕连茹习宦艾鱼容向古易慎戈廖庾终暨居衡步都耿满弘"
    "匡国文寇广禄阙东欧殳沃利蔚越夔隆师巩厍聂晁勾敖融冷訾辛阚那简饶空"
    "曾毋沙乜养鞠须丰巢关蒯相查后荆红游竺权逯盖益桓公"
    "修仙道缘灵气丹田元婴化神渡劫飞升天尊真人上仙魔妖鬼怪剑诀法宝符箓"
    "乾坤阴阳五行金木水火土风雷冰霜云雾霞星月日辰宿张翼轸角亢氐房心尾箕"
    "青龙白虎朱雀玄武麒麟凤凰饕餮梼杌混沌穷奇"
    "一二三四五六七八九十百千万亿零壹贰叁肆伍陆柒捌玖拾佰仟"
    "清静虚无太极大极无极混元鸿蒙紫府丹鼎洞天福地瀛洲蓬莱方丈昆仑蜀山"
    "青云太虚玄天九幽黄泉碧落幽冥轮回涅槃般若菩提"
    "甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥"
    "春夏秋冬雨雪风霜露霜霞雳霹震霁"
)


def collect_project_chars() -> set:
    chars = set()
    exts = {".ts", ".tsx", ".html", ".json"}
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in exts:
            continue
        skip = {"node_modules", "dist", ".git", ".font-cache", ".workbuddy"}
        if skip & set(path.parts):
            continue
        try:
            chars.update(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, OSError):
            continue
    return chars


def collect_title_chars() -> set:
    """Ma Shan Zheng 只渲染标题，不需要背负事件正文那两千多字。

    这里抓 data/ 下所有 title / name 字段，再并上固定 UI 文案与人名兜底集。
    玩家道号是自由输入，用到子集外的字会回退到衬线体，不影响可用性。
    """
    chars = set()
    pat = re.compile(r"(?:title|name)\s*:\s*['\"`]([^'\"`\n]+)['\"`]")
    data_dir = ROOT / "src" / "data"
    for path in data_dir.rglob("*.ts"):
        try:
            chars.update(pat.findall(path.read_text(encoding="utf-8")))
        except (UnicodeDecodeError, OSError):
            continue
    return {c for c in "".join(chars) if c.isprintable()}


def build_charset() -> str:
    chars = collect_project_chars()
    chars.update(EXTRA_CHARS)
    # 拉丁、数字、常用标点、全角符号、竖排与装饰符号
    chars.update(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        " !\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
        "，。、；：？！「」『』（）《》〈〉【】〔〕～·—…"
        "　"
        "°×÷±≈≠≤≥∞§¶©®™"
        "─━│┃┄┅┈┉┌┐└┘├┤┬┴┼"
        "■□▲△▼▽◆◇○●★☆"
    )
    return "".join(sorted(c for c in chars if c.isprintable() and c not in "\n\r\t"))


CHUNK = 4 * 1024 * 1024
HEADERS = {"User-Agent": "Mozilla/5.0"}


def _fetch(url: str, start: int | None = None, end: int | None = None) -> bytes:
    headers = dict(HEADERS)
    if start is not None:
        headers["Range"] = f"bytes={start}-{end}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def download(name: str, url: str) -> pathlib.Path:
    """分块下载大字体文件，每块独立重试，避免单次长连接被中途掐断。"""
    CACHE.mkdir(exist_ok=True)
    dest = CACHE / f"{name}.ttf"
    if dest.exists() and dest.stat().st_size > 100_000:
        print(f"  {name}: 使用缓存 {dest.stat().st_size / 1048576:.1f} MB")
        return dest

    req = urllib.request.Request(url, headers=HEADERS, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as resp:
        total = int(resp.headers["Content-Length"])
    print(f"  {name}: 下载 {total / 1048576:.1f} MB（分块）")

    parts = []
    for start in range(0, total, CHUNK):
        end = min(start + CHUNK - 1, total - 1)
        for attempt in range(5):
            try:
                parts.append(_fetch(url, start, end))
                break
            except Exception as err:
                if attempt == 4:
                    raise
                print(f"    块 {start // CHUNK} 第 {attempt + 1} 次失败（{type(err).__name__}），重试")
    dest.write_bytes(b"".join(parts))
    return dest


def subset(src: pathlib.Path, charset: str, out: pathlib.Path) -> None:
    subsetter = [
        sys.executable, "-m", "fontTools.subset", str(src),
        f"--text={charset}",
        "--flavor=woff2",
        f"--output-file={out}",
        "--layout-features=*",
        "--drop-tables+=DSIG",
        "--no-hinting",
    ]
    subprocess.run(subsetter, check=True, capture_output=True)


def emit(name: str, src: pathlib.Path, charset: str, suffix: str) -> None:
    out = FONTS / f"{name}{suffix}.woff2"
    try:
        subset(src, charset, out)
    except subprocess.CalledProcessError as err:
        print(f"  子集化失败：{err.stderr.decode('utf-8', 'replace')[-800:]}")
        return
    print(f"  -> {out.name}  {out.stat().st_size / 1024:.0f} KB")


def main() -> None:
    body_charset = build_charset()
    print(f"正文（Noto Serif SC）字集：{len(body_charset)} 字符")

    title_chars = collect_title_chars() | set(CRITICAL_CHARS) | set(EXTRA_CHARS)
    title_charset = "".join(sorted(title_chars))
    print(f"标题（Ma Shan Zheng）字集：{len(title_charset)} 字符")

    FONTS.mkdir(parents=True, exist_ok=True)
    for name, url in SOURCES.items():
        print(f"[{name}]")
        src = download(name, url)
        if name == "MaShanZheng":
            emit(name, src, title_charset, ".subset")
            emit(name, src, "".join(sorted(set(CRITICAL_CHARS))), ".critical")
        else:
            emit(name, src, body_charset, ".subset")


if __name__ == "__main__":
    main()
