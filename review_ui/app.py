"""Gradio UI app for Review UI (Stage 7).

- Hiển thị segment list, candidate list, preview, inspector
- Đổi clip, chỉnh tham số, validate/save, dirty state, readonly mode
- Tích hợp bộ quản lý trạng thái, cập nhật timeline.json
- Tích hợp Bản đồ Timeline trực quan (Visual Timeline Map) và Dashboard thống kê
- Giao diện phẳng (Flat mode), tối giản, màu sắc trung tính nhẹ nhàng, tối ưu dễ dùng
"""

import os
import tempfile
import time
import gradio as gr
import gradio_client.utils as gradio_client_utils
import soundfile as sf
import numpy as np

from review_ui.loader import load_project_data
from review_ui.validator import validate_project_data
from review_ui.editor import replace_clip, create_visual_from_candidate, update_timing, update_speed, mark_reviewed, update_visual_properties
from review_ui.storage import save_timeline, backup_timeline
from review_ui.media import resolve_video_path, resolve_audio_path
from review_ui.transaction_log import TransactionLog
from renderer.core import extract_segment_ffmpeg, render_timeline

# Resolve Repo Root Path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_ORIGINAL_JSON_SCHEMA_TO_PYTHON_TYPE = gradio_client_utils._json_schema_to_python_type


def _json_schema_to_python_type_compat(schema, defs):
    """Handle boolean JSON-schema nodes produced by newer Pydantic/FastAPI."""
    if isinstance(schema, bool):
        return "Any"
    return _ORIGINAL_JSON_SCHEMA_TO_PYTHON_TYPE(schema, defs)


gradio_client_utils._json_schema_to_python_type = _json_schema_to_python_type_compat


def make_abs(path):
    if not path:
        return None
    if os.path.isabs(path):
        return path
    return os.path.abspath(os.path.join(REPO_ROOT, path))

def generate_timeline_html(data, selected_id):
    """
    Generate horizontal visual timeline HTML representing segments proportional to duration.
    Clean flat design for Light mode.
    """
    items = data.timeline.get("items", [])
    if not items:
        return "<p style='color: #64748b; font-family: sans-serif; font-size: 13px;'>Timeline trống</p>"
    
    total_duration = sum(item["duration"] for item in items)
    if total_duration <= 0:
        total_duration = 1.0
        
    html = '<div class="storyboard-container" style="display: flex; overflow-x: auto; gap: 10px; padding: 15px; background-color: transparent; box-sizing: border-box;">'
    
    msgs = validate_project_data(data, mode="edit_save")
    needs_review_segs = {m.segment_id for m in msgs if m.code == "NEEDS_REVIEW"}
    error_segs = {m.segment_id for m in msgs if m.level == "error"}
    
    # Load user edited tags
    edited_segs = {item["segment_id"] for item in data.timeline["items"] if item.get("user_edited")}

    for item in items:
        sid = item["segment_id"]
        
        # Determine background color/border
        is_selected = (sid == selected_id)
        
        badge_html = ""
        if sid in error_segs:
            badge_html = '<span style="position: absolute; top: 4px; right: 4px; background: #ef4444; color: white; padding: 2px 4px; border-radius: 4px; font-size: 10px; font-weight: bold; z-index: 10;">Lỗi</span>'
        elif sid in needs_review_segs:
            badge_html = '<span style="position: absolute; top: 4px; right: 4px; background: #f59e0b; color: white; padding: 2px 4px; border-radius: 4px; font-size: 10px; font-weight: bold; z-index: 10;">Review</span>'
        elif sid in edited_segs:
            badge_html = '<span style="position: absolute; top: 4px; right: 4px; background: #3b82f6; color: white; padding: 2px 4px; border-radius: 4px; font-size: 10px; font-weight: bold; z-index: 10;">Đã sửa</span>'
            
        border_style = "border: 3px solid #0ea5e9; box-shadow: 0 0 0 3px rgba(14,165,233,0.3);" if is_selected else "border: 3px solid transparent;"
        
        bg_html = ""
        text_color = "#52525b"
        bg_color = "#a1a1aa"
        text_shadow = "none"
        
        visual_items = item.get("visual_items", [])
        if visual_items and "source_path" in visual_items[0] and visual_items[0]["source_path"]:
            source_path = visual_items[0]["source_path"]
            abs_source = make_abs(source_path)
            if abs_source:
                ext = abs_source.lower()
                if ext.endswith(('.mp4', '.webm', '.mov')):
                    bg_html = f'<video src="/file={abs_source}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; opacity: 0.7; pointer-events: none;" autoplay muted loop playsinline></video>'
                    text_color = "#ffffff"
                    bg_color = "#18181b"
                    text_shadow = "0 1px 4px rgba(0,0,0,0.9)"
                elif ext.endswith(('.jpg', '.png', '.jpeg')):
                    bg_html = f'<img src="/file={abs_source}" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; opacity: 0.7;" />'
                    text_color = "#ffffff"
                    bg_color = "#18181b"
                    text_shadow = "0 1px 4px rgba(0,0,0,0.9)"
        
        html += f'''
        <div style="flex: 0 0 auto; width: 140px; display: flex; flex-direction: column; gap: 8px; cursor: pointer; font-family: -apple-system, sans-serif; {border_style} border-radius: 8px; padding: 4px; transition: all 0.2s;" title="Segment: {sid}">
            <div style="height: 80px; background-color: {bg_color}; border-radius: 4px; position: relative; overflow: hidden; display: flex; justify-content: center; align-items: center; box-shadow: inset 0 0 10px rgba(0,0,0,0.1);">
                {bg_html}
                <span style="color: {text_color}; font-size: 14px; font-weight: 600; z-index: 10; text-shadow: {text_shadow};">{sid}</span>
                <span style="position: absolute; bottom: 4px; left: 4px; background: rgba(0,0,0,0.7); color: white; padding: 2px 5px; border-radius: 4px; font-size: 11px; z-index: 10;">{item["duration"]:.1f}s</span>
                {badge_html}
            </div>
            <div style="font-size: 12px; color: #3f3f46; text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 2px;">
                {item["text"]}
            </div>
        </div>
        '''
        
    html += '</div>'
    
    # Legend & stats dashboard
    edited_count = len(edited_segs)
    review_count = len(needs_review_segs)
    error_count = len(error_segs)
    
    html += f'''
    <div style="display: flex; gap: 15px; font-size: 12px; margin-top: 10px; flex-wrap: wrap; color: #52525b; font-family: -apple-system, sans-serif; justify-content: center;">
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #a1a1aa; border-radius: 3px;"></span> Chưa sửa ({len(items) - edited_count})</div>
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #3b82f6; border-radius: 3px;"></span> Đã sửa ({edited_count})</div>
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #f59e0b; border-radius: 3px;"></span> Cần Review ({review_count})</div>
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #ef4444; border-radius: 3px;"></span> Lỗi ({error_count})</div>
        <div style="margin-left: 20px; color: #18181b; font-weight: 600;">Tổng: {total_duration:.2f}s | {len(items)} phân đoạn</div>
    </div>
    '''
    return html

