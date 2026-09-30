import { Navigate } from "react-router-dom";

/** @deprecated Compatibility route; the implementation lives in the capability registry. */
export function MonitoringPage() {
  return <Navigate to="/capabilities/request_status/lookup" replace />;
}
