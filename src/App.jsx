import { useEffect, useState } from "react";
import "./App.css";

function App() {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchTransactions = async () => {
    try {
      const response = await fetch("http://127.0.0.1:8000/transactions");
      const data = await response.json();

      setTransactions(data);
    } catch (error) {
      console.error("Could not connect to backend:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTransactions();
  }, []);

  const highRisk = transactions.filter(
    (transaction) => transaction.risk_level === "HIGH"
  ).length;

  const mediumRisk = transactions.filter(
    (transaction) => transaction.risk_level === "MEDIUM"
  ).length;

  const lowRisk = transactions.filter(
    (transaction) => transaction.risk_level === "LOW"
  ).length;

  return (
    <div className="dashboard">

      {/* HEADER */}
      <header className="header">
        <div>
          <h1>🛡️ SENTINEL</h1>
          <p>Real-Time Fraud Detection System</p>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          System Online
        </div>
      </header>

      {/* SUMMARY CARDS */}
      <section className="cards">

        <div className="card">
          <h3>Total Transactions</h3>
          <div className="card-number">{transactions.length}</div>
          <p>Transactions monitored</p>
        </div>

        <div className="card danger">
          <h3>High Risk</h3>
          <div className="card-number">{highRisk}</div>
          <p>Requires immediate attention</p>
        </div>

        <div className="card warning">
          <h3>Medium Risk</h3>
          <div className="card-number">{mediumRisk}</div>
          <p>Needs investigation</p>
        </div>

        <div className="card safe">
          <h3>Low Risk</h3>
          <div className="card-number">{lowRisk}</div>
          <p>Normal transactions</p>
        </div>

      </section>

      {/* TRANSACTIONS */}
      <section className="panel">

        <div className="panel-header">
          <div>
            <h2>Transaction Monitoring</h2>
            <p>Live transactions analyzed by Sentinel</p>
          </div>

          <button onClick={fetchTransactions}>
            ↻ Refresh
          </button>
        </div>

        {loading ? (
          <div className="loading">
            Loading transactions...
          </div>
        ) : transactions.length === 0 ? (
          <div className="empty">
            No transactions found.
          </div>
        ) : (
          <div className="table-container">
            <table>

              <thead>
                <tr>
                  <th>Transaction ID</th>
                  <th>User</th>
                  <th>Amount</th>
                  <th>Risk Score</th>
                  <th>Risk Level</th>
                  <th>Triggered Rules</th>
                </tr>
              </thead>

              <tbody>
                {transactions.map((transaction, index) => (
                  <tr key={index}>

                    <td>
                      <strong>{transaction.transaction_id}</strong>
                    </td>

                    <td>
                      {transaction.user_id}
                    </td>

                    <td>
                      ₹{Number(transaction.amount).toLocaleString("en-IN")}
                    </td>

                    <td>
                      <div className="score">
                        {transaction.risk_score}
                      </div>
                    </td>

                    <td>
                      <span
                        className={`risk ${transaction.risk_level?.toLowerCase()}`}
                      >
                        {transaction.risk_level}
                      </span>
                    </td>

                    <td>
               <td>
 <div className="rules">
  {transaction.rules
    .filter((rule) => rule.triggered)
    .map((rule, ruleIndex) => (
      <span className="rule-wrapper" key={ruleIndex}>
        <span className="rule">
          {rule.rule}
        </span>

        <span className="rule-reason">
          {rule.reason}
        </span>
      </span>
    ))}
</div>
</td>
                    </td>

                  </tr>
                ))}
              </tbody>

            </table>
          </div>
        )}

      </section>

      {/* FOOTER */}
      <footer>
        <p>Sentinel Fraud Detection • AI-Powered Transaction Monitoring</p>
      </footer>

    </div>
  );
}

export default App;