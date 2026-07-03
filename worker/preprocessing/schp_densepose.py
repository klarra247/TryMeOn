"""SCHP + DensePose 기반 cloth-agnostic 마스크 생성 — Phase 1 실구현 (GPU 전용).

CatVTON repo 가 SCHP/DensePose 를 로컬라이즈해 뒀으므로 그 AutoMasker 를 그대로
쓴다. AutoMasker.__call__ 은 {'mask', 'densepose', 'schp_lip', 'schp_atr'} 를
반환 → 설계 원칙 3(데이터 과수집)대로 전부 저장해 PreprocessArtifacts 를 채운다.

요구사항:
- CATVTON_REPO 환경변수 = CatVTON repo 클론 경로 (sys.path 에 추가됨)
- 체크포인트는 HF zhengchong/CatVTON 스냅샷에서 자동 다운로드
- CUDA GPU. 맥/로컬에서는 import 자체가 실패해도 되게 지연 로딩.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from PIL import Image

from shared.schemas import PreprocessArtifacts

from .base import PersonPreprocessor

log = logging.getLogger(__name__)

# CatVTON AutoMasker 의 mask_type: upper / lower / overall (+ inner/outer)
DEFAULT_CLOTH_TYPE = "upper"


class SchpDensePoseMaskGenerator(PersonPreprocessor):
    name = "schp-densepose"

    def __init__(self, device: str = "cuda"):
        self.device = device
        self._automasker = None  # 지연 로딩 — 첫 run() 에서 체크포인트 로드

    def _load(self):
        if self._automasker is not None:
            return self._automasker

        repo_dir = os.environ.get("CATVTON_REPO", "/workspace/CatVTON")
        if repo_dir not in sys.path:
            sys.path.insert(0, repo_dir)

        from huggingface_hub import snapshot_download
        from model.cloth_masker import AutoMasker  # CatVTON repo 모듈

        ckpt_root = snapshot_download(repo_id=os.environ.get("CATVTON_CKPT", "zhengchong/CatVTON"))
        self._automasker = AutoMasker(
            densepose_ckpt=os.path.join(ckpt_root, "DensePose"),
            schp_ckpt=os.path.join(ckpt_root, "SCHP"),
            device=self.device,
        )
        log.info("AutoMasker 로드 완료 (ckpt=%s)", ckpt_root)
        return self._automasker

    def run(self, person_image: Path, out_dir: Path,
            cloth_type: str = DEFAULT_CLOTH_TYPE) -> PreprocessArtifacts:
        automasker = self._load()
        out_dir.mkdir(parents=True, exist_ok=True)

        result = automasker(Image.open(person_image).convert("RGB"), cloth_type)

        paths: dict[str, str | None] = {}
        for key, fname in [("mask", f"agnostic_mask_{cloth_type}.png"),
                           ("densepose", "densepose.png"),
                           ("schp_lip", "parse_lip.png"),
                           ("schp_atr", "parse_atr.png")]:
            artifact = result.get(key)
            if artifact is None:
                paths[key] = None
                continue
            p = out_dir / fname
            artifact.save(p)
            paths[key] = str(p)

        if paths["mask"] is None:
            raise RuntimeError("AutoMasker 가 mask 를 반환하지 않음")

        return PreprocessArtifacts(
            agnostic_mask=paths["mask"],
            parse_map=paths["schp_atr"] or paths["schp_lip"],
            pose=None,  # CatVTON 경로에선 별도 포즈 추정 없음 (DensePose 로 충분)
            densepose=paths["densepose"],
        )
