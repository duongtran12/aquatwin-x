function KpiCard({ label, value, detail, tone = "default" }) {
  return (
    <article className={`kpi-card kpi-card--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}


export default KpiCard;

