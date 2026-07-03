/**
 * TryMeOn 공유 타입 — shared/schemas.py 의 TypeScript 미러.
 * canonical 은 schemas.py. 스키마를 바꾸면 두 파일을 함께 바꿀 것.
 */

export const SCHEMA_VERSION = 1;

export type TryOnMode = "mannequin" | "user";

export type JobStatus = "queued" | "processing" | "done" | "failed";

/** 이산 회전의 한 앵글. angle 은 정면 0°, 좌 -, 우 + (도 단위). */
export interface ViewImage {
  angle: number;
  url: string;
}

/** 버전 있는 미디어 번들 — 단일 PNG가 아님. clip/asset3d 는 미래 슬롯. */
export interface TryOnResult {
  schema_version: number;
  id: string;
  status: JobStatus;
  mode: TryOnMode;
  product_id: string;
  views: ViewImage[];
  clip?: string | null;
  asset3d?: string | null;
  error?: string | null;
  meta: Record<string, unknown>;
}

export interface GarmentAssets {
  front: string;
  back?: string | null;
  side?: string | null;
}

export interface Product {
  id: string;
  name: string;
  price: number;
  description: string;
  garment: GarmentAssets;
  tags: string[];
}
