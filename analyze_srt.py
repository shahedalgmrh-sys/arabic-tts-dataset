# -*- coding: utf-8 -*-
"""تحليل جودة ملفات SRT في مجلد معين.

يفحص كل ملف .srt ويستخرج: عدد الترجمات، المدة الكلية، متوسط المدة،
التداخلات، الفجوات، سرعة الكلام (كلمة/حرف في الثانية)، الترجمات
القصيرة/الطويلة جداً، والكتل الفاسدة التي فشل تحليلها.
"""
import os
import re
import sys
from datetime import datetime, timedelta

SHORT_SEC = 1.0   # ترجمة أقصر من ثانية
LONG_SEC = 7.0    # ترجمة أطول من 7 ثوان


def parse_time(time_str):
    return datetime.strptime(time_str.strip().replace(',', '.'), '%H:%M:%S.%f')


def read_text(file_path):
    """قراءة الملف مع دعم BOM وتجربة ترميزات بديلة."""
    for enc in ('utf-8-sig', 'utf-8', 'cp1256'):
        try:
            with open(file_path, 'r', encoding=enc) as f:
                return f.read(), enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise UnicodeDecodeError(f'فشل فك ترميز الملف: {file_path}')


def analyze_srt(file_path):
    content, encoding = read_text(file_path)

    blocks = re.split(r'\n\n+', content.strip())
    subtitles = []
    bad_blocks = 0

    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 2 and ' --> ' in lines[1]:
            try:
                start_str, end_str = lines[1].split(' --> ')
                start = parse_time(start_str)
                end = parse_time(end_str)
                text = ' '.join(lines[2:])
                subtitles.append({'start': start, 'end': end, 'text': text})
            except Exception as e:
                bad_blocks += 1
        else:
            bad_blocks += 1

    if not subtitles:
        return None

    total_subs = len(subtitles)
    total_duration = timedelta()
    overlaps = 0
    total_gap = timedelta()
    gaps_count = 0
    max_gap = timedelta()
    total_words = 0
    total_chars = 0
    too_short_subs = 0
    too_long_subs = 0
    out_of_order = 0

    for i, sub in enumerate(subtitles):
        duration = sub['end'] - sub['start']
        total_duration += duration

        words = len(sub['text'].split())
        chars = len(sub['text'])
        total_words += words
        total_chars += chars

        if duration.total_seconds() < SHORT_SEC:
            too_short_subs += 1
        if duration.total_seconds() > LONG_SEC:
            too_long_subs += 1

        if i > 0:
            prev = subtitles[i - 1]
            if prev['end'] > sub['end']:
                out_of_order += 1
            gap = sub['start'] - prev['end']
            if gap.total_seconds() < 0:
                overlaps += 1
            else:
                total_gap += gap
                gaps_count += 1
                if gap > max_gap:
                    max_gap = gap

    total_sec = total_duration.total_seconds()
    span = (subtitles[-1]['end'] - subtitles[0]['start']).total_seconds()

    return {
        'encoding': encoding,
        'bad_blocks': bad_blocks,
        'out_of_order': out_of_order,
        'total_subs': total_subs,
        'span_sec': span,
        'total_duration_sec': total_sec,
        'avg_duration_sec': total_sec / total_subs if total_subs else 0,
        'overlaps': overlaps,
        'avg_gap_sec': total_gap.total_seconds() / gaps_count if gaps_count else 0,
        'max_gap_sec': max_gap.total_seconds(),
        'wps': total_words / total_sec if total_sec > 0 else 0,
        'cps': total_chars / total_sec if total_sec > 0 else 0,
        'too_short_subs': too_short_subs,
        'too_long_subs': too_long_subs,
    }


def fmt_time(sec):
    h, m, s = int(sec // 3600), int(sec % 3600 // 60), sec % 60
    return f'{h:02d}:{m:02d}:{s:04.1f}'


def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else r'e:\raw_data'
    srt_files = sorted(f for f in os.listdir(directory) if f.lower().endswith('.srt'))

    print(f'{"File":<70} | {"Subs":<6} | {"Span":<8} | {"AvgDur":<6} | {"Ovl":<4} | '
          f'{"AvgGap":<6} | {"MaxGap":<6} | {"WPS":<5} | {"CPS":<5} | {"Bad":<4} | {"OOO":<4}')
    print('-' * 145)

    for f in srt_files:
        file_path = os.path.join(directory, f)
        try:
            stats = analyze_srt(file_path)
        except UnicodeDecodeError as e:
            print(f'{f[:70]:<70} | خطأ: {e}')
            continue
        if not stats:
            continue
        name = f[:67] + '...' if len(f) > 70 else f
        print(f'{name:<70} | {stats["total_subs"]:<6} | {fmt_time(stats["span_sec"]):<8} | '
              f'{stats["avg_duration_sec"]:<6.2f} | {stats["overlaps"]:<4} | '
              f'{stats["avg_gap_sec"]:<6.2f} | {stats["max_gap_sec"]:<6.2f} | '
              f'{stats["wps"]:<5.2f} | {stats["cps"]:<5.2f} | '
              f'{stats["bad_blocks"]:<4} | {stats["out_of_order"]:<4}')


if __name__ == '__main__':
    main()
