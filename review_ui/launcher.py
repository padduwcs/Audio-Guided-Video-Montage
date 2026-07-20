from __future__ import annotations

import html
import os
import socket
from urllib.parse import quote

import gradio as gr

from review_ui.app import build_review_workspace
from review_ui.launcher_backend import (
    FINAL_VIDEO,
    ROOT,
    check_kaggle_credentials,
    draft_status,
    final_status,
    read_kaggle_username,
    run_kaggle_draft,
    run_render_final,
    save_kaggle_credentials,
    stage_inputs,
)
from review_ui.theme import APP_THEME_CSS, REVIEW_WORKSPACE_CSS, THEME_JS, THEME_SWITCHER_HTML


def _operation_status_html(state: str, title: str, detail: str) -> str:
    icons = {"idle": "○", "running": "↻", "success": "✓", "error": "!"}
    safe_state = state if state in icons else "idle"
    return f"""
    <div class="operation-status state-{safe_state}" role="status" aria-live="polite">
      <div class="operation-icon" aria-hidden="true">{icons[safe_state]}</div>
      <div>
        <div class="operation-title">{html.escape(title)}</div>
        <div class="operation-detail">{html.escape(detail)}</div>
      </div>
    </div>
    """


def _draft_running_detail(log_text: str) -> str:
    lowered = (log_text or "").lower()
    if "kernels output" in lowered or "đang tải kết quả" in lowered:
        return "Đang tải và kiểm tra kết quả từ Kaggle..."
    if "kernelworkerstatus.running" in lowered or "sleeping 60s" in lowered:
        return "Kaggle đang phân tích audio và video..."
    if "kernels push" in lowered or "kernel version" in lowered:
        return "Đã gửi tác vụ; đang khởi động môi trường Kaggle..."
    if "dataset" in lowered:
        return "Đang đóng gói và tải dữ liệu đầu vào..."
    return "Đang chuẩn bị tác vụ tạo bản nháp..."


def _file_url(path) -> str:
    return "/gradio_api/file=" + quote(str(path).replace("\\", "/"), safe="/:")


def _final_video_preview_html(path) -> str:
    if not path or not FINAL_VIDEO.is_file():
        return """
        <div class="final-video-empty">
            Video hoàn chỉnh chưa có sẵn trong phiên này.
        </div>
        """

    source = html.escape(_file_url(path), quote=True)
    return f"""
    <div class="final-video-player">
      <video controls preload="metadata" playsinline>
        <source src="{source}" type="video/mp4">
        Trình duyệt không hỗ trợ phát video này.
      </video>
    </div>
    """


LAUNCHER_CSS = APP_THEME_CSS + REVIEW_WORKSPACE_CSS + """
.app-shell { max-width: 1280px; margin: 0 auto; padding-bottom: 36px; }
.app-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 24px; padding: 24px 4px 16px; border-bottom: 1px solid var(--app-border);
}
.brand-kicker {
    color: var(--app-primary) !important; font-size: 12px; font-weight: 750;
    letter-spacing: .08em; text-transform: uppercase; margin-bottom: 6px;
}
.app-header h1 { font-size: 28px; line-height: 1.15; margin: 0 0 8px; }
.app-header p { color: var(--app-text-muted) !important; margin: 0; font-size: 14px; max-width: 720px; }
.simple-panel {
    border: 1px solid var(--app-border) !important; border-radius: 14px !important;
    background: var(--app-surface) !important; padding: 18px !important; box-shadow: var(--app-shadow);
}
.operation-status {
    display: flex; align-items: flex-start; gap: 12px; min-height: 78px;
    margin: 10px 0 14px; padding: 14px; border: 1px solid var(--app-border);
    border-radius: 12px; background: var(--app-surface-soft);
}
.operation-icon {
    display: inline-grid; place-items: center; width: 34px; height: 34px; flex: 0 0 34px;
    border-radius: 50%; color: var(--app-text-muted) !important;
    background: var(--app-surface-strong); font-size: 18px; font-weight: 800;
}
.operation-title { color: var(--app-text) !important; font-size: 14px; font-weight: 750; margin: 1px 0 4px; }
.operation-detail { color: var(--app-text-muted) !important; font-size: 13px; white-space: pre-wrap; }
.operation-status.state-running { border-color: var(--app-warning); background: var(--app-warning-soft); }
.operation-status.state-running .operation-icon { color: var(--app-warning) !important; animation: status-spin 1.1s linear infinite; }
.operation-status.state-success { border-color: var(--app-success); background: var(--app-success-soft); }
.operation-status.state-success .operation-icon { color: var(--app-success) !important; }
.operation-status.state-error { border-color: var(--app-danger); background: var(--app-danger-soft); }
.operation-status.state-error .operation-icon { color: var(--app-danger) !important; }
@keyframes status-spin { to { transform: rotate(360deg); } }
.log-box textarea {
    height: 290px !important; max-height: 290px !important; overflow-y: scroll !important;
    resize: vertical !important; font-family: Consolas, "SFMono-Regular", monospace !important;
    font-size: 12px !important; scrollbar-width: thin;
}
.final-video-player {
    width: 100%;
    min-height: 420px;
    display: grid;
    place-items: center;
    border: 1px solid var(--app-border);
    border-radius: 8px;
    background: #111827;
    overflow: hidden;
}
.final-video-player video {
    width: 100%;
    height: 420px;
    display: block;
    background: #000;
    object-fit: contain;
}
.final-video-empty {
    min-height: 160px;
    display: grid;
    place-items: center;
    border: 1px dashed var(--app-border);
    border-radius: 8px;
    color: var(--app-text-muted);
    background: var(--app-surface-soft);
    font-size: 14px;
}
@media (max-width: 760px) {
    .app-header { flex-direction: column; }
}
"""


