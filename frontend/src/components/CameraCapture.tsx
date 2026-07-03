import { useEffect, useRef, useState } from "react";

/**
 * "착용샷 보기" — 정면 전신 사진 1장 촬영 스텁.
 * getUserMedia 로 카메라 프리뷰 → 캡처. 카메라가 없거나 거부되면
 * 파일 업로드로 폴백 (개발 환경/데스크톱용).
 */
export default function CameraCapture({
  onCapture,
  onCancel,
}: {
  onCapture: (photo: Blob) => void;
  onCancel: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraOk, setCameraOk] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: 720, height: 1280 },
        });
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
        setCameraOk(true);
      } catch {
        setCameraOk(false);
      }
    })();
    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  const capture = () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")!.drawImage(video, 0, 0);
    canvas.toBlob((blob) => blob && onCapture(blob), "image/png");
  };

  return (
    <div className="camera">
      <h2>정면을 보고 전신이 나오게 서주세요</h2>
      {cameraOk !== false ? (
        <>
          <video ref={videoRef} autoPlay playsInline muted />
          <div className="camera-actions">
            <button className="btn secondary" onClick={onCancel}>취소</button>
            <button className="btn primary" onClick={capture} disabled={!cameraOk}>
              📸 촬영
            </button>
          </div>
        </>
      ) : (
        <>
          <p>카메라를 사용할 수 없어요. 사진 파일로 대신할게요.</p>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onCapture(f);
            }}
          />
          <button className="btn secondary" onClick={onCancel}>취소</button>
        </>
      )}
    </div>
  );
}
