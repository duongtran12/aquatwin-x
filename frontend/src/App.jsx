const modules = [
  "Network Overview",
  "Failure Simulation",
  "Impact Analysis",
  "AI Recovery",
  "Before / After Comparison",
];


function App() {
  return (
    <main className="app-shell">
      <section className="hero">
        <p className="eyebrow">DIGITAL WATER NETWORK</p>
        <h1>AquaTwin-X</h1>
        <p className="description">
          Mô phỏng sự cố, phân tích tác động và đề xuất phương án phục hồi mạng
          lưới cấp nước.
        </p>
      </section>

      <section className="module-grid" aria-label="Các module dự kiến">
        {modules.map((module) => (
          <article className="module-card" key={module}>
            <span>{module}</span>
            <small>Đang phát triển</small>
          </article>
        ))}
      </section>
    </main>
  );
}


export default App;