def build_launcher() -> gr.Blocks:
    with gr.Blocks(title="Audio-Guided Video Montage", css=LAUNCHER_CSS) as demo:
        staged_videos_state = gr.State([])
        staged_audio_state = gr.State(None)
        draft_ready_initial, _ = draft_status()

        with gr.Column(elem_classes="app-shell"):
            gr.HTML(
                f"""
                <div class="app-header">
                  <div>
                    <div class="brand-kicker">Không gian dựng video</div>
                    <h1>Audio-Guided Video Montage</h1>
                    <p>Chọn video và voice-over, tạo bản nháp trên Kaggle, tinh chỉnh từng đoạn rồi xuất video hoàn chỉnh.</p>
                  </div>
                  {THEME_SWITCHER_HTML}
                </div>
                """
            )
            with gr.Tabs():
                with gr.Tab("Bắt đầu", id="start"):
                    with gr.Row():
                        with gr.Column(scale=3, elem_classes="simple-panel"):
                            gr.Markdown("### Dữ liệu đầu vào\nChọn các video nguồn và một file voice-over cho dự án.")
                            video_files = gr.Files(
                                label="Video nguồn",
                                file_types=[".mp4", ".mov", ".mkv", ".webm"],
                                type="filepath",
                            )
                            audio_file = gr.File(
                                label="Voice-over hoặc audio",
                                file_types=[".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"],
                                type="filepath",
                            )
                            stage_btn = gr.Button("Xác nhận dữ liệu", variant="primary")
                            input_status = gr.Markdown("Chưa chọn dữ liệu.")

                        with gr.Column(scale=2, elem_classes="simple-panel"):
                            gr.Markdown("### Kết nối Kaggle\nThông tin được lưu trong cấu hình Kaggle trên máy của bạn.")
                            username_box = gr.Textbox(
                                label="Tên người dùng",
                                value=read_kaggle_username(),
                                placeholder="kaggle_username",
                            )
                            api_key_box = gr.Textbox(
                                label="Khóa API",
                                type="password",
                                placeholder="Dán khóa trong file kaggle.json",
                            )
                            with gr.Row():
                                save_key_btn = gr.Button("Lưu kết nối", variant="secondary")
                                check_key_btn = gr.Button("Kiểm tra", variant="secondary")
                            kaggle_status = gr.Markdown("Chưa kiểm tra kết nối Kaggle.")

                    with gr.Accordion("Tùy chọn nâng cao", open=False):
                        with gr.Row():
                            project_id_box = gr.Textbox(label="Tên dự án", value="demo_01")
                            device_dropdown = gr.Dropdown(
                                label="Thiết bị Kaggle", choices=["cpu", "auto", "cuda"], value="cpu"
                            )
                            compute_type_box = gr.Dropdown(
                                label="Kiểu tính toán", choices=["int8", "float16", "auto"], value="int8"
                            )
                            fake_embeddings_box = gr.Checkbox(
                                label="Kiểm thử nhanh bằng embedding giả", value=False
                            )

                    with gr.Column(elem_classes="simple-panel"):
                        gr.Markdown("### Tạo bản nháp\nGửi dữ liệu lên Kaggle, phân tích và tải kết quả về máy.")
                        run_btn = gr.Button("Tạo bản nháp video", variant="primary")
                        draft_job_status = gr.HTML(
                            _operation_status_html(
                                "idle",
                                "Chưa bắt đầu trong phiên này",
                                "Xác nhận dữ liệu trước khi tạo bản nháp mới.",
                            )
                        )
                        with gr.Accordion("Nhật ký kỹ thuật", open=False):
                            run_log = gr.Textbox(
                                label="Chi tiết tiến trình",
                                lines=12,
                                interactive=False,
                                elem_classes="log-box",
                            )

                with gr.Tab("Chỉnh sửa", id="review"):
                    review_workspace = build_review_workspace(show_header=False)

                with gr.Tab("Xuất video", id="export"):
                    with gr.Column(elem_classes="simple-panel"):
                        gr.Markdown("### Xuất video hoàn chỉnh\nKiểm tra timeline và render video thành phẩm trên máy.")
                        render_btn = gr.Button(
                            "Xuất video", variant="primary", interactive=draft_ready_initial
                        )
                        render_job_status = gr.HTML(
                            _operation_status_html(
                                "idle",
                                "Chưa xuất trong phiên này",
                                "Bấm Xuất video khi bạn muốn tạo lại video hoàn chỉnh.",
                            )
                        )
                        with gr.Accordion("Nhật ký kỹ thuật", open=False):
                            render_log = gr.Textbox(
                                label="Chi tiết render",
                                lines=12,
                                interactive=False,
                                elem_classes="log-box",
                            )
                        gr.Markdown("#### Video hoàn chỉnh")
                        final_video_direct = gr.HTML(_final_video_preview_html(None))

        def on_stage_inputs(videos, audio):
            try:
                staged_videos, staged_audio, message = stage_inputs(videos, audio)
                return [str(path) for path in staged_videos], str(staged_audio), message
            except Exception as exc:
                return [], None, f"Lỗi: {exc}"

        def on_save_key(username, key):
            try:
                return save_kaggle_credentials(username, key)
            except Exception as exc:
                return f"Lỗi: {exc}"

        def on_check_key():
            return check_kaggle_credentials()

        def on_run_draft(videos, audio, project_id, device, compute_type, fake_embeddings):
            if not videos or not audio:
                yield (
                    _operation_status_html("error", "Chưa có dữ liệu", "Hãy chọn video và voice-over ở phía trên."),
                    "Hãy bấm Xác nhận dữ liệu trước khi tạo bản nháp.",
                )
                return

            last_update = ""
            for update in run_kaggle_draft(
                videos,
                audio,
                project_id=project_id,
                device=device,
                compute_type=compute_type,
                fake_embeddings=fake_embeddings,
            ):
                last_update = update
                yield (
                    _operation_status_html("running", "Đang tạo bản nháp", _draft_running_detail(update)),
                    update,
                )

            ready, message = draft_status()
            if ready:
                yield _operation_status_html("success", "Tạo bản nháp hoàn thành", message), last_update
            else:
                yield _operation_status_html("error", "Tạo bản nháp chưa hoàn thành", message), last_update

        def refresh_actions():
            draft_ready, _ = draft_status()
            return gr.update(interactive=draft_ready)

        def on_render():
            last_update = ""
            for update in run_render_final():
                last_update = update
                yield (
                    _operation_status_html(
                        "running",
                        "Đang xuất video",
                        "Hệ thống đang kiểm tra timeline và render các đoạn video...",
                    ),
                    update,
                    gr.update(),
                )
            ready, message = final_status()
            if ready:
                yield (
                    _operation_status_html("success", "Xuất video hoàn thành", message),
                    last_update,
                    _final_video_preview_html(FINAL_VIDEO),
                )
            else:
                yield (
                    _operation_status_html("error", "Xuất video thất bại", message),
                    last_update,
                    _final_video_preview_html(None),
                )

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
            outputs=[draft_job_status, run_log],
            show_api=False,
        ).then(
            fn=refresh_actions,
            outputs=[render_btn],
            show_api=False,
        ).then(
            fn=review_workspace["reload_fn"],
            outputs=review_workspace["reload_outputs"],
            show_api=False,
        )
        render_btn.click(
            fn=on_render,
            outputs=[render_job_status, render_log, final_video_direct],
            show_api=False,
        ).then(
            fn=refresh_actions,
            outputs=[render_btn],
            show_api=False,
        )
        demo.load(fn=None, js=THEME_JS)

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
            raise ValueError("GRADIO_SERVER_PORT phải là một số nguyên.") from exc

    for port in range(default_port, default_port + attempts):
        if _port_is_available(port):
            return port

    last_port = default_port + attempts - 1
    raise OSError(f"Không tìm thấy cổng trống trong khoảng {default_port}-{last_port}.")


def main() -> None:
    app = build_launcher()
    port = _pick_server_port()
    app.launch(server_name="127.0.0.1", server_port=port, show_api=False, allowed_paths=[str(ROOT)])


if __name__ == "__main__":
    main()
