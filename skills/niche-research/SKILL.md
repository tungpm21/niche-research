---
name: niche-research
description: "Dùng khi cần research một ngách content YouTube trước khi lên idea video. Skill tìm kênh và video cùng ngách đang lên, đo view so với mức nền của từng kênh, ghép bảng thumbnail video thắng và video hụt, lấy từ khoá đang trend từ gợi ý tìm kiếm, Google Trends và tab Xu hướng của YouTube Studio (mức tìm kiếm, mảng trống nội dung), rồi viết báo cáo kèm ý tưởng video mới. Gọi khi người dùng nói \"research ngách\", \"tìm kênh cùng ngách\", \"đối thủ đang làm gì\", \"keyword đang trend\", \"ý tưởng đang trend để dễ lên\", \"xem mấy kênh này\", \"niche research\", \"competitor channels\", \"trending topics on YouTube\", hoặc dán link kênh/video YouTube để làm mẫu. Gọi cả trước khi lên idea video mới cho một kênh khi lần research gần nhất đã cũ hơn khoảng một tháng."
---

# Research ngách content YouTube

Trao đổi bằng ngôn ngữ người dùng đang dùng. Skill này cho ra số liệu và ý tưởng, không làm video. Viết kịch bản là việc của bước sau.

## Chạy script

Script chỉ cần Python 3.9+ chuẩn, không cần API key hay thư viện ngoài. Bảng thumbnail cần thêm `ffmpeg` trên PATH.

```bash
SCAN="python ${CLAUDE_PLUGIN_ROOT}/skills/niche-research/scripts/yt_scan.py"
```

- Cài dạng plugin: `${CLAUDE_PLUGIN_ROOT}` là thư mục plugin. Nếu biến này rỗng trong shell, đặt `CLAUDE_PLUGIN_ROOT=$(ls -d ~/.claude/plugins/cache/niche-research/niche-research/*/ | sort -V | tail -1)`.
- Chép thẳng thư mục skill vào `~/.claude/skills/`: trỏ `SCAN` tới `scripts/yt_scan.py` trong thư mục skill đó.

## File

| File | Là gì |
|---|---|
| `references/niches/example.json` | Cấu hình quét mẫu: kênh mẫu, từ khoá tìm, từ khoá gợi ý, bộ lọc nhiễu, bộ từ cho Google Trends |
| `references/report-template.md` | Khung báo cáo |

Cấu hình và kết quả của từng ngách nằm trong project của người dùng, không nằm trong plugin, để cập nhật plugin không xoá mất:
- `docs/research/niches/<ngách>.json`: cấu hình quét;
- `docs/research/niches/<ngách>-findings.md`: tóm tắt lần research gần nhất kèm đường dẫn báo cáo;
- `docs/research/<ngách>-<YYYY-MM-DD>/`: kết quả mỗi lần quét.

Nếu project đã có chỗ khác cho research thì dùng chỗ đó và nói cho người dùng biết.

## Quy trình

### 1. Xác định ngách

- Nếu ngách đã có `-findings.md`, đọc nó trước. Còn mới (dưới khoảng một tháng) và người dùng chỉ cần ý tưởng thì dùng luôn, nói rõ ngày của số liệu.
- Người dùng đưa kênh hoặc video mới thì thêm vào `channels` của cấu hình.
- Ngách mới thì chép `references/niches/example.json` thành `docs/research/niches/<ngách>.json` và sửa:
  - `about`: một câu mô tả ngách, độ dài và ngôn ngữ video.
  - `channels`: 3–5 kênh mẫu. Hỏi người dùng nếu họ chưa đưa.
  - `searches`: 10–20 cụm từ người xem ngách đó sẽ gõ. `when` là week, month hoặc year; thêm `"by": "views"` để xếp theo view.
  - `suggest`: các từ gốc để lấy gợi ý tìm kiếm.
  - `exclude_title`: biểu thức chính quy lọc kết quả lạc đề.
  - `min_length_s` / `max_length_s`: độ dài video đúng format của ngách.
  - `trends.sets`: các bộ tối đa 5 từ để so trên Google Trends.

### 2. Quét YouTube

```bash
$SCAN run docs/research/niches/<ngách>.json --out docs/research/<ngách>-<ngày>
```

Lệnh này mất vài phút và cho ra:
- `data.json`: dữ liệu thô.
- `scan.md`: các bảng kênh (mới nhất và phổ biến nhất), video tìm được xếp theo view/ngày, Short đang lên, các kênh xuất hiện trong kết quả, và gợi ý tìm kiếm.
- `thumbs/`: bảng thumbnail, cần ffmpeg. Gồm:
  - `winners-*.jpg`: video từ 2× nền kênh trở lên, 4 video phổ biến nhất của mỗi kênh mẫu, và video đang lên trong kết quả tìm;
  - `low-1.jpg`: video hụt, dưới 0,5× nền kênh và đăng được từ 3 ngày;
  - `index.md`: số thứ tự, link và lý do chọn từng ô.

  Chạy lại riêng phần này bằng `$SCAN thumbs <thư mục>/data.json`, chỉnh ngưỡng bằng `--min-outlier` và `--low-outlier`.

