from __future__ import annotations

import os
import socket

import gradio as gr

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


def _status_html(label: str, detail: str) -> str:
    return f"""
    <div class="status-card">
      <div class="status-title">{label}</div>
      <div class="status-detail">{detail}</div>
    </div>
    """


def _initial_status() -> tuple[str, str]:
    draft_ready, draft_message = draft_status()
    final_ready, final_message = final_status()
    draft_label = "Ban nhap san sang" if draft_ready else "Chua co ban nhap"
    final_label = "Video da xuat" if final_ready else "Chua xuat video"
    return _status_html(draft_label, draft_message), _status_html(final_label, final_message)


def build_launcher() -> gr.Blocks:
    css = """
    .gradio-container { background: #f7f8fa !important; color: #111827 !important; }
    .app-shell { max-width: 1180px; margin: 0 auto; }
    .hero {
        padding: 20px 4px 10px;
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 14px;
    }
    .hero h1 { font-size: 28px; line-height: 1.15; margin: 0 0 8px; letter-spacing: 0; }
    .hero p { color: #4b5563; margin: 0; font-size: 14px; max-width: 760px; }
    .status-card {
        border: 1px solid #e5e7eb;
        background: #ffffff;
        border-radius: 8px;
        padding: 14px;
        min-height: 82px;
    }
    .status-title { font-weight: 700; font-size: 14px; margin-bottom: 6px; }
    .status-detail { color: #4b5563; font-size: 13px; white-space: pre-wrap; }
    .simple-panel {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        background: #ffffff;
        padding: 14px;
    }
    textarea { font-family: Consolas, monospace !important; font-size: 12px !important; }
    """

    with gr.Blocks(title="Audio-Guided Video Montage", css=css) as demo:
        staged_videos_state = gr.State([])
        staged_audio_state = gr.State(None)

        with gr.Column(elem_classes="app-shell"):
            gr.HTML(
                """
                <div class="hero">
                  <h1>Audio-Guided Video Montage</h1>
                  <p>Chon video, chon voice-over, tao ban nhap tren Kaggle, chinh sua va xuat video ngay tren giao dien local.</p>
                </div>
                """
            )

            draft_status_box, final_status_box = _initial_status()
            with gr.Row():
                draft_status_html = gr.HTML(draft_status_box)
                final_status_html = gr.HTML(final_status_box)

            with gr.Tabs() as tabs:
                with gr.Tab("Bat dau", id="start"):
                    with gr.Row():
                        with gr.Column(scale=3, elem_classes="simple-panel"):
                            gr.Markdown("### Du lieu dau vao")
                            video_files = gr.Files(
                                label="Video nguon",
                                file_types=[".mp4", ".mov", ".mkv", ".webm"],
                                type="filepath",
                            )
                            audio_file = gr.File(
                                label="Voice-over / audio",
                                file_types=[".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"],
                                type="filepath",
                            )
                            stage_btn = gr.Button("Dung cac file nay", variant="secondary")
                            input_status = gr.Markdown("Chua chon du lieu.")

                        with gr.Column(scale=2, elem_classes="simple-panel"):
                            gr.Markdown("### Kaggle")
                            username_box = gr.Textbox(
                                label="Username",
                                value=read_kaggle_username(),
                                placeholder="kaggle_username",
                            )
                            api_key_box = gr.Textbox(
                                label="API key",
                                type="password",
                                placeholder="Dan key trong file kaggle.json",
                            )
                            with gr.Row():
                                save_key_btn = gr.Button("Luu Kaggle", variant="secondary")
                                check_key_btn = gr.Button("Kiem tra", variant="secondary")
                            kaggle_status = gr.Markdown("Kaggle chua duoc kiem tra.")

                    with gr.Accordion("Tuy chon nang cao", open=False):
                        with gr.Row():
                            project_id_box = gr.Textbox(label="Ten du an", value="demo_01")
                            device_dropdown = gr.Dropdown(
                                label="Thiet bi Kaggle",
                                choices=["cuda", "cpu", "auto"],
                                value="cuda",
                            )
                            compute_type_box = gr.Textbox(label="Compute type", value="float16")
                            fake_embeddings_box = gr.Checkbox(label="Test nhanh bang fake embeddings", value=False)

                    gr.Markdown("### Tao ban nhap")
                    run_btn = gr.Button("Tao ban nhap video", variant="primary")
                    run_log = gr.Textbox(label="Tien trinh", lines=16, interactive=False)

                with gr.Tab("Chinh sua", id="review"):
                    gr.Markdown("### Chinh sua ban dung")
                    gr.Markdown(
                        "Khi ban nhap da san sang, mo man hinh chinh sua de xem tung doan, doi clip va luu timeline."
                    )
                    open_review_btn = gr.Button("Mo man hinh chinh sua", variant="primary")
                    review_status = gr.Markdown("Review UI chua mo.")

                with gr.Tab("Xuat video", id="export"):
                    gr.Markdown("### Xuat video cuoi")
                    gr.Markdown("Sau khi da review va luu timeline, bam nut duoi day de render video thanh pham.")
                    render_btn = gr.Button("Xuat video", variant="primary")
                    render_log = gr.Textbox(label="Tien trinh render", lines=14, interactive=False)
                    final_video = gr.Video(label="Video thanh pham", interactive=False)

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
            draft_label = "Ban nhap san sang" if draft_ready else "Chua co ban nhap"
            final_label = "Video da xuat" if final_ready else "Chua xuat video"
            return _status_html(draft_label, draft_message), _status_html(final_label, final_message)

        def on_open_review():
            return launch_review_server()

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
        open_review_btn.click(fn=on_open_review, outputs=[review_status], show_api=False)
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
