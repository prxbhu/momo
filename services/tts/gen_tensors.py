import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("+ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Pocket TTS voice cloning wrapper")
    parser.add_argument("--input-audio", required=True, help="Reference voice audio (.wav/.mp3)")
    parser.add_argument("--voice", required=True, help="Output .safetensors file")
    parser.add_argument("--text", required=True, help="Text to synthesize")
    parser.add_argument("--output", required=True, help="Output WAV file")

    # Quality tuning
    parser.add_argument("--temperature", type=float, default=0.5)
    parser.add_argument("--lsd-decode-steps", type=int, default=5)
    parser.add_argument("--eos-threshold", type=float, default=-4.0)
    parser.add_argument("--frames-after-eos", type=int, default=None)

    # Public CLI supports device on generate; default is cpu
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"], help="Generation device")
    parser.add_argument("--config", default="b6369a24", help="Model config signature")

    args = parser.parse_args()

    input_audio = Path(args.input_audio)
    voice_path = Path(args.voice)
    output_path = Path(args.output)

    if not input_audio.exists():
        raise FileNotFoundError(f"Input audio not found: {input_audio}")

    voice_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) Export voice state to safetensors
    run([
        "pocket-tts", "export-voice",
        str(input_audio),
        str(voice_path),
        "--config", args.config,
    ])

    # 2) Generate using the exported safetensors
    generate_cmd = [
        "pocket-tts", "generate",
        "--voice", str(voice_path),
        "--text", args.text,
        "--output-path", str(output_path),
        "--temperature", str(args.temperature),
        "--lsd-decode-steps", str(args.lsd_decode_steps),
        "--eos-threshold", str(args.eos_threshold),
        "--device", args.device,
        "--config", args.config,
    ]

    if args.frames_after_eos is not None:
        generate_cmd += ["--frames-after-eos", str(args.frames_after_eos)]

    run(generate_cmd)

    print(f"\nSaved voice tensor: {voice_path}")
    print(f"Saved audio:        {output_path}")


if __name__ == "__main__":
    main()