import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";


function FitnessChart({ history }) {
  if (!history?.length) {
    return <p className="empty-state">Fitness history appears after AI Recovery finishes.</p>;
  }
  return (
    <div className="fitness-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={history} margin={{ top: 10, right: 14, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="#183946" strokeDasharray="4 4" />
          <XAxis dataKey="generation" stroke="#7696a3" fontSize={11} />
          <YAxis domain={[0, 100]} stroke="#7696a3" fontSize={11} />
          <Tooltip
            contentStyle={{ background: "#0b2632", border: "1px solid #2c5260" }}
          />
          <Line
            type="monotone"
            dataKey="best_score"
            stroke="#56dfce"
            strokeWidth={3}
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="average_score"
            stroke="#ffb95c"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}


export default FitnessChart;
