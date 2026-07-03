import type { Product, TryOnMode, TryOnResult } from "@shared/types";

export async function fetchProducts(): Promise<Product[]> {
  const res = await fetch("/api/products");
  if (!res.ok) throw new Error(`products: ${res.status}`);
  return res.json();
}

export async function createTryOn(
  productId: string,
  mode: TryOnMode,
  personImage?: Blob,
): Promise<TryOnResult> {
  const form = new FormData();
  form.append("product_id", productId);
  form.append("mode", mode);
  if (personImage) form.append("person_image", personImage, "person.png");
  const res = await fetch("/api/tryon", { method: "POST", body: form });
  if (!res.ok) throw new Error(`tryon: ${res.status}`);
  return res.json();
}

export async function getTryOn(id: string): Promise<TryOnResult> {
  const res = await fetch(`/api/tryon/${id}`);
  if (!res.ok) throw new Error(`tryon/${id}: ${res.status}`);
  return res.json();
}

/** done/failed 가 될 때까지 폴링. onUpdate 로 중간 상태(로딩 UX)를 전달. */
export async function pollTryOn(
  id: string,
  onUpdate: (r: TryOnResult) => void,
  intervalMs = 800,
  timeoutMs = 120_000,
): Promise<TryOnResult> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const r = await getTryOn(id);
    onUpdate(r);
    if (r.status === "done" || r.status === "failed") return r;
    if (Date.now() > deadline) throw new Error("tryon 폴링 타임아웃");
    await new Promise((ok) => setTimeout(ok, intervalMs));
  }
}
