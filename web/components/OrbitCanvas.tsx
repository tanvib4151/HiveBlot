'use client';

import { useEffect, useRef } from 'react';

export default function OrbitCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = Math.min(2, window.devicePixelRatio || 1);
    let W = 0;
    let H = 0;
    let raf = 0;
    let isVisible = true;

    const resize = () => {
      const r = canvas.getBoundingClientRect();
      W = r.width;
      H = r.height;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(canvas);
    resize();

    const draw = (t: number) => {
      if (!W) resize();
      ctx.clearRect(0, 0, W, H);
      const cx = W / 2;
      const cy = H * 0.52;

      // soft center glow
      const bg = ctx.createRadialGradient(cx, cy, 0, cx, cy, 180);
      bg.addColorStop(0, 'rgba(74,214,176,.09)');
      bg.addColorStop(0.5, 'rgba(74,214,176,.04)');
      bg.addColorStop(1, 'rgba(74,214,176,0)');
      ctx.fillStyle = bg;
      ctx.beginPath();
      ctx.arc(cx, cy, 180, 0, 7);
      ctx.fill();

      const rings = [
        { R: 50, n: 28, spd: 8500, dir: 1, r: 1.15, a: 0.6 },
        { R: 92, n: 48, spd: 12000, dir: -1, r: 1.35, a: 0.4 },
        { R: 136, n: 68, spd: 16000, dir: 1, r: 1.4, a: 0.27 },
        { R: 180, n: 88, spd: 20500, dir: -1, r: 1.3, a: 0.17 },
        { R: 224, n: 108, spd: 26000, dir: 1, r: 1.15, a: 0.1 },
      ];

      rings.forEach(({ R, n, spd, dir, r, a }) => {
        const rot = (dir * t) / spd;
        for (let i = 0; i < n; i++) {
          const ang = rot + (i / n) * Math.PI * 2;
          const x = cx + Math.cos(ang) * R;
          const y = cy + Math.sin(ang) * R * 0.97;
          const accent = i % 10 === 0;
          const alpha = accent ? Math.min(1, a * 2.8) : a;
          const radius = accent ? r * 2.3 : r;
          ctx.beginPath();
          ctx.arc(x, y, radius, 0, 7);
          ctx.fillStyle = accent
            ? `rgba(143,233,207,${alpha})`
            : `rgba(74,214,176,${alpha})`;
          ctx.fill();
        }
      });

      // center label
      const monoFamily = getComputedStyle(canvas).getPropertyValue('--font-mono').trim();
      ctx.font = `500 11.5px ${monoFamily || 'monospace'}`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillStyle = 'rgba(74,214,176,.45)';
      ctx.fillText('hiveblot', cx, cy);

      if (isVisible) raf = requestAnimationFrame(draw);
    };

    const io = new IntersectionObserver(
      ([entry]) => {
        const wasVisible = isVisible;
        isVisible = entry.isIntersecting;
        if (isVisible && !wasVisible) {
          cancelAnimationFrame(raf);
          raf = requestAnimationFrame(draw);
        } else if (!isVisible) {
          cancelAnimationFrame(raf);
        }
      },
      { threshold: 0 }
    );
    io.observe(canvas);

    if (isVisible) draw(performance.now());

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      io.disconnect();
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        display: 'block',
        width: '580px',
        height: '350px',
      }}
    />
  );
}