custom_css = """
/* ═══════════════════════════════════════════════
   Review UI — "Studio" design system
   Audio-Guided Video Montage
   Dark/Light editor-grade UI.
   ═══════════════════════════════════════════════ */

@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    /* Light mode default */
    --bg-app:        #f8fafc;
    --bg-surface:     #ffffff;
    --bg-surface2:    #f1f5f9;
    --bg-hover:       #e2e8f0;
    --bg-inset:       #f8fafc;

    --border:         #e2e8f0;
    --border-strong:  #cbd5e1;

    --text-1:         #0f172a;
    --text-2:         #475569;
    --text-3:         #94a3b8;

    /* Signature gradient */
    --grad-start:     #7c5cfc;
    --grad-mid:       #d94fd1;
    --grad-end:       #ff6a5a;
    --accent:         #6366f1;
    --accent-soft:    rgba(99, 102, 241, 0.1);
    --accent-ring:    rgba(99, 102, 241, 0.2);

    --success:        #10b981;
    --success-bg:     rgba(16, 185, 129, 0.12);
    --warning:        #f59e0b;
    --warning-bg:     rgba(245, 158, 11, 0.12);
    --danger:         #ef4444;
    --danger-bg:      rgba(239, 68, 68, 0.12);

    --radius-sm:      8px;
    --radius:         12px;
    --radius-lg:      18px;

    --shadow-sm:      0 1px 2px rgba(0,0,0,0.05);
    --shadow-md:      0 8px 24px rgba(0,0,0,0.05);
    --shadow-glow:    0 0 0 1px rgba(99,102,241,0.15), 0 8px 24px rgba(124,92,252,0.15);

    --font:           'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-mono:      'JetBrains Mono', 'SF Mono', Consolas, monospace;
}

/* System dark preference */
@media (prefers-color-scheme: dark) {
    :root {
        --bg-app:        #0b0d12;
        --bg-surface:     #14161d;
        --bg-surface2:    #191c24;
        --bg-hover:       #20232c;
        --bg-inset:       #0e1015;

        --border:         #262a35;
        --border-strong:  #34394a;

        --text-1:         #f4f5f7;
        --text-2:         #a3a8b8;
        --text-3:         #6b7080;

        --accent:         #8b6bff;
        --accent-soft:    rgba(139, 107, 255, 0.14);
        --accent-ring:    rgba(139, 107, 255, 0.35);

        --success:        #35d18f;
        --success-bg:     rgba(53, 209, 143, 0.12);
        --warning:        #ffb23e;
        --warning-bg:     rgba(255, 178, 62, 0.12);
        --danger:         #ff5c72;
        --danger-bg:      rgba(255, 92, 114, 0.12);

        --shadow-sm:      0 2px 8px rgba(0,0,0,0.5);
        --shadow-md:      0 10px 30px rgba(0,0,0,0.65);
        --shadow-glow:    0 0 0 1px rgba(139,107,255,0.25), 0 8px 24px rgba(124,92,252,0.25);
    }
}

/* Gradio user dark class override */
html.dark {
    --bg-app:        #0b0d12;
    --bg-surface:     #14161d;
    --bg-surface2:    #191c24;
    --bg-hover:       #20232c;
    --bg-inset:       #0e1015;

    --border:         #262a35;
    --border-strong:  #34394a;

    --text-1:         #f4f5f7;
    --text-2:         #a3a8b8;
    --text-3:         #6b7080;

    --accent:         #8b6bff;
    --accent-soft:    rgba(139, 107, 255, 0.14);
    --accent-ring:    rgba(139, 107, 255, 0.35);

    --success:        #35d18f;
    --success-bg:     rgba(53, 209, 143, 0.12);
    --warning:        #ffb23e;
    --warning-bg:     rgba(255, 178, 62, 0.12);
    --danger:         #ff5c72;
    --danger-bg:      rgba(255, 92, 114, 0.12);

    --shadow-sm:      0 2px 8px rgba(0,0,0,0.5);
    --shadow-md:      0 10px 30px rgba(0,0,0,0.65);
    --shadow-glow:    0 0 0 1px rgba(139,107,255,0.25), 0 8px 24px rgba(124,92,252,0.25);
}

/* ── Base ── */
body { font-family: var(--font) !important; background: var(--bg-app) !important; }
.gradio-container {
    background:
        radial-gradient(1200px 500px at 12% -10%, rgba(124,92,252,0.10), transparent 60%),
        radial-gradient(900px 400px at 100% 0%, rgba(255,106,90,0.06), transparent 55%),
        var(--bg-app) !important;
    font-family: var(--font) !important;
    max-width: 100% !important;
    padding: 0 !important;
    color: var(--text-1) !important;
}
footer {
    padding: 12px 0 !important;
    background: transparent !important;
    border: none !important;
}
footer a {
    display: none !important;
}

/* ── Inputs ── */
body .gradio-container input[type="text"],
body .gradio-container input[type="password"],
body .gradio-container input[type="number"],
body .gradio-container textarea,
body .gradio-container select {
    background: var(--bg-inset) !important; color: var(--text-1) !important;
    border: 1px solid var(--border) !important; border-radius: var(--radius-sm) !important;
    font-family: var(--font) !important; font-size: 13px !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
body .gradio-container input[type="text"]:focus,
body .gradio-container input[type="password"]:focus,
body .gradio-container input[type="number"]:focus,
body .gradio-container textarea:focus,
body .gradio-container select:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px var(--accent-ring) !important;
}

/* ── Badges ── */
.project-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 4px 10px; background: var(--accent-soft);
    color: var(--accent); border-radius: 20px;
    font-size: 12px; font-weight: 600;
    border: 1px solid var(--accent-ring);
}
.file-badge {
    padding: 3px 9px; background: var(--bg-surface2);
    border: 1px solid var(--border);
    border-radius: 5px; font-size: 12px;
    font-family: var(--font-mono); color: var(--text-2);
}
.readonly-badge {
    padding: 3px 10px; background: var(--danger-bg);
    border: 1px solid var(--danger);
    border-radius: 20px; font-size: 12px; font-weight: 600; color: var(--danger);
}
.backup-badge {
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 10px; background: var(--success-bg);
    border: 1px solid var(--success);
    border-radius: 20px; font-size: 12px; font-weight: 600; color: var(--success);
}

/* Layout panels */
.imovie-top-row {
    background: transparent !important;
    padding: 16px 20px 0 !important; gap: 16px !important; align-items: stretch !important;
}
.imovie-top-row > div { height: auto !important; }
.imovie-media-panel, .imovie-preview-panel {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important; overflow: hidden !important;
}
.imovie-bottom-row {
    background: transparent !important; border-top: none !important;
    padding: 12px 20px 20px !important; min-height: auto !important; margin-top: 0 !important;
}
.imovie-storyboard-panel {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important; padding: 16px 18px !important; overflow: hidden !important;
}
.imovie-video-row {
    background: transparent !important;
    padding: 16px 20px 0 !important; gap: 16px !important;
}

/* Status/Markdown output */
.status-md .prose p { font-size: 13px !important; color: var(--text-2) !important; }

/* Waveform & preview frames */
.waveform-container { background: var(--bg-inset) !important; border-radius: 8px !important; }
video, .gr-video { border-radius: var(--radius) !important; border: 1px solid var(--border) !important; }
"""

