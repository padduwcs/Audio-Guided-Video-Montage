from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import stat
import subprocess
import sys
import time
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORK_ROOT = ROOT / ".kaggle_work"
DATASET_DIR = WORK_ROOT / "dataset"
KERNEL_DIR = WORK_ROOT / "kernel"
OUTPUT_DIR = WORK_ROOT / "output"
EXTRACT_DIR = WORK_ROOT / "pulled"
STATE_PATH = WORK_ROOT / "active_package.json"

DEFAULT_DATASET = "audio-guided-video-montage-input"
DEFAULT_KERNEL = "audio-guided-video-montage-runner"
DEFAULT_TRANSFER_MODE = "dataset"


class KaggleInputConfigMissingError(RuntimeError):
    """Raised when the Kaggle runner cannot resolve the generated config file."""

EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "env310",
    "env",
    ".kaggle_work",
    "__pycache__",
    ".pytest_cache",
    ".gradio",
    "tmp",
}
EXCLUDED_TOP_LEVEL_DIRS = {
    "data",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".mp4",
    ".mov",
    ".mkv",
    ".wav",
    ".mp3",
    ".m4a",
    ".npy",
    ".index",
}


def default_kaggle_username() -> str | None:
    env_username = os.environ.get("KAGGLE_USERNAME")
    if env_username:
        return env_username

    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"
    if kaggle_json.is_file():
        try:
            data = json.loads(kaggle_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        username = data.get("username")
        if username:
            return str(username)

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package, submit, wait for, and pull Kaggle pipeline jobs."
    )
    parser.add_argument(
        "command",
        choices=(
            "package",
            "push-dataset",
            "push-kernel",
            "run",
            "status",
            "logs",
            "pull",
            "submit",
        ),
    )
    parser.add_argument("--username", default=default_kaggle_username())
    parser.add_argument("--dataset", default=DEFAULT_DATASET)
    parser.add_argument("--kernel", default=DEFAULT_KERNEL)
    parser.add_argument("--project-id", default="demo_01")
    parser.add_argument("--videos", nargs="+", type=Path, default=None)
    parser.add_argument("--audio", type=Path, default=None)
    parser.add_argument("--from-stage", type=int, default=1)
    parser.add_argument("--to-stage", type=int, default=6)
    parser.add_argument(
        "--fake-embeddings",
        action="store_true",
        default=False,
        help="Use deterministic fake vectors for quick debugging instead of real CLIP embeddings.",
    )
    parser.add_argument(
        "--real-embeddings",
        action="store_false",
        dest="fake_embeddings",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--video-method", choices=("content", "fixed_window"), default="fixed_window")
    parser.add_argument("--asr-model", default="medium")
    parser.add_argument("--language", choices=("auto", "vi", "en"), default="auto")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument(
        "--transfer-mode",
        choices=("kernel", "dataset"),
        default=DEFAULT_TRANSFER_MODE,
        help="dataset uploads inputs as a Kaggle Dataset; kernel embeds small inputs into the code file.",
    )
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--pull", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--max-wait-minutes", type=int, default=360)
    parser.add_argument("--dataset-wait-seconds", type=int, default=30)
    parser.add_argument("--dataset-max-wait-minutes", type=int, default=20)
    parser.add_argument(
        "--kernel-mount-retries",
        type=int,
        default=2,
        help=(
            "Retry by pushing a new Kernel version when Kaggle starts a Kernel "
            "before mounting the generated input Dataset."
        ),
    )
    parser.add_argument("--message", default="Update Audio-Guided Video Montage job input")
    return parser.parse_args()


def rel_to_root(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def kaggle_ref(username: str, slug: str) -> str:
    if not username:
        raise ValueError(
            "Missing Kaggle username. Set KAGGLE_USERNAME, create ~/.kaggle/kaggle.json, "
            "or pass --username."
        )
    return f"{username}/{slug}"


def set_active_dirs(dataset_dir: Path, kernel_dir: Path) -> None:
    global DATASET_DIR, KERNEL_DIR
    DATASET_DIR = dataset_dir
    KERNEL_DIR = kernel_dir


def save_active_dirs(args: argparse.Namespace | None = None) -> None:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    state = {
        "dataset_dir": str(DATASET_DIR.relative_to(ROOT)),
        "kernel_dir": str(KERNEL_DIR.relative_to(ROOT)),
    }
    if args is not None:
        state["dataset"] = args.dataset
        state["kernel"] = args.kernel
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def load_active_dirs(args: argparse.Namespace | None = None) -> None:
    if not STATE_PATH.is_file():
        return
    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    dataset_dir = ROOT / state["dataset_dir"]
    kernel_dir = ROOT / state["kernel_dir"]
    if dataset_dir.is_dir() and kernel_dir.is_dir():
        set_active_dirs(dataset_dir, kernel_dir)
    if args is not None:
        if args.dataset == DEFAULT_DATASET and state.get("dataset"):
            args.dataset = state["dataset"]
        if args.kernel == DEFAULT_KERNEL and state.get("kernel"):
            args.kernel = state["kernel"]


def run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    print("+", " ".join(command), flush=True)
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUTF8", "1")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        check=False,
    )
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if check and result.returncode != 0:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")
    return result


