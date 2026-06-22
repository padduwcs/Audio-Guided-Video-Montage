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
import soundfile as sf
import numpy as np

from review_ui.loader import load_project_data
from review_ui.validator import validate_project_data
from review_ui.editor import replace_clip, create_visual_from_candidate, update_timing, update_speed, mark_reviewed, update_visual_properties
from review_ui.storage import save_timeline, backup_timeline
from review_ui.media import resolve_video_path, resolve_audio_path
from review_ui.transaction_log import TransactionLog

# Resolve Repo Root Path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
        
    html = '<div style="display: flex; width: 100%; height: 48px; background-color: #f1f5f9; border-radius: 6px; overflow: hidden; border: 1px solid #cbd5e1; margin-bottom: 12px; box-sizing: border-box;">'
    
    msgs = validate_project_data(data, mode="edit_save")
    needs_review_segs = {m.segment_id for m in msgs if m.code == "NEEDS_REVIEW"}
    error_segs = {m.segment_id for m in msgs if m.level == "error"}
    
    # Load user edited tags
    edited_segs = {item["segment_id"] for item in data.timeline["items"] if item.get("user_edited")}

    for item in items:
        sid = item["segment_id"]
        pct = (item["duration"] / total_duration) * 100
        
        # Determine background color
        is_selected = (sid == selected_id)
        
        if sid in error_segs:
            bg_color = "#ef4444"      # Flat Red
            text_color = "#ffffff"
        elif sid in needs_review_segs:
            bg_color = "#f59e0b"      # Flat Yellow
            text_color = "#1e293b"
        elif sid in edited_segs:
            bg_color = "#3b82f6"      # Flat Blue
            text_color = "#ffffff"
        else:
            bg_color = "#e2e8f0"      # Flat Light Gray
            text_color = "#475569"
            
        border_style = "border: 3px solid #0f172a; font-weight: bold;" if is_selected else "border-right: 1px solid #cbd5e1;"
        
        html += f'''
        <div style="flex-grow: 0; flex-shrink: 0; width: {pct:.2f}%; height: 100%; background-color: {bg_color}; {border_style} display: flex; flex-direction: column; justify-content: center; align-items: center; padding: 4px; box-sizing: border-box; cursor: pointer; font-family: sans-serif;" title="Segment: {sid} | Duration: {item["duration"]}s">
            <span style="font-size: 11px; font-weight: bold; color: {text_color}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%;">{sid}</span>
            <span style="font-size: 8px; color: {text_color}; opacity: 0.85; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%;">{item["text"][:12]}</span>
        </div>
        '''
        
    html += '</div>'
    
    # Legend & stats dashboard
    edited_count = len(edited_segs)
    review_count = len(needs_review_segs)
    error_count = len(error_segs)
    
    html += f'''
    <div style="display: flex; gap: 15px; font-size: 12px; margin-bottom: 15px; flex-wrap: wrap; color: #475569; border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; font-family: sans-serif;">
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #e2e8f0; border-radius: 3px; border: 1px solid #94a3b8;"></span> Chưa sửa ({len(items) - edited_count})</div>
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #3b82f6; border-radius: 3px;"></span> Đã sửa ({edited_count})</div>
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #f59e0b; border-radius: 3px;"></span> Cần Review ({review_count})</div>
        <div style="display: flex; align-items: center; gap: 6px;"><span style="display: inline-block; width: 12px; height: 12px; background-color: #ef4444; border-radius: 3px;"></span> Lỗi ({error_count})</div>
        <div style="margin-left: auto; color: #0f172a; font-weight: bold;">Tổng thời lượng: {total_duration:.2f}s | Phân đoạn: {len(items)}</div>
    </div>
    '''
    return html

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
    # Initial load of project data
    project_data = load_project_data(
        timeline_path=timeline_path,
        matching_candidates_path=matching_candidates_path,
        clip_metadata_path=clip_metadata_path,
        audio_segments_path=audio_segments_path,
        media_metadata_path=media_metadata_path,
        project_id=project_id,
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

    # Load layout
    with gr.Blocks(title="Review UI - Audio-Guided Video Montage") as demo:
        gr.Markdown(
            f"""
            # Review UI - Biên tập & Chỉnh sửa phân đoạn timeline
            Dự án: **{project_data.timeline.get('project_id')}** | Tập tin: `{os.path.basename(timeline_path)}`
            """
        )
        
        # App state variables
        project_state = gr.State(project_data)
        dirty_state = gr.State(False)
        selected_vi_state = gr.State("") # Current visual item id
        transaction_log_state = gr.State(transaction_log)

        # Header status section
        with gr.Row():
            with gr.Column(scale=2):
                status_box = gr.Markdown("Giao diện đã sẵn sàng.")
            with gr.Column(scale=1):
                with gr.Row():
                    undo_btn = gr.Button("↶ Undo", variant="secondary", interactive=True)
                    redo_btn = gr.Button("↷ Redo", variant="secondary", interactive=True)
                save_btn = gr.Button("Lưu Thay Đổi", variant="primary", interactive=not readonly)
                validate_btn = gr.Button("Kiểm lỗi", variant="secondary")

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

        export_audit_btn = gr.Button("Export Audit Log", variant="secondary")
        audit_log_box = gr.Textbox(label="Audit Log (JSON)", lines=8, interactive=False)

        export_audit_btn.click(
            fn=on_export_audit_log,
            inputs=[transaction_log_state],
            outputs=[audit_log_box]
        )

        # Premium Timeline Map at the top
        gr.Markdown("### Bản đồ phân đoạn Timeline")
        timeline_html_map = gr.HTML(generate_timeline_html(project_data, None))

        # 3 Column layout
        with gr.Row():
            # Column 1: Segments List & Details
            with gr.Column(scale=1):
                gr.Markdown("### Danh sách phân đoạn")
                filter_dropdown = gr.Dropdown(
                    choices=[
                        ("Tất cả", "all"),
                        ("Cần review", "needs_review"),
                        ("Độ tin cậy thấp", "low_confidence"),
                        ("Sử dụng fallback", "fallback"),
                        ("Đã chỉnh sửa", "edited"),
                        ("Thiếu hình ảnh", "missing_visual"),
                        ("Có lỗi", "error"),
                    ],
                    value="all",
                    label="Lọc theo điều kiện"
                )
                
                segment_dropdown = gr.Dropdown(
                    choices=get_segment_options(project_data, "all"),
                    value=project_data.timeline["items"][0]["segment_id"] if project_data.timeline["items"] else None,
                    label="Chọn phân đoạn"
                )

                gr.Markdown("### Preview Thuyết Minh")
                audio_player = gr.Audio(label="File audio segment", interactive=False)
                transcript_box = gr.Textbox(label="Nội dung lời thoại", interactive=False)
                
                with gr.Row():
                    conf_box = gr.Textbox(label="Độ tin cậy", interactive=False)
                    score_box = gr.Textbox(label="Điểm số", interactive=False)
                
                needs_review_cb = gr.Checkbox(label="Đánh dấu cần Review", interactive=not readonly)
                notes_box = gr.Textbox(label="Ghi chú người dùng", placeholder="Ghi chú...", interactive=not readonly)
                apply_properties_btn = gr.Button("Cập nhật ghi chú", variant="secondary", interactive=not readonly)

            # Column 2: Visual Item Inspector & Preview
            with gr.Column(scale=1):
                gr.Markdown("### Xem trước Video")
                video_player = gr.Video(label="Video preview", interactive=False)
                
                gr.Markdown("### Inspector - Điều chỉnh chi tiết")
                
                # Visual item selector
                vi_dropdown = gr.Dropdown(choices=[], label="Chọn Visual Item", interactive=True)
                create_vi_btn = gr.Button("Tạo Visual Item từ Candidate", variant="secondary", visible=False, interactive=not readonly)
                
                # Active editing fields
                inspector_group = gr.Group(visible=True)
                with inspector_group:
                    clip_id_input = gr.Textbox(label="Mã Clip ID", interactive=False)
                    video_id_input = gr.Textbox(label="Mã Video ID", interactive=False)
                    source_path_input = gr.Textbox(label="Đường dẫn file nguồn", interactive=False)
                    
                    with gr.Row():
                        clip_start_input = gr.Number(label="Thời điểm bắt đầu (giây)", interactive=not readonly)
                        clip_end_input = gr.Number(label="Thời điểm kết thúc (giây)", interactive=not readonly)
                    
                    speed_input = gr.Slider(minimum=0.75, maximum=1.25, step=0.01, label="Tốc độ clip (Speed)", interactive=not readonly)
                    
                    with gr.Row():
                        transition_input = gr.Dropdown(choices=["cut", "fade", "crossfade"], label="Kiểu chuyển cảnh", interactive=not readonly)
                        crop_mode_input = gr.Dropdown(choices=["fit", "fill", "center_crop", "blur_background"], label="Chế độ crop hình", interactive=not readonly)
                    
                    volume_input = gr.Slider(minimum=0.0, maximum=1.0, step=0.1, label="Âm lượng clip gốc", interactive=not readonly)
                    locked_input = gr.Checkbox(label="Khóa Clip này", interactive=not readonly)
                    
                    update_inspector_btn = gr.Button("Áp dụng điều chỉnh", variant="primary", interactive=not readonly)

            # Column 3: Candidate Clips
            with gr.Column(scale=1):
                gr.Markdown("### Đề xuất gợi ý (Candidates)")
                candidates_markdown = gr.Markdown("Không có đề xuất.")
                candidate_dropdown = gr.Dropdown(choices=[], label="Chọn Clip Candidate", interactive=not readonly)
                choose_cand_btn = gr.Button("Đổi sang Candidate đã chọn", variant="primary", interactive=not readonly)

        # Flat, clean, user-friendly CSS styles
        gr.Markdown(
            """
            <style>
            .gradio-container {
                background-color: #f8fafc !important;
                color: #334155 !important;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            }
            .gr-box, .gr-group {
                background: #ffffff !important;
                border: 1px solid #e2e8f0 !important;
                border-radius: 6px !important;
                box-shadow: none !important;
                padding: 12px !important;
            }
            input, select, textarea, .gr-input {
                background: #ffffff !important;
                color: #0f172a !important;
                border: 1px solid #cbd5e1 !important;
                border-radius: 4px !important;
                padding: 6px !important;
            }
            button.primary {
                background: #2563eb !important;
                color: #ffffff !important;
                border: none !important;
                border-radius: 4px !important;
                font-weight: 500 !important;
                cursor: pointer;
                box-shadow: none !important;
            }
            button.primary:hover {
                background: #1d4ed8 !important;
            }
            button.secondary, .gr-button-secondary {
                background: #f1f5f9 !important;
                border: 1px solid #cbd5e1 !important;
                color: #475569 !important;
                border-radius: 4px !important;
                font-weight: 500 !important;
                cursor: pointer;
            }
            button.secondary:hover, .gr-button-secondary:hover {
                background: #e2e8f0 !important;
            }
            </style>
            """
        )

        # Helper function to refresh choices on segment load
        def load_segment_data(segment_id, data):
            if not segment_id:
                return [
                    "Không tìm thấy segment", None, "", "", "", False, "",
                    gr.update(choices=[], value=None), gr.update(visible=False), gr.update(visible=False),
                    "", "", "", 0, 0, 1.0, "cut", "center_crop", 0.0, False,
                    None, None,
                    "Không có đề xuất", gr.update(choices=[]),
                    generate_timeline_html(data, None)
                ]
                
            item = next((i for i in data.timeline["items"] if i["segment_id"] == segment_id), None)
            if not item:
                return [
                    "Không tìm thấy segment", None, "", "", "", False, "",
                    gr.update(choices=[], value=None), gr.update(visible=False), gr.update(visible=False),
                    "", "", "", 0, 0, 1.0, "cut", "center_crop", 0.0, False,
                    None, None,
                    "Không có đề xuất", gr.update(choices=[]),
                    generate_timeline_html(data, segment_id)
                ]
            
            # Slice audio preview
            audio_path = data.media_metadata.get("audio", {}).get("normalized_path")
            audio_preview = slice_audio(audio_path, item["audio_start"], item["audio_end"])
            
            # Details
            info = f"Lời thoại: {item['text']}\nThời lượng: {item['audio_start']} - {item['audio_end']}s ({item['duration']}s)"
            transcript = item["text"]
            conf = item["confidence"]
            score = str(item["score"]) if item.get("score") is not None else "null"
            needs_review = item.get("needs_review", False)
            notes = item.get("notes", "")
            
            # Visual Items Dropdown
            vi_items = item.get("visual_items", [])
            vi_choices = [(f"{v['timeline_item_id']} | Clip: {v['clip_id']}", v['timeline_item_id']) for v in vi_items]
            
            selected_vi_id = vi_items[0]["timeline_item_id"] if vi_items else None
            
            # Candidate list building
            cref = item.get("candidates_ref")
            candidate_set = data.candidate_sets_by_id.get(cref)
            cand_md = ""
            cand_choices = []
            if candidate_set:
                cand_md = "#### Clip gợi ý có sẵn:\n"
                for cand in candidate_set.get("candidates", []):
                    cand_md += f"* **Rank {cand['rank']}**: `{cand['clip_id']}` (Điểm: {cand['final_score']:.2f})\n"
                    cand_choices.append((f"Rank {cand['rank']} | {cand['clip_id']} ({cand['final_score']:.2f})", cand['clip_id']))
            else:
                cand_md = "Không có đề xuất"
                
            # Preview Video Path
            video_preview = None
            if selected_vi_id:
                rel_path = resolve_video_path(data, segment_id, selected_vi_id)
                video_preview = make_abs(rel_path)
                
            # Inspector values
            active_vi = next((v for v in vi_items if v["timeline_item_id"] == selected_vi_id), None) if selected_vi_id else None
            
            html_timeline = generate_timeline_html(data, segment_id)

            if active_vi:
                clip_id = active_vi["clip_id"]
                video_id = active_vi["video_id"]
                src_path = active_vi["source_path"]
                c_start = active_vi["clip_start"]
                c_end = active_vi["clip_end"]
                speed = active_vi["speed"]
                trans = active_vi["transition"]
                crop = active_vi.get("crop_mode", "center_crop")
                vol = active_vi.get("volume", 0.0)
                locked = active_vi.get("locked", False)
                
                return [
                    info, audio_preview, transcript, conf, score, needs_review, notes,
                    gr.update(choices=vi_choices, value=selected_vi_id),
                    gr.update(visible=True), # Show inspector group
                    gr.update(visible=False), # Hide create visual button
                    clip_id, video_id, src_path, c_start, c_end, speed, trans, crop, vol, locked,
                    video_preview, selected_vi_id,
                    cand_md, gr.update(choices=cand_choices),
                    html_timeline
                ]
            else:
                # No visual item exists
                return [
                    info, audio_preview, transcript, conf, score, needs_review, notes,
                    gr.update(choices=[], value=None),
                    gr.update(visible=False), # Hide inspector group
                    gr.update(visible=True), # Show create visual button
                    "", "", "", 0, 0, 1.0, "cut", "center_crop", 0.0, False,
                    None, None,
                    cand_md, gr.update(choices=cand_choices),
                    html_timeline
                ]

        def load_visual_item_data(segment_id, vi_id, data):
            if not segment_id or not vi_id:
                return [None, "", "", "", 0, 0, 1.0, "cut", "center_crop", 0.0, False, vi_id]
                
            item = next((i for i in data.timeline["items"] if i["segment_id"] == segment_id), None)
            if not item:
                return [None, "", "", "", 0, 0, 1.0, "cut", "center_crop", 0.0, False, vi_id]
                
            active_vi = next((v for v in item.get("visual_items", []) if v["timeline_item_id"] == vi_id), None)
            if not active_vi:
                return [None, "", "", "", 0, 0, 1.0, "cut", "center_crop", 0.0, False, vi_id]
                
            rel_path = resolve_video_path(data, segment_id, vi_id)
            video_preview = make_abs(rel_path)
            
            return [
                video_preview,
                active_vi["clip_id"],
                active_vi["video_id"],
                active_vi["source_path"],
                active_vi["clip_start"],
                active_vi["clip_end"],
                active_vi["speed"],
                active_vi["transition"],
                active_vi.get("crop_mode", "center_crop"),
                active_vi.get("volume", 0.0),
                active_vi.get("locked", False),
                vi_id
            ]

        # Filter trigger
        def on_filter_change(filter_val, data):
            opts = get_segment_options(data, filter_val)
            default_val = opts[0][1] if opts else None
            return gr.update(choices=opts, value=default_val)

        filter_dropdown.change(
            fn=on_filter_change,
            inputs=[filter_dropdown, project_state],
            outputs=[segment_dropdown]
        )

        # Segment change trigger
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

        # Visual item dropdown trigger
        vi_dropdown.change(
            fn=load_visual_item_data,
            inputs=[segment_dropdown, vi_dropdown, project_state],
            outputs=[
                video_player, clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                selected_vi_state
            ]
        )

        # Update visual properties trigger
        def on_apply_properties(segment_id, notes, needs_review, data, tlog):
            if readonly:
                return data, False, "Chế độ chỉ xem.", gr.update(), tlog
            try:
                # Update text notes and needs_review
                update_visual_properties(
                    data, segment_id, visual_item_id=None,
                    notes=notes, needs_review=needs_review
                )
                tlog.record_state(data, f"apply_properties:{segment_id}")
                html_timeline = generate_timeline_html(data, segment_id)
                return data, True, "Đã cập nhật ghi chú thành công.", html_timeline, tlog
            except Exception as e:
                return data, True, f"Lỗi: {e}", gr.update(), tlog

        apply_properties_btn.click(
            fn=on_apply_properties,
            inputs=[segment_dropdown, notes_box, needs_review_cb, project_state, transaction_log_state],
            outputs=[project_state, dirty_state, status_box, timeline_html_map, transaction_log_state]
        )

        # Apply inspector changes trigger
        def on_apply_inspector(segment_id, vi_id, clip_start, clip_end, speed, transition, crop_mode, volume, locked, data, tlog):
            if readonly:
                return data, False, None, gr.update(), gr.update(), gr.update(), "Chế độ chỉ xem.", gr.update(), tlog
            try:
                # Update timing
                update_timing(data, segment_id, vi_id, clip_start, clip_end)
                # Update speed
                update_speed(data, segment_id, vi_id, speed)
                # Update other properties
                update_visual_properties(
                    data, segment_id, vi_id,
                    transition=transition, crop_mode=crop_mode, volume=volume, locked=locked
                )
                tlog.record_state(data, f"apply_inspector:{segment_id}:{vi_id}")
                # Resolve new video preview
                rel_path = resolve_video_path(data, segment_id, vi_id)
                abs_video = make_abs(rel_path)
                
                # Fetch updated active vi timing to refresh inputs
                item = next(i for i in data.timeline["items"] if i["segment_id"] == segment_id)
                vi = next(v for v in item["visual_items"] if v["timeline_item_id"] == vi_id)
                
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

        # Choose candidate trigger
        def on_choose_candidate(segment_id, vi_id, cand_clip_id, data, tlog):
            if readonly:
                return data, False, None, "Chế độ chỉ xem.", gr.update(), gr.update(), gr.update(), tlog
            try:
                if vi_id:
                    replace_clip(data, segment_id, vi_id, cand_clip_id)
                    action_msg = f"Đã thay thế Visual Item {vi_id} bằng clip {cand_clip_id}."
                else:
                    create_visual_from_candidate(data, segment_id, cand_clip_id)
                    action_msg = f"Đã tạo Visual Item mới từ clip {cand_clip_id}."
                tlog.record_state(data, f"choose_candidate:{segment_id}:{vi_id}:{cand_clip_id}")
                # Reload segment view
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

        # Create Visual trigger (when visual_items is empty)
        create_vi_btn.click(
            fn=on_choose_candidate,
            inputs=[segment_dropdown, selected_vi_state, candidate_dropdown, project_state, transaction_log_state],
            outputs=[project_state, dirty_state, video_player, status_box, vi_dropdown, selected_vi_state, timeline_html_map, transaction_log_state]
        )

        # Validate trigger
        def on_validate(data):
            try:
                msgs = validate_project_data(data, mode="edit_save")
                errors = [m for m in msgs if m.level == "error"]
                warnings = [m for m in msgs if m.level == "warning"]
                
                res_text = f"### Kết quả xác thực (Validation Results)\n"
                res_text += f"* **Lỗi chặn (Errors)**: {len(errors)}\n"
                res_text += f"* **Cảnh báo (Warnings)**: {len(warnings)}\n\n"
                
                if errors:
                    res_text += "#### Lỗi nghiêm trọng (Chặn lưu):\n"
                    for err in errors:
                        res_text += f"- **{err.code}**: {err.message} (Segment: `{err.segment_id}`)\n"
                if warnings:
                    res_text += "#### Cảnh báo (Cho phép lưu):\n"
                    for warn in warnings:
                        res_text += f"- **{warn.code}**: {warn.message} (Segment: `{warn.segment_id}`)\n"
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

        # Force browser to Light Mode & load initial preview
        demo.load(
            fn=load_segment_data,
            inputs=[segment_dropdown, project_state],
            outputs=[
                status_box, audio_player, transcript_box, conf_box, score_box, needs_review_cb, notes_box,
                vi_dropdown, inspector_group, create_vi_btn,
                clip_id_input, video_id_input, source_path_input, clip_start_input, clip_end_input, speed_input, transition_input, crop_mode_input, volume_input, locked_input,
                video_player, selected_vi_state,
                candidates_markdown, candidate_dropdown,
                timeline_html_map
            ],
            js="() => { document.body.classList.remove('dark'); }"
        )

    # Launch Gradio app with explicit allowed_paths whitelisting for local media serving
    demo.launch(server_name=host, server_port=port, allowed_paths=[REPO_ROOT])