def build_editor_tab(
    demo,
    timeline_path,
    matching_candidates_path,
    clip_metadata_path,
    audio_segments_path,
    media_metadata_path,
    project_id=None,
    readonly=False,
    no_backup=False,
    log_path=None,
):
    # Try to load initial project data, or fall back to empty ProjectData
    try:
        project_data = load_project_data(
            timeline_path=timeline_path,
            matching_candidates_path=matching_candidates_path,
            clip_metadata_path=clip_metadata_path,
            audio_segments_path=audio_segments_path,
            media_metadata_path=media_metadata_path,
            project_id=project_id,
        )
    except Exception:
        from review_ui.loader import ProjectData
        project_data = ProjectData(
            timeline={"items": [], "project_id": project_id or "demo_01"},
            matching_candidates={"items": []},
            clip_metadata={"items": []},
            audio_segments={"items": []},
            media_metadata={"videos": []}
        )

    transaction_log = TransactionLog()
    transaction_log.reset(project_data)

    # Initial backup if requested
    backup_created = False
    if not readonly and not no_backup:
        try:
            backup_path = timeline_path + ".before_review.json"
            backup_timeline(project_data.timeline, backup_path)
            backup_created = True
        except Exception as e:
            print(f"[Warning] Failed to create initial backup: {e}")

    # Build segment options helper (strictly text labels, no emojis)
    def get_segment_options(data, filter_type="all"):
        options = []
        msgs = validate_project_data(data, mode="edit_save")
        
        # Build category sets
        needs_review_segs = {m.segment_id for m in msgs if m.code == "NEEDS_REVIEW"}
        low_conf_segs = {m.segment_id for m in msgs if m.code == "LOW_CONFIDENCE"}
        fallback_segs = {m.segment_id for m in msgs if m.code == "FALLBACK_USED"}
        missing_visual_segs = {m.segment_id for m in msgs if m.code == "MISSING_VISUAL"}
        error_segs = {m.segment_id for m in msgs if m.level == "error"}
        
        # Load user edited tags
        edited_segs = {item["segment_id"] for item in data.timeline["items"] if item.get("user_edited")}

        for item in data.timeline["items"]:
            sid = item["segment_id"]
            
            # Filter condition
            if filter_type == "needs_review" and sid not in needs_review_segs:
                continue
            if filter_type == "low_confidence" and sid not in low_conf_segs:
                continue
            if filter_type == "fallback" and sid not in fallback_segs:
                continue
            if filter_type == "edited" and sid not in edited_segs:
                continue
            if filter_type == "missing_visual" and sid not in missing_visual_segs:
                continue
            if filter_type == "error" and sid not in error_segs:
                continue
                
            badge = ""
            if sid in error_segs:
                badge = "[Lỗi] "
            elif sid in needs_review_segs:
                badge = "[Review] "
            elif sid in edited_segs:
                badge = "[Sửa] "
            elif sid in missing_visual_segs:
                badge = "[Trống] "
                
            text = f"{badge}{sid} | {item['text'][:35]}..."
            options.append((text, sid))
        return options

    # Slice audio segment preview wav
    def slice_audio(audio_path, start, end):
        abs_audio = make_abs(audio_path)
        if not abs_audio or not os.path.exists(abs_audio):
            return None
        try:
            data, sr = sf.read(abs_audio)
            start_frame = int(start * sr)
            end_frame = int(end * sr)
            # Ensure valid bounds
            start_frame = max(0, min(start_frame, len(data)))
            end_frame = max(0, min(end_frame, len(data)))
            segment_data = data[start_frame:end_frame]
            
            # Write to local tmp file inside workspace
            tmp_wav_dir = os.path.join(REPO_ROOT, "tmp")
            os.makedirs(tmp_wav_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix=".wav", dir=tmp_wav_dir, delete=False) as tmpf:
                sf.write(tmpf.name, segment_data, sr)
                return tmpf.name
        except Exception as e:
            print(f"[Error] Failed to slice audio: {e}")
            return None

    # Slice video segment preview mp4 using ffmpeg
    def slice_video(video_path, start, end, speed=1.0, crop_mode=None, render_settings=None):
        abs_video = make_abs(video_path)
        if not abs_video or not os.path.exists(abs_video):
            return None
        try:
            tmp_video_dir = os.path.join(REPO_ROOT, "tmp")
            os.makedirs(tmp_video_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix=".mp4", dir=tmp_video_dir, delete=False) as tmpf:
                tmp_sliced_path = tmpf.name
            
            render_settings = render_settings or {}
            extract_segment_ffmpeg(
                abs_video,
                start,
                end,
                tmp_sliced_path,
                speed=speed or 1.0,
                width=render_settings.get("width", 1920),
                height=render_settings.get("height", 1080),
                fps=render_settings.get("fps", 30),
                crop_mode=crop_mode or render_settings.get("crop_mode", "fit"),
                video_codec="libx264",
                video_bitrate="900k",
                audio_codec="aac",
                audio_bitrate="64k",
                keep_original_audio=False,
            )
            return tmp_sliced_path
        except Exception as e:
            return abs_video

    if True:  # Context placeholder to preserve indentation
        # App state variables
        project_state = gr.State(project_data)
        dirty_state = gr.State(False)
        selected_vi_state = gr.State("") # Current visual item id
        transaction_log_state = gr.State(transaction_log)

        with gr.Row(elem_classes="imovie-top-row"):
            # LEFT: Segments, Audio, Log tabs
            with gr.Column(scale=1, elem_classes="imovie-media-panel", min_width=350):
                with gr.Tabs():
                    with gr.Tab("📋 Phân Đoạn"):
                        gr.Markdown("### Quản lý Phân Đoạn")
                        with gr.Row():
                            reload_btn = gr.Button("🔄 Nạp/Tải lại dự án", variant="secondary", scale=1)
                            filter_dropdown = gr.Dropdown(choices=[("Tất cả", "all"), ("Cần review", "needs_review"), ("Độ tin cậy thấp", "low_confidence"), ("Sử dụng fallback", "fallback"), ("Đã chỉnh sửa", "edited"), ("Thiếu hình ảnh", "missing_visual"), ("Có lỗi", "error")], value="all", label="Lọc theo điều kiện", scale=1)
                            segment_dropdown = gr.Dropdown(choices=get_segment_options(project_data, "all"), value=project_data.timeline["items"][0]["segment_id"] if project_data.timeline["items"] else None, label="Chọn phân đoạn", scale=2)

                        gr.Markdown("### Gợi ý Thay thế")
                        candidates_markdown = gr.Markdown("Không có đề xuất.")
                        with gr.Row():
                            candidate_dropdown = gr.Dropdown(choices=[], label="Clip gợi ý", scale=2, interactive=not readonly)
                            choose_cand_btn = gr.Button("⇄ Đổi Clip", variant="primary", scale=1, interactive=not readonly)

                        status_box = gr.Markdown("✅ Sẵn sàng.", elem_classes="status-md")
                        with gr.Row():
                            undo_btn = gr.Button("↶ Hoàn tác", variant="secondary", interactive=True)
                            redo_btn = gr.Button("↷ Làm lại", variant="secondary", interactive=True)
                        with gr.Row():
                            save_btn = gr.Button("💾 Lưu Thay Đổi", variant="primary", interactive=not readonly)
                            render_btn = gr.Button("▶ Render Video", variant="primary", interactive=not readonly)

                    with gr.Tab("🎵 Audio & Văn bản"):
                        audio_player = gr.Audio(label="Audio gốc", interactive=False)
                        transcript_box = gr.Textbox(label="Lời thoại (Transcript)", interactive=False, lines=4)
                        with gr.Row():
                            conf_box = gr.Textbox(label="Độ tin cậy", interactive=False)
                            score_box = gr.Textbox(label="Điểm match", interactive=False)
                        needs_review_cb = gr.Checkbox(label="Đánh dấu cần Review", interactive=not readonly)
                        notes_box = gr.Textbox(label="Ghi chú", interactive=not readonly, placeholder="Nhập ghi chú cho phân đoạn này...")
                        apply_properties_btn = gr.Button("💬 Lưu ghi chú", variant="secondary", interactive=not readonly)

                    with gr.Tab("⚙ Dự án & Log"):
                        validate_btn = gr.Button("🔍 Kiểm lỗi dự án", variant="secondary")
                        export_audit_btn = gr.Button("📤 Xuất Audit Log", variant="secondary")
                        audit_log_box = gr.Textbox(label="Audit Log (JSON)", lines=5, interactive=False)

            # RIGHT: Inspector Panel
            with gr.Column(scale=1, elem_classes="imovie-media-panel", min_width=350):
                with gr.Accordion("🔎 Inspector — Chi tiết Clip", open=True):
                    with gr.Row():
                        vi_dropdown = gr.Dropdown(choices=[], label="Lớp hình ảnh (Visual Item)", interactive=True, scale=2)
                        create_vi_btn = gr.Button("+ Tạo từ Candidate", variant="secondary", visible=False, interactive=not readonly, scale=1)

                    inspector_group = gr.Group(visible=True)
                    with inspector_group:
                        with gr.Row():
                            clip_id_input = gr.Textbox(label="Clip ID", interactive=False)
                            video_id_input = gr.Textbox(label="Video ID", interactive=False)
                        source_path_input = gr.Textbox(label="Đường dẫn nguồn", interactive=False)
                        with gr.Row():
                            clip_start_input = gr.Number(label="Bắt đầu (s)")
                            clip_end_input = gr.Number(label="Kết thúc (s)")
                        speed_input = gr.Slider(minimum=0.75, maximum=1.25, step=0.01, label="Tốc độ phát", interactive=not readonly)
                        with gr.Row():
                            transition_input = gr.Dropdown(choices=["cut", "fade", "crossfade", "slide"], label="Hiệu ứng chuyển cảnh", interactive=not readonly)
                            crop_mode_input = gr.Dropdown(choices=["fit", "blur_background", "center_crop", "fill"], label="Chế độ cắt khung", interactive=not readonly)
                        with gr.Row():
                            volume_input = gr.Slider(minimum=0.0, maximum=1.0, step=0.1, label="Âm lượng clip", interactive=not readonly)
                            locked_input = gr.Checkbox(label="Khoá phân đoạn", interactive=not readonly)
                        update_inspector_btn = gr.Button("✔ Áp dụng thay đổi", variant="primary", interactive=not readonly)

        # MIDDLE ROW: Videos side-by-side
        with gr.Row(elem_classes="imovie-video-row"):
            with gr.Column(scale=1, elem_classes="imovie-preview-panel"):
                video_player = gr.Video(label="▶ Xem trước phân đoạn", interactive=False, height=360)
            with gr.Column(scale=1, elem_classes="imovie-preview-panel"):
                final_video_player = gr.Video(label="🎬 Video Kết Quả (Sau Render)", interactive=False, height=360)

        # BOTTOM ROW: Storyboard Timeline
        with gr.Row(elem_classes="imovie-bottom-row"):
            with gr.Column(scale=1, elem_classes="imovie-storyboard-panel"):
                timeline_html_map = gr.HTML(generate_timeline_html(project_data, project_data.timeline["items"][0]["segment_id"] if project_data.timeline["items"] else None))

        # Undo/Redo callbacks
        def on_undo(data, tlog):
            new_state = tlog.undo()
            if new_state is not None:
                return new_state, False, "Đã hoàn tác thao tác gần nhất.", tlog
            return data, False, "Không thể hoàn tác.", tlog

        def on_redo(data, tlog):
            new_state = tlog.redo()
            if new_state is not None:
                return new_state, False, "Đã làm lại thao tác.", tlog
            return data, False, "Không thể làm lại.", tlog

        undo_btn.click(
            fn=on_undo,
            inputs=[project_state, transaction_log_state],
            outputs=[project_state, dirty_state, status_box, transaction_log_state]
        )
        redo_btn.click(
            fn=on_redo,
            inputs=[project_state, transaction_log_state],
            outputs=[project_state, dirty_state, status_box, transaction_log_state]
        )

        # Export audit log
        def on_export_audit_log(tlog):
            import json
            return json.dumps(tlog.get_audit_log(), indent=2, ensure_ascii=False)

        export_audit_btn.click(
            fn=on_export_audit_log,
            inputs=[transaction_log_state],
            outputs=[audit_log_box]
        )

        # Render final video callback
        def on_render(data, is_dirty, progress=gr.Progress()):
            # 1. Check and auto-save if dirty
            if is_dirty:
                try:
                    save_timeline(
                        data.timeline, timeline_path,
                        validate_fn=lambda t: validate_project_data(data, mode="edit_save")
                    )
                except Exception as e:
                    return None, f"Tự động lưu thất bại: {e}. Vui lòng kiểm tra lại!", is_dirty

            # 2. Validate for renderer handoff
            msgs = validate_project_data(data, mode="renderer_handoff")
            errors = [m for m in msgs if m.level == "error"]
            if errors:
                err_msg = "\n".join([f"- Segment {err.segment_id}: {err.message}" for err in errors[:5]])
                if len(errors) > 5:
                    err_msg += f"\n... và {len(errors) - 5} lỗi khác."
                return None, f"Lỗi không thể render (Thiếu hình ảnh hoặc lỗi nghiêm trọng):\n{err_msg}", is_dirty

            # Resolve voice-over path from media_metadata
            voice_over_path = None
            try:
                voice_over_rel = data.media_metadata.get("audio", {}).get("normalized_path")
                if voice_over_rel:
                    voice_over_path = make_abs(voice_over_rel)
            except Exception as e:
                print(f"[Warning] Failed to resolve voice-over audio: {e}")

            output_dir = os.path.join(REPO_ROOT, "data", "final")
            os.makedirs(output_dir, exist_ok=True)
            output_video_path = os.path.join(output_dir, "final_video.mp4")
            log_path_render = os.path.join(REPO_ROOT, "data", "intermediate", "render_log.json")
            
            try:
                progress(0.0, desc="Bắt đầu chuẩn bị render...")
                render_timeline(
                    timeline_path=timeline_path,
                    output_path=output_video_path,
                    log_path=log_path_render,
                    voice_over_path=voice_over_path,
                    progress_callback=lambda ratio, desc: progress(ratio, desc=desc)
                )
                return output_video_path, "Render video thành công tại data/final/final_video.mp4!", False
            except Exception as e:
                return None, f"Render video thất bại: {e}", is_dirty

        render_btn.click(
            fn=on_render,
            inputs=[project_state, dirty_state],
            outputs=[final_video_player, status_box, dirty_state]
        )

        # Helper function to refresh choices on segment load
        def load_segment_data(segment_id, data):
            if not segment_id:
                return [
                    "Không tìm thấy segment", None, "", "", "", False, "",
                    gr.update(choices=[], value=None), gr.update(visible=False), gr.update(visible=False),
                    "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False,
                    None, None,
                    "Không có đề xuất", gr.update(choices=[]),
                    generate_timeline_html(data, None)
                ]
            
            # Find item in timeline
            item = next((x for x in data.timeline["items"] if x["segment_id"] == segment_id), None)
            if not item:
                return [
                    f"Không tìm thấy segment {segment_id}", None, "", "", "", False, "",
                    gr.update(choices=[], value=None), gr.update(visible=False), gr.update(visible=False),
                    "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False,
                    None, None,
                    "Không có đề xuất", gr.update(choices=[]),
                    generate_timeline_html(data, segment_id)
                ]

            # Resolve transcript info
            aseg = data.segments_by_id.get(segment_id, {})
            transcript = aseg.get("text", "")
            conf = aseg.get("confidence", 0.0)
            conf_str = f"{conf:.2%}" if conf else "N/A"
            score = item.get("score", 0.0)
            score_str = f"{score:.2f}" if score else "N/A"

            # Load notes
            notes = item.get("notes", "")
            needs_review = item.get("needs_review", False)
            info = f"📋 Phân đoạn {segment_id} (Dài {item['duration']:.2f}s)"

            # Load visual item options
            visual_items = item.get("visual_items", [])
            vi_choices = []
            for vi in visual_items:
                v_id = vi.get("timeline_item_id", vi.get("id", ""))
                label = f"{v_id} | Clip: {vi.get('clip_id', '')}"
                if vi.get("locked"):
                    label += " 🔒"
                vi_choices.append((label, v_id))

            selected_vi_id = None
            if visual_items:
                selected_vi_id = visual_items[0].get("timeline_item_id", visual_items[0].get("id", ""))

            # Load candidates list
            candidates = data.matching_candidates.get(segment_id, [])
            cand_choices = []
            cand_md = "### Clip gợi ý sẵn:\n"
            for i, cand in enumerate(candidates):
                c_lbl = f"v{i+1} | {cand['clip_id']} (Điểm: {cand['score']:.2f})"
                cand_choices.append((c_lbl, cand["clip_id"]))
                cand_md += f"* **Rank {i+1}**: `{cand['clip_id']}` (Điểm: {cand['score']:.2f})\n"
            if not candidates:
                cand_md = "Không có đề xuất nào."

            # Sliced Audio preview path
            audio_rel = data.media_metadata.get("audio", {}).get("normalized_path")
            audio_preview = None
            if audio_rel:
                audio_preview = slice_audio(audio_rel, item.get("audio_start", 0.0), item.get("audio_end", 0.0))

            # Active Visual Item details
            vi = next((x for x in visual_items if x.get("timeline_item_id", x.get("id")) == selected_vi_id), {})
            clip_id = vi.get("clip_id", "")
            video_id = vi.get("video_id", "")
            c_start = vi.get("clip_start", 0.0)
            c_end = vi.get("clip_end", 0.0)
            speed = vi.get("speed", 1.0)
            trans = vi.get("transition", "cut")
            crop = vi.get("crop_mode", "fit")
            vol = vi.get("volume", 1.0)
            locked = vi.get("locked", False)
            
            src_path = ""
            video_preview = None
            if clip_id:
                clip_meta = data.clip_metadata.get(clip_id, {})
                src_rel = clip_meta.get("relative_path", "")
                src_path = src_rel
                video_preview = slice_video(
                    src_rel,
                    c_start,
                    c_end,
                    speed=speed,
                    crop_mode=crop,
                    render_settings=data.media_metadata.get("video", {})
                )

            # Storyboard html map
            html_timeline = generate_timeline_html(data, segment_id)

            # Toggle inspector elements visibility based on visual item existence
            show_inspector = gr.update(visible=True) if visual_items else gr.update(visible=False)
            show_create_vi = gr.update(visible=False) if visual_items else gr.update(visible=True)

            return [
                info, audio_preview, transcript, conf_str, score_str, needs_review, notes,
                gr.update(choices=vi_choices, value=selected_vi_id),
                show_inspector,
                show_create_vi,
                clip_id, video_id, src_path, c_start, c_end, speed, trans, crop, vol, locked,
                video_preview, selected_vi_id,
                cand_md, gr.update(choices=cand_choices),
                html_timeline
            ]

        # Load segment event listener
        def on_segment_change(segment_id, data):
            return load_segment_data(segment_id, data)

        segment_dropdown.change(
            fn=on_segment_change,
            inputs=[segment_dropdown, project_state],
            outputs=[
                status_box, audio_player, transcript_box, conf_box, score_box, needs_review_cb, notes_box,
                vi_dropdown, inspector_group, create_vi_btn,
                clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                video_player, selected_vi_state,
                candidates_markdown, candidate_dropdown,
                timeline_html_map
            ],
            show_api=False,
        )

        # Filter dropdown listener
        def on_filter_change(filter_val, data):
            opts = get_segment_options(data, filter_val)
            new_id = opts[0][1] if opts else None
            return gr.update(choices=opts, value=new_id)

        filter_dropdown.change(
            fn=on_filter_change,
            inputs=[filter_dropdown, project_state],
            outputs=[segment_dropdown],
            show_api=False,
        )

        # Active visual item dropdown change listener
        def on_vi_change(vi_id, segment_id, data):
            if not vi_id or not segment_id:
                return ["", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False, None, vi_id]
            
            item = next((x for x in data.timeline["items"] if x["segment_id"] == segment_id), None)
            if not item:
                return ["", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False, None, vi_id]
            
            vi = next((x for x in item.get("visual_items", []) if x.get("timeline_item_id", x.get("id")) == vi_id), {})
            clip_id = vi.get("clip_id", "")
            video_id = vi.get("video_id", "")
            c_start = vi.get("clip_start", 0.0)
            c_end = vi.get("clip_end", 0.0)
            speed = vi.get("speed", 1.0)
            trans = vi.get("transition", "cut")
            crop = vi.get("crop_mode", "fit")
            vol = vi.get("volume", 1.0)
            locked = vi.get("locked", False)

            src_path = ""
            video_preview = None
            if clip_id:
                clip_meta = data.clip_metadata.get(clip_id, {})
                src_rel = clip_meta.get("relative_path", "")
                src_path = src_rel
                video_preview = slice_video(
                    src_rel,
                    c_start,
                    c_end,
                    speed=speed,
                    crop_mode=crop,
                    render_settings=data.media_metadata.get("video", {})
                )

            return [
                clip_id, video_id, src_path, c_start, c_end, speed, trans, crop, vol, locked,
                video_preview, vi_id
            ]

        vi_dropdown.change(
            fn=on_vi_change,
            inputs=[vi_dropdown, segment_dropdown, project_state],
            outputs=[
                clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                video_player, selected_vi_state
            ],
            show_api=False,
        )

        # Inspector update callback
        def on_update_inspector(
            segment_id, vi_id, clip_start, clip_end, speed, transition, crop_mode, volume, locked, data, is_dirty
        ):
            if not segment_id or not vi_id:
                return data, is_dirty, "Không có Visual Item nào được chọn để cập nhật.", gr.update()
            
            try:
                # Update item state
                success, msg = update_visual_properties(
                    data, segment_id, vi_id,
                    clip_start=clip_start, clip_end=clip_end,
                    speed=speed, transition=transition, crop_mode=crop_mode,
                    volume=volume, locked=locked
                )
                if not success:
                    return data, is_dirty, f"Cập nhật thất bại: {msg}", gr.update()

                # Slice video again to reflect updates in preview
                item = next((x for x in data.timeline["items"] if x["segment_id"] == segment_id), None)
                vi = next((x for x in item.get("visual_items", []) if x.get("timeline_item_id", x.get("id")) == vi_id), {})
                clip_meta = data.clip_metadata.get(vi.get("clip_id"), {})
                src_rel = clip_meta.get("relative_path", "")
                
                video_preview = slice_video(
                    src_rel,
                    clip_start,
                    clip_end,
                    speed=speed,
                    crop_mode=crop_mode,
                    render_settings=data.media_metadata.get("video", {})
                )

                # Push changes to transaction log
                transaction_log.push(data)

                # Reload visual item list to reflect badges
                vi_choices = []
                for v in item.get("visual_items", []):
                    v_id = v.get("timeline_item_id", v.get("id", ""))
                    lbl = f"{v_id} | Clip: {v.get('clip_id', '')}"
                    if v.get("locked"):
                        lbl += " 🔒"
                    vi_choices.append((lbl, v_id))

                html_timeline = generate_timeline_html(data, segment_id)

                return data, True, f"✓ Đã áp dụng thay đổi cho {vi_id} ({time.strftime('%H:%M:%S')})", video_preview, gr.update(choices=vi_choices, value=vi_id), html_timeline
            except Exception as e:
                return data, is_dirty, f"Lỗi: {e}", gr.update(), gr.update(), gr.update()

        update_inspector_btn.click(
            fn=on_update_inspector,
            inputs=[
                segment_dropdown, selected_vi_state,
                clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                project_state, dirty_state
            ],
            outputs=[project_state, dirty_state, status_box, video_player, vi_dropdown, timeline_html_map]
        )

        # Replace clip callback
        def on_replace_clip(segment_id, new_clip_id, data, is_dirty):
            if not segment_id or not new_clip_id:
                return data, is_dirty, "Vui lòng chọn một clip gợi ý từ danh sách.", gr.update()
            
            try:
                success, msg = replace_clip(data, segment_id, new_clip_id)
                if not success:
                    return data, is_dirty, f"Đổi clip thất bại: {msg}", gr.update()

                # Push changes to transaction log
                transaction_log.push(data)

                # Reload segment details
                details = load_segment_data(segment_id, data)
                return [data, True, f"✓ Đã đổi sang clip {new_clip_id}!", *details]
            except Exception as e:
                return [data, is_dirty, f"Lỗi khi đổi clip: {e}"] + [gr.update()] * 25

        choose_cand_btn.click(
            fn=on_replace_clip,
            inputs=[segment_dropdown, candidate_dropdown, project_state, dirty_state],
            outputs=[
                project_state, dirty_state, status_box,
                status_box, audio_player, transcript_box, conf_box, score_box, needs_review_cb, notes_box,
                vi_dropdown, inspector_group, create_vi_btn,
                clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                video_player, selected_vi_state,
                candidates_markdown, candidate_dropdown,
                timeline_html_map
            ],
            show_api=False,
        )

        # Create visual item from candidate callback
        def on_create_vi(segment_id, candidate_clip_id, data, is_dirty):
            if not segment_id or not candidate_clip_id:
                return data, is_dirty, "Vui lòng chọn clip gợi ý trước.", gr.update()
            try:
                success, msg = create_visual_from_candidate(data, segment_id, candidate_clip_id)
                if not success:
                    return data, is_dirty, f"Tạo Visual Item thất bại: {msg}", gr.update()
                
                transaction_log.push(data)
                details = load_segment_data(segment_id, data)
                return [data, True, f"✓ Đã tạo Visual Item từ clip {candidate_clip_id}!", *details]
            except Exception as e:
                return [data, is_dirty, f"Lỗi: {e}"] + [gr.update()] * 25

        create_vi_btn.click(
            fn=on_create_vi,
            inputs=[segment_dropdown, candidate_dropdown, project_state, dirty_state],
            outputs=[
                project_state, dirty_state, status_box,
                status_box, audio_player, transcript_box, conf_box, score_box, needs_review_cb, notes_box,
                vi_dropdown, inspector_group, create_vi_btn,
                clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                video_player, selected_vi_state,
                candidates_markdown, candidate_dropdown,
                timeline_html_map
            ],
            show_api=False,
        )

        # Apply properties (notes and needs_review checkbox)
        def on_apply_properties(segment_id, notes, needs_review, data, is_dirty):
            if not segment_id:
                return data, is_dirty, "Chưa chọn phân đoạn nào.", gr.update()
            try:
                # Update item status
                item = next((x for x in data.timeline["items"] if x["segment_id"] == segment_id), None)
                if item:
                    item["notes"] = notes
                    item["needs_review"] = needs_review
                    item["user_edited"] = True

                transaction_log.push(data)
                
                # Reload segment options to reflect review badges
                opts = get_segment_options(data, filter_dropdown.value)
                html_timeline = generate_timeline_html(data, segment_id)
                
                return data, True, f"✓ Đã cập nhật trạng thái phân đoạn!", gr.update(choices=opts, value=segment_id), html_timeline
            except Exception as e:
                return data, is_dirty, f"Lỗi: {e}", gr.update(), gr.update()

        apply_properties_btn.click(
            fn=on_apply_properties,
            inputs=[segment_dropdown, notes_box, needs_review_cb, project_state, dirty_state],
            outputs=[project_state, dirty_state, status_box, segment_dropdown, timeline_html_map],
            show_api=False,
        )

        # Project validation callback
        def on_validate(data):
            messages = validate_project_data(data, mode="edit_save")
            if not messages:
                return "✓ Không tìm thấy lỗi nào trong timeline. Sẵn sàng render!"
            res = "Tìm thấy các vấn đề cần lưu ý:\n"
            for m in messages:
                res += f"- [{m.level.upper()}] {m.segment_id}: {m.message}\n"
            return res

        validate_btn.click(
            fn=on_validate,
            inputs=[project_state],
            outputs=[audit_log_box],
            show_api=False,
        )

        # Save trigger
        def on_save(data, is_dirty, segment_id):
            if readonly:
                return False, "Chế độ chỉ xem. Không thể lưu file.", gr.update()
            if not is_dirty:
                return False, "Không có thay đổi nào cần lưu.", gr.update()
            try:
                # Save atomically
                save_timeline(
                    data.timeline, timeline_path,
                    validate_fn=lambda t: validate_project_data(data, mode="edit_save")
                )
                
                # If there's a log path requested, write to log
                if log_path:
                    try:
                        log_data = {
                            "schema_version": "1.0",
                            "project_id": data.timeline["project_id"],
                            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            "timeline_path": timeline_path,
                            "items_count": len(data.timeline["items"])
                        }
                        with open(log_path, "w", encoding="utf-8") as lf:
                            import json
                            json.dump(log_data, lf, indent=2)
                    except Exception as le:
                        print(f"[Warning] Failed to write review log: {le}")

                # Reload segment options to reflect badges
                opts = get_segment_options(data, filter_dropdown.value)
                html_timeline = generate_timeline_html(data, segment_id)
                
                return False, f"Đã lưu timeline thành công! ({time.strftime('%H:%M:%S')})", html_timeline
            except Exception as e:
                return True, f"Lỗi khi lưu timeline: {e}", gr.update()

        save_btn.click(
            fn=on_save,
            inputs=[project_state, dirty_state, segment_dropdown],
            outputs=[dirty_state, status_box, timeline_html_map]
        )

        def on_reload_editor(filter_val):
            try:
                data = load_project_data(
                    timeline_path=timeline_path,
                    matching_candidates_path=matching_candidates_path,
                    clip_metadata_path=clip_metadata_path,
                    audio_segments_path=audio_segments_path,
                    media_metadata_path=media_metadata_path,
                    project_id=project_id,
                )
                transaction_log.reset(data)
                
                segment_options = get_segment_options(data, filter_val)
                initial_segment_id = data.timeline["items"][0]["segment_id"] if data.timeline["items"] else None
                initial_segment_details = load_segment_data(initial_segment_id, data)
                
                return [
                    data, False, transaction_log,
                    gr.update(choices=segment_options, value=initial_segment_id),
                    *initial_segment_details
                ]
            except Exception as e:
                from review_ui.loader import ProjectData
                dummy_data = ProjectData(
                    timeline={"items": [], "project_id": project_id or "demo_01"},
                    matching_candidates={"items": []},
                    clip_metadata={"items": []},
                    audio_segments={"items": []},
                    media_metadata={"videos": []}
                )
                return [
                    dummy_data, False, transaction_log,
                    gr.update(choices=[], value=None),
                    f"❌ Nạp dữ liệu thất bại: {e}", None, "", "", "", False, "",
                    gr.update(choices=[], value=None), gr.update(visible=False), gr.update(visible=True),
                    "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False,
                    None, None,
                    "Không có đề xuất", gr.update(choices=[]),
                    generate_timeline_html(dummy_data, None)
                ]

        reload_btn.click(
            fn=on_reload_editor,
            inputs=[filter_dropdown],
            outputs=[
                project_state, dirty_state, transaction_log_state,
                segment_dropdown,
                status_box, audio_player, transcript_box, conf_box, score_box, needs_review_cb, notes_box,
                vi_dropdown, inspector_group, create_vi_btn,
                clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                video_player, selected_vi_state,
                candidates_markdown, candidate_dropdown,
                timeline_html_map
            ],
            show_api=False,
        )

        # Helper function to load initial segment
        def load_initial_segment(data):
            items = data.timeline.get("items", [])
            initial_segment_id = items[0]["segment_id"] if items else None
            segment_options = get_segment_options(data, "all")
            return [
                gr.update(choices=segment_options, value=initial_segment_id),
                *load_segment_data(initial_segment_id, data)
            ]

        js_code = """
        () => {
            window.isGradioDirty = false;
            window.addEventListener('beforeunload', function (e) {
                if (window.isGradioDirty) {
                    e.preventDefault();
                    e.returnValue = 'Bạn có thay đổi chưa lưu. Bạn có chắc chắn muốn rời khỏi trang không?';
                }
            });

            function styleButtons() {
                document.querySelectorAll('.imovie-bottom-row *').forEach(el => {
                    if(el.style) el.style.color = '#111';
                });
            }
            
            setInterval(styleButtons, 500);
            document.body.addEventListener('click', () => setTimeout(styleButtons, 100));
        }
        """
        demo.load(
            fn=load_initial_segment,
            inputs=[project_state],
            outputs=[
                segment_dropdown,
                status_box, audio_player, transcript_box, conf_box, score_box, needs_review_cb, notes_box,
                vi_dropdown, inspector_group, create_vi_btn,
                clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                video_player, selected_vi_state,
                candidates_markdown, candidate_dropdown,
                timeline_html_map
            ],
            js=js_code
        )
        
        # Sync dirty state to JS variable for beforeunload
        dirty_state.change(
            fn=None,
            inputs=[dirty_state],
            js="(val) => { window.isGradioDirty = val; return []; }"
        )

def launch_review_ui(
    timeline_path,
    matching_candidates_path,
    clip_metadata_path,
    audio_segments_path,
    media_metadata_path,
    project_id=None,
    readonly=False,
    no_backup=False,
    log_path=None,
    host="127.0.0.1",
    port=7860,
):
    with gr.Blocks(title="Review UI — Audio-Guided Video Montage", css=custom_css) as demo:
        with gr.Row(elem_classes="capcut-nav-bar"):
            gr.HTML(
                f"""
                <div class="app-header">
                    <div class="app-logo">🎬</div>
                    <div>
                        <div class="app-title">Review UI</div>
                        <div class="app-subtitle">Audio-Guided Video Montage</div>
                    </div>
                </div>
                """
            )
        build_editor_tab(
            demo=demo,
            timeline_path=timeline_path,
            matching_candidates_path=matching_candidates_path,
            clip_metadata_path=clip_metadata_path,
            audio_segments_path=audio_segments_path,
            media_metadata_path=media_metadata_path,
            project_id=project_id,
            readonly=readonly,
            no_backup=no_backup,
            log_path=log_path,
        )
    demo.launch(
        server_name=host,
        server_port=port,
        allowed_paths=[REPO_ROOT],
    )
