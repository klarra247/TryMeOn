"""CatVTON 엔진 — Phase 1 실모델 (GPU 전용, 비상업 라이선스: docs/LICENSES.md).

TryOnEngine 구현체. EngineInput → 전처리(SCHP+DensePose 마스크) → CatVTON
추론 → 정면 1뷰 번들. backend/frontend 는 이 파일의 존재를 모른다.

요구사항:
- CATVTON_REPO 환경변수 = CatVTON repo 클론 경로
- 체크포인트 자동 다운로드 (HF: zhengchong/CatVTON + SD1.5 inpaint 베이스)
- bf16 기준 약 8GB VRAM (1024×768)

스톡 모델 최적화 (Step 5): preset_model_id 입력이면 전처리 산출물을
data/models/{id}/preprocess/ 에 한 번만 계산해 재사용한다.
"""
from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path

from PIL import Image

from shared.schemas import EngineInput, PreprocessArtifacts

from .. import presets
from ..media import resolve_media_path
from ..preprocessing.schp_densepose import SchpDensePoseMaskGenerator
from .base import EngineOutput, TryOnEngine

log = logging.getLogger(__name__)

WIDTH, HEIGHT = 768, 1024


class CatVTONEngine(TryOnEngine):
    name = "catvton"

    def __init__(self, device: str = "cuda"):
        self.device = device
        self.preprocessor = SchpDensePoseMaskGenerator(device=device)
        self._pipeline = None

    def _load(self):
        if self._pipeline is not None:
            return self._pipeline

        repo_dir = os.environ.get("CATVTON_REPO", "/workspace/CatVTON")
        if repo_dir not in sys.path:
            sys.path.insert(0, repo_dir)

        from huggingface_hub import snapshot_download
        from model.pipeline import CatVTONPipeline  # CatVTON repo 모듈
        from utils import init_weight_dtype

        ckpt_root = snapshot_download(repo_id=os.environ.get("CATVTON_CKPT", "zhengchong/CatVTON"))
        self._pipeline = CatVTONPipeline(
            base_ckpt=os.environ.get(
                "CATVTON_BASE_CKPT", "booksforcharlie/stable-diffusion-inpainting"),
            attn_ckpt=ckpt_root,
            attn_ckpt_version="mix",
            weight_dtype=init_weight_dtype(os.environ.get("CATVTON_PRECISION", "bf16")),
            use_tf32=True,
            device=self.device,
        )
        log.info("CatVTONPipeline 로드 완료")
        return self._pipeline

    def _resolve_person(self, inp: EngineInput) -> tuple[Path, Path | None]:
        """(사람 사진 경로, 전처리 캐시 디렉터리|None) — 캐시는 preset 만."""
        if inp.person_image_path:
            return Path(inp.person_image_path), None
        assert inp.preset_model_id, "person_image_path 나 preset_model_id 중 하나는 필수"
        p = presets.preset_person_image(inp.preset_model_id)
        if p is None:
            raise RuntimeError(
                f"스톡 모델 사진이 없습니다: data/models/{inp.preset_model_id}/person.png "
                "에 정면 전신 사진을 넣어주세요")
        return p, presets.preset_preprocess_dir(inp.preset_model_id)

    def _preprocess(self, person: Path, cache_dir: Path | None,
                    out_dir: Path, cloth_type: str) -> PreprocessArtifacts:
        """마스크 생성. preset 이면 캐시 디렉터리에서 재사용."""
        target = cache_dir if cache_dir is not None else out_dir / "preprocess"
        cached_mask = target / f"agnostic_mask_{cloth_type}.png"
        if cache_dir is not None and cached_mask.exists():
            return PreprocessArtifacts(
                agnostic_mask=str(cached_mask),
                parse_map=str(p) if (p := target / "parse_atr.png").exists() else None,
                densepose=str(p) if (p := target / "densepose.png").exists() else None,
            )
        return self.preprocessor.run(person, target, cloth_type=cloth_type)

    def run(self, inp: EngineInput, out_dir: Path) -> EngineOutput:
        import torch  # GPU 워커 환경에서만 존재

        repo_dir = os.environ.get("CATVTON_REPO", "/workspace/CatVTON")
        if repo_dir not in sys.path:
            sys.path.insert(0, repo_dir)
        from utils import resize_and_crop, resize_and_padding  # CatVTON repo 모듈

        cloth_type = inp.options.get("cloth_type", "upper")
        steps = int(inp.options.get("num_inference_steps", 50))
        guidance = float(inp.options.get("guidance_scale", 2.5))
        seed = int(inp.options.get("seed", 42))

        person_path, preprocess_cache = self._resolve_person(inp)
        t0 = time.monotonic()
        artifacts = self._preprocess(person_path, preprocess_cache, out_dir, cloth_type)
        t_mask = time.monotonic() - t0

        pipeline = self._load()
        person = resize_and_crop(Image.open(person_path).convert("RGB"), (WIDTH, HEIGHT))
        cloth = resize_and_padding(
            Image.open(resolve_media_path(inp.garment.front)).convert("RGB"), (WIDTH, HEIGHT))
        mask = resize_and_crop(
            Image.open(artifacts.agnostic_mask).convert("L"), (WIDTH, HEIGHT))

        t0 = time.monotonic()
        result = pipeline(
            image=person,
            condition_image=cloth,
            mask=mask,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=torch.Generator(device=self.device).manual_seed(seed),
        )[0]
        t_infer = time.monotonic() - t0

        # Phase 1 = 정면 1뷰. 번들 스키마 덕에 뷰어는 그대로 동작한다.
        view_path = out_dir / "view_0_+0.png"
        result.save(view_path)
        return EngineOutput(
            views=[(0, view_path)],
            meta={
                "engine": self.name,
                "cloth_type": cloth_type,
                "num_inference_steps": steps,
                "guidance_scale": guidance,
                "seed": seed,
                "mask_sec": round(t_mask, 2),
                "infer_sec": round(t_infer, 2),
                "preprocess": artifacts.model_dump(),  # 산출물 경로 기록 (과수집 원칙)
            },
        )
