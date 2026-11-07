# niche-research

Skill cho Claude Code để research một ngách content YouTube trước khi lên idea video. Không cần API key.

*English below.*

## Skill làm gì

1. **Quét YouTube** bằng `yt_scan.py`, chỉ dùng Python chuẩn và đọc trang công khai:
   - video mới nhất và phổ biến nhất của các kênh mẫu, kèm cột **× nền kênh** (view của video chia cho trung vị view các video gần nhất của kênh);
   - kết quả tìm kiếm theo tuần, tháng, năm, xếp theo view;
   - Short đang lên, các kênh xuất hiện trong kết quả;
   - gợi ý tìm kiếm của YouTube.
2. **Bảng thumbnail** (cần ffmpeg): ghép video thắng và video hụt thành ảnh để so kiểu thumbnail.
3. **Google Trends** ở chế độ tìm kiếm trên YouTube, đọc qua trình duyệt.
4. **YouTube Studio → Xu hướng**: truy vấn quanh một chủ đề, mức tìm kiếm và mảng trống nội dung. Bước này chỉ đọc, qua Claude in Chrome trên phiên YouTube bạn đã đăng nhập.
5. **Báo cáo** `REPORT.md` theo khung có sẵn, gồm kênh cùng ngách, từ khoá, kiểu tiêu đề và thumbnail, ý tưởng video mới kèm lý do và rủi ro.

## Cài

```bash
claude plugin marketplace add tungpm21/niche-research
```

```bash
claude plugin install niche-research@niche-research
```

Hoặc chép thư mục `skills/niche-research` vào `~/.claude/skills/`.

Yêu cầu:
- Python 3.9+.
- `ffmpeg` trên PATH, nếu muốn có bảng thumbnail.
- Claude in Chrome, nếu muốn đọc YouTube Studio.

## Dùng

Nói với Claude, ví dụ: "research ngách phim hoạt hình self-improvement, đây là 3 kênh mẫu …". Skill sẽ:
- tạo `docs/research/niches/<ngách>.json` từ `references/niches/example.json`;
- quét vào `docs/research/<ngách>-<ngày>/`;
- viết báo cáo và cập nhật `docs/research/niches/<ngách>-findings.md`.

Chạy tay:

```bash
python skills/niche-research/scripts/yt_scan.py channel @handle --popular
```

```bash
python skills/niche-research/scripts/yt_scan.py run docs/research/niches/my-niche.json --out docs/research/my-niche-2026-11-07
```

Các lệnh khác: `search`, `suggest`, `video`, `thumbs`. Xem `--help`.

## Giới hạn

- Script đọc trang YouTube công khai, không qua API chính thức. YouTube đổi cấu trúc trang thì script có thể hỏng.
- Không có CTR hay thời gian xem của kênh khác, nên ý tưởng là giả thuyết để thử, không phải công thức.
- Chỉ đọc: không đăng nhập, bình luận, đăng ký hay đổi cài đặt kênh.

---

## English

A Claude Code skill for researching a YouTube content niche before you plan videos. No API key needed.

**What it does:**
- `yt_scan.py` (Python standard library only) reads public YouTube pages:
  - each sample channel's latest and most popular videos, with an "× channel baseline" outlier score (views divided by the median of the channel's recent videos);
  - search results by week, month or year, sorted by views;
  - rising Shorts;
  - YouTube search suggestions.
- With ffmpeg, it builds contact sheets of winning and losing thumbnails.
- In the browser, the skill reads Google Trends (YouTube search mode) and, read-only through Claude in Chrome, the YouTube Studio Research tab, which shows search volume and content gaps.
- It ends with a `REPORT.md` of competitor channels, keywords, title and thumbnail patterns, and new video ideas with reasons and risks.

**Install:** run `claude plugin marketplace add tungpm21/niche-research`, then `claude plugin install niche-research@niche-research`. Alternatively, copy `skills/niche-research` into `~/.claude/skills/`.

**Notes:**
- The skill's instructions are written in Vietnamese. Claude follows them and replies in your language.
- This is unofficial page scraping, so it may break when YouTube changes its pages.
- View counts are public numbers with no CTR or watch time, so treat the ideas as hypotheses to test.

License: MIT.
