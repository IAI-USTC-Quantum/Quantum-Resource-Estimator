const canvas = document.getElementById("signalCanvas");
const ctx = canvas.getContext("2d");
let width = 0;
let height = 0;
let dpr = 1;
let points = [];

function resizeCanvas() {
  dpr = Math.min(window.devicePixelRatio || 1, 2);
  width = window.innerWidth;
  height = window.innerHeight;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  const cols = Math.max(9, Math.floor(width / 140));
  const rows = Math.max(6, Math.floor(height / 120));
  points = [];
  for (let y = 0; y <= rows; y += 1) {
    for (let x = 0; x <= cols; x += 1) {
      points.push({
        x: (x / cols) * width,
        y: (y / rows) * height,
        phase: Math.random() * Math.PI * 2,
      });
    }
  }
}

function draw(time) {
  ctx.clearRect(0, 0, width, height);
  ctx.lineWidth = 1;

  for (const point of points) {
    const pulse = Math.sin(time * 0.0014 + point.phase);
    const x = point.x + pulse * 12;
    const y = point.y + Math.cos(time * 0.001 + point.phase) * 10;

    ctx.beginPath();
    ctx.arc(x, y, 1.6 + Math.max(0, pulse) * 1.3, 0, Math.PI * 2);
    ctx.fillStyle = pulse > 0.62 ? "rgba(255, 209, 102, 0.52)" : "rgba(80, 227, 194, 0.24)";
    ctx.fill();

    const neighbor = points.find((candidate) => {
      const dx = candidate.x - point.x;
      const dy = candidate.y - point.y;
      return dx > 70 && dx < 180 && Math.abs(dy) < 34;
    });

    if (neighbor) {
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(
        neighbor.x + Math.sin(time * 0.0014 + neighbor.phase) * 12,
        neighbor.y + Math.cos(time * 0.001 + neighbor.phase) * 10,
      );
      ctx.strokeStyle = "rgba(247, 242, 232, 0.08)";
      ctx.stroke();
    }
  }

  requestAnimationFrame(draw);
}

document.querySelectorAll(".copy-button").forEach((button) => {
  button.addEventListener("click", async () => {
    const value = button.getAttribute("data-copy") || "";
    try {
      await navigator.clipboard.writeText(value);
      const oldText = button.textContent;
      button.textContent = "Copied";
      window.setTimeout(() => {
        button.textContent = oldText;
      }, 1200);
    } catch {
      button.textContent = "Select";
    }
  });
});

document.querySelectorAll(".tab-button").forEach((button) => {
  button.addEventListener("click", () => {
    const panelId = button.getAttribute("aria-controls");
    document.querySelectorAll(".tab-button").forEach((tab) => {
      tab.classList.remove("is-active");
      tab.setAttribute("aria-selected", "false");
    });
    document.querySelectorAll(".case-panel").forEach((panel) => {
      panel.classList.remove("is-active");
      panel.hidden = true;
    });

    button.classList.add("is-active");
    button.setAttribute("aria-selected", "true");
    const panel = document.getElementById(panelId);
    panel.hidden = false;
    panel.classList.add("is-active");
  });
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
requestAnimationFrame(draw);
