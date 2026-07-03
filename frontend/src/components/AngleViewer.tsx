import { useCallback, useEffect, useRef, useState } from "react";
import type { ViewImage } from "@shared/types";

/**
 * N앵글 스와이퍼 — 동물의 숲식 이산 회전 UI 골격.
 * views[] 가 1장이어도, Phase 4에서 6장이 와도 그대로 동작한다.
 * 좌우 화살표 / 키보드 ←→ / 터치 스와이프 지원.
 */
export default function AngleViewer({ views }: { views: ViewImage[] }) {
  const sorted = [...views].sort((a, b) => a.angle - b.angle);
  const initial = Math.max(0, sorted.findIndex((v) => v.angle === 0));
  const [idx, setIdx] = useState(initial);
  const touchX = useRef<number | null>(null);

  const step = useCallback(
    (delta: number) =>
      setIdx((i) => Math.min(sorted.length - 1, Math.max(0, i + delta))),
    [sorted.length],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") step(-1);
      if (e.key === "ArrowRight") step(1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [step]);

  if (sorted.length === 0) return null;
  const current = sorted[Math.min(idx, sorted.length - 1)];

  return (
    <div className="viewer">
      <div
        className="viewer-stage"
        onTouchStart={(e) => (touchX.current = e.touches[0].clientX)}
        onTouchEnd={(e) => {
          if (touchX.current === null) return;
          const dx = e.changedTouches[0].clientX - touchX.current;
          if (Math.abs(dx) > 40) step(dx < 0 ? 1 : -1);
          touchX.current = null;
        }}
      >
        <button
          className="arrow"
          onClick={() => step(-1)}
          disabled={idx === 0}
          aria-label="왼쪽으로 회전"
        >
          ◀
        </button>
        <img src={current.url} alt={`${current.angle}° 뷰`} />
        <button
          className="arrow"
          onClick={() => step(1)}
          disabled={idx === sorted.length - 1}
          aria-label="오른쪽으로 회전"
        >
          ▶
        </button>
      </div>
      <div className="viewer-dots">
        {sorted.map((v, i) => (
          <button
            key={v.angle}
            className={`dot ${i === idx ? "active" : ""}`}
            onClick={() => setIdx(i)}
            aria-label={`${v.angle}°`}
          >
            {v.angle}°
          </button>
        ))}
      </div>
    </div>
  );
}
