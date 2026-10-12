# -*- coding: utf-8 -*-
"""CH32V203F8U6 -- QFN20 3x3 mm, same package geometry as CH32V002F4U6 /
CH32V003F4U6 (the datasheet gives the same "QFN20 3*3mm 0.4mm 15.7mil" land), so
this script reuses the CH32V002F4U6 generator (repo-internal cross-folder
reference is allowed) and overrides:

  identity      -> part id / title / chip / schematic label / top mark / tags / desc
  pin table     -> CH32V203F8U6's own 20 pins + exposed pad (pin 0 = VSS)
  epad name     -> "VSS"   (datasheet 表3-1-1 pin-0 row reads `0 / VSS`;
                            AGENTS §5: 命名尊重原厂 + 裸焊盘独立成网、不进总线)

Datasheet: D:\\Downloads\\CH32V203数据手册.pdf (V2.8), 2026-10-12 查证：
  · 表2-1 (p.4)     : F8 = 20 脚 / 64K flash / 20K SRAM / 17 GPIO / 2×USART / 1×I2C ✓
  · 模 3.1 (p.15-16): CH32V203F8U6 pin arrangement (pin 1..20 + pin 0 = GND label)
  · 表3-1-1 (p.17-20): pin definition —— pin 0 = VSS；PB10/PB11 = I2C2_SCL/SDA；
                       PA9/PA10 = USART1_TX/RX；PA2/PA3 = USART2_TX/RX；
                       PA13/SWD + PA14/SWC = SWD；BOOT0 内部接 GND、**无 NRST 引脚**
  · 表5-1 (p.49)    : QFN20 = 3*3 mm, 0.4 mm pitch, 15.7 mil

★ 本元件对**本项目的意义**（写清楚，免得以后猜）：载板要用它当主控 ⇒
  · 安全元件 ATECC608B 必须挂在 **I2C2 (PB10/PB11)**，不是台架上的 I2C1 (PB6/PB7)；
  · 没有 NRST / BOOT0 引脚 ⇒ 烧录只能 SWD，"下载后按 RST" 改成断电复位。
"""

import importlib.util
import os
import re
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.normpath(os.path.join(HERE, "..", "CH32V002F4U6"))
FZPZ_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "fzpz"))

PART_ID = "CH32V203F8U6"
TITLE = "CH32V203F8U6"
CHIP = "CH32V203"
SCHEM_NAME = "CH32V203"
TOP_MARK = "V203"
TAGS = "<tag>IC</tag><tag>MCU</tag><tag>RISC-V</tag><tag>CH32V203</tag>"
DESC = ("WCH CH32V203F8U6 RISC-V MCU, QFN20 3x3 mm / 0.4 mm pitch, 3.3 V, "
        "64K flash / 20K SRAM, 17 I/O, 2x USART (PA9/PA10, PA2/PA3), "
        "I2C2 on PB10/PB11, 9+2 ch 12-bit ADC. No NRST / BOOT0 pin "
        "(BOOT0 is tied to GND internally) - SWD only, reset by power cycle. "
        "Exposed pad = pin 0 / VSS - route to GND.")

# 20 pins, datasheet order (pin 1..20 go counter-clockwise, same as the
# generator's geometry): left top->bottom, bottom left->right,
# right bottom->top, top right->left.  Alternates we depend on are kept.
PIN_NAMES = ["PA0/WKUP", "PA1/ADC1", "PA2/USART2_TX", "PA3/USART2_RX", "PA4/ADC4",
             "PA5/ADC5", "PA7/ADC7", "PB0/ADC8", "PB1/ADC9", "PB10/I2C2_SCL",
             "PB11/I2C2_SDA", "PB14", "PB15", "PA8",
             "PA9/USART1_TX", "PA13/SWD", "PA14/SWC", "PA10/USART1_RX",
             "VDD", "PA6/ADC6"]
PIN_DESC = {
    "PA0/WKUP": "PA0 (WKUP, ADC0)",
    "PA1/ADC1": "PA1 (ADC1)",
    "PA2/USART2_TX": "PA2 - USART2_TX (module data port on the carrier)",
    "PA3/USART2_RX": "PA3 - USART2_RX",
    "PA4/ADC4": "PA4 (ADC4)", "PA5/ADC5": "PA5 (ADC5)",
    "PA6/ADC6": "PA6 (ADC6)", "PA7/ADC7": "PA7 (ADC7)",
    "PA8": "PA8", "PA9/USART1_TX": "PA9 - USART1_TX (console on the carrier)",
    "PA10/USART1_RX": "PA10 - USART1_RX (console)",
    "PA13/SWD": "PA13 - SWDIO (debug/flash)",
    "PA14/SWC": "PA14 - SWCLK (debug/flash)",
    "PB0/ADC8": "PB0 (ADC8)", "PB1/ADC9": "PB1 (ADC9)",
    "PB10/I2C2_SCL": "PB10 - I2C2_SCL (ATECC608B on the carrier)",
    "PB11/I2C2_SDA": "PB11 - I2C2_SDA (ATECC608B)",
    "PB14": "PB14", "PB15": "PB15",
    "VDD": "supply 3.3 V",
}
PAD_NAME = "VSS"        # 表3-1-1 pin-0 行 = `0 / VSS`（原厂口径；独立成网、不进总线）
GND_PINS = []           # 本封装除 VSS 焊盘外没有其它地脚 ⇒ 不建总线


def main():
    spec = importlib.util.spec_from_file_location(
        "ch32v002f4u6_gen", os.path.join(BASE_DIR, "gen_part.py"))
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    # geometry / package stay as-is (same land pattern)
    g.OUT_DIR = HERE
    g.PART_ID = PART_ID
    g.TITLE = TITLE
    g.TOP_MARK = TOP_MARK
    g.CHIP = CHIP
    g.SCHEM_NAME = SCHEM_NAME
    g.PIN_NAMES = PIN_NAMES
    g.PIN_DESC = PIN_DESC
    g.PAD_NAME = PAD_NAME
    g.GND_PINS = GND_PINS
    files = {
        "svg.icon.%s_icon.svg" % PART_ID: g.icon_svg(),
        "svg.breadboard.%s_breadboard.svg" % PART_ID: g.breadboard_svg(),
        "svg.schematic.%s_schematic.svg" % PART_ID: g.schematic_svg(),
        "svg.pcb.%s_pcb.svg" % PART_ID: g.pcb_svg(),
        "part.%s.fzp" % PART_ID: g.fzp_xml(),
    }
    out = {}
    for fn, text in files.items():
        text = text.replace("CH32V002F4U6", PART_ID).replace("CH32V002", CHIP)
        if fn.endswith(".fzp"):
            # only the MODULE description (right after </properties>)
            text = re.sub(r"(</properties>\s*)<description>.*?</description>",
                          lambda m: m.group(1) + "<description>%s</description>" % DESC,
                          text, count=1, flags=re.S)
            text = re.sub(r"<tags>.*?</tags>", "<tags>%s</tags>" % TAGS, text, flags=re.S)
        out[fn] = text
    for fn, text in out.items():
        with open(os.path.join(HERE, fn), "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        print("wrote %-46s %6d bytes" % (fn, len(text.encode("utf-8"))))
    os.makedirs(FZPZ_DIR, exist_ok=True)
    dst = os.path.join(FZPZ_DIR, PART_ID + ".fzpz")
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
        for fn in sorted(out):
            z.write(os.path.join(HERE, fn), fn)
    print("wrote %s  (%d bytes)" % (dst, os.path.getsize(dst)))


if __name__ == "__main__":
    main()
