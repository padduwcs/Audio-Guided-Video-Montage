from __future__ import annotations

import os
import socket

import gradio as gr

from review_ui.app import build_editor_tab, custom_css as app_css
from review_ui.launcher_backend import (
    FINAL_VIDEO,
    check_kaggle_credentials,
    draft_status,
    final_status,
    launch_review_server,
    read_kaggle_username,
    run_kaggle_draft,
    run_render_final,
    save_kaggle_credentials,
    stage_inputs,
)


def _status_html(label: str, detail: str, tone: str = "neutral") -> str:
    return f"""
    <div class="status-card status-{tone}">
      <div class="status-icon"></div>
      <div class="status-body">
        <div class="status-title">{label}</div>
        <div class="status-detail">{detail}</div>
      </div>
    </div>
    """


def _initial_status() -> tuple[str, str]:
    draft_ready, draft_message = draft_status()
    final_ready, final_message = final_status()
    draft_label = "Bản nháp sẵn sàng" if draft_ready else "Chưa có bản nháp"
    final_label = "Video đã xuất" if final_ready else "Chưa xuất video"
    return (
        _status_html(draft_label, draft_message, "ok" if draft_ready else "pending"),
        _status_html(final_label, final_message, "ok" if final_ready else "pending"),
    )


def build_launcher() -> gr.Blocks:
    css = """
    /* ═══════════════════════════════════════════════
       Launcher UI — "Studio" design system
       Audio-Guided Video Montage
       Dark, editor-grade UI inspired by video-editing
       tools: deep charcoal canvas, violet→coral accent
       gradient standing in for the "render" action,
       segmented pill tabs, glowing status chips.
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

    /* ── App Shell ── */
    .app-shell { max-width: 1180px; margin: 0 auto; padding: 0 20px 48px; }

    /* ── Hero Header ── */
    .lnc-hero {
        padding: 32px 0 24px;
        margin-bottom: 22px;
        display: flex;
        align-items: center;
        gap: 18px;
    }
    .lnc-hero-icon {
        flex: none;
        width: 52px; height: 52px;
        display: flex; align-items: center; justify-content: center;
        font-size: 24px; line-height: 1;
        border-radius: 14px;
        background: linear-gradient(135deg, var(--grad-start), var(--grad-mid) 55%, var(--grad-end));
        box-shadow: 0 6px 18px rgba(124,92,252,0.35);
    }
    .lnc-hero h1 {
        font-size: 23px; font-weight: 800; color: var(--text-1);
        margin: 0 0 5px; letter-spacing: -0.02em; line-height: 1.2;
    }
    .lnc-hero p {
        color: var(--text-2); margin: 0; font-size: 13.5px;
        max-width: 680px; line-height: 1.6;
    }

    /* ── Status Cards ── */
    .status-card {
        border: 1px solid var(--border);
        background: var(--bg-surface);
        border-radius: var(--radius);
        padding: 14px 16px;
        min-height: 76px;
        box-shadow: var(--shadow-sm);
        transition: border-color 0.15s, transform 0.15s;
        display: flex;
        align-items: flex-start;
        gap: 12px;
    }
    .status-card:hover { border-color: var(--border-strong); }
    .status-icon {
        flex: none;
        width: 9px; height: 9px; margin-top: 5px;
        border-radius: 50%;
        background: var(--text-3);
    }
    .status-ok .status-icon { background: var(--success); box-shadow: 0 0 0 4px var(--success-bg); }
    .status-pending .status-icon { background: var(--warning); box-shadow: 0 0 0 4px var(--warning-bg); }
    .status-title {
        font-weight: 700; font-size: 13px;
        color: var(--text-1); margin-bottom: 4px;
    }
    .status-detail {
        color: var(--text-2); font-size: 12px;
        white-space: pre-wrap; line-height: 1.5;
    }

    /* ── Panels ── */
    .simple-panel {
        border: 1px solid var(--border);
        border-radius: var(--radius-lg);
        background: var(--bg-surface);
        padding: 20px;
        box-shadow: var(--shadow-sm);
    }

    /* ── Tabs — segmented pill control, CapCut-style ── */
    .tab-nav {
        padding: 5px !important;
        border: 1px solid var(--border) !important;
        border-bottom: 1px solid var(--border) !important;
        background: var(--bg-inset) !important;
        border-radius: var(--radius) !important;
        gap: 4px !important;
        display: flex !important;
        margin-bottom: 18px !important;
    }
    .tab-nav button {
        padding: 9px 18px !important;
        color: var(--text-3) !important;
        font-weight: 600 !important; font-size: 13px !important;
        border: none !important;
        border-radius: 8px !important;
        background: transparent !important;
        transition: color 0.15s, background 0.2s !important;
        font-family: var(--font) !important;
    }
    .tab-nav button:hover { color: var(--text-1) !important; background: var(--bg-hover) !important; }
    .tab-nav button.selected {
        color: #fff !important;
        background: linear-gradient(135deg, var(--grad-start), var(--grad-mid) 60%, var(--grad-end)) !important;
        box-shadow: 0 4px 14px rgba(124,92,252,0.35) !important;
    }

    /* ── Buttons ── */
    button, .gr-button {
        font-family: var(--font) !important;
        font-weight: 600 !important;
        border-radius: var(--radius-sm) !important;
        font-size: 13px !important;
        transition: all 0.15s ease !important;
    }
    button.primary, .gr-button-primary {
        background: linear-gradient(135deg, var(--grad-start), var(--grad-mid) 60%, var(--grad-end)) !important;
        color: #fff !important; border: none !important;
        box-shadow: 0 4px 16px rgba(124,92,252,0.35) !important;
    }
    button.primary:hover, .gr-button-primary:hover {
        filter: brightness(1.08) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 8px 22px rgba(124,92,252,0.45) !important;
    }
    button.secondary, .gr-button-secondary {
        background: var(--bg-surface2) !important;
        color: var(--text-1) !important;
        border: 1px solid var(--border) !important;
    }
    button.secondary:hover, .gr-button-secondary:hover {
        background: var(--bg-hover) !important;
        border-color: var(--border-strong) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Inputs ── */
    input, textarea, select {
        background: var(--bg-inset) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-1) !important;
        border-radius: var(--radius-sm) !important;
        font-family: var(--font) !important;
        font-size: 13px !important;
        transition: border-color 0.15s, box-shadow 0.15s !important;
    }
    input::placeholder, textarea::placeholder { color: var(--text-3) !important; }
    input:focus, textarea:focus {
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 3px var(--accent-ring) !important;
        outline: none !important;
    }
    textarea {
        font-family: var(--font-mono) !important;
        font-size: 12px !important;
    }

    /* ── File drop zones ── */
    .file-preview, [data-testid="file-upload"], .upload-box, .wrap.default {
        background: var(--bg-inset) !important;
        border: 1.5px dashed var(--border-strong) !important;
        border-radius: var(--radius) !important;
    }

    /* ── Labels ── */
    label span, .label-wrap span {
        font-size: 11px !important; font-weight: 700 !important;
        color: var(--text-3) !important;
        text-transform: uppercase !important; letter-spacing: 0.07em !important;
        font-family: var(--font) !important;
    }

    /* ── Markdown sections ── */
    .prose h3 {
        font-size: 12.5px !important; font-weight: 800 !important;
        color: var(--text-1) !important;
        text-transform: uppercase !important; letter-spacing: 0.07em !important;
        margin: 0 0 14px !important; padding-bottom: 10px !important;
        border-bottom: 1px solid var(--border) !important;
        position: relative;
    }
    .prose h3::before {
        content: "";
        display: inline-block;
        width: 6px; height: 6px;
        margin-right: 8px;
        border-radius: 50%;
        background: linear-gradient(135deg, var(--grad-start), var(--grad-end));
        vertical-align: middle;
    }
    .prose p { color: var(--text-2) !important; font-size: 13px !important; line-height: 1.6 !important; }

    /* ── Accordion ── */
    details.gr-accordion {
        background: var(--bg-surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
    }
    details.gr-accordion > summary {
        background: var(--bg-surface2) !important;
        border-bottom: 1px solid var(--border) !important;
        font-weight: 700 !important; font-size: 13px !important;
        color: var(--text-1) !important; padding: 11px 16px !important;
        border-radius: var(--radius) !important;
    }

    /* ── Checkbox ── */
    input[type="checkbox"] { accent-color: var(--accent) !important; }

    /* ── Dropdown ── */
    ul.options {
        background: var(--bg-surface2) !important;
        border: 1px solid var(--border) !important;
        border-radius: var(--radius) !important;
        box-shadow: var(--shadow-md) !important;
    }
    ul.options li {
        color: var(--text-1) !important; font-size: 13px !important;
        font-family: var(--font) !important;
    }
    ul.options li:hover, ul.options li.selected {
        background: var(--accent-soft) !important;
        color: #fff !important;
    }

    /* ── Video / log preview frame ── */
    video, .gr-video { border-radius: var(--radius) !important; border: 1px solid var(--border) !important; }

    /* ── Scrollbars ── */
    ::-webkit-scrollbar            { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track      { background: var(--bg-inset); border-radius: 3px; }
    ::-webkit-scrollbar-thumb      { background: var(--border-strong); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover{ background: var(--text-3); }

    /* ── Status Row Alignment ── */
    .status-row {
        justify-content: flex-start !important;
        gap: 16px !important;
    }
    .status-row > div {
        flex: none !important;
        width: 360px !important;
        max-width: 100% !important;
    }
    """
    css = css + "\n" + app_css

    with gr.Blocks(title="Audio-Guided Video Montage — Launcher", css=css) as demo:
        staged_videos_state = gr.State([])
        staged_audio_state = gr.State(None)

        with gr.Column(elem_classes="app-shell"):
            gr.HTML(
                """
                <div class="lnc-hero">
                  <div class="lnc-hero-icon">🎬</div>
                  <div>
                    <h1>Audio-Guided Video Montage</h1>
                    <p>Chọn video nguồn, tải voice-over, tạo bản nháp trên Kaggle, chỉnh sửa từng cảnh và xuất video thành phẩm — tất cả trên giao diện này.</p>
                  </div>
                </div>
                """
            )

            draft_status_box, final_status_box = _initial_status()
            with gr.Row(elem_classes="status-row"):
                draft_status_html = gr.HTML(draft_status_box)
                final_status_html = gr.HTML(final_status_box)

            with gr.Tabs() as tabs:
                with gr.Tab("📥 Bắt đầu", id="start"):
                    with gr.Row():
                        with gr.Column(scale=3, elem_classes="simple-panel"):
                            gr.Markdown("### Dữ liệu đầu vào")
                            video_files = gr.Files(
                                label="Video nguồn (.mp4 .mov .mkv .webm)",
                                file_types=[".mp4", ".mov", ".mkv", ".webm"],
                                type="filepath",
                            )
                            audio_file = gr.File(
                                label="Voice-over / audio (.mp3 .wav .m4a ...)",
                                file_types=[".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"],
                                type="filepath",
                            )
                            stage_btn = gr.Button("✓ Xác nhận file này", variant="secondary")
                            input_status = gr.Markdown("Chưa chọn dữ liệu.")

                        with gr.Column(scale=2, elem_classes="simple-panel"):
                            gr.Markdown("### Kaggle")
                            username_box = gr.Textbox(
                                label="Username",
                                value=read_kaggle_username(),
                                placeholder="tên tài khoản Kaggle",
                            )
                            api_key_box = gr.Textbox(
                                label="API Key",
                                type="password",
                                placeholder="Dán key từ file kaggle.json",
                            )
                            with gr.Row():
                                save_key_btn = gr.Button("💾 Lưu Kaggle", variant="secondary")
                                check_key_btn = gr.Button("✔ Kiểm tra", variant="secondary")
                            kaggle_status = gr.Markdown("Kaggle chưa được kiểm tra.")

                    with gr.Accordion("⚙ Tùy chọn nâng cao", open=False):
                        with gr.Row():
                            project_id_box = gr.Textbox(label="Tên dự án", value="demo_01")
                            device_dropdown = gr.Dropdown(
                                label="Thiết bị Kaggle",
                                choices=["cpu", "auto", "cuda"],
                                value="cpu",
                            )
                            compute_type_box = gr.Dropdown(
                                label="Compute type",
                                choices=["int8", "float16", "auto"],
                                value="int8",
                            )
                            fake_embeddings_box = gr.Checkbox(label="Test nhanh bằng fake embeddings", value=False)

                    gr.Markdown("### Tạo bản nháp")
                    run_btn = gr.Button("🚀 Tạo bản nháp video", variant="primary")
                    run_log = gr.Textbox(label="Tiến trình xử lý", lines=16, interactive=False)

                with gr.Tab("📹 Chỉnh sửa", id="review"):
                    build_editor_tab(
                        demo=demo,
                        timeline_path="data/intermediate/timeline.json",
                        matching_candidates_path="data/intermediate/matching_candidates.json",
                        clip_metadata_path="data/intermediate/clip_metadata.json",
                        audio_segments_path="data/intermediate/audio_segments.json",
                        media_metadata_path="data/intermediate/media_metadata.json",
                        project_id=None,
                        readonly=False,
                    )

                with gr.Tab("🎥 Xuất video", id="export"):
                    gr.Markdown("### Xuất video cuối")
                    gr.Markdown("Sau khi đã review và lưu timeline, bấm nút dưới đây để render video thành phẩm.")
                    render_btn = gr.Button("▶ Xuất video", variant="primary")
                    render_log = gr.Textbox(label="Tiến trình render", lines=14, interactive=False)
                    final_video = gr.Video(label="Video thành phẩm", interactive=False)

        def on_stage_inputs(videos, audio):
            try:
                staged_videos, staged_audio, message = stage_inputs(videos, audio)
                return [str(path) for path in staged_videos], str(staged_audio), message
            except Exception as exc:
                return [], None, f"Loi: {exc}"

        def on_save_key(username, key):
            try:
                return save_kaggle_credentials(username, key)
            except Exception as exc:
                return f"Loi: {exc}"

        def on_check_key():
            return check_kaggle_credentials()

        def on_run_draft(videos, audio, project_id, device, compute_type, fake_embeddings):
            if not videos or not audio:
                yield "Hay chon video/audio va bam 'Dung cac file nay' truoc."
                return
            for update in run_kaggle_draft(
                videos,
                audio,
                project_id=project_id,
                device=device,
                compute_type=compute_type,
                fake_embeddings=fake_embeddings,
            ):
                yield update

        def refresh_status():
            draft_ready, draft_message = draft_status()
            final_ready, final_message = final_status()
            draft_label = "Bản nháp sẵn sàng" if draft_ready else "Chưa có bản nháp"
            final_label = "Video đã xuất" if final_ready else "Chưa xuất video"
            return (
                _status_html(draft_label, draft_message, "ok" if draft_ready else "pending"),
                _status_html(final_label, final_message, "ok" if final_ready else "pending"),
            )


        def on_render():
            last_update = ""
            for update in run_render_final():
                last_update = update
                yield update, gr.update()
            ready, _message = final_status()
            yield last_update, gr.update(value=str(FINAL_VIDEO) if ready else None)

        stage_btn.click(
            fn=on_stage_inputs,
            inputs=[video_files, audio_file],
            outputs=[staged_videos_state, staged_audio_state, input_status],
            show_api=False,
        )
        save_key_btn.click(
            fn=on_save_key,
            inputs=[username_box, api_key_box],
            outputs=[kaggle_status],
            show_api=False,
        )
        check_key_btn.click(fn=on_check_key, outputs=[kaggle_status], show_api=False)
        run_btn.click(
            fn=on_run_draft,
            inputs=[
                staged_videos_state,
                staged_audio_state,
                project_id_box,
                device_dropdown,
                compute_type_box,
                fake_embeddings_box,
            ],
            outputs=[run_log],
            show_api=False,
        ).then(fn=refresh_status, outputs=[draft_status_html, final_status_html], show_api=False)

        render_btn.click(fn=on_render, outputs=[render_log, final_video], show_api=False).then(
            fn=refresh_status,
            outputs=[draft_status_html, final_status_html],
            show_api=False,
        )

    return demo


def _port_is_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def _pick_server_port(default_port: int = 7860, attempts: int = 20) -> int:
    env_port = os.environ.get("GRADIO_SERVER_PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError as exc:
            raise ValueError("GRADIO_SERVER_PORT phai la mot so nguyen.") from exc

    for port in range(default_port, default_port + attempts):
        if _port_is_available(port):
            return port

    last_port = default_port + attempts - 1
    raise OSError(f"Khong tim thay cong trong trong khoang {default_port}-{last_port}.")


def main() -> None:
    app = build_launcher()
    port = _pick_server_port()
    app.launch(server_name="127.0.0.1", server_port=port, show_api=False)


if __name__ == "__main__":
    main()