Lệnh lẻ khi cần đào thêm (thêm `--json` để in JSON):
- `$SCAN channel @handle`: video mới nhất, kèm cột "× nền kênh".
- `$SCAN channel @handle --popular`: video phổ biến nhất.
- `$SCAN search "từ khoá" --when month --by views`.
- `$SCAN suggest "từ khoá"`: gợi ý tìm kiếm của YouTube.
- `$SCAN video <id>`: mô tả, mốc chương và tag của một video. Dùng cho video nổi bật để xem cách họ viết mô tả và đặt chương.

Kết quả tìm kiếm luôn có video lạc đề. `scan.md` chỉ lọc thô bằng `exclude_title`. Trước khi đưa video nào vào báo cáo, xem tên kênh và tiêu đề để chắc nó đúng ngách.

Script chỉ đọc trang công khai, không đăng nhập, với hl=en và gl=US để số view và ngày có dạng cố định. Nếu một lệnh trả về rỗng hoặc báo không thấy `ytInitialData`, chạy lại một lần. Vẫn lỗi thì mở trang đó trong trình duyệt để kiểm, rồi báo người dùng là YouTube đã đổi trang. Không kết luận là không có dữ liệu.

### 3. Google Trends

Không có API ổn định, nên đọc bằng trình duyệt (Claude in Chrome hoặc trình duyệt có sẵn trong app). Mỗi lần so tối đa 5 từ, ở chế độ tìm kiếm trên YouTube:

```
https://trends.google.com/trends/explore?date=today%2012-m&gprop=youtube&q=<từ 1>,<từ 2>,<từ 3>,<từ 4>,<từ 5>
```

- Dùng các bộ từ trong `trends.sets`. Muốn so giữa các bộ thì giữ một từ chung trong mọi bộ.
- Đổi `today%2012-m` thành `today%203-m` để xem 90 ngày gần nhất.
- Đọc đồ thị bằng screenshot vùng biểu đồ. Khi chỉ có một từ, `get_page_text` trả cả chuỗi số theo ngày và mục "Related queries".
- Ghi mức tương đối (ví dụ "từ A khoảng 95, từ B khoảng 40"), hướng đi (tăng, ổn định, vừa qua đỉnh) và đỉnh theo mùa.
- Từ mơ hồ, lẫn meme hay tên bài hát, thì ghi rõ là không dùng được thay vì coi là xu hướng.

Bấm nút đồng ý cookie là việc cần người dùng cho phép. Nếu có banner thì đọc qua nó, không bấm.

### 4. YouTube Studio: người ta tìm gì và mảng trống nội dung

Tab Xu hướng (Research) trong YouTube Studio cho biết người ta tìm gì quanh một chủ đề, mức tìm kiếm cao/trung bình/thấp, và đánh dấu **mảng trống nội dung**: truy vấn tìm nhiều mà ít video đáp ứng. Số liệu này sát nhu cầu hơn Google Trends.

Bước này cần trình duyệt có phiên đăng nhập YouTube của người dùng, thường là **Claude in Chrome**. Không có thì bỏ qua bước này và ghi rõ trong báo cáo.

1. Mở `https://studio.youtube.com`. Trang tự chuyển sang `/channel/UC…`: đó là mã kênh.
   - Báo người dùng kênh đang đăng nhập là kênh nào.
   - Danh sách tìm kiếm là của toàn YouTube, nên kênh nào cũng dùng được. Riêng các mục "người xem của bạn" phản ánh khán giả của kênh đó. Nếu kênh không cùng ngách, ghi rõ trong báo cáo.
   - Chưa đăng nhập thì nhờ người dùng tự đăng nhập. Không nhập mật khẩu thay họ.
2. Mỗi chủ đề mở một trang:
   ```
   https://studio.youtube.com/channel/<UC…>/analytics/tab-research/period-default?pageType=TOPIC_PAGE&topic=<từ khoá>
   ```
3. Bấm "Hiện tất cả" (Show all) cạnh "Nội dung tìm kiếm hàng đầu về chủ đề này" (Top searches on this topic), rồi đọc bằng `get_page_text`. Mỗi truy vấn đi kèm mức tìm kiếm. Mở thẳng URL `pageType=DEEPDIVE_…` sẽ bị đưa về trang chủ đề, nên phải bấm.
4. Bấm bộ lọc "Mảng trống nội dung" (Content gaps) rồi đọc lại. Ghi rõ mảng trống cho video dài hay video ngắn.
5. Ghi phần "Nội dung mọi người đang xem" của chủ đề. Nếu kênh cùng ngách, ghi cả tab "Đối tượng người xem" (Audience): kênh và định dạng khán giả hay xem.

