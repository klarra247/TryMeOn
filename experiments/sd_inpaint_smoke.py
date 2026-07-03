"""Step 3 학습: 맥(MPS)에서 SD1.5 inpainting 을 diffusers 로 1회 실행.

CatVTON 의 베이스가 정확히 이 SD1.5 inpaint 계열이라, 같은 파이프라인을
직접 돌려보는 것이 곧 모델 이해다. (의류+사람 concat → inpaint 가 CatVTON 발상)

실행 (맥):
    uv sync --extra learn
    uv run python experiments/sd_inpaint_smoke.py

첫 실행은 모델 다운로드(~4GB)로 오래 걸린다. M4에서 수 분 소요.
"""
from pathlib import Path

import torch
from diffusers import StableDiffusionInpaintPipeline
from PIL import Image, ImageDraw

OUT = Path(__file__).parent / "out"
OUT.mkdir(exist_ok=True)


def pick_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def main() -> None:
    device = pick_device()
    print(f"device = {device}")

    # 입력: 회색 배경 인물풍 이미지 + 상체 영역 마스크 (VTON 마스크의 미니어처)
    base = Image.new("RGB", (512, 512), (200, 200, 205))
    d = ImageDraw.Draw(base)
    d.ellipse([216, 60, 296, 140], fill=(180, 150, 130))       # 머리
    d.polygon([(180, 150), (332, 150), (312, 400), (200, 400)], fill=(120, 120, 128))  # 몸통
    base.save(OUT / "input.png")

    mask = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mask).rectangle([170, 145, 342, 410], fill=255)  # 인페인팅 영역 = 상체
    mask.save(OUT / "mask.png")

    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        "runwayml/stable-diffusion-inpainting",
        torch_dtype=torch.float16 if device != "cpu" else torch.float32,
    ).to(device)

    result = pipe(
        prompt="a person wearing a bright red hoodie, studio photo",
        image=base,
        mask_image=mask,
        num_inference_steps=25,
    ).images[0]
    result.save(OUT / "result.png")
    print(f"saved → {OUT / 'result.png'}")
    print("관찰 포인트: 마스크 영역만 다시 그려졌다 — CatVTON 은 이 원리에 "
          "의류 참조 이미지를 concat 해서 '무엇을 입힐지'를 조건으로 준다.")


if __name__ == "__main__":
    main()