def kaggle_command(*args: str) -> list[str]:
    script_dir = Path(sys.executable).resolve().parent
    names = ("kaggle.exe", "kaggle.cmd", "kaggle") if os.name == "nt" else ("kaggle",)
    for name in names:
        executable = script_dir / name
        if executable.is_file():
            return [str(executable), *args]

    executable = shutil.which("kaggle")
    if executable:
        return [executable, *args]

    raise RuntimeError(
        "Kaggle CLI executable was not found in the active Python environment "
        "or PATH. Activate the Conda environment, then run "
        "`python -m pip install -r requirements-terminal.txt` or recreate it "
        "from environment-terminal.yml."
    )


def output_lines(output: str) -> list[str]:
    return [line.strip() for line in output.splitlines() if line.strip()]


def kaggle_status_value(output: str) -> str:
    lines = output_lines(output)
    if not lines:
        return ""
    return lines[-1].lower()


def is_dataset_status_ready(returncode: int, output: str) -> bool:
    return returncode == 0 and kaggle_status_value(output) == "ready"


def missing_dataset_file_groups(
    files_output: str,
    required_file_groups: list[list[str]],
) -> list[str]:
    """Return required file groups that are not visible in Kaggle's file list.

    Kaggle can expose directories uploaded with --dir-mode zip either as the
    compressed archive name or as extracted paths, depending on processing
    timing and CLI/API behavior. Each group contains equivalent forms.
    """

    text = (files_output or "").lower()
    missing: list[str] = []
    for group in required_file_groups:
        normalized = [item.lower() for item in group if item]
        if normalized and not any(item in text for item in normalized):
            missing.append(" or ".join(normalized))
    return missing


def is_kaggle_auth_error(output: str) -> bool:
    text = (output or "").lower()
    return ("401" in text and "unauthorized" in text) or ("403" in text and "forbidden" in text)


def is_kaggle_unauthorized(output: str) -> bool:
    text = (output or "").lower()
    return "401" in text and "unauthorized" in text


def is_kaggle_forbidden(output: str) -> bool:
    text = (output or "").lower()
    return "403" in text and "forbidden" in text


def kaggle_permission_help(resource_ref: str) -> str:
    return (
        f"Kaggle denied access to {resource_ref} (401 Unauthorized or 403 Forbidden). "
        "This usually means the Kaggle username/API key is missing, expired, "
        "copied incorrectly, or does not belong to the account that owns the "
        "private Dataset/Kernel. In the Launcher, save the Kaggle username and "
        "API key from the same Kaggle account, then click Kiem tra. If it still "
        "fails after Kiem tra succeeds, delete the old private Dataset/Kernel "
        f"named {resource_ref} on Kaggle or pass a new --dataset/--kernel slug "
        "and submit again."
    )


def ensure_inside_workspace(path: Path) -> Path:
    candidate = path if path.is_absolute() else ROOT / path
    resolved = candidate.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"Path must stay inside repo: {path}") from exc
    return resolved


def reset_dir(path: Path) -> None:
    path = ensure_inside_workspace(path)
    if path.exists():
        def handle_remove_error(function, failed_path, _exc_info):
            os.chmod(failed_path, stat.S_IWRITE)
            function(failed_path)

        shutil.rmtree(path, onerror=handle_remove_error)
    path.mkdir(parents=True, exist_ok=True)


def ensure_dir(path: Path) -> None:
    ensure_inside_workspace(path).mkdir(parents=True, exist_ok=True)


def best_effort_unlink(path: Path) -> None:
    if not path.exists():
        return
    try:
        path.unlink()
    except OSError as exc:
        print(f"[warn] could not remove old temporary file {path}: {exc}")


