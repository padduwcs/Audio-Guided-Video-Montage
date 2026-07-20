"""Shared visual theme for the launcher and review workspace."""

THEME_SWITCHER_HTML = """
<div class="preference-controls">
<div class="theme-switcher" role="group" aria-label="Chế độ hiển thị">
  <button type="button" data-theme-choice="dark" aria-pressed="false">Tối</button>
  <button type="button" data-theme-choice="light" aria-pressed="false">Sáng</button>
</div>
<div class="language-switcher" role="group" aria-label="Ngôn ngữ">
  <button type="button" data-language-choice="vi" aria-pressed="false">VI</button>
  <button type="button" data-language-choice="en" aria-pressed="false">EN</button>
</div>
</div>
"""


THEME_JS = """
() => {
    const themeStorageKey = "audio-montage-theme";
    const languageStorageKey = "audio-montage-language";
    const root = document.documentElement;
    const translations = new Map([
        ["Tối", "Dark"], ["Sáng", "Light"],
        ["Không gian dựng video", "Video workspace"],
        ["Chọn video và voice-over, tạo bản nháp trên Kaggle, tinh chỉnh từng đoạn rồi xuất video hoàn chỉnh.", "Select videos and a voice-over, create a Kaggle draft, refine each segment, and export the final video."],
        ["Bắt đầu", "Start"], ["Dữ liệu đầu vào", "Input data"],
        ["Chọn các video nguồn và một file voice-over cho dự án.", "Select source videos and one voice-over file for the project."],
        ["Video nguồn", "Source videos"], ["Voice-over hoặc audio", "Voice-over or audio"],
        ["Xác nhận dữ liệu", "Confirm input"], ["Chưa chọn dữ liệu.", "No input selected."],
        ["Kết nối Kaggle", "Kaggle connection"],
        ["Thông tin được lưu trong cấu hình Kaggle trên máy của bạn.", "Credentials are saved in the Kaggle configuration on your computer."],
        ["Tên người dùng", "Username"], ["Khóa API", "API key"],
        ["Dán khóa trong file kaggle.json", "Paste the key from kaggle.json"],
        ["Lưu kết nối", "Save connection"], ["Kiểm tra", "Check"],
        ["Chưa kiểm tra kết nối Kaggle.", "Kaggle connection has not been checked."],
        ["Tùy chọn nâng cao", "Advanced options"], ["Tên dự án", "Project name"],
        ["Thiết bị Kaggle", "Kaggle device"], ["Kiểu tính toán", "Compute type"],
        ["Kiểm thử nhanh bằng embedding giả", "Quick test with fake embeddings"],
        ["Tạo bản nháp", "Create draft"],
        ["Gửi dữ liệu lên Kaggle, phân tích và tải kết quả về máy.", "Upload data to Kaggle, analyze it, and download the results."],
        ["Tạo bản nháp video", "Create video draft"], ["Chưa bắt đầu", "Not started"],
        ["Chưa bắt đầu trong phiên này", "Not started in this session"],
        ["Xác nhận dữ liệu trước khi tạo bản nháp.", "Confirm the input before creating a draft."],
        ["Xác nhận dữ liệu trước khi tạo bản nháp mới.", "Confirm the input before creating a new draft."],
        ["Nhật ký kỹ thuật", "Technical log"], ["Chi tiết tiến trình", "Process details"],
        ["Chỉnh sửa", "Edit"], ["Chỉnh sửa bản dựng", "Edit montage"],
        ["Xem từng đoạn, so sánh clip gợi ý, điều chỉnh thuộc tính và lưu timeline.", "Review segments, compare suggested clips, adjust properties, and save the timeline."],
        ["Mở không gian chỉnh sửa", "Open editing workspace"],
        ["Sẵn sàng mở không gian chỉnh sửa.", "The editing workspace is ready."],
        ["Bản nháp chưa sẵn sàng.", "The draft is not ready."],
        ["Xuất video", "Export video"], ["Xuất video hoàn chỉnh", "Export final video"],
        ["Kiểm tra timeline và render video thành phẩm trên máy.", "Validate the timeline and render the final video locally."],
        ["Chưa xuất trong phiên này", "Not exported in this session"],
        ["Hãy hoàn tất bước chỉnh sửa trước khi xuất video.", "Finish editing before exporting the video."],
        ["Bấm Xuất video khi bạn muốn tạo lại video hoàn chỉnh.", "Click Export video when you want to create a new final video."],
        ["Chi tiết render", "Render details"], ["Video hoàn chỉnh", "Final video"],
        ["Không gian chỉnh sửa", "Editing workspace"], ["Phân đoạn", "Segments"],
        ["Quản lý phân đoạn", "Segment management"], ["Lọc điều kiện", "Filter"],
        ["Tất cả", "All"], ["Cần kiểm tra", "Needs review"],
        ["Độ tin cậy thấp", "Low confidence"], ["Sử dụng fallback", "Uses fallback"],
        ["Đã chỉnh sửa", "Edited"], ["Thiếu hình ảnh", "Missing visual"], ["Có lỗi", "Has errors"],
        ["Chọn phân đoạn", "Select segment"], ["Clip thay thế được đề xuất", "Suggested replacement clips"],
        ["Không có đề xuất.", "No suggestions."], ["Chọn clip gợi ý", "Select a suggested clip"],
        ["Thay clip", "Replace clip"], ["Sẵn sàng.", "Ready."],
        ["Hoàn tác", "Undo"], ["Làm lại", "Redo"], ["Lưu thay đổi", "Save changes"],
        ["Âm thanh và văn bản", "Audio and text"], ["Âm thanh gốc", "Original audio"],
        ["Lời thoại", "Transcript"], ["Độ tin cậy", "Confidence"], ["Điểm số", "Score"],
        ["Cần kiểm tra lại", "Needs review"], ["Ghi chú", "Notes"],
        ["Cập nhật ghi chú", "Update notes"], ["Dự án và nhật ký", "Project and logs"],
        ["Kiểm lỗi dự án", "Validate project"], ["Xuất nhật ký thao tác", "Export audit log"],
        ["Nhật ký thao tác (JSON)", "Audit log (JSON)"], ["Xem trước clip", "Clip preview"],
        ["Clip đang chọn", "Selected clip"], ["Thuộc tính clip", "Clip properties"],
        ["Lớp video", "Video layer"], ["Tạo từ clip gợi ý", "Create from suggestion"],
        ["Mã clip", "Clip ID"], ["Mã video", "Video ID"], ["Nguồn", "Source"],
        ["Bắt đầu (giây)", "Start (seconds)"], ["Kết thúc (giây)", "End (seconds)"],
        ["Tốc độ", "Speed"], ["Chuyển cảnh", "Transition"],
        ["Chế độ khung hình", "Frame mode"], ["Âm lượng", "Volume"],
        ["Khóa clip", "Lock clip"], ["Áp dụng thay đổi", "Apply changes"],
        ["Cắt", "Cut"], ["Mờ dần", "Fade"], ["Hòa trộn", "Crossfade"], ["Trượt", "Slide"],
        ["Vừa khung", "Fit"], ["Nền làm mờ", "Blurred background"],
        ["Cắt giữa", "Center crop"], ["Lấp đầy", "Fill"],
        ["Thiếu dữ liệu", "Missing input"], ["Đang tạo bản nháp", "Creating draft"],
        ["Đang chuẩn bị tác vụ tạo bản nháp...", "Preparing the draft task..."],
        ["Đang đóng gói và tải dữ liệu đầu vào...", "Packaging and uploading input data..."],
        ["Đã gửi tác vụ; đang khởi động môi trường Kaggle...", "Task submitted; starting the Kaggle environment..."],
        ["Kaggle đang phân tích audio và video...", "Kaggle is analyzing the audio and video..."],
        ["Đang tải và kiểm tra kết quả từ Kaggle...", "Downloading and validating Kaggle results..."],
        ["Tạo bản nháp hoàn thành", "Draft completed"],
        ["Tạo bản nháp chưa hoàn thành", "Draft was not completed"],
        ["Đang xuất video", "Exporting video"],
        ["Hệ thống đang kiểm tra timeline và render các đoạn video...", "Validating the timeline and rendering video segments..."],
        ["Xuất video hoàn thành", "Video export completed"],
        ["Xuất video thất bại", "Video export failed"]
    ]);
    const reverseTranslations = new Map(Array.from(translations, ([vi, en]) => [en, vi]));
    const prefixTranslations = [
        ["Video hoàn chỉnh đã sẵn sàng:", "Completed video is available:"],
        ["Bản nháp đã sẵn sàng.", "The draft is ready."],
        ["Đã khởi động không gian chỉnh sửa:", "Editing workspace started:"],
        ["Không gian chỉnh sửa đang chạy tại", "Editing workspace is running at"]
    ];

    function applyTheme(theme) {
        const normalized = ["light", "dark"].includes(theme) ? theme : "dark";
        const resolvedDark = normalized === "dark";
        root.dataset.appTheme = normalized;
        root.style.colorScheme = normalized;
        root.classList.toggle("dark", resolvedDark);
        document.body.classList.toggle("dark", resolvedDark);
        try { localStorage.setItem(themeStorageKey, normalized); } catch (_) {}
        document.querySelectorAll("[data-theme-choice]").forEach((button) => {
            const active = button.dataset.themeChoice === normalized;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
    }

    function translateValue(value, language) {
        const directMap = language === "en" ? translations : reverseTranslations;
        if (directMap.has(value)) return directMap.get(value);
        const prefixes = language === "en"
            ? prefixTranslations
            : prefixTranslations.map(([vi, en]) => [en, vi]);
        for (const [source, target] of prefixes) {
            if (value.startsWith(source)) return target + value.slice(source.length);
        }
        return value;
    }

    function translateSubtree(container, language) {
        if (!container) return;
        const rootElement = container.nodeType === Node.ELEMENT_NODE ? container : container.parentElement;
        if (!rootElement || rootElement.closest("pre, code, textarea, .log-box")) return;
        const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach((node) => {
            if (node.parentElement?.closest("pre, code, textarea, .log-box")) return;
            const trimmed = node.nodeValue.trim();
            if (!trimmed) return;
            const translated = translateValue(trimmed, language);
            if (translated !== trimmed) node.nodeValue = node.nodeValue.replace(trimmed, translated);
        });
        rootElement.querySelectorAll?.("[placeholder], [title], [aria-label]").forEach((element) => {
            ["placeholder", "title", "aria-label"].forEach((attribute) => {
                const value = element.getAttribute(attribute);
                if (value) element.setAttribute(attribute, translateValue(value, language));
            });
        });
    }

    function applyLanguage(language) {
        const normalized = language === "en" ? "en" : "vi";
        root.dataset.appLanguage = normalized;
        document.documentElement.lang = normalized;
        try { localStorage.setItem(languageStorageKey, normalized); } catch (_) {}
        translateSubtree(document.body, normalized);
        document.querySelectorAll("[data-language-choice]").forEach((button) => {
            const active = button.dataset.languageChoice === normalized;
            button.classList.toggle("active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
    }

    function bindControls() {
        document.querySelectorAll("[data-theme-choice]").forEach((button) => {
            if (button.dataset.themeBound === "true") return;
            button.dataset.themeBound = "true";
            button.addEventListener("click", () => applyTheme(button.dataset.themeChoice));
        });
        document.querySelectorAll("[data-language-choice]").forEach((button) => {
            if (button.dataset.languageBound === "true") return;
            button.dataset.languageBound = "true";
            button.addEventListener("click", () => applyLanguage(button.dataset.languageChoice));
        });
    }

    let savedTheme = "dark";
    let savedLanguage = "vi";
    try { savedTheme = localStorage.getItem(themeStorageKey) || "dark"; } catch (_) {}
    try { savedLanguage = localStorage.getItem(languageStorageKey) || "vi"; } catch (_) {}
    applyTheme(savedTheme);
    bindControls();
    applyLanguage(savedLanguage);

    if (!window.__audioMontageThemeObserver) {
        window.__audioMontageThemeObserver = new MutationObserver((mutations) => {
            bindControls();
            if (root.dataset.appLanguage === "en") {
                mutations.forEach((mutation) => mutation.addedNodes.forEach((node) => translateSubtree(node, "en")));
            }
        });
        window.__audioMontageThemeObserver.observe(document.body, { childList: true, subtree: true });
    }
}
"""


