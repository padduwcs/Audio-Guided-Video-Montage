"""Gradio UI app for Review UI (Stage 7).

- Hiển thị segment list, candidate list, preview, inspector
- Đổi clip, chỉnh tham số, validate/save, dirty state, readonly mode
- Tích hợp bộ quản lý trạng thái, cập nhật timeline.json
- Tích hợp Bản đồ Timeline trực quan (Visual Timeline Map) và Dashboard thống kê
- Giao diện phẳng (Flat mode), tối giản, màu sắc trung tính nhẹ nhàng, tối ưu dễ dùng
"""

import html
import os
import tempfile
import time
from urllib.parse import quote
import gradio as gr
import gradio_client.utils as gradio_client_utils
import soundfile as sf

from review_ui.loader import load_project_data
from review_ui.validator import validate_project_data
from review_ui.editor import replace_clip, create_visual_from_candidate, update_timing, update_speed, update_visual_properties
from review_ui.storage import save_timeline, backup_timeline
from review_ui.media import resolve_video_path
from review_ui.transaction_log import TransactionLog
from review_ui.theme import APP_THEME_CSS, THEME_JS, THEME_SWITCHER_HTML
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


def make_file_url(path):
    abs_path = make_abs(path)
    if not abs_path:
        return ""
    return "/gradio_api/file=" + quote(abs_path.replace("\\", "/"), safe="/:")


def final_video_html(path):
    abs_path = make_abs(path)
    if not abs_path or not os.path.exists(abs_path):
        return """
        <div class="final-video-empty">
            Video hoàn chỉnh chưa có sẵn trong phiên này.
        </div>
        """

    source = html.escape(make_file_url(abs_path), quote=True)
    return f"""
    <div class="final-video-player">
      <video controls preload="metadata" playsinline>
        <source src="{source}" type="video/mp4">
        Trình duyệt không hỗ trợ phát video này.
      </video>
    </div>
    """


def generate_timeline_html(data, selected_id):
    """
    Generate horizontal visual timeline HTML representing segments proportional to duration.
    Clean flat design for Light mode.
    """
    if not data or not getattr(data, "timeline", None):
        return "<p style='color: var(--app-text-muted); font-family: sans-serif; font-size: 13px;'>Timeline trống</p>"

    items = data.timeline.get("items", [])
    if not items:
        return "<p style='color: var(--app-text-muted); font-family: sans-serif; font-size: 13px;'>Timeline trống</p>"

    total_duration = sum(item["duration"] for item in items)
    if total_duration <= 0:
        total_duration = 1.0

    html_out = '<div class="storyboard-container" style="display: flex; overflow-x: auto; gap: 10px; padding: 15px; background-color: transparent; box-sizing: border-box;">'

    msgs = validate_project_data(data, mode="edit_save")
    needs_review_segs = {m.segment_id for m in msgs if m.code == "NEEDS_REVIEW"}
    error_segs = {m.segment_id for m in msgs if m.level == "error"}

    # Load user edited tags
    edited_segs = {item["segment_id"] for item in data.timeline["items"] if item.get("user_edited")}

    for item in items:
        sid = item["segment_id"]

        is_selected = (sid == selected_id)

        badge_html = ""
        if sid in error_segs:
            badge_html = '<span style="position: absolute; top: 4px; right: 4px; background: #ef4444; color: white; padding: 2px 4px; border-radius: 4px; font-size: 10px; font-weight: bold; z-index: 10;">Lỗi</span>'
        elif sid in needs_review_segs:
            badge_html = '<span style="position: absolute; top: 4px; right: 4px; background: #f59e0b; color: white; padding: 2px 4px; border-radius: 4px; font-size: 10px; font-weight: bold; z-index: 10;">Kiểm tra</span>'
        elif sid in edited_segs:
            badge_html = '<span style="position: absolute; top: 4px; right: 4px; background: #3b82f6; color: white; padding: 2px 4px; border-radius: 4px; font-size: 10px; font-weight: bold; z-index: 10;">Đã sửa</span>'

        border_style = "border: 3px solid var(--app-primary); box-shadow: 0 0 0 3px var(--app-primary-soft);" if is_selected else "border: 3px solid transparent;"

        bg_html = ""
        text_color = "var(--app-text-muted)"
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

        html_out += f'''
        <div style="flex: 0 0 auto; width: 140px; display: flex; flex-direction: column; gap: 8px; font-family: -apple-system, sans-serif; {border_style} border-radius: 8px; padding: 4px; transition: all 0.2s;" title="Phân đoạn: {sid}">
            <div style="height: 80px; background-color: {bg_color}; border-radius: 4px; position: relative; overflow: hidden; display: flex; justify-content: center; align-items: center; box-shadow: inset 0 0 10px rgba(0,0,0,0.1);">
                {bg_html}
                <span style="color: {text_color}; font-size: 14px; font-weight: 600; z-index: 10; text-shadow: {text_shadow};">{sid}</span>
                <span style="position: absolute; bottom: 4px; left: 4px; background: rgba(0,0,0,0.7); color: white; padding: 2px 5px; border-radius: 4px; font-size: 11px; z-index: 10;">{item["duration"]:.1f}s</span>
                {badge_html}
            </div>
            <div style="font-size: 12px; color: var(--app-text); text-align: center; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 2px;">
                {item["text"]}
            </div>
        </div>
        '''

    html_out += '</div>'

    edited_count = len(edited_segs)
    review_count = len(needs_review_segs)
    error_count = len(error_segs)

    html_out += f'''
    <div style="display: flex; gap: 15px; font-size: 12px; margin-top: 10px; flex-wrap: wrap; color: var(--app-text-muted); font-family: -apple-system, sans-serif; justify-content: center;">
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #a1a1aa; border-radius: 3px;"></span> Chưa sửa ({len(items) - edited_count})</div>
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #3b82f6; border-radius: 3px;"></span> Đã sửa ({edited_count})</div>
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #f59e0b; border-radius: 3px;"></span> Cần kiểm tra ({review_count})</div>
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #ef4444; border-radius: 3px;"></span> Lỗi ({error_count})</div>
        <div style="margin-left: 20px; color: var(--app-text); font-weight: 600;">Tổng: {total_duration:.2f}s | {len(items)} phân đoạn</div>
    </div>
    '''
    return html_out