def should_include_source(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    parts = relative.parts
    if not parts:
        return False
    if parts[0] in EXCLUDED_TOP_LEVEL_DIRS:
        return False
    if any(part in EXCLUDED_DIR_NAMES for part in parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return path.is_file()


def write_source_zip(target: Path) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            if should_include_source(path):
                archive.write(path, path.relative_to(ROOT))


def write_source_tree(target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for path in ROOT.rglob("*"):
        if should_include_source(path):
            relative = path.relative_to(ROOT)
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)


def encode_file(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def write_kernel_runner(dataset_videos: list[str], dataset_audio: str) -> None:
    embedded_paths = [
        ("source.zip", DATASET_DIR / "source.zip"),
        ("kaggle_job_config.json", DATASET_DIR / "kaggle_job_config.json"),
        *[(path, DATASET_DIR / path) for path in dataset_videos],
        (dataset_audio, DATASET_DIR / dataset_audio),
    ]
    embedded = {relative: encode_file(path) for relative, path in embedded_paths}
    template = (ROOT / "kaggle" / "runner.py").read_text(encoding="utf-8")
    marker = "EMBEDDED_FILES: dict[str, str] = {}"
    replacement = (
        "# Generated by scripts/kaggle_job.py. The Kaggle API uploads only the\n"
        "# code file for a script kernel, so small terminal jobs embed their\n"
        "# source archive, config, and raw media directly here.\n"
        f"EMBEDDED_FILES: dict[str, str] = {json.dumps(embedded, indent=2)}"
    )
    if marker not in template:
        raise RuntimeError("Could not find EMBEDDED_FILES marker in kaggle/runner.py")
    (KERNEL_DIR / "runner.py").write_text(
        template.replace(marker, replacement),
        encoding="utf-8",
    )


def copy_inputs(args: argparse.Namespace) -> list[str]:
    if not args.videos:
        raise ValueError("Missing --videos. Pass one or more files under data/raw.")
    if args.audio is None:
        raise ValueError("Missing --audio. Pass the voice/audio file under data/raw.")

    raw_dir = DATASET_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    dataset_video_paths: list[str] = []
    seen_names: set[str] = set()
    for video in args.videos:
        source = ensure_inside_workspace(video)
        if not source.is_file():
            raise FileNotFoundError(f"Video not found: {source}")
        if source.name in seen_names:
            raise ValueError(f"Duplicate input basename is not supported: {source.name}")
        seen_names.add(source.name)
        shutil.copy2(source, raw_dir / source.name)
        dataset_video_paths.append(f"raw/{source.name}")

    audio = ensure_inside_workspace(args.audio)
    if not audio.is_file():
        raise FileNotFoundError(f"Audio not found: {audio}")
    if audio.name in seen_names:
        raise ValueError(f"Audio basename duplicates a video basename: {audio.name}")
    shutil.copy2(audio, raw_dir / audio.name)

    keep_names = seen_names | {audio.name}
    for stale in raw_dir.iterdir():
        if stale.is_file() and stale.name not in keep_names:
            best_effort_unlink(stale)
    return dataset_video_paths


def build_package(args: argparse.Namespace) -> None:
    package_millis = int(time.time() * 1000)
    package_id = f"job_{package_millis}"
    if args.dataset == DEFAULT_DATASET:
        args.dataset = f"{DEFAULT_DATASET}-{package_millis}"
    if args.kernel == DEFAULT_KERNEL:
        args.kernel = f"{DEFAULT_KERNEL}-{package_millis}"
    set_active_dirs(
        WORK_ROOT / "packages" / package_id / "dataset",
        WORK_ROOT / "packages" / package_id / "kernel",
    )
    ensure_dir(DATASET_DIR)
    ensure_dir(KERNEL_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("[package] copying raw media")
    dataset_videos = copy_inputs(args)
    dataset_audio = f"raw/{ensure_inside_workspace(args.audio).name}"

    dataset_ref = kaggle_ref(args.username, args.dataset)
    kernel_ref = kaggle_ref(args.username, args.kernel)
    source_dir_name = f"project_source_{int(time.time() * 1000)}"
    source_dir = DATASET_DIR / source_dir_name
    write_source_tree(source_dir)

    (DATASET_DIR / "dataset-metadata.json").write_text(
        json.dumps(
            {
                "title": args.dataset.replace("-", " ").title(),
                "id": dataset_ref,
                "licenses": [{"name": "CC0-1.0"}],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (DATASET_DIR / "kaggle_job_config.json").write_text(
        json.dumps(
            {
                "project_id": args.project_id,
                "videos": dataset_videos,
                "audio": dataset_audio,
                "from_stage": args.from_stage,
                "to_stage": args.to_stage,
                "fake_embeddings": args.fake_embeddings,
                "video_method": args.video_method,
                "asr_model": args.asr_model,
                "language": args.language,
                "device": args.device,
                "compute_type": args.compute_type,
                "source_dir": source_dir_name,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    if args.transfer_mode == "kernel":
        write_kernel_runner(dataset_videos, dataset_audio)
    else:
        shutil.copy2(ROOT / "kaggle" / "runner.py", KERNEL_DIR / "runner.py")
    required_kernel_files = [
        KERNEL_DIR / "runner.py",
    ]
    missing_kernel_files = [path for path in required_kernel_files if not path.is_file()]
    if missing_kernel_files:
        missing = ", ".join(str(path) for path in missing_kernel_files)
        raise RuntimeError(f"Kernel bundle is incomplete: {missing}")

    enable_gpu = args.device == "cuda"
    (KERNEL_DIR / "kernel-metadata.json").write_text(
        json.dumps(
            {
                "id": kernel_ref,
                "title": args.kernel.replace("-", " ").title(),
                "code_file": "runner.py",
                "language": "python",
                "kernel_type": "script",
                "is_private": True,
                "enable_gpu": enable_gpu,
                "enable_internet": True,
                "machine_shape": "NvidiaTeslaT4" if enable_gpu else "",
                "dataset_sources": [dataset_ref] if args.transfer_mode == "dataset" else [],
                "competition_sources": [],
                "kernel_sources": [],
                "model_sources": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[package] dataset ref: {dataset_ref}")
    print(f"[package] kernel ref: {kernel_ref}")
    print(f"[package] transfer mode: {args.transfer_mode}")
    print(f"[package] video(s): {', '.join(dataset_videos)}")
    print(f"[package] audio: {dataset_audio}")
    print(f"[package] active package: {DATASET_DIR.parent.relative_to(ROOT)}")
    save_active_dirs(args)


def push_dataset(args: argparse.Namespace) -> None:
    if not (DATASET_DIR / "dataset-metadata.json").is_file():
        build_package(args)
    dataset_ref = kaggle_ref(args.username, args.dataset)
    create = run(
        kaggle_command("datasets", "create", "-p", str(DATASET_DIR), "--dir-mode", "zip"),
        check=False,
    )
    create_output = create.stdout.lower()
    if is_kaggle_auth_error(create.stdout):
        raise PermissionError(kaggle_permission_help(dataset_ref))
    if create.returncode == 0 and "dataset creation error" not in create_output and "already in use" not in create_output:
        return
    print("[dataset] create failed, trying dataset version update")
    version = run(
        kaggle_command(
            "datasets",
            "version",
            "-p",
            str(DATASET_DIR),
            "-m",
            args.message,
            "--dir-mode",
            "zip",
        ),
        check=False,
    )
    if is_kaggle_auth_error(version.stdout):
        raise PermissionError(kaggle_permission_help(dataset_ref))
    if version.returncode != 0:
        raise RuntimeError(f"Kaggle dataset version update failed for {dataset_ref}.")


def wait_for_dataset(args: argparse.Namespace) -> None:
    """Wait until a just-created dataset exposes the files the runner needs."""

    dataset_ref = kaggle_ref(args.username, args.dataset)
    deadline = time.time() + (args.dataset_max_wait_minutes * 60)
    config_path = DATASET_DIR / "kaggle_job_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.is_file() else {}
    source_dir = config.get("source_dir", "")
    required_file_groups = [
        ["kaggle_job_config.json"],
        [
            "raw.zip",
            *config.get("videos", []),
            config.get("audio", ""),
        ],
        [
            f"{source_dir}.zip" if source_dir else "",
            f"{source_dir}/requirements-kaggle.txt" if source_dir else "",
            f"{source_dir}/integration/run_pipeline.py" if source_dir else "",
        ],
    ]
    while True:
        status = run(kaggle_command("datasets", "status", dataset_ref), check=False)
        if is_kaggle_unauthorized(status.stdout):
            raise PermissionError(kaggle_permission_help(dataset_ref))
        status_value = kaggle_status_value(status.stdout)
        status_ready = is_dataset_status_ready(status.returncode, status.stdout)
        files = run(
            kaggle_command("datasets", "files", dataset_ref, "--page-size", "200"),
            check=False,
        )
        if is_kaggle_unauthorized(files.stdout):
            raise PermissionError(kaggle_permission_help(dataset_ref))
        if files.returncode == 0:
            missing = missing_dataset_file_groups(files.stdout, required_file_groups)
            if not missing and status_ready:
                print("[dataset] ready for kernel attachment")
                return
            if not missing:
                if is_kaggle_forbidden(status.stdout):
                    print(
                        "[dataset] files are visible, but Kaggle has not marked "
                        "the private Dataset ready for Kernel attachment yet."
                    )
                else:
                    shown_status = status_value or "unknown"
                    print(
                        "[dataset] files are visible, but Dataset status is "
                        f"{shown_status!r}; waiting for 'ready'."
                    )
                print("[dataset] waiting for Dataset to become attachable")
            else:
                print("[dataset] waiting for required files: " + ", ".join(missing))
        elif is_kaggle_forbidden(files.stdout) or is_kaggle_forbidden(status.stdout):
            print("[dataset] Kaggle has not exposed the new private Dataset yet.")
        elif status_ready:
            print("[dataset] ready, but file listing failed.")
        if status.returncode == 0 and status_value in {"error", "failed", "cancelled", "canceled"}:
            raise RuntimeError("Kaggle dataset creation/versioning failed.")
        if time.time() > deadline:
            raise TimeoutError(
                "Timed out waiting for Kaggle dataset to become attachable. "
                "Run the submit command again in a minute."
            )
        print(f"[dataset] not attachable yet; sleeping {args.dataset_wait_seconds}s")
        time.sleep(args.dataset_wait_seconds)


def push_kernel(args: argparse.Namespace) -> None:
    if not (KERNEL_DIR / "kernel-metadata.json").is_file():
        build_package(args)
    kernel_ref = kaggle_ref(args.username, args.kernel)
    deadline = time.time() + (args.dataset_max_wait_minutes * 60)
    while True:
        result = run(kaggle_command("kernels", "push", "-p", str(KERNEL_DIR)), check=False)
        output = result.stdout.lower()
        if is_kaggle_auth_error(result.stdout):
            raise PermissionError(kaggle_permission_help(kernel_ref))
        if result.returncode != 0:
            raise RuntimeError(
                f"Kernel push failed with exit code {result.returncode}. "
                "If this happens in kernel transfer mode, the code file may be too large; "
                "use --transfer-mode dataset."
            )
        if args.transfer_mode != "dataset" or "not valid dataset sources" not in output:
            return
        if time.time() > deadline:
            raise TimeoutError(
                "Kaggle still does not accept the dataset as a kernel source. "
                "Wait a minute and run submit again."
            )
        print(
            "[kernel] dataset source not attached yet; "
            f"sleeping {args.dataset_wait_seconds}s before retry"
        )
        time.sleep(args.dataset_wait_seconds)


def print_status(args: argparse.Namespace) -> str:
    result = run(kaggle_command("kernels", "status", kaggle_ref(args.username, args.kernel)))
    return result.stdout.lower()


def print_logs(args: argparse.Namespace) -> str:
    try:
        reset_dir(OUTPUT_DIR)
        run(
            kaggle_command(
                "kernels",
                "output",
                kaggle_ref(args.username, args.kernel),
                "-p",
                str(OUTPUT_DIR),
            )
        )
    except Exception as exc:
        message = (
            "Could not download kernel output for logs. "
            f"Open https://www.kaggle.com/code/{kaggle_ref(args.username, args.kernel)} "
            f"for the Kaggle run log. Details: {exc}"
        )
        print(message)
        return message

    log_path = OUTPUT_DIR / "job.log"
    if not log_path.is_file():
        runner_logs = sorted(OUTPUT_DIR.glob("*.log"))
        if runner_logs:
            output = _read_kaggle_log_file(runner_logs[0])
            print(output, end="" if output.endswith("\n") else "\n")
            return output
        message = (
            f"job.log not found in downloaded kernel output. "
            f"Open https://www.kaggle.com/code/{kaggle_ref(args.username, args.kernel)} "
            "for the Kaggle run log."
        )
        print(message)
        return message

    output = log_path.read_text(encoding="utf-8", errors="replace")
    runner_logs = sorted(path for path in OUTPUT_DIR.glob("*.log") if path.name != "job.log")
    if runner_logs:
        runner_output = _read_kaggle_log_file(runner_logs[0])
        if runner_output.strip() and runner_output.strip() not in output:
            output = output.rstrip() + "\n\n[kaggle runner log]\n" + runner_output
    print(output, end="" if output.endswith("\n") else "\n")
    return output


def _read_kaggle_log_file(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="replace")
    try:
        entries = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if not isinstance(entries, list):
        return raw
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        data = entry.get("data")
        if isinstance(data, str):
            lines.append(data.rstrip("\n"))
    return "\n".join(lines)


def wait_for_kernel(args: argparse.Namespace) -> None:
    deadline = time.time() + (args.max_wait_minutes * 60)
    while True:
        output = print_status(args)
        if "complete" in output:
            print("[wait] Kaggle kernel completed")
            return
        if any(word in output for word in ("error", "failed", "cancel")):
            print("[logs] latest Kaggle kernel logs:")
            logs = print_logs(args)
            if "Missing kaggle_job_config.json" in logs:
                raise KaggleInputConfigMissingError(
                    "Kaggle kernel could not resolve kaggle_job_config.json "
                    "inside /kaggle/input. Check the runner log for the printed "
                    "/kaggle/input tree."
                )
            raise RuntimeError("Kaggle kernel did not complete successfully.")
        if time.time() > deadline:
            raise TimeoutError("Timed out waiting for Kaggle kernel.")
        print(f"[wait] sleeping {args.poll_seconds}s")
        time.sleep(args.poll_seconds)


def push_kernel_and_optionally_wait(args: argparse.Namespace) -> None:
    attempts = max(1, args.kernel_mount_retries + 1) if args.wait else 1
    for attempt in range(1, attempts + 1):
        push_kernel(args)
        if not args.wait:
            return
        try:
            wait_for_kernel(args)
            return
        except KaggleInputConfigMissingError as exc:
            if attempt >= attempts:
                raise
            print(
                "[kernel] Kaggle runner could not resolve the generated input "
                "config. Waiting before pushing a new Kernel version "
                f"(retry {attempt}/{attempts - 1})."
            )
            print(f"[kernel] details: {exc}")
            time.sleep(args.dataset_wait_seconds)


def pull_outputs(args: argparse.Namespace, *, copy_to_data: bool = True) -> None:
    reset_dir(OUTPUT_DIR)
    command = kaggle_command("kernels", "output", kaggle_ref(args.username, args.kernel), "-p", str(OUTPUT_DIR))
    run(command)

    zip_candidates = list(OUTPUT_DIR.rglob("kaggle_outputs.zip"))
    if not zip_candidates:
        raise FileNotFoundError(f"kaggle_outputs.zip not found under {OUTPUT_DIR}")

    reset_dir(EXTRACT_DIR)
    with zipfile.ZipFile(zip_candidates[0]) as archive:
        archive.extractall(EXTRACT_DIR)

    output_data = EXTRACT_DIR / "output_data"
    if not output_data.is_dir():
        raise FileNotFoundError(f"Extracted output_data directory not found: {output_data}")

    if not copy_to_data:
        print(f"[pull] downloaded Kaggle outputs into {EXTRACT_DIR}")
        return

    local_data = ROOT / "data"
    for child in output_data.iterdir():
        target = local_data / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, target)
    print(f"[pull] copied Kaggle outputs into {local_data}")


def main() -> int:
    args = parse_args()
    try:
        if args.command not in {"package", "submit"}:
            load_active_dirs(args)
        if args.command == "package":
            build_package(args)
        elif args.command == "push-dataset":
            push_dataset(args)
        elif args.command == "push-kernel":
            push_kernel(args)
        elif args.command == "run":
            push_kernel_and_optionally_wait(args)
        elif args.command == "status":
            print_status(args)
        elif args.command == "logs":
            print_logs(args)
        elif args.command == "pull":
            if args.wait:
                wait_for_kernel(args)
            pull_outputs(args, copy_to_data=True)
        elif args.command == "submit":
            build_package(args)
            if args.transfer_mode == "dataset":
                push_dataset(args)
                wait_for_dataset(args)
            push_kernel_and_optionally_wait(args)
            if args.pull:
                pull_outputs(args, copy_to_data=True)
        else:
            raise RuntimeError(f"Unsupported command: {args.command}")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