APP_THEME_CSS = """
.gradio-container {
    --app-bg: #0f141d;
    --app-surface: #171e29;
    --app-surface-soft: #1d2633;
    --app-surface-strong: #273242;
    --app-text: #edf2f7;
    --app-text-muted: #a9b6c7;
    --app-border: #344154;
    --app-primary: #ff6469;
    --app-primary-hover: #ff777c;
    --app-primary-soft: #3b2229;
    --app-success: #52d391;
    --app-success-soft: #173328;
    --app-warning: #f4bd61;
    --app-warning-soft: #3a2d19;
    --app-danger: #ff7c82;
    --app-danger-soft: #3c2229;
    --app-shadow: 0 14px 34px rgba(0, 0, 0, 0.28);
    background: var(--app-bg) !important;
    color: var(--app-text) !important;
}

html[data-app-theme="light"] .gradio-container {
    --app-bg: #f4f6f9;
    --app-surface: #ffffff;
    --app-surface-soft: #f8fafc;
    --app-surface-strong: #eef2f7;
    --app-text: #172033;
    --app-text-muted: #64748b;
    --app-border: #dce2ea;
    --app-primary: #e5484d;
    --app-primary-hover: #cf3c42;
    --app-primary-soft: #fff0f1;
    --app-success: #178650;
    --app-success-soft: #eaf8f0;
    --app-warning: #b66a00;
    --app-warning-soft: #fff6df;
    --app-danger: #c7373f;
    --app-danger-soft: #fff0f1;
    --app-shadow: 0 10px 30px rgba(27, 36, 50, 0.07);
}

.gradio-container, .gradio-container .prose, .gradio-container label,
.gradio-container h1, .gradio-container h2, .gradio-container h3,
.gradio-container h4, .gradio-container p, .gradio-container span,
.gradio-container strong, .gradio-container summary {
    color: var(--app-text);
}
.gradio-container .prose p, .gradio-container .prose li,
.gradio-container .secondary-wrap, .gradio-container .info {
    color: var(--app-text-muted) !important;
}
.gradio-container input, .gradio-container textarea,
.gradio-container [data-testid="textbox"], .gradio-container [role="listbox"] {
    background: var(--app-surface-soft) !important;
    color: var(--app-text) !important;
    border-color: var(--app-border) !important;
}
.gradio-container input::placeholder, .gradio-container textarea::placeholder {
    color: var(--app-text-muted) !important;
}
.gradio-container [role="tablist"] {
    border-color: var(--app-border) !important;
}
.gradio-container [role="tablist"] button {
    color: var(--app-text-muted) !important;
    background: transparent !important;
}
.gradio-container [role="tablist"] button.selected,
.gradio-container [role="tablist"] button[aria-selected="true"] {
    color: var(--app-primary) !important;
    border-color: var(--app-primary) !important;
    background: var(--app-primary-soft) !important;
}
.gradio-container button.primary {
    color: #ffffff !important;
    background: var(--app-primary) !important;
    border-color: var(--app-primary) !important;
}
.gradio-container button.primary * { color: #ffffff !important; }
.gradio-container button.primary:hover { background: var(--app-primary-hover) !important; }
.gradio-container button.secondary {
    color: var(--app-text) !important;
    background: var(--app-surface-soft) !important;
    border-color: var(--app-border) !important;
}
.gradio-container button:focus-visible,
.gradio-container input:focus-visible,
.gradio-container textarea:focus-visible {
    outline: 3px solid color-mix(in srgb, var(--app-primary) 35%, transparent) !important;
    outline-offset: 2px;
}
.preference-controls { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.theme-switcher, .language-switcher {
    display: inline-flex;
    gap: 3px;
    padding: 4px;
    border: 1px solid var(--app-border);
    border-radius: 10px;
    background: var(--app-surface-soft);
}
.theme-switcher button, .language-switcher button {
    min-width: 62px;
    padding: 7px 10px;
    border: 0;
    border-radius: 7px;
    background: transparent;
    color: var(--app-text-muted) !important;
    font-size: 12px;
    font-weight: 650;
    cursor: pointer;
}
.language-switcher button { min-width: 38px; }
.theme-switcher button.active, .language-switcher button.active {
    color: var(--app-text) !important;
    background: var(--app-surface) !important;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
}
html[data-app-theme="light"] .gradio-container button:not(.primary),
html[data-app-theme="light"] .gradio-container button:not(.primary) * {
    color: var(--app-text) !important;
}
footer { display: none !important; }
"""