def build_review_workspace(
    timeline_path=None,
    matching_candidates_path=None,
    clip_metadata_path=None,
    audio_segments_path=None,
    media_metadata_path=None,
    project_id=None,
    readonly=False,
    no_backup=False,
    log_path=None,
    show_header=False,
):
    """Build review workspace components into the current active Gradio context."""
    timeline_path = timeline_path or os.path.join(REPO_ROOT, "data", "intermediate", "timeline.json")
    matching_candidates_path = matching_candidates_path or os.path.join(REPO_ROOT, "data", "intermediate", "matching_candidates.json")
    clip_metadata_path = clip_metadata_path or os.path.join(REPO_ROOT, "data", "intermediate", "clip_metadata.json")
    audio_segments_path = audio_segments_path or os.path.join(REPO_ROOT, "data", "intermediate", "audio_segments.json")
    media_metadata_path = media_metadata_path or os.path.join(REPO_ROOT, "data", "intermediate", "media_metadata.json")

    def _check_files_exist():
        return all(
            os.path.exists(p)
            for p in [timeline_path, matching_candidates_path, clip_metadata_path, audio_segments_path, media_metadata_path]
        )

    initial_exist = _check_files_exist()
    project_data = None
    transaction_log = TransactionLog()

    if initial_exist:
        try:
            project_data = load_project_data(
                timeline_path=timeline_path,
                matching_candidates_path=matching_candidates_path,
                clip_metadata_path=clip_metadata_path,
                audio_segments_path=audio_segments_path,
                media_metadata_path=media_metadata_path,
                project_id=project_id,
            )
            transaction_log.reset(project_data)

            if not readonly and not no_backup:
                try:
                    backup_path = timeline_path + ".before_review.json"
                    backup_timeline(project_data.timeline, backup_path)
                except Exception as e:
                    print(f"[Warning] Failed to create initial backup: {e}")
        except Exception as e:
            print(f"[Warning] Initial project load failed: {e}")
            initial_exist = False

    def get_segment_options(data, filter_type="all"):
        if not data or not getattr(data, "timeline", None):
            return []
        options = []
        msgs = validate_project_data(data, mode="edit_save")

        needs_review_segs = {m.segment_id for m in msgs if m.code == "NEEDS_REVIEW"}
        low_conf_segs = {m.segment_id for m in msgs if m.code == "LOW_CONFIDENCE"}
        fallback_segs = {m.segment_id for m in msgs if m.code == "FALLBACK_USED"}
        missing_visual_segs = {m.segment_id for m in msgs if m.code == "MISSING_VISUAL"}
        error_segs = {m.segment_id for m in msgs if m.level == "error"}

        edited_segs = {item["segment_id"] for item in data.timeline["items"] if item.get("user_edited")}

        for item in data.timeline["items"]:
            sid = item["segment_id"]

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
                badge = "[Kiểm tra] "
            elif sid in edited_segs:
                badge = "[Sửa] "
            elif sid in missing_visual_segs:
                badge = "[Trống] "

            text = f"{badge}{sid} | {item['text'][:35]}..."
            options.append((text, sid))
        return options

    def slice_audio(audio_path, start, end):
        abs_audio = make_abs(audio_path)
        if not abs_audio or not os.path.exists(abs_audio):
            return None
        try:
            data, sr = sf.read(abs_audio)
            start_frame = int(start * sr)
            end_frame = int(end * sr)
            start_frame = max(0, min(start_frame, len(data)))
            end_frame = max(0, min(end_frame, len(data)))
            segment_data = data[start_frame:end_frame]

            tmp_wav_dir = os.path.join(REPO_ROOT, "tmp")
            os.makedirs(tmp_wav_dir, exist_ok=True)
            with tempfile.NamedTemporaryFile(suffix=".wav", dir=tmp_wav_dir, delete=False) as tmpf:
                sf.write(tmpf.name, segment_data, sr)
                return tmpf.name
        except Exception as e:
            print(f"[Error] Failed to slice audio: {e}")
            return None

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
        except Exception:
            return abs_video

    with gr.Column(elem_classes="review-workspace-shell"):
        if show_header:
            proj_title = project_data.timeline.get('project_id') if project_data else "Chưa có"
            gr.HTML(
                f"""
                <div class="workspace-header">
                  <div>
                    <div class="workspace-title"><strong>Không gian chỉnh sửa</strong> — {proj_title}</div>
                    <div class="workspace-meta">Timeline: <code>{os.path.basename(timeline_path)}</code></div>
                  </div>
                  {THEME_SWITCHER_HTML}
                </div>
                """
            )

        # State variables
        project_state = gr.State(project_data)
        dirty_state = gr.State(False)
        selected_vi_state = gr.State("")
        transaction_log_state = gr.State(transaction_log)

        # Container when draft does not exist yet
        no_draft_panel = gr.Group(visible=not initial_exist)
        with no_draft_panel:
            with gr.Column(elem_classes="simple-panel"):
                gr.Markdown(
                    "### Bản nháp chưa sẵn sàng\n"
                    "Vui lòng chuyển sang Tab **Bắt đầu** để chọn các file video nguồn, voice-over và thực hiện **Tạo bản nháp video** trước."
                )
                refresh_data_btn = gr.Button("Tải lại dữ liệu bản nháp", variant="primary")

        # Container for main editor layout
        editor_panel = gr.Group(visible=initial_exist)
        with editor_panel:
            with gr.Row():
                gr.Markdown("### Chỉnh sửa bản dựng\nXem từng đoạn, so sánh clip gợi ý, điều chỉnh thuộc tính và lưu timeline.")
                refresh_editor_btn = gr.Button("Tải lại dữ liệu", variant="secondary", scale=0)

            with gr.Row(elem_classes="imovie-top-row"):
                with gr.Column(scale=3, elem_classes="imovie-media-panel", min_width=350):
                    with gr.Tabs():
                        with gr.Tab("Phân đoạn"):
                            gr.Markdown("### Quản lý phân đoạn")
                            with gr.Row():
                                filter_dropdown = gr.Dropdown(
                                    choices=[("Tất cả", "all"), ("Cần review", "needs_review"), ("Độ tin cậy thấp", "low_confidence"), ("Sử dụng fallback", "fallback"), ("Đã chỉnh sửa", "edited"), ("Thiếu hình ảnh", "missing_visual"), ("Có lỗi", "error")],
                                    value="all", label="Lọc điều kiện", scale=1
                                )
                                initial_segs = get_segment_options(project_data, "all")
                                initial_first_sid = project_data.timeline["items"][0]["segment_id"] if (project_data and project_data.timeline.get("items")) else None
                                segment_dropdown = gr.Dropdown(choices=initial_segs, value=initial_first_sid, label="Chọn phân đoạn", scale=2)

                            gr.Markdown("### Clip thay thế được đề xuất")
                            candidates_markdown = gr.Markdown("Không có đề xuất.")
                            with gr.Row():
                                candidate_dropdown = gr.Dropdown(choices=[], label="Chọn clip gợi ý", scale=2, interactive=not readonly)
                                choose_cand_btn = gr.Button("Thay clip", variant="primary", scale=1, interactive=not readonly)

                            status_box = gr.Markdown("Sẵn sàng.")
                            with gr.Row():
                                undo_btn = gr.Button("↶ Hoàn tác", variant="secondary", interactive=True)
                                redo_btn = gr.Button("↷ Làm lại", variant="secondary", interactive=True)
                            with gr.Row():
                                save_btn = gr.Button("Lưu thay đổi", variant="primary", interactive=not readonly)
                                render_btn = gr.Button("Xuất video", variant="secondary", interactive=not readonly)

                        with gr.Tab("Âm thanh và văn bản"):
                            audio_player = gr.Audio(label="Âm thanh gốc", interactive=False)
                            transcript_box = gr.Textbox(label="Lời thoại", interactive=False, lines=4)
                            with gr.Row():
                                conf_box = gr.Textbox(label="Độ tin cậy", interactive=False)
                                score_box = gr.Textbox(label="Điểm số", interactive=False)
                            needs_review_cb = gr.Checkbox(label="Cần kiểm tra lại", interactive=not readonly)
                            notes_box = gr.Textbox(label="Ghi chú", interactive=not readonly)
                            apply_properties_btn = gr.Button("Cập nhật ghi chú", variant="secondary", interactive=not readonly)

                        with gr.Tab("Dự án và nhật ký"):
                            validate_btn = gr.Button("Kiểm lỗi dự án", variant="secondary")
                            export_audit_btn = gr.Button("Xuất nhật ký thao tác", variant="secondary")
                            audit_log_box = gr.Textbox(label="Nhật ký thao tác (JSON)", lines=5, interactive=False)

                # CENTER: Video Preview
                with gr.Column(scale=4, elem_classes="imovie-preview-panel", min_width=400):
                    with gr.Tabs(selected="preview_tab") as video_tabs:
                        with gr.Tab("Xem trước clip", id="preview_tab"):
                            video_player = gr.Video(label="Clip đang chọn", interactive=False, height=450)
                        with gr.Tab("Video hoàn chỉnh", id="render_tab"):
                            final_video_player = gr.HTML(final_video_html(None))

                # RIGHT SIDE: Inspector Panel
                with gr.Column(scale=3, elem_classes="imovie-media-panel", min_width=350):
                    with gr.Accordion("Thuộc tính clip", open=True):
                        with gr.Row():
                            vi_dropdown = gr.Dropdown(choices=[], label="Lớp video", interactive=True, scale=2)
                            create_vi_btn = gr.Button("Tạo từ clip gợi ý", variant="secondary", visible=False, interactive=not readonly, scale=1)

                        inspector_group = gr.Group(visible=True)
                        with inspector_group:
                            with gr.Row():
                                clip_id_input = gr.Textbox(label="Mã clip", interactive=False)
                                video_id_input = gr.Textbox(label="Mã video", interactive=False)
                            source_path_input = gr.Textbox(label="Nguồn", interactive=False)
                            with gr.Row():
                                clip_start_input = gr.Number(label="Bắt đầu (giây)", interactive=not readonly)
                                clip_end_input = gr.Number(label="Kết thúc (giây)", interactive=not readonly)
                            with gr.Row():
                                speed_input = gr.Number(label="Tốc độ", value=1.0, interactive=not readonly)
                                transition_input = gr.Dropdown(choices=["cut", "fade", "crossfade", "slide"], value="cut", label="Chuyển cảnh", interactive=not readonly)
                            with gr.Row():
                                crop_mode_input = gr.Dropdown(choices=[("Vừa khung", "fit"), ("Nền làm mờ", "blur_padding"), ("Cắt giữa", "center_crop"), ("Lấp đầy", "fill")], value="fit", label="Chế độ khung hình", interactive=not readonly)
                                volume_input = gr.Number(label="Âm lượng", value=0.0, interactive=not readonly)
                            locked_input = gr.Checkbox(label="Khóa clip", interactive=not readonly)
                            update_inspector_btn = gr.Button("Áp dụng thay đổi", variant="primary", interactive=not readonly)

            # BOTTOM: Visual Timeline Map
            with gr.Row(elem_classes="imovie-bottom-row"):
                with gr.Column(elem_classes="imovie-storyboard-panel"):
                    gr.Markdown("### Bản đồ Timeline trực quan")
                    timeline_html_map = gr.HTML(generate_timeline_html(project_data, None))

        # Helper function to refresh segment data
        def load_segment_data(segment_id, data):
            if not data or not getattr(data, "timeline", None) or not segment_id:
                return [
                    "Không tìm thấy segment", None, "", "", "", False, "",
                    gr.update(choices=[], value=None), gr.update(visible=False), gr.update(visible=False),
                    "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False,
                    None, None,
                    "Không có đề xuất", gr.update(choices=[]),
                    generate_timeline_html(data, None)
                ]

            item = next((i for i in data.timeline["items"] if i["segment_id"] == segment_id), None)
            if not item:
                return [
                    "Không tìm thấy segment", None, "", "", "", False, "",
                    gr.update(choices=[], value=None), gr.update(visible=False), gr.update(visible=False),
                    "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False,
                    None, None,
                    "Không có đề xuất", gr.update(choices=[]),
                    generate_timeline_html(data, segment_id)
                ]

            audio_path = data.media_metadata.get("audio", {}).get("normalized_path")
            audio_preview = slice_audio(audio_path, item["audio_start"], item["audio_end"])

            info = f"Lời thoại: {item['text']}\nThời lượng: {item['audio_start']} - {item['audio_end']}s ({item['duration']}s)"
            transcript = item["text"]
            conf = item["confidence"]
            score = str(item["score"]) if item.get("score") is not None else "Không có"
            needs_review = item.get("needs_review", False)
            notes = item.get("notes", "")

            vi_items = item.get("visual_items", [])
            vi_choices = [(f"{v['timeline_item_id']} | Clip: {v['clip_id']}", v['timeline_item_id']) for v in vi_items]

            selected_vi_id = vi_items[0]["timeline_item_id"] if vi_items else None

            cref = item.get("candidates_ref")
            candidate_set = data.candidate_sets_by_id.get(cref)
            cand_md = ""
            cand_choices = []
            if candidate_set:
                cand_md = "#### Clip gợi ý có sẵn:\n"
                for cand in candidate_set.get("candidates", []):
                    cand_md += f"* **Hạng {cand['rank']}**: `{cand['clip_id']}` (Điểm: {cand['final_score']:.2f})\n"
                    cand_choices.append((f"Hạng {cand['rank']} | {cand['clip_id']} ({cand['final_score']:.2f})", cand['clip_id']))
            else:
                cand_md = "Không có đề xuất"

            active_vi = next((v for v in vi_items if v["timeline_item_id"] == selected_vi_id), None) if selected_vi_id else None

            video_preview = None
            if selected_vi_id and active_vi:
                rel_path = resolve_video_path(data, segment_id, selected_vi_id)
                video_preview = slice_video(
                    rel_path,
                    active_vi["clip_start"],
                    active_vi["clip_end"],
                    speed=active_vi.get("speed", 1.0),
                    crop_mode=active_vi.get("crop_mode"),
                    render_settings=data.timeline.get("render_settings", {}),
                )

            html_timeline = generate_timeline_html(data, segment_id)

            if active_vi:
                clip_id = active_vi["clip_id"]
                video_id = active_vi["video_id"]
                src_path = active_vi["source_path"]
                c_start = active_vi["clip_start"]
                c_end = active_vi["clip_end"]
                speed = active_vi["speed"]
                trans = active_vi["transition"]
                crop = active_vi.get("crop_mode", "fit")
                vol = active_vi.get("volume", 0.0)
                locked = active_vi.get("locked", False)

                return [
                    info, audio_preview, transcript, conf, score, needs_review, notes,
                    gr.update(choices=vi_choices, value=selected_vi_id),
                    gr.update(visible=True),
                    gr.update(visible=False),
                    clip_id, video_id, src_path, c_start, c_end, speed, trans, crop, vol, locked,
                    video_preview, selected_vi_id,
                    cand_md, gr.update(choices=cand_choices),
                    html_timeline
                ]
            else:
                return [
                    info, audio_preview, transcript, conf, score, needs_review, notes,
                    gr.update(choices=[], value=None),
                    gr.update(visible=False),
                    gr.update(visible=True),
                    "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False,
                    None, None,
                    cand_md, gr.update(choices=cand_choices),
                    html_timeline
                ]

        def load_initial_segment(data):
            if not data or not getattr(data, "timeline", None) or not data.timeline.get("items"):
                return [
                    "Chưa có dữ liệu phân đoạn", None, "", "", "", False, "",
                    gr.update(choices=[], value=None), gr.update(visible=False), gr.update(visible=False),
                    "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False,
                    None, None,
                    "Không có đề xuất", gr.update(choices=[]),
                    generate_timeline_html(data, None)
                ]
            first_sid = data.timeline["items"][0]["segment_id"]
            return load_segment_data(first_sid, data)

        def on_filter_change(filter_val, data):
            opts = get_segment_options(data, filter_val)
            val = opts[0][1] if opts else None
            return gr.update(choices=opts, value=val)

        filter_dropdown.change(
            fn=on_filter_change,
            inputs=[filter_dropdown, project_state],
            outputs=[segment_dropdown]
        )

        segment_dropdown.change(
            fn=load_segment_data,
            inputs=[segment_dropdown, project_state],
            outputs=[
                status_box, audio_player, transcript_box, conf_box, score_box, needs_review_cb, notes_box,
                vi_dropdown, inspector_group, create_vi_btn,
                clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                video_player, selected_vi_state,
                candidates_markdown, candidate_dropdown,
                timeline_html_map
            ]
        )

        def on_vi_change(segment_id, vi_id, data):
            if not data or not vi_id or not segment_id:
                return gr.update(), "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False, None, vi_id
            item = next((i for i in data.timeline["items"] if i["segment_id"] == segment_id), None)
            if not item:
                return gr.update(), "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False, None, vi_id
            vi = next((v for v in item["visual_items"] if v["timeline_item_id"] == vi_id), None)
            if not vi:
                return gr.update(), "", "", "", 0, 0, 1.0, "cut", "fit", 0.0, False, None, vi_id

            rel_path = resolve_video_path(data, segment_id, vi_id)
            video_preview = slice_video(
                rel_path,
                vi["clip_start"],
                vi["clip_end"],
                speed=vi.get("speed", 1.0),
                crop_mode=vi.get("crop_mode"),
                render_settings=data.timeline.get("render_settings", {}),
            )
            return (
                gr.update(visible=True),
                vi["clip_id"], vi["video_id"], vi["source_path"],
                vi["clip_start"], vi["clip_end"], vi["speed"],
                vi["transition"], vi.get("crop_mode", "fit"), vi.get("volume", 0.0), vi.get("locked", False),
                video_preview, vi_id
            )

        vi_dropdown.change(
            fn=on_vi_change,
            inputs=[segment_dropdown, vi_dropdown, project_state],
            outputs=[
                inspector_group,
                clip_id_input, video_id_input, source_path_input,
                clip_start_input, clip_end_input, speed_input,
                transition_input, crop_mode_input, volume_input, locked_input,
                video_player, selected_vi_state
            ]
        )

        def on_apply_properties(segment_id, needs_review, notes, data, tlog):
            if readonly:
                return data, False, "Chế độ chỉ xem.", tlog
            try:
                item = next(i for i in data.timeline["items"] if i["segment_id"] == segment_id)
                item["needs_review"] = needs_review
                item["notes"] = notes
                item["user_edited"] = True
                tlog.record_state(data, f"properties:{segment_id}")
                html_timeline = generate_timeline_html(data, segment_id)
                return data, True, "Đã cập nhật ghi chú phân đoạn.", html_timeline, tlog
            except Exception as e:
                return data, True, f"Lỗi cập nhật ghi chú: {e}", gr.update(), tlog

        apply_properties_btn.click(
            fn=on_apply_properties,
            inputs=[segment_dropdown, needs_review_cb, notes_box, project_state, transaction_log_state],
            outputs=[project_state, dirty_state, status_box, timeline_html_map, transaction_log_state]
        )

        def on_undo(data, tlog, current_segment_id):
            if not tlog.can_undo():
                return data, False, "Không thể hoàn tác thêm.", gr.update(), tlog
            prev_state = tlog.undo()
            data.timeline = prev_state["timeline"]
            res = load_segment_data(current_segment_id, data)
            return [data, True, "Đã hoàn tác.", res[24], tlog]

        def on_redo(data, tlog, current_segment_id):
            if not tlog.can_redo():
                return data, False, "Không thể làm lại thêm.", gr.update(), tlog
            next_state = tlog.redo()
            data.timeline = next_state["timeline"]
            res = load_segment_data(current_segment_id, data)
            return [data, True, "Đã làm lại.", res[24], tlog]

        undo_btn.click(
            fn=on_undo,
            inputs=[project_state, transaction_log_state, segment_dropdown],
            outputs=[project_state, dirty_state, status_box, timeline_html_map, transaction_log_state]
        )

        redo_btn.click(
            fn=on_redo,
            inputs=[project_state, transaction_log_state, segment_dropdown],
            outputs=[project_state, dirty_state, status_box, timeline_html_map, transaction_log_state]
        )

        def on_apply_inspector(segment_id, vi_id, clip_start, clip_end, speed, transition, crop_mode, volume, locked, data, tlog):
            if readonly:
                return data, False, None, gr.update(), gr.update(), gr.update(), "Chế độ chỉ xem.", gr.update(), tlog
            try:
                update_timing(data, segment_id, vi_id, clip_start, clip_end)
                update_speed(data, segment_id, vi_id, speed)
                update_visual_properties(
                    data, segment_id, vi_id,
                    transition=transition, crop_mode=crop_mode, volume=volume, locked=locked
                )
                tlog.record_state(data, f"apply_inspector:{segment_id}:{vi_id}")
                item = next(i for i in data.timeline["items"] if i["segment_id"] == segment_id)
                vi = next(v for v in item["visual_items"] if v["timeline_item_id"] == vi_id)

                rel_path = resolve_video_path(data, segment_id, vi_id)
                abs_video = slice_video(
                    rel_path,
                    vi["clip_start"],
                    vi["clip_end"],
                    speed=vi.get("speed", 1.0),
                    crop_mode=vi.get("crop_mode"),
                    render_settings=data.timeline.get("render_settings", {}),
                )
                html_timeline = generate_timeline_html(data, segment_id)
                return data, True, abs_video, vi["clip_start"], vi["clip_end"], vi["speed"], "Đã áp dụng các thay đổi.", html_timeline, tlog
            except Exception as e:
                return data, True, None, clip_start, clip_end, speed, f"Lỗi áp dụng chỉnh sửa: {e}", gr.update(), tlog

        update_inspector_btn.click(
            fn=on_apply_inspector,
            inputs=[
                segment_dropdown, selected_vi_state,
                clip_start_input, clip_end_input, speed_input,
                transition_input, crop_mode_input, volume_input, locked_input,
                project_state, transaction_log_state
            ],
            outputs=[project_state, dirty_state, video_player, clip_start_input, clip_end_input, speed_input, status_box, timeline_html_map, transaction_log_state]
        )

        def on_choose_candidate(segment_id, vi_id, cand_clip_id, data, tlog):
            if readonly:
                return data, False, None, "Chế độ chỉ xem.", gr.update(), gr.update(), gr.update(), tlog
            try:
                if vi_id:
                    replace_clip(data, segment_id, vi_id, cand_clip_id)
                    action_msg = f"Đã thay lớp video {vi_id} bằng clip {cand_clip_id}."
                else:
                    create_visual_from_candidate(data, segment_id, cand_clip_id)
                    action_msg = f"Đã tạo lớp video mới từ clip {cand_clip_id}."
                tlog.record_state(data, f"choose_candidate:{segment_id}:{vi_id}:{cand_clip_id}")
                res = load_segment_data(segment_id, data)
                return [
                    data, True, res[20], action_msg,
                    res[7], res[21], res[24], tlog
                ]
            except Exception as e:
                return [
                    data, True, None, f"Lỗi thay thế clip: {e}",
                    gr.update(), vi_id, gr.update(), tlog
                ]

        choose_cand_btn.click(
            fn=on_choose_candidate,
            inputs=[segment_dropdown, selected_vi_state, candidate_dropdown, project_state, transaction_log_state],
            outputs=[project_state, dirty_state, video_player, status_box, vi_dropdown, selected_vi_state, timeline_html_map, transaction_log_state]
        )

        create_vi_btn.click(
            fn=on_choose_candidate,
            inputs=[segment_dropdown, selected_vi_state, candidate_dropdown, project_state, transaction_log_state],
            outputs=[project_state, dirty_state, video_player, status_box, vi_dropdown, selected_vi_state, timeline_html_map, transaction_log_state]
        )

        def on_validate(data):
            try:
                msgs = validate_project_data(data, mode="edit_save")
                errors = [m for m in msgs if m.level == "error"]
                warnings = [m for m in msgs if m.level == "warning"]

                res_text = "### Kết quả kiểm tra\n"
                res_text += f"* **Lỗi chặn**: {len(errors)}\n"
                res_text += f"* **Cảnh báo**: {len(warnings)}\n\n"

                if errors:
                    res_text += "#### Lỗi nghiêm trọng (Chặn lưu):\n"
                    for err in errors:
                        res_text += f"- **{err.code}**: {err.message} (Phân đoạn: `{err.segment_id}`)\n"
                if warnings:
                    res_text += "#### Cảnh báo (Cho phép lưu):\n"
                    for warn in warnings:
                        res_text += f"- **{warn.code}**: {warn.message} (Phân đoạn: `{warn.segment_id}`)\n"
                if not errors and not warnings:
                    res_text += "Không tìm thấy lỗi nào. Sẵn sàng render!"
                return res_text
            except Exception as e:
                return f"Lỗi tiến trình kiểm tra: {e}"

        validate_btn.click(
            fn=on_validate,
            inputs=[project_state],
            outputs=[status_box]
        )

        def on_save(data, is_dirty, segment_id):
            if readonly:
                return False, "Chế độ chỉ xem. Không thể lưu file.", gr.update()
            if not is_dirty:
                return False, "Không có thay đổi nào cần lưu.", gr.update()
            try:
                save_timeline(
                    data.timeline, timeline_path,
                    validate_fn=lambda t: validate_project_data(data, mode="edit_save")
                )

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

                html_timeline = generate_timeline_html(data, segment_id)
                return False, f"Đã lưu timeline thành công! ({time.strftime('%H:%M:%S')})", html_timeline
            except Exception as e:
                return True, f"Lỗi khi lưu timeline: {e}", gr.update()

        save_btn.click(
            fn=on_save,
            inputs=[project_state, dirty_state, segment_dropdown],
            outputs=[dirty_state, status_box, timeline_html_map]
        )

        # Render final video callback
        def on_render_editor(data, is_dirty, progress=gr.Progress()):
            if is_dirty:
                try:
                    save_timeline(
                        data.timeline, timeline_path,
                        validate_fn=lambda t: validate_project_data(data, mode="edit_save")
                    )
                except Exception as e:
                    return final_video_html(None), f"Tự động lưu thất bại: {e}. Vui lòng kiểm tra lại!", is_dirty, gr.update()

            msgs = validate_project_data(data, mode="renderer_handoff")
            errors = [m for m in msgs if m.level == "error"]
            if errors:
                err_msg = "\n".join([f"- Phân đoạn {err.segment_id}: {err.message}" for err in errors[:5]])
                if len(errors) > 5:
                    err_msg += f"\n... và {len(errors) - 5} lỗi khác."
                return final_video_html(None), f"Lỗi không thể render:\n{err_msg}", is_dirty, gr.update()

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
                return final_video_html(output_video_path), "Xuất video thành công tại data/final/final_video.mp4!", False, gr.update(selected="render_tab")
            except Exception as e:
                return final_video_html(None), f"Xuất video thất bại: {e}", is_dirty, gr.update()

        render_btn.click(
            fn=on_render_editor,
            inputs=[project_state, dirty_state],
            outputs=[final_video_player, status_box, dirty_state, video_tabs]
        )

        def on_export_audit(data, tlog):
            try:
                audit_log = tlog.export_audit_log()
                import json
                return json.dumps(audit_log, indent=2, ensure_ascii=False)
            except Exception as e:
                return f"Lỗi xuất audit log: {e}"

        export_audit_btn.click(
            fn=on_export_audit,
            inputs=[project_state, transaction_log_state],
            outputs=[audit_log_box]
        )

        # Reload function for refreshing workspace when draft files are updated
        def reload_workspace_data():
            files_ok = _check_files_exist()
            if not files_ok:
                return [
                    gr.update(visible=True),   # no_draft_panel
                    gr.update(visible=False),  # editor_panel
                    None,                      # project_state
                    gr.update(choices=[], value=None), # segment_dropdown
                    "Bản nháp chưa sẵn sàng."  # status_box
                ] + [gr.update()] * 20
            try:
                new_data = load_project_data(
                    timeline_path=timeline_path,
                    matching_candidates_path=matching_candidates_path,
                    clip_metadata_path=clip_metadata_path,
                    audio_segments_path=audio_segments_path,
                    media_metadata_path=media_metadata_path,
                    project_id=project_id,
                )
                opts = get_segment_options(new_data, "all")
                first_sid = new_data.timeline["items"][0]["segment_id"] if (new_data.timeline and new_data.timeline.get("items")) else None
                seg_res = load_segment_data(first_sid, new_data)
                return [
                    gr.update(visible=False),  # no_draft_panel
                    gr.update(visible=True),   # editor_panel
                    new_data,                  # project_state
                    gr.update(choices=opts, value=first_sid),
                    *seg_res
                ]
            except Exception as e:
                return [
                    gr.update(visible=True),
                    gr.update(visible=False),
                    None,
                    gr.update(choices=[], value=None),
                    f"Lỗi nạp dữ liệu: {e}"
                ] + [gr.update()] * 20

        reload_outputs = [
            no_draft_panel, editor_panel, project_state, segment_dropdown,
            status_box, audio_player, transcript_box, conf_box, score_box, needs_review_cb, notes_box,
            vi_dropdown, inspector_group, create_vi_btn,
            clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
            video_player, selected_vi_state,
            candidates_markdown, candidate_dropdown,
            timeline_html_map
        ]

        refresh_data_btn.click(
            fn=reload_workspace_data,
            outputs=reload_outputs
        )
        refresh_editor_btn.click(
            fn=reload_workspace_data,
            outputs=reload_outputs
        )


        dirty_state.change(
            fn=None,
            inputs=[dirty_state],
            js="(val) => { window.isGradioDirty = val; return []; }"
        )

    return {
        "reload_fn": reload_workspace_data,
        "reload_outputs": reload_outputs,
        "editor_panel": editor_panel,
        "no_draft_panel": no_draft_panel,
        "project_state": project_state,
    }


def launch_review_ui(
    timeline_path=None,
    matching_candidates_path=None,
    clip_metadata_path=None,
    audio_segments_path=None,
    media_metadata_path=None,
    project_id=None,
    readonly=False,
    no_backup=False,
    log_path=None,
    host="127.0.0.1",
    port=7860,
):
    with gr.Blocks(title="Không gian chỉnh sửa", css=APP_THEME_CSS) as demo:
        build_review_workspace(
            timeline_path=timeline_path,
            matching_candidates_path=matching_candidates_path,
            clip_metadata_path=clip_metadata_path,
            audio_segments_path=audio_segments_path,
            media_metadata_path=media_metadata_path,
            project_id=project_id,
            readonly=readonly,
            no_backup=no_backup,
            log_path=log_path,
            show_header=True,
        )
        demo.load(fn=None, js=THEME_JS)

    demo.launch(
        server_name=host,
        server_port=port,
        allowed_paths=[REPO_ROOT],
    )
