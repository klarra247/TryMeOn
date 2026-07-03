import { useEffect, useState } from "react";
import type { Product, TryOnMode, TryOnResult } from "@shared/types";
import { createTryOn, fetchProducts, pollTryOn } from "./api";
import AngleViewer from "./components/AngleViewer";
import CameraCapture from "./components/CameraCapture";

/**
 * 키오스크 화면 흐름 (docs/DESIGN.md §2):
 * 상품 목록 → 선택 → 마네킹 착용(자동) → "착용샷 보기" → 촬영 → 본인 착용.
 * 결과는 항상 TryOnResult 미디어 번들이고 AngleViewer 가 N앵글을 소화한다.
 */

type Screen =
  | { name: "catalog" }
  | { name: "product"; product: Product }
  | { name: "camera"; product: Product };

export default function App() {
  const [screen, setScreen] = useState<Screen>({ name: "catalog" });
  const [products, setProducts] = useState<Product[]>([]);
  const [result, setResult] = useState<TryOnResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProducts().then(setProducts).catch((e) => setError(String(e)));
  }, []);

  const runTryOn = async (product: Product, mode: TryOnMode, photo?: Blob) => {
    setResult(null);
    setError(null);
    setScreen({ name: "product", product });
    try {
      const job = await createTryOn(product.id, mode, photo);
      setResult(job); // queued 상태 표시
      const final = await pollTryOn(job.id, setResult);
      if (final.status === "failed") setError(final.error ?? "생성 실패");
    } catch (e) {
      setError(String(e));
    }
  };

  if (screen.name === "camera") {
    return (
      <CameraCapture
        onCapture={(photo) => runTryOn(screen.product, "user", photo)}
        onCancel={() => setScreen({ name: "product", product: screen.product })}
      />
    );
  }

  if (screen.name === "product") {
    const { product } = screen;
    const loading =
      result !== null && (result.status === "queued" || result.status === "processing");
    return (
      <div className="page">
        <header>
          <button className="btn secondary" onClick={() => setScreen({ name: "catalog" })}>
            ← 목록
          </button>
          <h1>{product.name}</h1>
          <span className="price">{product.price.toLocaleString()}원</span>
        </header>

        {error && <p className="error">{error}</p>}
        {loading && (
          <div className="loading">
            <div className="spinner" />
            <p>{result?.status === "queued" ? "대기 중…" : "입혀보는 중…"}</p>
          </div>
        )}
        {result?.status === "done" && <AngleViewer views={result.views} />}

        <footer>
          <button
            className="btn secondary"
            onClick={() => runTryOn(product, "mannequin")}
            disabled={loading}
          >
            마네킹으로 보기
          </button>
          <button
            className="btn primary"
            onClick={() => setScreen({ name: "camera", product })}
            disabled={loading}
          >
            내 착용샷 보기
          </button>
        </footer>
      </div>
    );
  }

  return (
    <div className="page">
      <header>
        <h1>TryMeOn</h1>
        <span className="sub">입어보고 싶은 옷을 골라주세요</span>
      </header>
      {error && <p className="error">{error}</p>}
      <div className="grid">
        {products.map((p) => (
          <button
            key={p.id}
            className="card"
            onClick={() => runTryOn(p, "mannequin")}
          >
            <img src={p.garment.front} alt={p.name} />
            <div className="card-body">
              <strong>{p.name}</strong>
              <span>{p.price.toLocaleString()}원</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