Ghi tất cả vào `studio-research.md` trong thư mục research. Chỉ đọc:
- Không bấm "Lên ý tưởng cho video", không lưu hay thả tim chủ đề.
- Không đổi cài đặt nào của kênh.
- Chỉ mở Studio của kênh người dùng chỉ định.

### 5. Phân tích

Đọc `scan.md` theo thứ tự:
1. **Mức nền và video vượt nền.** Cột "× nền kênh" bằng view của video chia cho trung vị view các video mới nhất của kênh đó. Video từ 3× trở lên là đề tài hoặc tiêu đề đã chạm được người xem. Video dưới 0,5× là đề tài hụt. So trong cùng kênh, đừng so view thô giữa kênh lớn và kênh nhỏ.
2. **Tốc độ.** View/ngày cho thấy video nào đang lên. Mốc ngày của YouTube bị làm tròn ("3 weeks ago"), nên chỉ dùng để so tương đối.
3. **Kiểu tiêu đề.** Gom các tiêu đề vượt nền theo kiểu viết, ví dụ một từ in hoa, câu nói ở ngôi thứ nhất, câu khẳng định gây tranh cãi. Để ý đợt chép tiêu đề: nhiều kênh nhỏ đặt y hệt tên một video hit mà chỉ được vài trăm view.
4. **Thumbnail.** Mở `thumbs/winners-*.jpg` và `thumbs/low-1.jpg` bằng Read để xem tận mắt. Với mỗi bảng, ghi:
   - số chữ và vị trí chữ;
   - nhân vật và biểu cảm;
   - đồ vật kể chuyện;
   - màu nền và mảng sáng.

   Rồi so bảng thắng với bảng hụt. Nếu hai bên cùng một kiểu thumbnail thì khác biệt nằm ở đề tài, đừng gán cho thumbnail. Nếu một kênh làm khác hẳn mà vượt nền, ghi lại điểm khác đó.
5. **Kênh bị một chuỗi kéo mức nền.** Khi một chuỗi hit kéo trung vị của kênh lên, mọi đề tài khác của kênh đó trông như hụt. Ghi rõ điều này, đừng kết luận các đề tài kia thất bại.
6. **Video quá mới.** Video dưới khoảng một tuần chưa ổn định. Video hụt mà còn mới thì gọi là tín hiệu sớm, chưa phải kết luận.
7. **Chuỗi nhiều phần.** Xem view có giảm qua từng phần không.
8. **Short cùng đề tài.** Short lên nhanh gợi ý nên cắt thêm một bản dọc từ mỗi video.
9. **Từ khoá.** Ghép gợi ý tìm kiếm, Trends và YouTube Studio để biết:
   - từ nào lớn và ổn định;
   - từ nào theo mùa;
   - từ nào đang lên;
   - truy vấn nào là mảng trống mà video của người dùng trả lời được.

   Chọn truy vấn khớp với dạng video của người dùng. Ví dụ kênh làm phim ngắn thì ưu tiên truy vấn dạng cảm xúc hoặc phim ("…short film", "what X feels like") hơn truy vấn dạng hướng dẫn ("how to stop…").

### 6. Viết báo cáo và ý tưởng

Viết `REPORT.md` cạnh `scan.md`, theo `references/report-template.md`.

- Mỗi con số ghi kèm nguồn và ngày. Tách rõ số đo được với suy luận.
- Không có số click (CTR) hay thời gian xem của kênh khác, nên không khẳng định idea nào chắc chắn hiệu quả. Gọi là giả thuyết để thử.
- Hỏi hoặc tìm trong project danh sách video kênh đã làm, để ý tưởng không trùng.
- Mỗi ý tưởng gồm:
  - tiêu đề thử;
  - đề tài và nhóm người xem;
  - lý do theo số liệu;
  - rủi ro.

  Các ý tưởng phải khác nhau về đề tài, không chỉ khác bối cảnh.
- Nêu ý tưởng nên chọn và lý do, rồi để người dùng chốt.

Sau đó cập nhật `docs/research/niches/<ngách>-findings.md` bằng tóm tắt mới và đường dẫn báo cáo. Gửi người dùng bản tóm tắt kèm đường dẫn các file.

## Giới hạn

- Chỉ đọc. Không tự đăng nhập, không bình luận, không bấm theo dõi hay đăng ký kênh. YouTube Studio chỉ mở trên phiên người dùng đã đăng nhập sẵn.
- Script nghỉ giữa các lần gọi. Đừng chạy song song nhiều lệnh `run`.
- Đừng chép tiêu đề hay thumbnail của kênh khác. Học kiểu viết, không học từng chữ.
- Số liệu cũ đi rất nhanh. Báo cáo nào cũng phải có ngày quét.
- Script đọc trang YouTube công khai, không qua API chính thức. YouTube đổi trang thì script có thể hỏng; khi đó báo người dùng thay vì đoán số.
