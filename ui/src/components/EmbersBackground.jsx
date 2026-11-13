import { useEffect, useRef } from "react";

// Draws a few slow, floating ember dots on a full-screen canvas.
export default function EmbersBackground() {
  const canvasRef = useRef(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    let width, height, frameId;

    const resize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const embers = Array.from({ length: 32 }, () => ({
      x: Math.random() * width, y: Math.random() * height,
      radius: Math.random() * 1.6 + 0.4, speed: Math.random() * 0.35 + 0.1, phase: Math.random() * 6,
    }));

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      embers.forEach((e) => {
        e.y -= e.speed;
        e.phase += 0.01;
        e.x += Math.sin(e.phase) * 0.25;
        if (e.y < -5) { e.y = height + 5; e.x = Math.random() * width; }
        ctx.beginPath();
        ctx.arc(e.x, e.y, e.radius, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255, ${140 + e.radius * 30}, 70, ${0.2 + e.radius * 0.15})`;
        ctx.fill();
      });
      frameId = requestAnimationFrame(draw);
    };
    draw();

    return () => { cancelAnimationFrame(frameId); window.removeEventListener("resize", resize); };
  }, []);

  return <canvas ref={canvasRef} className="embers" aria-hidden="true" />;
}