REVIEW_WORKSPACE_CSS = """
/* === Review Workspace (Editor) Layout === */
.review-workspace-shell { width: 100%; }
.imovie-top-row { background: transparent !important; padding-bottom: 10px; align-items: stretch !important; }
.imovie-top-row > div { height: auto !important; }
.imovie-media-panel, .imovie-preview-panel {
    background: var(--app-surface) !important;
    border-radius: 14px !important;
    border: 1px solid var(--app-border) !important;
    padding: 16px !important;
    box-shadow: var(--app-shadow) !important;
    height: 100% !important;
    display: flex !important;
    flex-direction: column !important;
}
.imovie-bottom-row {
    background: var(--app-surface) !important;
    border: 1px solid var(--app-border) !important;
    border-radius: 14px !important;
    padding: 20px 30px !important;
    min-height: 250px;
    margin-top: 10px;
    box-shadow: var(--app-shadow) !important;
}
.imovie-storyboard-panel { background: transparent !important; border: none !important; }
.workspace-header {
    display: flex; align-items: center; justify-content: space-between; gap: 18px;
    padding: 12px 14px; margin-bottom: 12px; border: 1px solid var(--app-border);
    border-radius: 12px; background: var(--app-surface); box-shadow: var(--app-shadow);
}
.workspace-title { color: var(--app-text) !important; font-size: 15px; }
.workspace-meta { color: var(--app-text-muted) !important; font-size: 12px; margin-top: 3px; }
.storyboard-container { scrollbar-width: thin; }
.final-video-player {
    width: 100%; min-height: 450px; display: grid; place-items: center;
    border: 1px solid var(--app-border); border-radius: 8px;
    background: #111827; overflow: hidden;
}
.final-video-player video {
    width: 100%; height: 450px; display: block;
    background: #000; object-fit: contain;
}
.final-video-empty {
    min-height: 200px; display: grid; place-items: center;
    border: 1px dashed var(--app-border); border-radius: 8px;
    color: var(--app-text-muted); background: var(--app-surface-soft); font-size: 14px;
}
@media (max-width: 1120px) {
    .imovie-top-row { flex-wrap: wrap !important; }
    .imovie-top-row > div { min-width: min(100%, 360px) !important; }
}
@media (max-width: 700px) {
    .workspace-header { align-items: flex-start; flex-direction: column; }
    .imovie-bottom-row { padding: 14px !important; }
}
"""
