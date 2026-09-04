import { useEffect, useState } from "react";
import CaseQueue from "./CaseQueue.jsx";
import CaseDetail from "./CaseDetail.jsx";
import LiveCall from "./LiveCall.jsx";
import { getCases } from "./api.js";

export default function App() {
  const [cases, setCases] = useState([]);
  const [selectedId, setSelectedId] = useState(null);

  async function refresh() {
    const data = await getCases();
    setCases(data.cases);
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="app">
      <div className="header">
        <h1>Voice Risk Console</h1>
        <span className="meta">{cases.length} cases</span>
      </div>
      <CaseQueue cases={cases} selectedId={selectedId} onSelect={setSelectedId} />
      <div>
        <CaseDetail caseId={selectedId} onReviewed={refresh} />
        <LiveCall claimedChannel="app" onCallEnded={refresh} />
      </div>
    </div>
  );
}
